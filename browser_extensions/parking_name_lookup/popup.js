const DEFAULTS = {
  apiBase: "",
  apiUsername: "",
  apiPassword: "",
  currentIndex: 0,
  lookupUrlTemplate: "https://www.vegvesen.no/dinside/kjoretoy/finn-eier-og-kjoretoyopplysninger#/finn-eier-og-kjoretoyopplysninger?kjennemerke={plate}"
};

const ids = Object.keys(DEFAULTS);
let stopRequested = false;
let saveTimer = null;

function el(id) {
  return document.getElementById(id);
}

function logLine(text, type = "") {
  const line = document.createElement("div");
  line.className = `log-line ${type}`;
  line.textContent = text;
  el("log").prepend(line);
}

function setStatus(message) {
  el("message").textContent = message;
  updateCurrentPlate();
}

function readSettings() {
  const settings = {};
  for (const id of ids) {
    const node = el(id);
    settings[id] = node.type === "number" ? Number(node.value || DEFAULTS[id]) : node.value.trim();
  }
  settings.apiBase = settings.apiBase.replace(/\/+$/, "");
  return settings;
}

async function saveSettings() {
  await chrome.storage.local.set(readSettings());
}

function scheduleSettingsSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    saveSettings().then(() => setStatus("Oppsett lagret")).catch((error) => logLine(error.message, "err"));
  }, 450);
}

async function loadSettings() {
  const stored = await chrome.storage.local.get(DEFAULTS);
  for (const id of ids) {
    el(id).value = stored[id] ?? DEFAULTS[id];
  }
  updateCurrentPlate();
}

function parsePlates() {
  const seen = new Set();
  return el("plates").value
    .split(/[\s,;]+/)
    .map((value) => value.replace(/[^A-Za-z0-9]/g, "").toUpperCase())
    .filter((value) => {
      if (!value || seen.has(value)) return false;
      seen.add(value);
      return true;
    });
}

function currentState() {
  const plates = parsePlates();
  const index = Math.max(0, Number(el("currentIndex").value || 0));
  return { plates, index, plate: plates[index] || "" };
}

function updateCurrentPlate() {
  const { plates, index, plate } = currentState();
  el("currentPlate").textContent = plate || "-";
  el("counter").textContent = `${Math.min(index + 1, plates.length || 0)}/${plates.length}`;
}

function authHeaders(settings) {
  return {
    "Content-Type": "application/json",
    "x-access-username": settings.apiUsername,
    "x-access-password": settings.apiPassword
  };
}

async function fetchBatch() {
  const settings = readSettings();
  if (!settings.apiBase) throw new Error("Fibaro10 URL mangler.");
  const response = await fetch(`${settings.apiBase}/api/parkering/kjoretoy/mangler-omrade?limit=1000`, {
    headers: authHeaders(settings)
  });
  if (!response.ok) throw new Error(`Fibaro10 svarte ${response.status}`);
  const data = await response.json();
  el("plates").value = (data.rows || []).map((row) => row.plate).join("\n");
  el("currentIndex").value = 0;
  await saveSettings();
  setStatus(`Hentet ${data.rows.length}`);
  logLine(`Hentet ${data.rows.length} registreringsnummer. ${data.count} mangler omrade totalt.`, "ok");
}

async function openCurrent() {
  const settings = readSettings();
  const { plate } = currentState();
  if (!plate) throw new Error("Ingen regnr valgt.");
  const template = settings.lookupUrlTemplate || DEFAULTS.lookupUrlTemplate;
  const url = template.replace("{plate}", encodeURIComponent(plate));
  await openUrl(url);
  await saveSettings();
  setStatus(`Apnet ${plate}`);
}

async function openUrl(url) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id) {
    await chrome.tabs.update(tab.id, { url });
    return tab.id;
  } else {
    const newTab = await chrome.tabs.create({ url });
    return newTab.id;
  }
}

async function postArea(plate, area, settings) {
  const response = await fetch(`${settings.apiBase}/api/parkering/kjoretoy/${encodeURIComponent(plate)}/omrade`, {
    method: "POST",
    headers: authHeaders(settings),
    body: JSON.stringify({
      omrade: area,
      source: "manual-browser-helper"
    })
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Fibaro10 ${response.status}: ${text.slice(0, 180)}`);
  }
  return response.json();
}

async function waitForTabComplete(tabId, timeoutMs = 25000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const tab = await chrome.tabs.get(tabId);
    if (tab.status === "complete") return;
    await new Promise((resolve) => setTimeout(resolve, 350));
  }
}

async function extractAreaFromActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("Fant ikke aktiv fane.");
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      const norm = (value) => (value || "").replace(/\s+/g, " ").trim();
      const labels = [...document.querySelectorAll("dt,.svv-dt")];
      for (const label of labels) {
        if (norm(label.textContent).toLowerCase() !== "område") continue;
        const container = label.closest(".svv-dl-container") || label.parentElement;
        const valueNode = container?.querySelector("dd,.svv-dd") || label.nextElementSibling;
        const text = norm(valueNode?.textContent || "");
        if (text) return text;
      }
      const bodyText = norm(document.body?.innerText || "");
      const match = bodyText.match(/Område\s+([^\n\r]+?)(?:\s+EU-kontroll|\s+Registreringsdata|$)/i);
      return match ? norm(match[1]) : "";
    }
  });
  return (result || "").trim();
}

async function readAndSaveCurrent() {
  const settings = readSettings();
  if (!settings.apiBase) throw new Error("Fibaro10 URL mangler.");
  const { plate } = currentState();
  if (!plate) throw new Error("Ingen regnr valgt.");
  const area = await extractAreaFromActiveTab();
  if (!area) throw new Error("Fant ikke omrade pa siden.");
  el("manualArea").value = area;
  await postArea(plate, area, settings);
  logLine(`${plate}: ${area}`, "ok");
  await advance(1);
  setStatus("Lagret");
}

async function autoRunList() {
  stopRequested = false;
  const settings = readSettings();
  if (!settings.apiBase) throw new Error("Fibaro10 URL mangler.");
  const state = currentState();
  const plates = state.plates.slice(state.index);
  if (!plates.length) throw new Error("Listen er tom.");
  const template = settings.lookupUrlTemplate || DEFAULTS.lookupUrlTemplate;
  for (const plate of plates) {
    if (stopRequested) {
      setStatus("Stoppet");
      return;
    }
    const indexNow = parsePlates().indexOf(plate);
    if (indexNow >= 0) {
      el("currentIndex").value = indexNow;
      updateCurrentPlate();
    }
    setStatus(`Apner ${plate}`);
    const tabId = await openUrl(template.replace("{plate}", encodeURIComponent(plate)));
    await waitForTabComplete(tabId);
    await new Promise((resolve) => setTimeout(resolve, 800));
    const area = await extractAreaFromActiveTab();
    if (!area) {
      logLine(`${plate}: fant ikke omrade`, "err");
      await advance(1);
      continue;
    }
    await postArea(plate, area, settings);
    logLine(`${plate}: ${area}`, "ok");
    await advance(1);
    await new Promise((resolve) => setTimeout(resolve, 900));
  }
  setStatus("Ferdig");
}

async function advance(delta = 1) {
  const { plates, index } = currentState();
  el("currentIndex").value = Math.min(Math.max(index + delta, 0), Math.max(plates.length - 1, 0));
  el("manualArea").value = "";
  await saveSettings();
  updateCurrentPlate();
}

async function saveAndNext() {
  const settings = readSettings();
  if (!settings.apiBase) throw new Error("Fibaro10 URL mangler.");
  const { plate } = currentState();
  const area = el("manualArea").value.trim();
  if (!plate) throw new Error("Ingen regnr valgt.");
  if (!area) throw new Error("Omrade mangler.");
  await postArea(plate, area, settings);
  logLine(`${plate}: ${area}`, "ok");
  await advance(1);
  setStatus("Lagret");
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  el("plates").addEventListener("input", updateCurrentPlate);
  el("currentIndex").addEventListener("input", updateCurrentPlate);
  for (const id of ids) {
    el(id).addEventListener("input", scheduleSettingsSave);
    el(id).addEventListener("change", scheduleSettingsSave);
  }
  el("saveSettings").addEventListener("click", () => saveSettings().then(() => logLine("Oppsett lagret.", "ok")).catch((error) => logLine(error.message, "err")));
  el("fetchBatch").addEventListener("click", () => fetchBatch().catch((error) => logLine(error.message, "err")));
  el("openCurrent").addEventListener("click", () => openCurrent().catch((error) => logLine(error.message, "err")));
  el("readAndSave").addEventListener("click", () => readAndSaveCurrent().catch((error) => logLine(error.message, "err")));
  el("autoRun").addEventListener("click", () => autoRunList().catch((error) => logLine(error.message, "err")));
  el("saveAndNext").addEventListener("click", () => saveAndNext().catch((error) => logLine(error.message, "err")));
  el("skip").addEventListener("click", () => advance(1).then(() => setStatus("Hoppet over")).catch((error) => logLine(error.message, "err")));
  el("stop").addEventListener("click", () => {
    stopRequested = true;
    setStatus("Stopper...");
  });
});
