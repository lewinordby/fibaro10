import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.resolve(__dirname, "..", "dist");
const port = Number(process.env.FIBARO10_UI_SMOKE_PORT || 5196);
const baseUrl = `http://127.0.0.1:${port}`;
const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

function sendJson(response, payload) {
  response.writeHead(200, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload));
}

async function sendStatic(request, response) {
  const url = new URL(request.url || "/", baseUrl);
  let pathname = decodeURIComponent(url.pathname);
  if (pathname === "/") pathname = "/index.html";
  let filePath = path.join(distDir, pathname);
  try {
    const stat = await fs.stat(filePath);
    if (!stat.isFile()) throw new Error("Not a file");
  } catch {
    filePath = path.join(distDir, "index.html");
  }
  const body = await fs.readFile(filePath);
  response.writeHead(200, { "content-type": mimeTypes[path.extname(filePath)] || "application/octet-stream" });
  response.end(body);
}

const buildEntry = {
  version: "1",
  build: "smoke",
  date: "10.06.2026",
  headline: "Smoke-test build",
  title: "UI smoke-test",
  description: "Mocket buildlogg for Playwright smoke-test.",
  applications: ["Desktop V2"],
  changes: ["Tester appskall, buildlogg og generisk modulside."],
  request: "smoke",
  workDuration: "0 min",
  creditsUsed: "0",
  path: "/admin/build/smoke",
  isCurrent: true,
};

const moduleResponse = {
  title: "Soling",
  subtitle: "Smoke",
  cards: [{ title: "I dag", value: "12", unit: "stk", detail: "Mock" }],
  charts: [
    {
      title: "Ukesutvikling",
      x: ["Man", "Tir"],
      series: [{ name: "Soling", type: "bar", data: [1, 2] }],
    },
  ],
  tables: [{ title: "Rader", columns: ["date", "title"], rows: [{ date: "2026-06-10", title: "Smoke row" }] }],
};

const moduleTitles = {
  admin: "Admin",
  energi: "Energi",
  lys: "Lys",
  omsetning: "Omsetning",
  parkering: "Parkering",
  renhold: "Renhold",
  soling: "Soling",
  ventilasjon: "Ventilasjon",
};

function modulePayload(url) {
  const [, , , module, view = "oversikt"] = url.pathname.split("/");
  const title = moduleTitles[module] || moduleResponse.title;
  return {
    ...moduleResponse,
    title,
    subtitle: `Smoke ${view}`,
    tables: [
      {
        title: `${title} rader`,
        columns: ["date", "title"],
        rows: [{ date: "2026-06-10", title: `${title} smoke row` }],
      },
    ],
  };
}

const server = http.createServer((request, response) => {
  const url = new URL(request.url || "/", baseUrl);
  if (url.pathname === "/api/auth/me") {
    return sendJson(response, {
      username: "smoke",
      roleLabel: "Smoke",
      isMaster: true,
      canSettings: true,
      appBuild: "smoke",
    });
  }
  if (url.pathname === "/api/admin/builds") return sendJson(response, { currentBuild: "smoke", rows: [buildEntry] });
  if (url.pathname === "/api/admin/builds/smoke") return sendJson(response, buildEntry);
  if (url.pathname === "/api/overview") {
    return sendJson(response, {
      generatedAt: "2026-06-10T12:00:00",
      operatingWindow: { label: "Åpent", detail: "Stenger 23:00", open: true },
      cards: [],
      statusPeriods: [],
      latestItems: [],
      services: [],
      lightItems: [],
      fanItems: [],
    });
  }
  if (url.pathname.startsWith("/api/modules/")) return sendJson(response, modulePayload(url));
  return sendStatic(request, response).catch((error) => {
    response.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
    response.end(String(error?.stack || error));
  });
});

function listen() {
  return new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
}

function close() {
  return new Promise((resolve) => server.close(resolve));
}

async function expectVisible(page, text) {
  await page.getByText(text, { exact: false }).first().waitFor({ timeout: 8000 });
}

async function smokeRoute(page, route, expectedTexts) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: "load" });
  for (const text of expectedTexts) {
    await expectVisible(page, text);
  }
}

async function run() {
  await fs.access(path.join(distDir, "index.html"));
  await listen();
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error" && !message.text().includes("favicon")) {
        errors.push(message.text());
      }
    });

    await smokeRoute(page, "/admin/build", ["Smoke-test build", "Build"]);

    const routes = [
      ["/status/oversikt", ["Status", "Datakilder"]],
      ["/omsetning/oversikt", ["Omsetning", "I dag", "Omsetning smoke row"]],
      ["/parkering/oversikt", ["Parkering", "I dag", "Parkering smoke row"]],
      ["/soling/oversikt", ["Soling", "I dag", "Soling smoke row"]],
      ["/energi/status", ["Energi", "I dag", "Energi smoke row"]],
      ["/ventilasjon/dagslogg", ["Ventilasjon", "I dag", "Ventilasjon smoke row"]],
      ["/lys/dagslogg", ["Lys", "I dag", "Lys smoke row"]],
      ["/renhold/oversikt", ["Renhold", "I dag", "Renhold smoke row"]],
      ["/admin/brukere", ["Admin", "I dag", "Admin smoke row"]],
    ];
    for (const [route, expectedTexts] of routes) {
      await smokeRoute(page, route, expectedTexts);
    }

    if (errors.length) {
      throw new Error(`Browser console errors:\n${errors.join("\n")}`);
    }
    console.log("UI smoke OK");
  } finally {
    await browser.close();
    await close();
  }
}

run().catch(async (error) => {
  await close().catch(() => {});
  console.error(error?.stack || error);
  process.exit(1);
});
