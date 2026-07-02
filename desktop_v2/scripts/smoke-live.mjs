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

async function smokeRoute(page, route) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: "load" });
  if (new URL(page.url()).pathname.startsWith("/auth/login")) {
    throw new Error(`${route} sendte tilbake til login`);
  }
  await page.locator("body").waitFor({ timeout: 10000 });
  await page.waitForTimeout(400);
  const bodyText = await page.locator("body").innerText({ timeout: 10000 });
  if (!bodyText.trim()) {
    throw new Error(`${route} rendret tom side`);
  }
  if (/ugyldig brukernavn|application error|internal server error|not found|404/i.test(bodyText)) {
    throw new Error(`${route} viste feilmelding`);
  }
  console.log(`Live route OK: ${route}`);
}

async function runAuthenticatedSmoke() {
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("response", (response) => {
      if (response.url().startsWith(baseUrl) && response.status() >= 500) {
        errors.push(`${response.status()} ${response.url()}`);
      }
    });

    await login(page);
    for (const route of routeList) {
      await smokeRoute(page, route.path);
    }
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
