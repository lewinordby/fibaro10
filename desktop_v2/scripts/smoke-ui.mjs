import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { smokeRoutePathsFromEnv } from "./smoke-routes.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.resolve(__dirname, "..", "dist");
const port = Number(process.env.FIBARO10_UI_SMOKE_PORT || 5196);
const baseUrl = `http://127.0.0.1:${port}`;
const routeList = smokeRoutePathsFromEnv(process.env.FIBARO10_UI_SMOKE_ROUTES);
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
  koble: "Koble",
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

const healthPayload = {
  status: "ok",
  app: {
    version: "1",
    build: "smoke",
    commit: "smoke",
    startedAt: "2026-06-10T12:00:00",
  },
  checks: { database: { status: "ok", detail: "Smoke database OK" } },
  summary: { sources: { total: 2, ok: 2, warn: 0, bad: 0, unknown: 0 } },
  sources: [
    {
      sourceNo: 1,
      jobName: "smoke_ok",
      title: "Smoke datakilde",
      label: "Smoke datakilde",
      category: "System",
      source: "Mock",
      status: "ok",
      statusText: "OK",
      detail: "Akkurat na",
      ageMinutes: 1,
      lastRunAt: "2026-06-10T11:59:00",
      lastSuccessAt: "2026-06-10T11:59:00",
      message: "Smoke OK",
    },
    {
      sourceNo: 2,
      jobName: "smoke_fresh",
      title: "Smoke fersk",
      label: "Smoke fersk",
      category: "System",
      source: "Mock",
      status: "ok",
      statusText: "OK",
      detail: "2 min siden",
      ageMinutes: 2,
      lastRunAt: "2026-06-10T11:58:00",
      lastSuccessAt: "2026-06-10T11:58:00",
      message: "Smoke fersk",
    },
  ],
  storage: ["import_job_status", "parkering", "sun2_tanning_sessions"],
};

function revenueMonthPayload() {
  const rows = Array.from({ length: 7 }, (_, index) => {
    const day = String(index + 1).padStart(2, "0");
    const sol = 900 + index * 80;
    const parking = 1400 + index * 120;
    return {
      day: `2026-06-${day}`,
      dayLabel: day,
      weekday: ["man", "tir", "ons", "tor", "fre", "lor", "son"][index],
      sol,
      solCount: 8 + index,
      parking,
      parkingCount: 20 + index,
      total: sol + parking,
      isToday: index === 6,
      isWeekend: index >= 5,
    };
  });
  const total = rows.reduce((sum, row) => sum + row.total, 0);
  const sol = rows.reduce((sum, row) => sum + row.sol, 0);
  const parking = rows.reduce((sum, row) => sum + row.parking, 0);
  return {
    summary: {
      label: "Juni 2026",
      month: "2026-06",
      previousMonth: "2026-05",
      nextMonth: "2026-07",
      currentMonth: "2026-06",
      total,
      sol,
      parking,
      solCount: rows.reduce((sum, row) => sum + row.solCount, 0),
      parkingCount: rows.reduce((sum, row) => sum + row.parkingCount, 0),
      averageDayCount: rows.length,
      averagePerDay: total / rows.length,
      maxTotal: Math.max(...rows.map((row) => row.total)),
      topDay: rows[rows.length - 1],
      todayRow: rows[rows.length - 1],
    },
    rows,
  };
}

function yearSeries(year, source, color, amountFactor = 1) {
  const points = [1, 32, 60, 91, 121, 152, 182].map((day, index) => {
    const amount = Math.round((index + 1) * 12000 * amountFactor);
    const count = (index + 1) * 45;
    return {
      day,
      date: `${year}-01-01`,
      label: `Dag ${day}`,
      amount,
      count,
      minutes: count * 12,
      cumulativeAmount: amount,
      cumulativeCount: count,
      cumulativeMinutes: count * 12,
    };
  });
  return {
    key: `${year}-${source}`,
    source,
    year,
    label: String(year),
    color,
    daysInYear: 365,
    asOfDay: points[points.length - 1].day,
    daysWithData: points.length,
    totalAmount: points[points.length - 1].cumulativeAmount,
    totalCount: points[points.length - 1].cumulativeCount,
    totalMinutes: points[points.length - 1].cumulativeMinutes,
    points,
  };
}

function yearComparisonPayload(title) {
  const selected = yearSeries(2026, "current", "#2563eb", 1);
  const comparison = yearSeries(2025, "comparison", "#64748b", 0.9);
  const comparisonFull = yearSeries(2025, "comparison-full", "#94a3b8", 1.1);
  const reference = yearSeries(2024, "reference", "#0f766e", 0.75);
  return {
    generatedAt: "2026-06-10T12:00:00",
    title,
    anchorYear: 2026,
    comparisonYear: 2025,
    navigation: {
      anchor: "2026",
      label: "2026",
      previousAnchor: "2025",
      nextAnchor: "2027",
      canPrevious: true,
      canNext: false,
      previousLabel: "2025",
      nextLabel: "2027",
    },
    axis: {
      days: 365,
      ticks: [
        { label: "Jan", day: 1 },
        { label: "Feb", day: 32 },
        { label: "Mar", day: 60 },
        { label: "Apr", day: 91 },
        { label: "Mai", day: 121 },
        { label: "Jun", day: 152 },
      ],
    },
    availableYears: [2026, 2025, 2024],
    series: [selected, comparison, comparisonFull, reference],
    selected,
    comparison,
    comparisonFull,
    delta: {
      amount: selected.totalAmount - comparison.totalAmount,
      count: selected.totalCount - comparison.totalCount,
      minutes: selected.totalMinutes - comparison.totalMinutes,
    },
    asOf: {
      selectedLabel: "Hittil i ar",
      selectedDate: "2026-06-10",
      comparisonLabel: "Til samme dag i aret",
      comparisonDate: "2025-06-10",
    },
  };
}

function statusComparisonPayload() {
  const event = (id, kind, source, left, amount) => ({
    id,
    kind,
    source,
    left,
    width: 2,
    label: id,
    title: `${kind} ${id}`,
    start: "2026-06-10T08:00:00",
    end: "2026-06-10T08:20:00",
    amount,
  });
  const lanes = [
    { key: "current-sun", source: "current", label: "Soling", periodLabel: "Valgt periode", kind: "sun", start: "2026-06-10T06:00:00", end: "2026-06-10T23:59:00", endLeft: 100, count: 2, paid: 300, events: [event("s1", "sun", "current", 20, 150), event("s2", "sun", "current", 50, 150)] },
    { key: "current-parking", source: "current", label: "Parkering", periodLabel: "Valgt periode", kind: "parking", start: "2026-06-10T06:00:00", end: "2026-06-10T23:59:00", endLeft: 100, count: 2, paid: 420, events: [event("p1", "parking", "current", 25, 200), event("p2", "parking", "current", 55, 220)] },
    { key: "comparison-sun", source: "comparison", label: "Soling", periodLabel: "Sammenligning", kind: "sun", start: "2026-06-09T06:00:00", end: "2026-06-09T23:59:00", endLeft: 100, count: 1, paid: 120, events: [event("s0", "sun", "comparison", 45, 120)] },
    { key: "comparison-parking", source: "comparison", label: "Parkering", periodLabel: "Sammenligning", kind: "parking", start: "2026-06-09T06:00:00", end: "2026-06-09T23:59:00", endLeft: 100, count: 1, paid: 180, events: [event("p0", "parking", "comparison", 40, 180)] },
  ];
  return {
    generatedAt: "2026-06-10T12:00:00",
    periodKey: "today",
    comparisonKey: "previous",
    anchor: "2026-06-10",
    title: "I dag",
    comparisonLabel: "I gar",
    navigation: {
      anchor: "2026-06-10",
      label: "10.06.2026",
      previousAnchor: "2026-06-09",
      nextAnchor: "2026-06-11",
      canPrevious: true,
      canNext: false,
      previousLabel: "09.06.2026",
      nextLabel: "11.06.2026",
    },
    axis: {
      start: "2026-06-10T06:00:00",
      end: "2026-06-11T00:00:00",
      seconds: 18 * 3600,
      ticks: [{ label: "06", left: 0 }, { label: "12", left: 33 }, { label: "18", left: 66 }, { label: "00", left: 100 }],
    },
    current: { label: "I dag", start: "2026-06-10T06:00:00", sunEnd: "2026-06-10T12:00:00", parkingEnd: "2026-06-10T12:00:00", solAsOfLabel: "til 12:00", parkingAsOfLabel: "til 12:00", sol: 300, solCount: 2, parking: 420, parkingCount: 2, total: 720 },
    comparison: { label: "I gar", start: "2026-06-09T06:00:00", sunEnd: "2026-06-09T12:00:00", parkingEnd: "2026-06-09T12:00:00", solAsOfLabel: "til 12:00", parkingAsOfLabel: "til 12:00", sol: 120, solCount: 1, parking: 180, parkingCount: 1, total: 300 },
    delta: { sol: 180, solCount: 1, parking: 240, parkingCount: 1, total: 420 },
    lanes,
    referenceComparisons: [],
  };
}

function mobileScreensPayload() {
  return {
    refreshSeconds: 60,
    screens: [
      {
        key: "status",
        title: "Status",
        subtitle: "Smoke",
        sourcePath: "/mobile/status",
        frameUrl: "/status/omsetning",
      },
    ],
  };
}

const server = http.createServer((request, response) => {
  const url = new URL(request.url || "/", baseUrl);
  if (url.pathname === "/health") return sendJson(response, healthPayload);
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
  if (url.pathname === "/api/revenue/month") return sendJson(response, revenueMonthPayload());
  if (url.pathname === "/api/status/comparison") return sendJson(response, statusComparisonPayload());
  if (url.pathname === "/api/soling/year-comparison") return sendJson(response, yearComparisonPayload("Soling arssammenligning"));
  if (url.pathname === "/api/parkering/year-comparison") return sendJson(response, yearComparisonPayload("Parkering arssammenligning"));
  if (url.pathname === "/api/omsetning/year-comparison") return sendJson(response, yearComparisonPayload("Omsetning arssammenligning"));
  if (url.pathname === "/api/mobile-preview/screens") return sendJson(response, mobileScreensPayload());
  if (url.pathname === "/api/overview") {
    return sendJson(response, {
      generatedAt: "2026-06-10T12:00:00",
      operatingWindow: { label: "Åpent", detail: "Stenger 23:00", open: true },
      cards: [],
      statusPeriods: [],
      latestItems: [],
      services: healthPayload.sources.map((source) => ({
        sourceNo: source.sourceNo,
        jobName: source.jobName,
        label: source.label,
        status: source.status,
        detail: source.detail,
        ageMinutes: source.ageMinutes,
      })),
      lightItems: [],
      fanItems: [],
    });
  }
  if (url.pathname.startsWith("/api/modules/")) return sendJson(response, modulePayload(url));
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/health")) {
    response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ detail: `Ingen smoke-mock for ${url.pathname}` }));
    return;
  }
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
  for (const text of expectedTexts || []) {
    await expectVisible(page, text);
  }
  const bodyText = await page.locator("body").innerText({ timeout: 8000 });
  if (!bodyText.trim()) {
    throw new Error(`${route} rendret tom side`);
  }
  if (/application error|internal server error|ingen smoke-mock|lading feilet|lasting feilet|not found/i.test(bodyText)) {
    throw new Error(`${route} viste feilmelding: ${bodyText.slice(0, 220)}`);
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
    page.on("response", (response) => {
      if (response.url().startsWith(baseUrl) && response.status() >= 400) {
        errors.push(`${response.status()} ${response.url()}`);
      }
    });

    await smokeRoute(page, "/admin/build", ["Smoke-test build", "Build"]);
    for (const route of routeList) {
      await smokeRoute(page, route.path);
      console.log(`UI route OK: ${route.path}`);
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
