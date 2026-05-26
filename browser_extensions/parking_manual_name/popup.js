const DEFAULTS = {
  apiBase: "",
  apiUsername: "",
  apiPassword: "",
  lookupUrlTemplate: "https://www.vegvesen.no/dinside/kjoretoy/finn-eier-og-kjoretoyopplysninger#/finn-eier-og-kjoretoyopplysninger?kjennemerke={plate}",
  plates: "",
  currentIndex: 0
};

const settingIds = ["apiBase", "apiUsername", "apiPassword", "lookupUrlTemplate"];

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
}

function parsePlates(value) {
  return (value || "")
    .split(/\n+/)
    .map((plate) => plate.replace(/[^A-Za-z0-9]/g, "").toUpperCase())
    .filter(Boolean);
}

async function getState() {
  const stored = await chrome.storage.local.get(DEFAULTS);
  const plates = parsePlates(stored.plates);
  const index = Math.max(0, Math.min(Number(stored.currentIndex || 0), Math.max(plates.length - 1, 0)));
  return { ...stored, plates, index, plate: plates[index] || "" };
}

async function setState(values) {
  await chrome.storage.local.set(values);
  await refreshStatus();
}

async function refreshStatus() {
  const state = await getState();
  el("currentPlate").textContent = state.plate || "-";
  el("counter").textContent = `${state.plates.length ? state.index + 1 : 0}/${state.plates.length}`;
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
  if (!settings.lookupUrlTemplate.includes("{plate}")) throw new Error("Oppslag URL-mal må inneholde {plate}.");
}

function authHeaders(settings) {
  return {
    "Content-Type": "application/json",
    "x-access-username": settings.apiUsername,
    "x-access-password": settings.apiPassword
  };
}

async function loadSettings() {
  const stored = await chrome.storage.local.get(DEFAULTS);
  for (const id of settingIds) {
    el(id).value = stored[id] ?? DEFAULTS[id];
  }
  await refreshStatus();
}

async function saveSettings() {
  const settings = readSettings();
  validateSettings(settings);
  await chrome.storage.local.set(settings);
  setStatus("Oppsett lagret");
  logLine("Oppsett lagret.", "ok");
}

async function fetchBatch() {
  const settings = readSettings();
  validateSettings(settings);
  await chrome.storage.local.set(settings);
  setStatus("Henter liste");
  const response = await fetch(`${settings.apiBase}/api/parkering/kjoretoy/mangler-navn?limit=500`, {
    headers: authHeaders(settings)
  });
  if (!response.ok) throw new Error(`Fibaro10 svarte ${response.status}`);
  const data = await response.json();
  const rows = data.rows || [];
  await setState({ plates: rows.map((row) => row.plate).join("\n"), currentIndex: 0 });
  el("vehicleName").value = "";
  setStatus(`Hentet ${rows.length}`);
  logLine(`Hentet ${rows.length} registreringsnummer. ${data.count} mangler navn totalt.`, "ok");
}

async function openCurrent() {
  const settings = readSettings();
  validateSettings(settings);
  const state = await getState();
  if (!state.plate) throw new Error("Ingen aktiv bil.");
  const url = settings.lookupUrlTemplate.replace("{plate}", encodeURIComponent(state.plate));
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id) {
    await chrome.tabs.update(tab.id, { url });
  } else {
    await chrome.tabs.create({ url });
  }
  setStatus(`Åpnet ${state.plate}`);
}

async function saveName() {
  const settings = readSettings();
  validateSettings(settings);
  const state = await getState();
  const name = el("vehicleName").value.trim();
  if (!state.plate) throw new Error("Ingen aktiv bil.");
  if (!name) throw new Error("Navn mangler.");
  const response = await fetch(`${settings.apiBase}/api/parkering/kjoretoy/${encodeURIComponent(state.plate)}/navn`, {
    method: "POST",
    headers: authHeaders(settings),
    body: JSON.stringify({ navn: name, source: "manual-browser-helper" })
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Fibaro10 ${response.status}: ${text.slice(0, 160)}`);
  }
  logLine(`${state.plate}: ${name}`, "ok");
  await move(1);
  setStatus("Lagret");
}

async function move(delta) {
  const state = await getState();
  const nextIndex = Math.max(0, Math.min(state.index + delta, Math.max(state.plates.length - 1, 0)));
  await setState({ currentIndex: nextIndex });
  el("vehicleName").value = "";
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  el("saveSettings").addEventListener("click", () => saveSettings().catch((error) => logLine(error.message, "err")));
  el("fetchBatch").addEventListener("click", () => fetchBatch().catch((error) => {
    setStatus("Feil");
    logLine(error.message, "err");
  }));
  el("openCurrent").addEventListener("click", () => openCurrent().catch((error) => logLine(error.message, "err")));
  el("saveName").addEventListener("click", () => saveName().catch((error) => logLine(error.message, "err")));
  el("previous").addEventListener("click", () => move(-1).catch((error) => logLine(error.message, "err")));
  el("skip").addEventListener("click", () => move(1).then(() => setStatus("Hoppet over")).catch((error) => logLine(error.message, "err")));
});
