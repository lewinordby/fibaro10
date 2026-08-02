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
const routeBudgetMs = Number(process.env.FIBARO10_LIVE_ROUTE_BUDGET_MS || 6_000);
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

async function smokeBollardImages(page) {
  const result = await page.evaluate(async () => {
    const statusResponse = await fetch("/api/unifi-protect/bollards", { cache: "no-store" });
    if (!statusResponse.ok) {
      return { error: `/api/unifi-protect/bollards svarte HTTP ${statusResponse.status}` };
    }

    const payload = await statusResponse.json();
    const camera = payload?.camera_monitors?.[0];
    const candidates = [
      { name: "siste utsnitt", url: camera?.latest_crop_url || camera?.latest_url },
      { name: "overlegg", url: camera?.overlay_crop_url || camera?.overlay_url },
      { name: "AI-varmekart kamera", url: camera?.ai_heatmap_url },
      ...(payload?.asset_monitors || []).map((asset) => ({
        name: `AI-varmekart ${asset.asset_label || asset.asset_key || "objekt"}`,
        url: asset.ai_heatmap_url,
      })),
    ].filter((candidate) => candidate.url);

    const images = [];
    for (const candidate of candidates) {
      const response = await fetch(candidate.url, { cache: "no-store" });
      const blob = await response.blob();
      images.push({
        ...candidate,
        ok: response.ok,
        status: response.status,
        contentType: response.headers.get("content-type") || blob.type || "",
        size: blob.size,
      });
    }
    return { images };
  });

  if (result.error) throw new Error(result.error);
  if (!result.images?.length) throw new Error("Pullertsiden mangler bildeadresser");
  const invalid = result.images.filter(
    (image) => !image.ok || !image.contentType.startsWith("image/") || image.size < 1_000,
  );
  if (invalid.length) {
    throw new Error(
      `Pullertbilder feilet:\n${invalid
        .map((image) => `${image.name}: HTTP ${image.status}, ${image.contentType || "ukjent type"}, ${image.size} byte`)
        .join("\n")}`,
    );
  }
  console.log(
    `Live bollard images OK: ${result.images
      .map((image) => `${image.name} ${Math.round(image.size / 1024)} kB`)
      .join(", ")}`,
  );
}

async function waitForBollardVisualImages(page) {
  await page.waitForFunction(
    () => {
      const images = [...document.querySelectorAll(".bollard-workbench-frame img")];
      return images.length === 2 && images.every((image) => image.complete && image.naturalWidth > 0 && image.naturalHeight > 0);
    },
    undefined,
    { timeout: 20000 },
  );
}

async function smokeBollardVisualControl(page) {
  await waitForBollardVisualImages(page);
  const slider = page.getByRole("slider", { name: /gjennomsiktighet for siste bilde/i });
  await slider.waitFor({ timeout: 5000 });
  if (await slider.inputValue() !== "50") throw new Error("Live pullertvisning startet ikke gjennomsiktig p\u00e5 50 prosent");
  await page.keyboard.press("ArrowRight");
  if (await slider.inputValue() !== "55") throw new Error("Live pullertvisning reagerte ikke p\u00e5 h\u00f8yre piltast");
  await page.keyboard.press("ArrowLeft");
  if (await slider.inputValue() !== "50") throw new Error("Live pullertvisning reagerte ikke p\u00e5 venstre piltast");
  await page.getByRole("button", { name: "Side om side", exact: true }).click();
  const visualPanels = page.locator(".bollard-visual-panel");
  if (await visualPanels.count() !== 2) {
    throw new Error(`Live pullertkontroll mangler side-om-side-visning (${await visualPanels.count()} bildefelt)`);
  }
  await page.getByRole("button", { name: "Markerte forskjeller", exact: true }).click();
  await page.getByText("Pikselforskjeller markert", { exact: true }).waitFor({ timeout: 5000 });
  await page.getByRole("button", { name: "Gjennomsiktig", exact: true }).click();
  const aiButton = page.locator(".bollard-ai-summary .ant-btn");
  if (await aiButton.count() !== 1) throw new Error("Live pullertkontroll mangler AI-forklaring");
  await aiButton.click();
  await page.getByText("Slik skal AI-resultatet tolkes", { exact: true }).waitFor({ timeout: 5000 });
  await aiButton.click();
  console.log("Live bollard visual control OK");
}

async function smokeCarsRegistryFilter(page) {
  const counts = await page.evaluate(async () => {
    const response = await fetch("/api/cars/day", { cache: "no-store" });
    if (!response.ok) throw new Error(`/api/cars/day svarte HTTP ${response.status}`);
    const payload = await response.json();
    const items = payload?.items || [];
    const registered = items.filter((item) => {
      const validation = item?.registryValidation || {};
      const registryFound = validation.is_valid === true && (
        validation.local_match === true
        || ["NO", "SE", "DK"].includes(String(validation.country_code || "").toUpperCase())
      );
      return registryFound || item?.knownInProtect || Boolean(item?.vehicle);
    });
    const score90 = items.filter((item) => Number(item?.maximumUnifiScore ?? item?.averageUnifiScore) >= 90);
    const latest = items[0] || null;
    const latestImages = await Promise.all((latest?.detections || []).map(async (detection) => {
      if (!detection?.snapshotUrl) return { ok: false, status: 0, size: 0, contentType: "" };
      const imageResponse = await fetch(detection.snapshotUrl, { cache: "no-store" });
      const content = imageResponse.ok ? await imageResponse.arrayBuffer() : new ArrayBuffer(0);
      return {
        ok: imageResponse.ok,
        status: imageResponse.status,
        size: content.byteLength,
        contentType: imageResponse.headers.get("content-type") || "",
      };
    }));
    return {
      total: items.length,
      registered: registered.length,
      score90: score90.length,
      latestPlate: latest?.plate || "",
      latestImages,
    };
  });

  const invalidLatestImages = counts.latestImages.filter(
    (image) => !image.ok || !image.contentType.startsWith("image/") || image.size < 1_000,
  );
  if (counts.latestImages.length === 0 || invalidLatestImages.length > 0) {
    throw new Error(`Siste bil ${counts.latestPlate || "ukjent"} mangler gyldige bilder: ${JSON.stringify(counts.latestImages)}`);
  }
  console.log(`Live latest car images OK: ${counts.latestPlate}, ${counts.latestImages.length} bilder`);

  const checkbox = page.getByRole("checkbox", { name: /kun kjente eller registerfunnet/i });
  await checkbox.check();
  await page.waitForFunction(
    ({ registered, total }) => document.querySelector(".cars-list-card .ant-card-extra")?.textContent?.trim() === `${registered} av ${total}`,
    counts,
    { timeout: 5000 },
  );
  await checkbox.uncheck();
  await page.waitForFunction(
    ({ total }) => document.querySelector(".cars-list-card .ant-card-extra")?.textContent?.trim() === `${total} av ${total}`,
    counts,
    { timeout: 5000 },
  );
  console.log(`Live cars registry filter OK: ${counts.registered} av ${counts.total} kjente eller registerfunnet`);

  await page.locator(".cars-score-filter").click();
  await page.getByText("Minst 90", { exact: true }).last().click();
  await page.waitForFunction(
    ({ score90, total }) => document.querySelector(".cars-list-card .ant-card-extra")?.textContent?.trim() === `${score90} av ${total}`,
    counts,
    { timeout: 5000 },
  );
  await page.locator(".cars-score-filter").click();
  await page.getByText("Alle scorer", { exact: true }).last().click();
  await page.waitForFunction(
    ({ total }) => document.querySelector(".cars-list-card .ant-card-extra")?.textContent?.trim() === `${total} av ${total}`,
    counts,
    { timeout: 5000 },
  );
  console.log(`Live cars score filter OK: ${counts.score90} av ${counts.total} med høyeste score minst 90`);
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
  const latestRouteTimings = [...new Map(routeTimings.map((item) => [item.route, item])).values()];
  const slowestRoutes = latestRouteTimings.sort((left, right) => right.durationMs - left.durationMs).slice(0, 12);
  const slowestApi = [...apiTimings].sort((left, right) => right.durationMs - left.durationMs).slice(0, 12);
  console.log("Live slowest routes:");
  slowestRoutes.forEach((item) => console.log(`  ${item.durationMs} ms  ${item.route}`));
  if (slowestApi.length) {
    console.log("Live slowest API responses (server time):");
    slowestApi.forEach((item) => console.log(`  ${item.durationMs.toFixed(1)} ms  ${item.path}`));
  }
  const overBudget = latestRouteTimings.filter((item) => item.durationMs > routeBudgetMs);
  if (overBudget.length) {
    throw new Error(
      `Live smoke fant ${overBudget.length} sider over ytelsesgrensen ${routeBudgetMs} ms:\n` +
        overBudget.map((item) => `${item.route}: ${item.durationMs} ms`).join("\n"),
    );
  }
}

async function retryRoutesOverBudget(page) {
  const overBudget = routeTimings.filter((item) => item.durationMs > routeBudgetMs);
  for (const item of overBudget) {
    const route = routeList.find((candidate) => candidate.path === item.route);
    if (!route) continue;
    console.log(`Live route retry: ${item.route} etter ${item.durationMs} ms`);
    await smokeRoute(page, route.path, route.expectedTexts);
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
        if (route === "/pullerter/oversikt") await waitForBollardVisualImages(page);
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
    await smokeBollardImages(page);
    await smokeShellControls(page);
    await smokeEnergyTopologyControls(page);
    for (const route of routeList) {
      await smokeRoute(page, route.path, route.expectedTexts);
      if (route.path === "/biler/oversikt") {
        await smokeCarsRegistryFilter(page);
      }
      if (route.path === "/pullerter/oversikt") {
        await smokeBollardVisualControl(page);
      }
    }
    await retryRoutesOverBudget(page);
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
