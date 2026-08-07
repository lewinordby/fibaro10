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
const screenshotRoute = String(process.env.FIBARO10_UI_SMOKE_SCREENSHOT_ROUTE || "").trim();
const screenshotPath = String(process.env.FIBARO10_UI_SMOKE_SCREENSHOT_PATH || "").trim();
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

function sendSmokeCameraImage(response) {
  const body = Buffer.from(
    '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360"><rect width="640" height="360" fill="#172033"/><rect x="285" y="95" width="42" height="210" rx="18" fill="#9aa8b8"/><text x="24" y="42" fill="#dbe5ef" font-family="sans-serif" font-size="22">Pullert smoke</text></svg>',
  );
  response.writeHead(200, { "content-type": "image/svg+xml", "cache-control": "no-store" });
  response.end(body);
}

function sendSmokeRecognitionImage(response) {
  const body = Buffer.from(
    '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360"><rect width="640" height="360" fill="#263443"/><path d="M110 230h420l-42-82H212l-60 82" fill="#708298"/><circle cx="205" cy="246" r="42" fill="#131b26"/><circle cx="450" cy="246" r="42" fill="#131b26"/><rect x="284" y="194" width="108" height="35" rx="3" fill="#eef3f7"/><text x="297" y="219" fill="#16202b" font-family="sans-serif" font-size="24" font-weight="700">AB12345</text><text x="20" y="35" fill="#dbe5ef" font-family="sans-serif" font-size="18">UniFi registreringsbilde</text></svg>',
  );
  response.writeHead(200, { "content-type": "image/svg+xml", "cache-control": "private, max-age=3600" });
  response.end(body);
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

const manualPayload = {
  build: "smoke",
  title: "Lilletorget drift",
  description: "Smoke-manual for rutesjekk.",
  chapters: [
    { id: "hva-losningen-er", number: "01", title: "Hva løsningen er", paragraphs: ["Smoke-oversikt over løsningen."] },
    { id: "daglig-bruk", number: "02", title: "Daglig bruk", paragraphs: ["Smoke for daglig bruk."] },
    { id: "menyvalg", number: "03", title: "Menyvalg", paragraphs: ["Smoke for menyvalg."] },
    { id: "okonomi", number: "04", title: "Økonomi", paragraphs: ["Smoke for økonomi."] },
    { id: "bygg-drift", number: "05", title: "Bygg og drift", paragraphs: ["Smoke for bygg og drift."] },
    { id: "system-underapper", number: "06", title: "System og underapper", paragraphs: ["Smoke for system."] },
    { id: "datagrunnlag", number: "07", title: "Datagrunnlag", paragraphs: ["Smoke for datagrunnlag."] },
    { id: "hc3-energi", number: "08", title: "HC3 energioppsamlinger", paragraphs: ["Smoke for HC3 energi."] },
    { id: "rutiner", number: "09", title: "Rutiner og kontroll", paragraphs: ["Smoke for rutiner."] },
    { id: "feilsoking", number: "09", title: "Feilsøking", paragraphs: ["Smoke for feilsøking."] },
  ],
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
  const tables = module === "omsetning" && view === "oversikt"
    ? ["Topp dager omsetning", "Topp uker omsetning", "Topp m\u00e5neder omsetning"].map((tableTitle) => ({
        title: tableTitle,
        columns: ["period_label", "total_paid", "parking_paid", "parking_count", "sun_paid", "sun_count"],
        rows: [{
          period_label: tableTitle.includes("uker") ? "Uke 23, 2026 (01.06-07.06.2026)" : "Smoke periode",
          total_paid: 3200,
          parking_paid: 1800,
          parking_count: 20,
          sun_paid: 1400,
          sun_count: 8,
        }],
      }))
    : [
        {
          title: `${title} rader`,
          columns: ["date", "title"],
          rows: [{ date: "2026-06-10", title: `${title} smoke row` }],
        },
      ];
  return {
    ...moduleResponse,
    title,
    subtitle: `Smoke ${view}`,
    tables,
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

function statusPeriodsPayload() {
  const definitions = [
    { key: "today", title: "I dag", scale: 1, previous: "I g\u00e5r", extra: "Samme ukedag forrige uke", full: "Hele g\u00e5rsdagen" },
    { key: "week", title: "Denne uke", scale: 8, previous: "Forrige uke", extra: "Samme uke 2025", full: "Hele forrige uke" },
    { key: "month", title: "Denne m\u00e5ned", scale: 24, previous: "Forrige m\u00e5ned", extra: "Samme m\u00e5ned 2025", full: "Hele forrige m\u00e5ned" },
    { key: "year", title: "Dette \u00e5r", scale: 620, previous: "2025", extra: "2024", full: "Hele 2025" },
  ];
  return definitions.map(({ key, title, scale, previous, extra, full }, index) => {
    const sol = 1850 * scale;
    const parking = 5350 * scale;
    const previousSol = Math.round(sol * 0.92);
    const previousParking = Math.round(parking * 0.86);
    const extraSol = Math.round(sol * 0.89);
    const extraParking = Math.round(parking * 0.8);
    return {
      key,
      title,
      sol,
      solCount: 10 * scale,
      parking,
      parkingCount: 62 * scale,
      total: sol + parking,
      rank: key === "today" ? { rank: 5, label: "5. beste", basis: "Historiske dager", totalDays: 200 } : null,
      previousSol,
      previousSolCount: 9 * scale,
      previousParking,
      previousParkingCount: 58 * scale,
      previousTotal: previousSol + previousParking,
      previousLabel: previous,
      previousFullLabel: full,
      previousFullSol: Math.round(sol * (1.7 + index * 0.08)),
      previousFullSolCount: 17 * scale,
      previousFullParking: Math.round(parking * (1.65 + index * 0.08)),
      previousFullParkingCount: 96 * scale,
      previousFullTotal: Math.round((sol + parking) * (1.66 + index * 0.08)),
      solAsOfLabel: "kl 12:32",
      parkingAsOfLabel: "kl 12:00",
      previousSolAsOfLabel: "kl 12:32",
      previousParkingAsOfLabel: "kl 12:00",
      extraComparisons: [
        {
          label: extra,
          sol: extraSol,
          solCount: 8 * scale,
          parking: extraParking,
          parkingCount: 52 * scale,
          total: extraSol + extraParking,
          solAsOfLabel: "kl 12:32",
          parkingAsOfLabel: "kl 12:00",
          fullLabel: `Hele ${extra.toLowerCase()}`,
          fullSol: Math.round(sol * (1.5 + index * 0.08)),
          fullSolCount: 15 * scale,
          fullParking: Math.round(parking * (1.48 + index * 0.08)),
          fullParkingCount: 86 * scale,
          fullTotal: Math.round((sol + parking) * (1.49 + index * 0.08)),
        },
      ],
    };
  });
}

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

function parkingTimeDistributionPayload() {
  const weekdays = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"].map((weekday, weekdayIndex) => {
    const hours = Array.from({ length: 24 }, (_, hour) => {
      const active = hour >= 8 && hour <= 20;
      const sessions = active ? Math.max(0, Math.round(((weekdayIndex + 1) * ((hour % 5) + 1)) / 2)) : 0;
      const paid = sessions * (62 + weekdayIndex * 7);
      const minutes = sessions * (30 + (hour % 4) * 10);
      return {
        weekdayIndex,
        weekday,
        hour,
        hourLabel: `${String(hour).padStart(2, "0")}:00`,
        sessions,
        paid,
        minutes,
        hours: minutes / 60,
        avgPaidPerSession: sessions ? paid / sessions : 0,
        avgMinutesPerSession: sessions ? minutes / sessions : 0,
        avgPaidPerDay: paid / 4,
        avgSessionsPerDay: sessions / 4,
        avgMinutesPerDay: minutes / 4,
      };
    });
    const total = hours.reduce(
      (acc, row) => ({
        sessions: acc.sessions + row.sessions,
        paid: acc.paid + row.paid,
        minutes: acc.minutes + row.minutes,
      }),
      { sessions: 0, paid: 0, minutes: 0 },
    );
    return {
      weekdayIndex,
      weekday,
      days: 4,
      sessions: total.sessions,
      paid: total.paid,
      minutes: total.minutes,
      avgPaidPerSession: total.sessions ? total.paid / total.sessions : 0,
      avgMinutesPerSession: total.sessions ? total.minutes / total.sessions : 0,
      avgPaidPerDay: total.paid / 4,
      avgSessionsPerDay: total.sessions / 4,
      avgMinutesPerDay: total.minutes / 4,
      hours,
    };
  });
  const cells = weekdays.flatMap((row) => row.hours);
  const hours = Array.from({ length: 24 }, (_, hour) => {
    const source = cells.filter((row) => row.hour === hour);
    const sessions = source.reduce((sum, row) => sum + row.sessions, 0);
    const paid = source.reduce((sum, row) => sum + row.paid, 0);
    const minutes = source.reduce((sum, row) => sum + row.minutes, 0);
    return {
      weekdayIndex: 0,
      weekday: "Alle",
      hour,
      hourLabel: `${String(hour).padStart(2, "0")}:00`,
      sessions,
      paid,
      minutes,
      hours: minutes / 60,
      avgPaidPerSession: sessions ? paid / sessions : 0,
      avgMinutesPerSession: sessions ? minutes / sessions : 0,
      avgPaidPerDay: paid / 28,
      avgSessionsPerDay: sessions / 28,
      avgMinutesPerDay: minutes / 28,
    };
  });
  const summary = weekdays.reduce(
    (acc, row) => ({
      sessions: acc.sessions + row.sessions,
      paid: acc.paid + row.paid,
      minutes: acc.minutes + row.minutes,
    }),
    { sessions: 0, paid: 0, minutes: 0 },
  );
  return {
    generatedAt: "2026-06-10T12:00:00",
    period: {
      key: "this_month",
      label: "Juni 2026",
      dateFrom: "2026-06-01",
      dateTo: "2026-06-10",
      daysCount: 10,
      detail: "10 dager - fordelt etter starttidspunkt",
      options: [
        { key: "this_month", label: "Denne måneden" },
        { key: "this_year", label: "Dette året" },
        { key: "last_90_days", label: "Siste 90 dager" },
        { key: "previous_month", label: "Forrige måned" },
        { key: "last_year", label: "I fjor" },
        { key: "custom", label: "Egendefinert" },
      ],
    },
    summary: {
      ...summary,
      hours: summary.minutes / 60,
      avgPaidPerSession: summary.sessions ? summary.paid / summary.sessions : 0,
      avgMinutesPerSession: summary.sessions ? summary.minutes / summary.sessions : 0,
      avgPaidPerDay: summary.paid / 10,
      avgSessionsPerDay: summary.sessions / 10,
    },
    max: {
      paid: Math.max(...cells.map((row) => row.paid), 1),
      minutes: Math.max(...cells.map((row) => row.minutes), 1),
      sessions: Math.max(...cells.map((row) => row.sessions), 1),
      avgPaidPerDay: Math.max(...cells.map((row) => row.avgPaidPerDay), 1),
      avgMinutesPerDay: Math.max(...cells.map((row) => row.avgMinutesPerDay), 1),
    },
    weekdays,
    hours,
    topSlots: [...cells].sort((a, b) => b.paid - a.paid).slice(0, 20),
  };
}

function parkingWeeklyPoint(week, paid, minutes, isPartial = false) {
  const sessions = 20 + week;
  return {
    key: `2026-W${String(week).padStart(2, "0")}`,
    label: `Uke ${week}`,
    shortLabel: `U${week}`,
    rangeLabel: `${week}.06 - ${week + 6}.06`,
    weekStart: "2026-06-01",
    weekEnd: "2026-06-07",
    isoYear: 2026,
    isoWeek: week,
    sessions,
    paid,
    minutes,
    durationSessions: sessions,
    durationCoveragePct: 100,
    avgPaidPerSession: paid / sessions,
    avgMinutesPerSession: minutes / sessions,
    isPartial,
  };
}

function parkingWeeklyAveragesPayload() {
  const weeks = [parkingWeeklyPoint(22, 4200, 1680), parkingWeeklyPoint(23, 5100, 1900, true)];
  return {
    generatedAt: "2026-06-10T12:00:00",
    period: {
      key: "this_year",
      label: "Dette året",
      dateFrom: "2026-01-01",
      dateTo: "2026-06-10",
      detail: "Til og med inneværende uke",
      options: [
        { key: "this_month", label: "Denne måneden" },
        { key: "this_year", label: "Dette året" },
        { key: "last_90_days", label: "Siste 90 dager" },
        { key: "previous_month", label: "Forrige måned" },
        { key: "last_year", label: "I fjor" },
        { key: "custom", label: "Egendefinert" },
      ],
    },
    summary: {
      sessions: 85,
      paid: 9300,
      minutes: 3580,
      durationSessions: 85,
      durationCoveragePct: 100,
      avgPaidPerSession: 109.4,
      avgMinutesPerSession: 42.1,
      weeksWithData: 2,
    },
    latest: weeks[1],
    previous: weeks[0],
    delta: { paidPct: 12.5, minutesPct: 3.2 },
    weeks,
  };
}

function parkingWeeklyYearsPayload() {
  const series = [2026, 2025].map((year, seriesIndex) => ({
    year,
    label: String(year),
    color: seriesIndex ? "#64748b" : "#2563eb",
    sessions: 85 - seriesIndex * 10,
    weeksWithData: 2,
    durationCoveragePct: 100,
    avgPaidPerSession: 109.4 - seriesIndex * 6,
    avgMinutesPerSession: 42.1 + seriesIndex * 2,
    points: [22, 23].map((week) => ({
      week,
      label: `Uke ${week}`,
      rangeLabel: `${week}.06 - ${week + 6}.06`,
      sessions: 40,
      paid: 4200 - seriesIndex * 300,
      minutes: 1680 + seriesIndex * 100,
      durationSessions: 40,
      durationCoveragePct: 100,
      avgPaidPerSession: 105 - seriesIndex * 7,
      avgMinutesPerSession: 42 + seriesIndex * 2,
      isPartial: year === 2026 && week === 23,
      isAvailable: true,
    })),
  }));
  return {
    generatedAt: "2026-06-10T12:00:00",
    currentYear: 2026,
    currentWeek: 23,
    availableYears: [2026, 2025],
    defaultYears: [2026, 2025],
    selectedYears: [2026, 2025],
    series,
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

function doorPeriod(id, deviceId, title, openedLabel, closedLabel, durationLabel) {
  return {
    id,
    deviceId,
    deviceKey: `door-${deviceId}`,
    deviceName: title,
    title,
    state: "closed",
    stateLabel: "Lukket",
    tone: "ok",
    openedAt: "2026-06-10T10:30:00",
    openedLabel,
    openedAgeLabel: "1 t siden",
    closedAt: "2026-06-10T10:52:00",
    closedLabel,
    closedAgeLabel: "42 min siden",
    durationSeconds: 1320,
    durationLabel,
    openedEventId: id * 10,
    closedEventId: id * 10 + 1,
  };
}

function doorStatusPayload() {
  const period = doorPeriod(1, 453, "Solrom 1", "10:52:00", "10:30:00", "22 min");
  const doors = [
    {
      deviceId: 453,
      deviceKey: "sunroom-1",
      title: "Solrom 1",
      hc3Name: "Solrom 1 dør",
      groupKey: "solrom",
      groupTitle: "Solrom",
      sectionKey: "1etg",
      sectionTitle: "1.etg",
      sortOrder: 1,
      normalState: "open",
      normalStateLabel: "Normalt åpen",
      isConfigured: true,
      state: "closed",
      stateLabel: "Lukket",
      tone: "warn",
      lastChangedAt: "2026-06-10T10:30:00",
      lastChangedLabel: "10:30:00",
      ageLabel: "22 min",
      rawValue: "false",
      batteryLevel: 94,
      batteryLabel: "94%",
      eventId: 11,
      recentPeriods: [period],
    },
    {
      deviceId: 447,
      deviceKey: "entrance",
      title: "Inngang",
      hc3Name: "Inngangsdør",
      groupKey: "andre",
      groupTitle: "Andre dører",
      sectionKey: "bygg",
      sectionTitle: "Bygg",
      sortOrder: 20,
      normalState: "closed",
      normalStateLabel: "Normalt lukket",
      isConfigured: true,
      state: "closed",
      stateLabel: "Lukket",
      tone: "ok",
      lastChangedAt: "2026-06-10T08:00:00",
      lastChangedLabel: "08:00:00",
      ageLabel: "3 t",
      rawValue: "false",
      batteryLevel: 88,
      batteryLabel: "88%",
      eventId: 22,
      recentPeriods: [],
    },
  ];
  return {
    generatedAt: "2026-06-10T12:00:00",
    datakildePath: "/admin/datakilder/hc3_door_events",
    summary: {
      total: doors.length,
      configured: doors.length,
      planned: 0,
      known: doors.length,
      open: 0,
      closed: doors.length,
      unknown: 0,
      latestAt: "2026-06-10T10:30:00",
      latestLabel: "10:30:00",
      latestAgeLabel: "22 min siden",
      latestChangeText: "Solrom 1 lukket",
      events: 2,
      changes: 2,
      periods: 1,
      activePeriods: 1,
    },
    doors,
    changes: [
      {
        id: 11,
        timestamp: "2026-06-10T10:30:00",
        timeLabel: "10:30:00",
        ageLabel: "22 min siden",
        eventType: "state",
        action: "closed",
        state: "closed",
        stateLabel: "Lukket",
        tone: "warn",
        deviceKey: "sunroom-1",
        deviceId: 453,
        deviceName: "Solrom 1",
        source: "HC3",
        rawValue: "false",
        batteryLevel: 94,
      },
    ],
    events: [],
    periods: [period],
  };
}

function sunroomSession(id, roomId, startedLabel, amount = 210) {
  return {
    id,
    sourceSessionId: `sun2-${id}`,
    roomId,
    roomLabel: `Solrom ${roomId}`,
    startedAt: "2026-06-10T10:31:00",
    startedLabel,
    sunStartAt: "2026-06-10T10:34:00",
    sunStartLabel: "10:34:00",
    endedAt: "2026-06-10T10:49:00",
    endedLabel: "10:49:00",
    expectedExitAt: "2026-06-10T10:52:00",
    expectedExitLabel: "10:52:00",
    sun2UserId: "1001",
    sun2BedId: roomId,
    userName: "Smoke kunde",
    sourceRoomName: `Rom ${roomId}`,
    durationMinutes: 15,
    paidAmountKr: amount,
    status: "Ferdig",
    href: `/soling/enkeltimer?session=${id}`,
  };
}

function sunroomEnergyEvidence() {
  return {
    quality: "clean",
    qualityLabel: "Ren måling",
    status: "confirmed",
    statusLabel: "Strøm OK",
    detail: "Effektøkning funnet omtrent ved forventet solstart.",
    samplesCount: 12,
    baselineSamples: 4,
    overlapCount: 0,
    edgeConflict: false,
    baselineW: 120,
    baselineLabel: "120 W",
    activeMedianW: 3120,
    activeMedianLabel: "3 120 W",
    estimatedNetW: 3000,
    estimatedNetLabel: "3 000 W",
    startDeltaW: 2800,
    startDeltaLabel: "2 800 W",
    expectedDelaySeconds: 180,
    expectedDelayLabel: "3 min",
    firstRiseAt: "2026-06-10T10:34:04",
    firstRiseLabel: "10:34:04",
    startDelaySeconds: 184,
    startDelayLabel: "3 min 4 sek",
    delayDeviationSeconds: 4,
    delayDeviationLabel: "4 sek",
  };
}

function sunroomPeriod(id, roomId, closedLabel, openedLabel, isActive = false) {
  const session = sunroomSession(id, roomId, "10:31:00");
  return {
    id: `period-${id}`,
    state: isActive ? "active" : "closed",
    isActive,
    closedAt: "2026-06-10T10:30:00",
    closedLabel,
    closedAgeLabel: "22 min siden",
    openedAt: isActive ? null : "2026-06-10T10:52:00",
    openedLabel,
    openedAgeLabel: isActive ? "" : "1 min siden",
    durationSeconds: isActive ? null : 1320,
    durationLabel: isActive ? "Pågår" : "22 min",
    closedEventId: id * 10,
    openedEventId: isActive ? null : id * 10 + 1,
    session,
    energy: sunroomEnergyEvidence(),
    severity: isActive ? "active" : "ok",
    status: isActive ? "I bruk" : "OK",
    detail: isActive ? "Kunde er på rommet." : "Dørperiode og soltime henger sammen.",
    missingSession: false,
    expectedExitAt: session.expectedExitAt,
    expectedExitLabel: session.expectedExitLabel,
    remainingSeconds: isActive ? 180 : null,
    remainingLabel: isActive ? "3 min igjen" : "",
    overstaySeconds: null,
    overstayLabel: "",
  };
}

function sunroomStatus(roomId, displayRoomNumber, isOccupied) {
  const session = sunroomSession(displayRoomNumber, roomId, "10:31:00");
  return {
    deviceId: 450 + displayRoomNumber,
    deviceKey: `sunroom-${displayRoomNumber}`,
    title: `Solrom ${displayRoomNumber}`,
    sectionKey: displayRoomNumber <= 3 ? "1etg" : "2etg",
    sectionTitle: displayRoomNumber <= 3 ? "1.etg" : "2.etg",
    sortOrder: displayRoomNumber,
    roomId,
    roomLabel: `Solrom ${displayRoomNumber}`,
    doorState: isOccupied ? "closed" : "open",
    doorStateLabel: isOccupied ? "Lukket" : "Åpen",
    doorChangedAt: "2026-06-10T10:30:00",
    doorChangedLabel: "10:30:00",
    doorAgeLabel: "22 min",
    isOccupied,
    occupiedSince: isOccupied ? "2026-06-10T10:30:00" : null,
    occupiedSinceLabel: isOccupied ? "10:30:00" : "",
    occupiedDurationSeconds: isOccupied ? 1320 : null,
    occupiedDurationLabel: isOccupied ? "22 min" : "",
    severity: isOccupied ? "active" : "free",
    status: isOccupied ? "I bruk" : "Ledig",
    detail: isOccupied ? "Soltime funnet." : "Dør åpen.",
    missingSession: false,
    session: isOccupied ? session : null,
    expectedExitAt: isOccupied ? session.expectedExitAt : null,
    expectedExitLabel: isOccupied ? session.expectedExitLabel : "",
    remainingSeconds: isOccupied ? 180 : null,
    remainingLabel: isOccupied ? "3 min igjen" : "",
    overstaySeconds: null,
    overstayLabel: "",
  };
}

function sunroomOverviewPayload() {
  const activePeriod = sunroomPeriod(1, "1", "10:30:00", "", true);
  const historyPeriod = sunroomPeriod(2, "1", "09:10:00", "09:32:00", false);
  const activeSession = activePeriod.session;
  return {
    generatedAt: "2026-06-10T12:00:00",
    dayDate: "2026-06-10",
    dayStart: "2026-06-10T00:00:00",
    dayEnd: "2026-06-11T00:00:00",
    days: 2,
    rules: {
      paymentDelayMinutes: 3,
      exitGraceMinutes: 3,
      fanAfterRunMinutes: 3,
      warnAfterEndMinutes: 5,
      alertAfterEndMinutes: 10,
    },
    summary: {
      rooms: 2,
      active: 1,
      warnings: 0,
      alerts: 0,
      sessions: 2,
      doorMatches: 2,
      sessionsWithoutDoor: 0,
      energyConfirmed: 1,
      energySamples: 12,
    },
    rooms: [
      {
        displayRoomNumber: 1,
        title: "Solrom 1",
        sectionKey: "1etg",
        sectionTitle: "1.etg",
        deviceId: 453,
        deviceKey: "sunroom-1",
        roomId: "1",
        roomLabel: "Solrom 1",
        status: sunroomStatus("1", 1, true),
        latestPeriod: activePeriod,
        periods: [activePeriod, historyPeriod],
        recentSessions: [{ ...activeSession, energy: sunroomEnergyEvidence(), hasDoorMatch: true }],
        sessionsWithoutDoor: [],
        dayEvents: [
          { id: "door-closed-1", kind: "door_closed", label: "Dør lukket", time: "2026-06-10T10:30:00", timeLabel: "10:30:00", detail: "22 min", source: "HC3 dør", tone: "door" },
          { id: "sun-start-1", kind: "sun_start", label: "Soltime start", time: "2026-06-10T10:34:00", timeLabel: "10:34:00", detail: "12 min · 210 kr", source: "Sun2", tone: "sun" },
          { id: "power-start-1", kind: "power_start", label: "Effektøkning", time: "2026-06-10T10:39:00", timeLabel: "10:39:00", detail: "6 200 W", source: "HC3 effekt", tone: "power" },
        ],
        summary: {
          periods: 2,
          sessions: 2,
          matched: 2,
          withoutDoor: 0,
          warnings: 0,
          alerts: 0,
          energyConfirmed: 1,
          energyOverlap: 0,
        },
      },
      {
        displayRoomNumber: 2,
        title: "Solrom 2",
        sectionKey: "1etg",
        sectionTitle: "1.etg",
        deviceId: 454,
        deviceKey: "sunroom-2",
        roomId: "2",
        roomLabel: "Solrom 2",
        status: sunroomStatus("2", 2, false),
        latestPeriod: null,
        periods: [],
        recentSessions: [],
        sessionsWithoutDoor: [],
        dayEvents: [],
        summary: {
          periods: 0,
          sessions: 0,
          matched: 0,
          withoutDoor: 0,
          warnings: 0,
          alerts: 0,
          energyConfirmed: 0,
          energyOverlap: 0,
        },
      },
    ],
  };
}

function sunroomSessionsPayload() {
  return {
    generatedAt: "2026-06-10T12:00:00",
    ntfyDoorsSubscribeUrl: "ntfy://doors",
    ntfyDoorsWebUrl: "https://ntfy.sh/doors",
    rules: {
      paymentDelayMinutes: 3,
      fanAfterRunMinutes: 3,
      exitGraceMinutes: 3,
      sessionGraceMinutes: 5,
      noSessionAlarmMinutes: 8,
      warnAfterEndMinutes: 5,
      alertAfterEndMinutes: 10,
      monitorIntervalSeconds: 30,
      alertConfirmSeconds: 15,
    },
    summary: {
      rooms: 2,
      active: 1,
      waiting: 0,
      warning: 0,
      alert: 0,
      missingSession: 0,
      noSessionAlarm: 0,
      ok: 1,
    },
    rooms: [sunroomStatus("1", 1, true), sunroomStatus("2", 2, false)],
  };
}

function doorAlarmPayload() {
  const payload = sunroomSessionsPayload();
  return {
    ...payload,
    alarms: [],
    watch: [],
    occupiedWithoutSession: [],
    history: [],
    summary: {
      ...payload.summary,
      alarm: 0,
      watch: 0,
      occupiedWithoutSession: 0,
      history: 0,
      historyActive: 0,
      historyNotified: 0,
    },
  };
}

function bollardStatusPayload() {
  const cameras = [
    ["69f3a8ae0069e103e437d742", "G6 Butikk Nord", { x: 614, y: 324, width: 1152, height: 1836 }],
    ["6a35149c002cef03e4018be0", "G6 Butikk Front", { x: 0, y: 1123, width: 2803, height: 1037 }],
    ["6a219d5e00513a03e4066cba", "G6 Solstudio Front", { x: 2765, y: 0, width: 537, height: 734 }],
  ];
  return {
    api_version: "v1",
    local_only: true,
    comparison_mode: "fixed_bollard_zones",
    settings: {
      monitoring_enabled: true,
      analysis_interval_seconds: 300,
      confirmation_seconds: 300,
      notification_enabled: true,
    },
    camera_monitors: cameras.map(([cameraId, cameraName, displayCrop]) => ({
      monitor_id: `camera:${cameraId}`,
      item_type: "bollards",
      display_name: cameraName,
      camera_id: cameraId,
      camera_name: cameraName,
      status: "normal",
      baseline_captured_at: "2026-06-10T09:00:00Z",
      latest_captured_at: "2026-06-10T12:00:00Z",
      last_checked_at: "2026-06-10T12:00:00Z",
      change_score: 0,
      baseline_url: `/api/unifi-protect/bollards/cameras/${cameraId}/baseline`,
      latest_url: `/api/unifi-protect/bollards/cameras/${cameraId}/latest`,
      overlay_url: `/api/unifi-protect/bollards/cameras/${cameraId}/overlay`,
      baseline_crop_url: `/api/unifi-protect/bollards/cameras/${cameraId}/baseline/crop`,
      latest_crop_url: `/api/unifi-protect/bollards/cameras/${cameraId}/latest/crop`,
      overlay_crop_url: `/api/unifi-protect/bollards/cameras/${cameraId}/overlay/crop`,
      ai_heatmap_url: `/api/unifi-protect/bollards/cameras/${cameraId}/ai`,
      ai_profile_id: cameraName === "G6 Butikk Nord" ? "north-bollards" : cameraName === "G6 Butikk Front" ? "front-bollards" : "solstudio-bollards",
      ai_status: "normal",
      ai_score: 0.34,
      ai_threshold: 0.5,
      ai_score_ratio: 0.68,
      ai_is_anomaly: false,
      ai_model_version: "patchcore-resnet18-v1",
      ai_training_samples: 128,
      ai_inference_ms: 420,
      ai_last_checked_at: "2026-06-10T12:00:00Z",
      hybrid_status: "normal",
      display_crop: displayCrop,
    })),
    asset_monitors: [{
      monitor_id: "asset:trapp-solstudio",
      item_type: "stairs",
      asset_key: "trapp-solstudio",
      display_name: "Trapp ved Solstudio",
      camera_id: "6a219d5e00513a03e4066cba",
      camera_name: "G6 Solstudio Front",
      status: "normal",
      baseline_captured_at: "2026-06-10T09:00:00Z",
      latest_captured_at: "2026-06-10T12:00:00Z",
      last_checked_at: "2026-06-10T12:00:00Z",
      change_score: 0,
      baseline_crop_url: "/api/unifi-protect/bollards/assets/trapp-solstudio/baseline",
      latest_crop_url: "/api/unifi-protect/bollards/assets/trapp-solstudio/latest",
      overlay_crop_url: "/api/unifi-protect/bollards/assets/trapp-solstudio/overlay",
      ai_heatmap_url: "/api/unifi-protect/bollards/assets/trapp-solstudio/ai",
      ai_profile_id: "solstudio-stairs",
      ai_status: "normal",
      ai_score: 0.31,
      ai_threshold: 0.49,
      ai_score_ratio: 0.63,
      ai_is_anomaly: false,
      ai_model_version: "patchcore-resnet18-v1",
      ai_training_samples: 128,
      ai_inference_ms: 440,
      ai_last_checked_at: "2026-06-10T12:00:00Z",
      hybrid_status: "normal",
      display_crop: { x: 2200, y: 400, width: 1640, height: 1760 },
    }],
    incidents: [],
    summary: {
      target_cameras: 3,
      connected_cameras: 3,
      baseline_cameras: 3,
      monitored_assets: 1,
      calibrated_assets: 1,
      inspection_objects: 4,
      active_incidents: 0,
      monitoring_ready: true,
      ai_profiles_ready: 4,
      ai_profiles_total: 4,
      ai_anomalies: 0,
    },
    visual_ai: {
      configured: true,
      mode: "advisory",
      profiles_ready: 4,
      profiles_total: 4,
      anomalies: 0,
      failure_isolation: true,
    },
    runtime: {
      running: true,
      last_success_at: "2026-06-10T12:00:00Z",
      checks_since_start: 18,
      incidents_since_start: 0,
      notification_configured: true,
    },
  };
}

function bollardNotificationPayload() {
  return {
    channelName: "Pullerter ved solstudio",
    configured: true,
    enabled: true,
    monitoringReady: true,
    activeIncidents: 0,
    lastCheckAt: "2026-06-10T12:00:00Z",
    subscribeUrl: "ntfy://ntfy.sh/pullerter-smoke",
    webUrl: "https://ntfy.sh/pullerter-smoke",
    provider: "ntfy.sh",
    privacy: "Kun alarmtekst sendes. Bilder og analysedata forblir lokale.",
  };
}

function carsDayPayload() {
  const firstAt = "2026-06-10T09:14:12+02:00";
  const lastAt = "2026-06-10T13:42:31+02:00";
  const detections = [
    {
      recognitionId: 101,
      occurredAt: firstAt,
      cameraId: "camera-front",
      cameraName: "G6 Butikk Front",
      observedPlate: "AB12345",
      unifiScore: 94,
      snapshotStatus: "captured",
      snapshotTimeOffsetMs: 180,
      snapshotUrl: "/api/unifi-protect/recognitions/101/snapshot",
    },
    {
      recognitionId: 102,
      occurredAt: lastAt,
      cameraId: "camera-north",
      cameraName: "G6 Butikk Nord",
      observedPlate: "AB12345",
      unifiScore: 71,
      snapshotStatus: "captured",
      snapshotTimeOffsetMs: -220,
      snapshotUrl: "/api/unifi-protect/recognitions/102/snapshot",
    },
  ];
  const paidSessions = [{
    id: 501,
    startAt: "2026-06-10T10:05:00+02:00",
    endAt: "2026-06-10T14:05:00+02:00",
    durationMinutes: 240,
    amountKr: 80,
    isPaid: true,
    status: "Completed",
    source: "EasyPark",
    area: "Lilletorget",
  }];
  return {
    generatedAt: "2026-06-10T14:10:00+02:00",
    selectedDay: "2026-06-10",
    selectedDayLabel: "10.06.2026",
    prevDay: "2026-06-09",
    nextDay: "2026-06-11",
    isToday: false,
    matchPolicy: {
      mode: "same_calendar_day",
      label: "Samme bil og samme dag",
      detail: "Betaling matches mot bilen for hele kalenderdagen.",
    },
    observationWindow: { firstDetectedAt: firstAt, lastDetectedAt: lastAt, spanMinutes: 268.3 },
    summary: {
      uniquePlates: 2,
      detections: 3,
      paidPlates: 1,
      coveredPlates: 1,
      withoutPayment: 1,
      mergedOcrVariants: 0,
      scoredDetections: 2,
      lowConfidencePlates: 0,
      ocrWarningPlates: 0,
      reviewPlates: 1,
      validatedPlates: 1,
      likelyMisreads: 0,
      pendingValidation: 1,
    },
    items: [{
      plate: "AB12345",
      displayValue: "AB 12345",
      detectionCount: 2,
      firstDetectedAt: firstAt,
      lastDetectedAt: lastAt,
      knownInProtect: true,
      cameraNames: ["G6 Butikk Front", "G6 Butikk Nord"],
      detections,
      averageUnifiScore: 82.5,
      minimumUnifiScore: 71,
      maximumUnifiScore: 94,
      scoredDetectionCount: 2,
      confidenceLevel: "high",
      matchingReadCount: 2,
      observedPlateValues: ["AB12345"],
      mergedVariantCount: 0,
      ocrWarning: false,
      isLikelyOcrVariant: false,
      likelyCanonicalPlate: "AB12345",
      ocrVariantCandidates: [],
      registryValidation: {
        status: "valid_local",
        is_valid: true,
        likely_misread: false,
        country_code: null,
        country: null,
        source: "Fibaro10",
        vehicle_label: "Volvo XC60",
        local_match: true,
        message: "Kjent fra lokalt kjøretøyregister",
        sources: {},
      },
      likelyMisread: false,
      presentationStatus: "valid",
      requiresReview: false,
      vehicle: { name: "Kundebil", area: "Lilletorget", title: "Volvo XC60", path: "/parkering/kjoretoy/AB12345" },
      hasParkingSession: true,
      hasPaidSession: true,
      paidSessionCount: 1,
      paidTotalKr: 80,
      dayMatchedDetectionCount: 2,
      coveredDetectionCount: 1,
      minutesBeforeFirstPayment: 50.8,
      minutesAfterLastPayment: 0,
      paymentStatus: "paid_same_day",
      parkingSessions: paidSessions,
      paidSessions,
    }, {
      plate: "ZZ98765",
      displayValue: "ZZ 98765",
      detectionCount: 1,
      firstDetectedAt: "2026-06-10T11:20:00+02:00",
      lastDetectedAt: "2026-06-10T11:20:00+02:00",
      knownInProtect: false,
      cameraNames: ["G6 Butikk Front"],
      detections: [{
        recognitionId: 103,
        occurredAt: "2026-06-10T11:20:00+02:00",
        cameraId: "camera-front",
        cameraName: "G6 Butikk Front",
        observedPlate: "ZZ98765",
        unifiScore: 78,
        snapshotStatus: "missing",
        snapshotUrl: null,
      }],
      averageUnifiScore: 78,
      minimumUnifiScore: 78,
      maximumUnifiScore: 78,
      scoredDetectionCount: 1,
      confidenceLevel: "medium",
      matchingReadCount: 1,
      observedPlateValues: ["ZZ98765"],
      mergedVariantCount: 0,
      ocrWarning: false,
      isLikelyOcrVariant: false,
      likelyCanonicalPlate: "ZZ98765",
      ocrVariantCandidates: [],
      registryValidation: {
        status: "not_found",
        is_valid: false,
        likely_misread: false,
        country_code: null,
        country: null,
        source: null,
        vehicle_label: null,
        local_match: false,
        message: "Ikke funnet i kjøretøyregister",
        sources: {},
      },
      likelyMisread: false,
      presentationStatus: "pending_review",
      requiresReview: true,
      vehicle: null,
      hasParkingSession: false,
      hasPaidSession: false,
      paidSessionCount: 0,
      paidTotalKr: 0,
      dayMatchedDetectionCount: 1,
      coveredDetectionCount: 0,
      minutesBeforeFirstPayment: null,
      minutesAfterLastPayment: null,
      paymentStatus: "no_payment",
      parkingSessions: [],
      paidSessions: [],
    }],
  };
}

async function smokeCarsRegistryFilter(page) {
  const rows = page.locator(".cars-day-table .ant-table-tbody > tr.ant-table-row");
  if (await rows.count() !== 2) {
    throw new Error(`Bilregisterfilter forventet 2 rader før filtrering, fikk ${await rows.count()}`);
  }
  await page.getByRole("checkbox", { name: /kun kjente eller registerfunnet/i }).check();
  await page.waitForFunction(
    () => document.querySelectorAll(".cars-day-table .ant-table-tbody > tr.ant-table-row").length === 1,
    undefined,
    { timeout: 5000 },
  );
  const filteredText = await rows.first().innerText();
  if (!filteredText.includes("AB12345") || filteredText.includes("ZZ98765")) {
    throw new Error(`Bilregisterfilter viste uventet rad: ${filteredText}`);
  }
  await page.getByRole("checkbox", { name: /kun kjente eller registerfunnet/i }).uncheck();
  await page.locator(".cars-score-filter").click();
  await page.getByText("Minst 90", { exact: true }).last().click();
  await page.waitForFunction(
    () => document.querySelectorAll(".cars-day-table .ant-table-tbody > tr.ant-table-row").length === 1,
    undefined,
    { timeout: 5000 },
  );
  const scoreFilteredText = await rows.first().innerText();
  if (!scoreFilteredText.includes("AB12345") || scoreFilteredText.includes("ZZ98765")) {
    throw new Error(`Bilscorefilter viste uventet rad: ${scoreFilteredText}`);
  }
  await page.locator(".cars-score-filter").click();
  await page.getByText("Alle scorer", { exact: true }).last().click();
  console.log("UI cars registry filter OK");
  console.log("UI cars score filter OK");
}

async function smokeBollardVisualControl(page) {
  const slider = page.getByRole("slider", { name: /gjennomsiktighet for siste bilde/i });
  await slider.waitFor({ timeout: 5000 });
  if (await slider.inputValue() !== "50") throw new Error("Gjennomsiktig pullertvisning startet ikke p\u00e5 50 prosent");
  await page.keyboard.press("ArrowRight");
  if (await slider.inputValue() !== "55") throw new Error("H\u00f8yre piltast justerte ikke gjennomsiktigheten med 5 prosent");
  await page.keyboard.press("ArrowLeft");
  if (await slider.inputValue() !== "50") throw new Error("Venstre piltast justerte ikke gjennomsiktigheten med 5 prosent");
  await page.getByRole("button", { name: "Side om side", exact: true }).click();
  const visualPanels = page.locator(".bollard-visual-panel");
  if (await visualPanels.count() !== 2) {
    throw new Error(`Pullertkontroll forventet referanse og siste bilde, fikk ${await visualPanels.count()} felt`);
  }
  await page.getByRole("button", { name: "Markerte forskjeller", exact: true }).click();
  await page.getByText("Pikselforskjeller markert", { exact: true }).waitFor({ timeout: 5000 });
  await page.getByRole("button", { name: "Gjennomsiktig", exact: true }).click();
  const aiButton = page.locator(".bollard-ai-summary .ant-btn");
  if (await aiButton.count() !== 1) {
    const summaryText = await page.locator(".bollard-ai-summary").innerText();
    throw new Error(`Pullertkontroll mangler knapp for AI-markering: ${summaryText}`);
  }
  await aiButton.click();
  await page.getByText("Slik skal AI-resultatet tolkes", { exact: true }).waitFor({ timeout: 5000 });
  await aiButton.click();
  console.log("UI bollard visual control OK");
}

async function smokeIncidentReview(page) {
  await page.getByRole("button", { name: "Behandle" }).first().click();
  await page.getByLabel("Kommentar").fill("Kontrollert i UI-smoke");
  await page.getByRole("button", { name: "Bekreft lest" }).click();
  await page.getByText("Hendelsen er kvittert.", { exact: true }).waitFor({ timeout: 5000 });
  console.log("UI incident review OK");
}

function systemNotificationsPayload() {
  const channel = (key, title, area, publishingEnabled = true) => ({
    key,
    title,
    area,
    description: `Varsler fra ${title}.`,
    triggers: ["Hendelse oppdaget", "Kontroll bekreftet"],
    priority: "Normal",
    configured: true,
    publishingEnabled,
    subscribeUrl: `ntfy://ntfy.sh/smoke-${key}`,
    webUrl: `https://ntfy.sh/smoke-${key}`,
  });
  return {
    generatedAt: "2026-06-10T12:00:00",
    provider: "ntfy.sh",
    providerUrl: "https://ntfy.sh",
    summary: { channels: 5, configured: 5, publishing: 5 },
    incidentSummary: { active: 1, critical: 1, warning: 0, info: 0, acknowledged: 0, unreviewed: 1, domains: 1 },
    controls: [
      { key: "data-sources", title: "Datakilder", status: "critical", statusLabel: "Feil", detail: "22/23 OK; 1 feil.", path: "/admin/datakilder" },
      { key: "nightly-backup", title: "Nattbackup", status: "ok", statusLabel: "OK", detail: "Sist fullført i natt.", path: "/manual/oversikt" },
      { key: "full-restore-backup", title: "Gjenopprettingsbackup", status: "ok", statusLabel: "OK", detail: "Sist fullført i går.", path: "/manual/oversikt" },
      { key: "notification-delivery", title: "Varselutsending", status: "ok", statusLabel: "OK", detail: "Ingen varsler venter.", path: "/varslinger/oversikt" },
      { key: "bollards", title: "Pullertkontroll", status: "ok", statusLabel: "OK", detail: "Ingen aktive hendelser.", path: "/pullerter/oversikt" },
    ],
    incidents: [
      {
        key: "source:easypark_parking_import",
        domain: "Datakilder",
        title: "EasyPark import",
        detail: "Siste import feilet.",
        severity: "critical",
        severityLabel: "Kritisk",
        source: "EasyPark",
        startedAt: "2026-06-10T11:50:00",
        observedAt: "2026-06-10T12:00:00",
        recommendedAction: "Les siste feilmelding og kjør importen på nytt.",
        path: "/admin/datakilder/easypark_parking_import",
        metadata: {},
        reviewState: "open",
        reviewedAt: null,
        reviewedBy: null,
        reviewNote: "",
      },
    ],
    delivery: { status: "ok", pending: 0, sending: 0, retrying: 0, sent: 12, oldestPendingAt: null },
    subscriptions: [
      channel("doors", "Døralarmer", "Dører og solrom"),
      channel("bollards", "Pullerter og trapp", "Kamera og bygg"),
      channel("lights", "Lysstyring", "Lys"),
      channel("ventilation", "Ventilasjon", "Ventilasjon"),
      channel("access", "Brukeraktivitet", "Tilgang"),
    ],
    setup: ["Installer ntfy.", "Trykk Abonner.", "Godkjenn varslinger.", "Kontroller kanalen."],
    privacy: "Ikke del de private abonnementslenkene.",
  };
}

function systemSubsystemsPayload() {
  const subsystem = (component, title, area, access, links) => ({
    component,
    title,
    area,
    role: `${title} brukes av Fibaro10.`,
    runtime: "Docker",
    compose_service: component,
    interface: access === "internal" ? "Intern" : "Web",
    status: "Aktiv",
    criticality: "Normal",
    has_web_interface: access !== "internal",
    primary_url: links[0]?.url || "",
    access,
    links,
  });
  return {
    generatedAt: "2026-06-10T12:00:00",
    summary: { components: 4, active: 4, critical: 2, web_interfaces: 3, areas: 3 },
    subsystems: [
      subsystem("desktop_v2", "Fibaro10 hovedgrensesnitt", "Frontend", "local", [
        { kind: "local", label: "Lokalt grensesnitt", url: "http://127.0.0.1:8110/" },
      ]),
      subsystem("maintenance_mobile", "Vedlikehold mobil", "Vedlikehold", "external", [
        { kind: "public", label: "Åpne", url: "https://vedl.lilletorget.net/" },
      ]),
      subsystem("owntracks_service", "OwnTracks", "Lokasjon", "external", [
        { kind: "public", label: "Åpne", url: "https://owntracks.lilletorget.net/" },
      ]),
      subsystem("owntracks_postgres", "OwnTracks database", "Lokasjon", "internal", []),
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
  if (url.pathname === "/api/manual" || url.pathname === "/api/admin/manual") return sendJson(response, manualPayload);
  if (url.pathname === "/api/system/notifications") return sendJson(response, systemNotificationsPayload());
  if (url.pathname.startsWith("/api/system/incidents/") && request.method === "POST") {
    return sendJson(response, { status: "ok", message: "Hendelsen er kvittert." });
  }
  if (url.pathname === "/api/system/subsystems") return sendJson(response, systemSubsystemsPayload());
  if (url.pathname === "/api/revenue/month") return sendJson(response, revenueMonthPayload());
  if (url.pathname === "/api/status/comparison") return sendJson(response, statusComparisonPayload());
  if (url.pathname === "/api/soling/year-comparison") return sendJson(response, yearComparisonPayload("Soling arssammenligning"));
  if (url.pathname === "/api/parkering/year-comparison") return sendJson(response, yearComparisonPayload("Parkering arssammenligning"));
  if (url.pathname === "/api/parkering/time-distribution") return sendJson(response, parkingTimeDistributionPayload());
  if (url.pathname === "/api/parkering/weekly-averages/years") return sendJson(response, parkingWeeklyYearsPayload());
  if (url.pathname === "/api/parkering/weekly-averages") return sendJson(response, parkingWeeklyAveragesPayload());
  if (url.pathname === "/api/omsetning/year-comparison") return sendJson(response, yearComparisonPayload("Omsetning arssammenligning"));
  if (url.pathname === "/api/mobile-preview/screens") return sendJson(response, mobileScreensPayload());
  if (url.pathname === "/api/cars/day") return sendJson(response, carsDayPayload());
  if (url.pathname.startsWith("/api/unifi-protect/recognitions/") && url.pathname.endsWith("/snapshot")) return sendSmokeRecognitionImage(response);
  if (url.pathname === "/api/unifi-protect/bollards") return sendJson(response, bollardStatusPayload());
  if (url.pathname === "/api/unifi-protect/bollards/mobile-notifications") return sendJson(response, bollardNotificationPayload());
  if (url.pathname.startsWith("/api/unifi-protect/bollards/cameras/")) return sendSmokeCameraImage(response);
  if (url.pathname.startsWith("/api/unifi-protect/bollards/assets/")) return sendSmokeCameraImage(response);
  if (url.pathname === "/api/hc3/doors/status") return sendJson(response, doorStatusPayload());
  if (url.pathname === "/api/hc3/doors/sunroom-overview") return sendJson(response, sunroomOverviewPayload());
  if (url.pathname === "/api/hc3/doors/alarm") return sendJson(response, doorAlarmPayload());
  if (url.pathname === "/api/hc3/doors/sunroom-sessions") return sendJson(response, sunroomSessionsPayload());
  if (url.pathname.startsWith("/api/hc3/doors/sunroom-sessions/")) {
    return sendJson(response, {
      generatedAt: "2026-06-10T12:00:00",
      days: 2,
      room: sunroomStatus("1", 1, true),
      summary: { periods: 2, active: 1, warnings: 0, alerts: 0, missingSession: 0, sessions: 2, sessionsWithoutDoor: 0 },
      currentPeriod: sunroomPeriod(1, "1", "10:30:00", "", true),
      periods: [sunroomPeriod(1, "1", "10:30:00", "", true), sunroomPeriod(2, "1", "09:10:00", "09:32:00", false)],
      sessionsWithoutDoor: [],
    });
  }
  if (url.pathname === "/api/overview") {
    return sendJson(response, {
      generatedAt: "2026-06-10T12:00:00",
      operatingWindow: { label: "Åpent", detail: "Stenger 23:00", open: true },
      cards: [],
      statusPeriods: statusPeriodsPayload(),
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

async function waitForPath(page, pathname) {
  await page.waitForFunction((expectedPath) => window.location.pathname === expectedPath, pathname, { timeout: 8000 });
}

async function shellHasClass(page, className) {
  return page.locator(".app-shell").evaluate((element, name) => element.classList.contains(name), className);
}

async function waitForShellClass(page, className, expected) {
  await page.waitForFunction(
    ({ name, expectedValue }) => document.querySelector(".app-shell")?.classList.contains(name) === expectedValue,
    { name: className, expectedValue: expected },
    { timeout: 8000 },
  );
}

async function smokeShellControls(page) {
  await page.goto(`${baseUrl}/status/omsetning`, { waitUntil: "load" });
  await page.locator(".app-shell").waitFor({ timeout: 8000 });

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
  await expectVisible(page, "Smoke-test build");

  await page.getByLabel("Gå til dashboard").click();
  await waitForPath(page, "/status/omsetning");
  await page.locator(".top-view-switcher").getByText("Parkering", { exact: true }).click();
  await waitForPath(page, "/status/parkering");
  await page.locator(".top-view-switcher").getByText("Omsetning", { exact: true }).click();
  await waitForPath(page, "/status/omsetning");

  console.log("UI shell controls OK");
}

async function smokeTabletLayout(page) {
  await page.setViewportSize({ width: 1024, height: 1366 });
  await page.goto(`${baseUrl}/status/omsetning`, { waitUntil: "load" });
  await page.evaluate(() => localStorage.removeItem("fibaro10:mainMenuHidden"));
  await page.reload({ waitUntil: "load" });
  await page.locator(".app-shell").waitFor({ timeout: 8000 });
  await waitForShellClass(page, "main-menu-hidden", true);
  await page.locator(".status-period-card").first().waitFor({ timeout: 8000 });
  if (await page.locator(".status-period-card").count() < 4) {
    throw new Error("Dashboardet rendret ikke alle fire periodekortene i iPad-testen");
  }

  const layout = async () => page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    cards: [...document.querySelectorAll(".status-period-card")].slice(0, 2).map((element) => {
      const rect = element.getBoundingClientRect();
      return { right: rect.right, top: rect.top, width: rect.width };
    }),
  }));
  const hiddenLayout = await layout();
  if (hiddenLayout.scrollWidth > hiddenLayout.clientWidth + 1) {
    throw new Error(`iPad-layout med skjult meny er ${hiddenLayout.scrollWidth - hiddenLayout.clientWidth}px for bred`);
  }
  if (hiddenLayout.cards.length === 2 && Math.abs(hiddenLayout.cards[0].top - hiddenLayout.cards[1].top) > 1) {
    throw new Error("iPad-layout med skjult meny viser ikke dashboardet i to kolonner");
  }

  await page.getByRole("button", { name: /vis hovedmeny/i }).click();
  await waitForShellClass(page, "main-menu-hidden", false);
  const visibleLayout = await layout();
  if (visibleLayout.scrollWidth > visibleLayout.clientWidth + 1) {
    throw new Error(`iPad-layout med synlig meny er ${visibleLayout.scrollWidth - visibleLayout.clientWidth}px for bred`);
  }
  if (visibleLayout.cards.some((card) => card.right > visibleLayout.clientWidth + 1)) {
    throw new Error("Dashboardkort havner utenfor iPad-visningen med synlig meny");
  }

  await page.evaluate(() => localStorage.setItem("fibaro10:mainMenuHidden", "0"));
  await page.setViewportSize({ width: 1440, height: 900 });
  console.log("UI iPad layout OK");
}

async function auditStandardThemeAccentContrast(page) {
  const results = await page.evaluate(() => {
    const parseRgb = (value) => {
      const channels = value.match(/[\d.]+/g)?.slice(0, 3).map(Number);
      return channels?.length === 3 ? channels : null;
    };
    const luminance = (channels) => {
      const linear = channels.map((channel) => {
        const normalized = channel / 255;
        return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
    };
    const contrast = (foreground, background) => {
      const foregroundRgb = parseRgb(foreground);
      const backgroundRgb = parseRgb(background);
      if (!foregroundRgb || !backgroundRgb) return 0;
      const lighter = Math.max(luminance(foregroundRgb), luminance(backgroundRgb));
      const darker = Math.min(luminance(foregroundRgb), luminance(backgroundRgb));
      return (lighter + 0.05) / (darker + 0.05);
    };
    const domains = [
      "domain-omsetning",
      "domain-parkering",
      "domain-soling",
      "domain-energi",
      "domain-ventilasjon",
      "domain-lys",
      "domain-dorer",
      "domain-vedlikehold",
      "domain-ideer",
      "domain-mobil",
      "domain-manual",
      "domain-status",
    ];
    return domains.map((domain) => {
      const probe = document.createElement("span");
      probe.className = domain;
      probe.style.cssText = "position:fixed;left:-10000px;color:var(--active-module-on-color);background-color:var(--active-module-color)";
      document.body.appendChild(probe);
      const style = getComputedStyle(probe);
      const foreground = style.color;
      const background = style.backgroundColor;
      probe.remove();
      return { domain, foreground, background, ratio: contrast(foreground, background) };
    });
  });
  const failures = results.filter((result) => result.ratio < 4.5);
  if (failures.length) {
    throw new Error(`For svak aksentkontrast: ${failures.map((item) => `${item.domain} ${item.ratio.toFixed(2)}:1`).join(", ")}`);
  }
  console.log(`UI accent contrast OK (${results.length} domains)`);
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

    await smokeShellControls(page);
    await smokeTabletLayout(page);
    await page.evaluate(() => localStorage.setItem("fibaro10:screenTheme", "standard"));
    await page.reload({ waitUntil: "load" });
    await page.locator(".app-shell.theme-standard").waitFor({ timeout: 8000 });
    await auditStandardThemeAccentContrast(page);
    await smokeRoute(page, "/admin/build", ["Smoke-test build", "Build"]);
    for (const route of routeList) {
      await smokeRoute(page, route.path, route.expectedTexts);
      if (route.path === "/biler/oversikt") {
        await smokeCarsRegistryFilter(page);
      }
      if (route.path === "/pullerter/oversikt") {
        await smokeBollardVisualControl(page);
      }
      if (route.path === "/varslinger/oversikt") {
        await smokeIncidentReview(page);
      }
      if (screenshotPath && screenshotRoute === route.path) {
        if (route.path.startsWith("/status/")) {
          await page.locator(".status-period-card").first().waitFor({ timeout: 8000 });
        }
        await fs.mkdir(path.dirname(screenshotPath), { recursive: true });
        await page.screenshot({ path: screenshotPath, fullPage: true });
      }
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
