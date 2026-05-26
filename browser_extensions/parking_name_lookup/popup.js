const DEFAULTS = {
  apiBase: "",
  apiUsername: "",
  apiPassword: "",
  lookupUrlTemplate: "https://www.vegvesen.no/dinside/kjoretoy/finn-eier-og-kjoretoyopplysninger#/finn-eier-og-kjoretoyopplysninger?kjennemerke={plate}"
};

const settingIds = Object.keys(DEFAULTS);

function el(id) {
  return document.getElementById(id);
}

function setStatus(message) {
  el("message").textContent = message;
}

function setProgress(done, total, plate = "-") {
  el("counter").textContent = `${done}/${total}`;
  el("currentPlate").textContent = plate || "-";
}

function logLine(text, type = "") {
  const line = document.createElement("div");
  line.className = `log-line ${type}`;
  line.textContent = text;
  el("log").prepend(line);
}

function readSettings() {
  const settings = {};
  for (const id of settingIds) {
    settings[id] = el(id).value.trim();
  }
  settings.apiBase = settings.apiBase.replace(/\/+$/, "");
  return settings;
}

function validateSettings(settings) {
  if (!settings.apiBase) throw new Error("Fibaro10 URL mangler.");
  if (!settings.apiUsername || !settings.apiPassword) throw new Error("Brukernavn/passord mangler.");
  if (!settings.lookupUrlTemplate.includes("{plate}")) throw new Error("Vegvesen URL-mal må inneholde {plate}.");
}

async function saveSettings() {
  const settings = readSettings();
  validateSettings(settings);
  await chrome.storage.local.set(settings);
  setStatus("Oppsett lagret");
  logLine("Oppsett lagret.", "ok");
}

async function loadSettings() {
  const stored = await chrome.storage.local.get(DEFAULTS);
  for (const id of settingIds) {
    el(id).value = stored[id] ?? DEFAULTS[id];
  }
}

function authHeaders(settings) {
  return {
    "Content-Type": "application/json",
    "x-access-username": settings.apiUsername,
    "x-access-password": settings.apiPassword
  };
}

async function fetchBatch(settings) {
  const response = await fetch(`${settings.apiBase}/api/parkering/kjoretoy/mangler-omrade?limit=1000`, {
    headers: authHeaders(settings)
  });
  if (!response.ok) throw new Error(`Fibaro10 svarte ${response.status}`);
  const data = await response.json();
  return data.rows || [];
}

async function openUrl(url) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id) {
    await chrome.tabs.update(tab.id, { url });
    return tab.id;
  }
  const newTab = await chrome.tabs.create({ url });
  return newTab.id;
}

async function waitForTabComplete(tabId, timeoutMs = 25000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const tab = await chrome.tabs.get(tabId);
    if (tab.status === "complete") return;
    await new Promise((resolve) => setTimeout(resolve, 350));
  }
  throw new Error("Vegvesen-siden brukte for lang tid.");
}

async function extractArea(tabId) {
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId },
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
      return "";
    }
  });
  return (result || "").trim();
}

async function postArea(settings, plate, area) {
  const response = await fetch(`${settings.apiBase}/api/parkering/kjoretoy/${encodeURIComponent(plate)}/omrade`, {
    method: "POST",
    headers: authHeaders(settings),
    body: JSON.stringify({ omrade: area, source: "browser-helper" })
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Fibaro10 ${response.status}: ${text.slice(0, 160)}`);
  }
}

function setBusy(isBusy) {
  el("runAll").disabled = isBusy;
  el("saveSettings").disabled = isBusy;
  el("runAll").textContent = isBusy ? "Kjører..." : "Hent og skriv 1000";
}

async function runAll() {
  const settings = readSettings();
  validateSettings(settings);
  await chrome.storage.local.set(settings);
  setBusy(true);
  try {
    setStatus("Henter liste");
    const rows = await fetchBatch(settings);
    if (!rows.length) {
      setProgress(0, 0);
      setStatus("Ingen mangler");
      logLine("Ingen biler mangler område.", "ok");
      return;
    }

    logLine(`Starter ${rows.length} områdeoppslag.`, "ok");
    for (let index = 0; index < rows.length; index += 1) {
      const plate = rows[index].plate;
      setProgress(index, rows.length, plate);
      setStatus("Åpner Vegvesen");
      const url = settings.lookupUrlTemplate.replace("{plate}", encodeURIComponent(plate));
      const tabId = await openUrl(url);
      await waitForTabComplete(tabId);
      await new Promise((resolve) => setTimeout(resolve, 500));

      setStatus("Leser område");
      const area = await extractArea(tabId);
      if (!area) {
        logLine(`${plate}: fant ikke område`, "err");
        setProgress(index + 1, rows.length, plate);
        continue;
      }

      setStatus("Skriver Fibaro10");
      await postArea(settings, plate, area);
      logLine(`${plate}: ${area}`, "ok");
      setProgress(index + 1, rows.length, plate);
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    setStatus("Ferdig");
  } finally {
    setBusy(false);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  el("saveSettings").addEventListener("click", () => saveSettings().catch((error) => logLine(error.message, "err")));
  el("runAll").addEventListener("click", () => runAll().catch((error) => {
    setBusy(false);
    setStatus("Feil");
    logLine(error.message, "err");
  }));
});
