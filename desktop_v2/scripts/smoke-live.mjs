import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { smokeRoutePathsFromEnv } from "./smoke-routes.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function unquoteEnvValue(value) {
  const trimmed = value.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function loadEnvFile(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return false;
  const content = fs.readFileSync(filePath, "utf8");
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const normalizedLine = line.startsWith("export ") ? line.slice(7).trim() : line;
    const separatorIndex = normalizedLine.indexOf("=");
    if (separatorIndex <= 0) continue;
    const key = normalizedLine.slice(0, separatorIndex).trim();
    const value = unquoteEnvValue(normalizedLine.slice(separatorIndex + 1));
    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
  return true;
}

const configuredEnvFile = process.env.FIBARO10_LIVE_ENV_FILE
  ? path.resolve(process.cwd(), process.env.FIBARO10_LIVE_ENV_FILE)
  : "";
for (const envFile of [
  configuredEnvFile,
  path.resolve(__dirname, "../../.env.live-smoke"),
  path.resolve(__dirname, "../.env.live-smoke"),
]) {
  if (loadEnvFile(envFile)) break;
}

const baseUrl = (process.env.FIBARO10_LIVE_BASE_URL || "http://192.168.20.218:8110").replace(/\/+$/, "");
const username = process.env.FIBARO10_LIVE_USERNAME || process.env.FIBARO10_SMOKE_USERNAME || "";
const password = process.env.FIBARO10_LIVE_PASSWORD || process.env.FIBARO10_SMOKE_PASSWORD || "";
const routeList = smokeRoutePathsFromEnv(process.env.FIBARO10_LIVE_SMOKE_ROUTES);
const routeBudgetMs = Number(process.env.FIBARO10_LIVE_ROUTE_BUDGET_MS || 10_000);
const visualAuditDir = process.env.FIBARO10_LIVE_VISUAL_AUDIT_DIR
  ? path.resolve(process.cwd(), process.env.FIBARO10_LIVE_VISUAL_AUDIT_DIR)
  : "";
const visualAuditRoutes = String(
  process.env.FIBARO10_LIVE_VISUAL_AUDIT_ROUTES ||
    "/status/omsetning,/parkering/parkeringer,/ventilasjon/dagslogg,/dorer/alarm",
)
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);
const routeTimings = [];
const apiTimings = [];

function timeoutSignal(milliseconds) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), milliseconds);
  return { signal: controller.signal, clear: () => clearTimeout(timeout) };
}

async function checkHealth() {
  const timeout = timeoutSignal(8000);
  try {
    const response = await fetch(`${baseUrl}/health`, { signal: timeout.signal });
    if (!response.ok) {
      throw new Error(`/health svarte HTTP ${response.status}`);
    }
    const payload = await response.json();
    console.log(`Live health OK: build ${payload?.app?.build || "ukjent"} (${payload?.status || "ukjent"})`);
  } finally {
    timeout.clear();
  }
}

async function login(page) {
  await page.goto(`${baseUrl}/auth/login`, { waitUntil: "load" });
  await page.locator('input[name="username"]').fill(username);
  await page.locator('input[name="password"]').fill(password);
  await Promise.all([
    page.waitForNavigation({ waitUntil: "load", timeout: 10000 }).catch(() => null),
    page.locator("form").evaluate((form) => form.requestSubmit()),
  ]);

  const auth = await page.evaluate(async () => {
    const response = await fetch("/api/auth/me");
    return {
      ok: response.ok,
      status: response.status,
      body: response.ok ? await response.json() : await response.text(),
    };
  });
  if (!auth.ok) {
    throw new Error(`Innlogging feilet: /api/auth/me svarte HTTP ${auth.status}`);
  }
  console.log(`Live login OK: ${auth.body?.username || "ukjent bruker"}`);
}

async function expectVisible(page, text) {
  await page.getByText(text, { exact: false }).first().waitFor({ timeout: 10000 });
}

async function smokeRoute(page, route, expectedTexts) {
  const startedAt = performance.now();
  const response = await page.goto(`${baseUrl}${route}`, { waitUntil: "load" });
  if (response && response.status() >= 400) {
    throw new Error(`${route} svarte HTTP ${response.status()}`);
  }
  if (new URL(page.url()).pathname.startsWith("/auth/login")) {
    throw new Error(`${route} sendte tilbake til login`);
  }
  await page.locator(".app-shell").waitFor({ timeout: 10000 });
  await page.waitForTimeout(50);
  await page.waitForFunction(() => !document.querySelector(".loading-block"), undefined, { timeout: 20000 });
  const bodyText = await page.locator("body").innerText({ timeout: 10000 });
  if (!bodyText.trim()) {
    throw new Error(`${route} rendret tom side`);
  }
  if (/ugyldig brukernavn|application error|internal server error/i.test(bodyText)) {
    throw new Error(`${route} viste feilmelding`);
  }
  for (const text of expectedTexts || []) {
    await expectVisible(page, text);
  }
  const durationMs = Math.round(performance.now() - startedAt);
  routeTimings.push({ route, durationMs });
  console.log(`Live route OK: ${route} (${durationMs} ms)`);
}

function printPerformanceSummary() {
  const slowestRoutes = [...routeTimings].sort((left, right) => right.durationMs - left.durationMs).slice(0, 12);
  const slowestApi = [...apiTimings].sort((left, right) => right.durationMs - left.durationMs).slice(0, 12);
  console.log("Live slowest routes:");
  slowestRoutes.forEach((item) => console.log(`  ${item.durationMs} ms  ${item.route}`));
  if (slowestApi.length) {
    console.log("Live slowest API responses (server time):");
    slowestApi.forEach((item) => console.log(`  ${item.durationMs.toFixed(1)} ms  ${item.path}`));
  }
  const overBudget = routeTimings.filter((item) => item.durationMs > routeBudgetMs);
  if (overBudget.length) {
    throw new Error(
      `Live smoke fant ${overBudget.length} sider over ytelsesgrensen ${routeBudgetMs} ms:\n` +
        overBudget.map((item) => `${item.route}: ${item.durationMs} ms`).join("\n"),
    );
  }
}

async function captureVisualAudit(page) {
  if (!visualAuditDir) return;
  fs.mkdirSync(visualAuditDir, { recursive: true });
  const viewports = [
    { name: "desktop", width: 1440, height: 900 },
    { name: "ipad", width: 1366, height: 1024 },
  ];
  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const theme of ["standard", "dark"]) {
      await page.evaluate((nextTheme) => window.localStorage.setItem("fibaro10:screenTheme", nextTheme), theme);
      for (const route of visualAuditRoutes) {
        await page.goto(`${baseUrl}${route}`, { waitUntil: "load" });
        await page.locator(".app-shell").waitFor({ timeout: 10000 });
        await page.waitForTimeout(50);
        await page.waitForFunction(() => !document.querySelector(".loading-block"), undefined, { timeout: 20000 });
        const routeName = route.replace(/^\/+/, "").replaceAll("/", "-") || "home";
        await page.screenshot({
          path: path.join(visualAuditDir, `${viewport.name}-${theme}-${routeName}.png`),
          fullPage: true,
        });
      }
    }
  }
  console.log(`Live visual audit saved: ${visualAuditDir}`);
}

async function waitForPath(page, pathname) {
  await page.waitForFunction((expectedPath) => window.location.pathname === expectedPath, pathname, { timeout: 10000 });
}

async function shellHasClass(page, className) {
  return page.locator(".app-shell").evaluate((element, name) => element.classList.contains(name), className);
}

async function waitForShellClass(page, className, expected) {
  await page.waitForFunction(
    ({ name, expectedValue }) => document.querySelector(".app-shell")?.classList.contains(name) === expectedValue,
    { name: className, expectedValue: expected },
    { timeout: 10000 },
  );
}

async function smokeShellControls(page) {
  await page.goto(`${baseUrl}/status/omsetning`, { waitUntil: "load" });
  await page.locator(".app-shell").waitFor({ timeout: 10000 });

  if (await shellHasClass(page, "main-menu-hidden")) {
    await page.getByRole("button", { name: /vis hovedmeny/i }).click();
    await waitForShellClass(page, "main-menu-hidden", false);
  }
  await page.getByRole("button", { name: /skjul hovedmeny/i }).click();
  await waitForShellClass(page, "main-menu-hidden", true);
  await page.getByRole("button", { name: /vis hovedmeny/i }).click();
  await waitForShellClass(page, "main-menu-hidden", false);

  const initiallyDark = await shellHasClass(page, "theme-dark");
  await page.getByRole("button", { name: initiallyDark ? /bruk standard tema/i : /bruk mørkt tema/i }).click();
  await waitForShellClass(page, initiallyDark ? "theme-standard" : "theme-dark", true);
  await page.getByRole("button", { name: initiallyDark ? /bruk mørkt tema/i : /bruk standard tema/i }).click();
  await waitForShellClass(page, initiallyDark ? "theme-dark" : "theme-standard", true);

  await page.getByLabel("Åpne buildlogg").click();
  await waitForPath(page, "/admin/build");

  await page.getByLabel("Gå til dashboard").click();
  await waitForPath(page, "/status/omsetning");
  await page.locator(".top-view-switcher").getByText("Parkering", { exact: true }).click();
  await waitForPath(page, "/status/parkering");
  await page.locator(".top-view-switcher").getByText("Omsetning", { exact: true }).click();
  await waitForPath(page, "/status/omsetning");

  console.log("Live shell controls OK");
}

async function smokeEnergyTopologyControls(page) {
  await page.goto(`${baseUrl}/energi/kurs-last`, { waitUntil: "load" });
  await expectVisible(page, "Kurs, enheter og laster");
  await page.locator(".energy-course-card").first().waitFor({ timeout: 10000 });

  await page.getByRole("button", { name: "Lukk alle", exact: true }).click();
  await page.waitForTimeout(150);
  if (await page.getByRole("button", { name: "Skjul kursdetaljer", exact: true }).count()) {
    throw new Error("Energi/Kurs-last åpnet kursene igjen etter Lukk alle");
  }

  await page.getByRole("button", { name: "Åpne alle", exact: true }).click();
  await page.getByRole("button", { name: "Skjul kursdetaljer", exact: true }).first().waitFor({ timeout: 5000 });
  const allCount = await page.locator(".energy-course-card").count();
  const search = page.getByRole("textbox", { name: "Søk etter kurs, enhet eller last", exact: true });
  await search.fill("Varmepumpe");
  await page.waitForTimeout(150);
  const searchCount = await page.locator(".energy-course-card").count();
  if (searchCount < 1 || searchCount >= allCount) {
    throw new Error(`Energi/Kurs-last søk filtrerte uventet (${searchCount} av ${allCount})`);
  }
  await search.fill("");
  console.log("Live energy topology controls OK");
}

async function runAuthenticatedSmoke() {
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("response", (response) => {
      const url = response.url();
      if (url.startsWith(baseUrl) && response.status() >= 400 && !url.endsWith("/favicon.ico")) {
        errors.push(`${response.status()} ${response.url()}`);
      }
      if (url.startsWith(baseUrl) && new URL(url).pathname.startsWith("/api/")) {
        void response.headerValue("x-response-time").then((value) => {
          const durationMs = Number.parseFloat(value || "");
          if (Number.isFinite(durationMs)) apiTimings.push({ path: new URL(url).pathname, durationMs });
        });
      }
    });

    await login(page);
    await smokeShellControls(page);
    await smokeEnergyTopologyControls(page);
    for (const route of routeList) {
      await smokeRoute(page, route.path, route.expectedTexts);
    }
    printPerformanceSummary();
    await captureVisualAudit(page);
    if (errors.length) {
      throw new Error(`Live smoke fant browser/API-feil:\n${errors.join("\n")}`);
    }
    console.log("Live UI smoke OK");
  } finally {
    await browser.close();
  }
}

async function run() {
  await checkHealth();
  if (!username || !password) {
    console.log("Live UI smoke hoppet over innloggede sider: sett FIBARO10_LIVE_USERNAME og FIBARO10_LIVE_PASSWORD.");
    return;
  }
  await runAuthenticatedSmoke();
}

run().catch((error) => {
  console.error(error?.stack || error);
  process.exit(1);
});
