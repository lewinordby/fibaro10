const DEFAULTS = {
  apiBase: "",
  apiUsername: "",
  apiPassword: "",
  currentIndex: 0,
  lookupUrlTemplate: "https://www.vegvesen.no/dinside/kjoretoy/finn-eier-og-kjoretoyopplysninger#/finn-eier-og-kjoretoyopplysninger?kjennemerke={plate}"
};

const ids = Object.keys(DEFAULTS);

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
  const response = await fetch(`${settings.apiBase}/api/parkering/kjoretoy/mangler-navn?limit=100`, {
    headers: authHeaders(settings)
  });
  if (!response.ok) throw new Error(`Fibaro10 svarte ${response.status}`);
  const data = await response.json();
  el("plates").value = (data.rows || []).map((row) => row.plate).join("\n");
  el("currentIndex").value = 0;
  await saveSettings();
  setStatus(`Hentet ${data.rows.length}`);
  logLine(`Hentet ${data.rows.length} registreringsnummer. ${data.count} mangler navn totalt.`, "ok");
}

async function openCurrent() {
  const settings = readSettings();
  const { plate } = currentState();
  if (!plate) throw new Error("Ingen regnr valgt.");
  const template = settings.lookupUrlTemplate || DEFAULTS.lookupUrlTemplate;
  const url = template.replace("{plate}", encodeURIComponent(plate));
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id) {
    await chrome.tabs.update(tab.id, { url });
  } else {
    await chrome.tabs.create({ url });
  }
  await saveSettings();
  setStatus(`Apnet ${plate}`);
}

async function postName(plate, name, settings) {
  const response = await fetch(`${settings.apiBase}/api/parkering/kjoretoy/${encodeURIComponent(plate)}/navn`, {
    method: "POST",
    headers: authHeaders(settings),
    body: JSON.stringify({
      navn: name,
      source: "manual-browser-helper"
    })
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Fibaro10 ${response.status}: ${text.slice(0, 180)}`);
  }
  return response.json();
}

async function advance(delta = 1) {
  const { plates, index } = currentState();
  el("currentIndex").value = Math.min(Math.max(index + delta, 0), Math.max(plates.length - 1, 0));
  el("manualName").value = "";
  await saveSettings();
  updateCurrentPlate();
}

async function saveAndNext() {
  const settings = readSettings();
  if (!settings.apiBase) throw new Error("Fibaro10 URL mangler.");
  const { plate } = currentState();
  const name = el("manualName").value.trim();
  if (!plate) throw new Error("Ingen regnr valgt.");
  if (!name) throw new Error("Navn mangler.");
  await postName(plate, name, settings);
  logLine(`${plate}: ${name}`, "ok");
  await advance(1);
  setStatus("Lagret");
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  el("plates").addEventListener("input", updateCurrentPlate);
  el("currentIndex").addEventListener("input", updateCurrentPlate);
  el("saveSettings").addEventListener("click", () => saveSettings().then(() => logLine("Oppsett lagret.", "ok")).catch((error) => logLine(error.message, "err")));
  el("fetchBatch").addEventListener("click", () => fetchBatch().catch((error) => logLine(error.message, "err")));
  el("openCurrent").addEventListener("click", () => openCurrent().catch((error) => logLine(error.message, "err")));
  el("saveAndNext").addEventListener("click", () => saveAndNext().catch((error) => logLine(error.message, "err")));
  el("skip").addEventListener("click", () => advance(1).then(() => setStatus("Hoppet over")).catch((error) => logLine(error.message, "err")));
});
