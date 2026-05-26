const DEFAULTS = {
  apiBase: "",
  apiUsername: "",
  apiPassword: "",
  searchInputSelector: "",
  searchButtonSelector: "",
  resultSelector: "",
  resultRegex: "",
  resultWaitMs: 2500,
  betweenDelayMs: 1500
};

const ids = Object.keys(DEFAULTS);
let stopRequested = false;

function el(id) {
  return document.getElementById(id);
}

function logLine(text, type = "") {
  const line = document.createElement("div");
  line.className = `log-line ${type}`;
  line.textContent = text;
  el("log").prepend(line);
}

function setStatus(message, done = null, total = null) {
  el("message").textContent = message;
  if (done !== null && total !== null) {
    el("counter").textContent = `${done}/${total}`;
  }
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
  logLine("Oppsett lagret.", "ok");
}

async function loadSettings() {
  const stored = await chrome.storage.local.get(DEFAULTS);
  for (const id of ids) {
    el(id).value = stored[id] ?? DEFAULTS[id];
  }
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
  logLine(`Hentet ${data.rows.length} registreringsnummer. ${data.count} mangler navn totalt.`, "ok");
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("Fant ikke aktiv fane.");
  return tab;
}

async function runLookupInTab(tabId, plate, settings) {
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId },
    args: [plate, settings],
    func: async (plateValue, config) => {
      const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const find = (selector) => selector ? document.querySelector(selector) : null;
      const waitFor = async (selector, timeoutMs) => {
        const started = Date.now();
        while (Date.now() - started < timeoutMs) {
          const node = find(selector);
          const text = node ? (node.value || node.innerText || node.textContent || "").trim() : "";
          if (text) return { node, text };
          await wait(200);
        }
        throw new Error(`Fant ikke resultat: ${selector}`);
      };

      const input = find(config.searchInputSelector);
      if (!input) throw new Error(`Fant ikke sokefelt: ${config.searchInputSelector}`);
      input.focus();
      input.value = "";
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.value = plateValue;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));

      const button = find(config.searchButtonSelector);
      if (button) {
        button.click();
      } else {
        input.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Enter", code: "Enter" }));
        input.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key: "Enter", code: "Enter" }));
      }

      await wait(Number(config.resultWaitMs || 2500));
      const found = await waitFor(config.resultSelector, 12000);
      let name = found.text.replace(/\s+/g, " ").trim();
      if (config.resultRegex) {
        const match = name.match(new RegExp(config.resultRegex, "i"));
        name = match ? (match[1] || match[0]).trim() : "";
      }
      if (!name) throw new Error("Resultatet ble tomt.");
      return { plate: plateValue, name, rawText: found.text };
    }
  });
  return result;
}

async function postName(plate, name, rawText, settings) {
  const response = await fetch(`${settings.apiBase}/api/parkering/kjoretoy/${encodeURIComponent(plate)}/navn`, {
    method: "POST",
    headers: authHeaders(settings),
    body: JSON.stringify({
      navn: name,
      source: "browser-extension",
      raw: { text: rawText }
    })
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Fibaro10 ${response.status}: ${text.slice(0, 180)}`);
  }
  return response.json();
}

async function runQueue(onlyFirst = false) {
  stopRequested = false;
  await saveSettings();
  const settings = readSettings();
  const plates = parsePlates();
  if (!plates.length) throw new Error("Listen er tom.");
  if (!settings.searchInputSelector || !settings.resultSelector) {
    throw new Error("Sokefelt selector og resultat selector ma fylles ut.");
  }
  const tab = await activeTab();
  const selected = onlyFirst ? plates.slice(0, 1) : plates;
  let done = 0;
  setStatus("Kjorer...", 0, selected.length);
  for (const plate of selected) {
    if (stopRequested) break;
    try {
      const result = await runLookupInTab(tab.id, plate, settings);
      await postName(result.plate, result.name, result.rawText, settings);
      done += 1;
      setStatus("Kjorer...", done, selected.length);
      logLine(`${plate}: ${result.name}`, "ok");
    } catch (error) {
      done += 1;
      setStatus("Kjorer...", done, selected.length);
      logLine(`${plate}: ${error.message}`, "err");
    }
    await new Promise((resolve) => setTimeout(resolve, Number(settings.betweenDelayMs || 0)));
  }
  setStatus(stopRequested ? "Stoppet" : "Ferdig", done, selected.length);
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  el("saveSettings").addEventListener("click", () => saveSettings().catch((error) => logLine(error.message, "err")));
  el("fetchBatch").addEventListener("click", () => fetchBatch().catch((error) => logLine(error.message, "err")));
  el("start").addEventListener("click", () => runQueue(false).catch((error) => {
    setStatus("Feil");
    logLine(error.message, "err");
  }));
  el("testOne").addEventListener("click", () => runQueue(true).catch((error) => {
    setStatus("Feil");
    logLine(error.message, "err");
  }));
  el("stop").addEventListener("click", () => {
    stopRequested = true;
    setStatus("Stopper...");
  });
});
