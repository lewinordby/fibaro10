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
    { id: "rutiner", number: "08", title: "Rutiner og kontroll", paragraphs: ["Smoke for rutiner."] },
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
      warnAfterEndMinutes: 5,
      alertAfterEndMinutes: 10,
      monitorIntervalSeconds: 30,
    },
    summary: {
      rooms: 2,
      active: 1,
      waiting: 0,
      warning: 0,
      alert: 0,
      missingSession: 0,
      ok: 1,
    },
    rooms: [sunroomStatus("1", 1, true), sunroomStatus("2", 2, false)],
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
  if (url.pathname === "/api/revenue/month") return sendJson(response, revenueMonthPayload());
  if (url.pathname === "/api/status/comparison") return sendJson(response, statusComparisonPayload());
  if (url.pathname === "/api/soling/year-comparison") return sendJson(response, yearComparisonPayload("Soling arssammenligning"));
  if (url.pathname === "/api/parkering/year-comparison") return sendJson(response, yearComparisonPayload("Parkering arssammenligning"));
  if (url.pathname === "/api/parkering/time-distribution") return sendJson(response, parkingTimeDistributionPayload());
  if (url.pathname === "/api/omsetning/year-comparison") return sendJson(response, yearComparisonPayload("Omsetning arssammenligning"));
  if (url.pathname === "/api/mobile-preview/screens") return sendJson(response, mobileScreensPayload());
  if (url.pathname === "/api/hc3/doors/status") return sendJson(response, doorStatusPayload());
  if (url.pathname === "/api/hc3/doors/sunroom-overview") return sendJson(response, sunroomOverviewPayload());
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
    await smokeRoute(page, "/admin/build", ["Smoke-test build", "Build"]);
    for (const route of routeList) {
      await smokeRoute(page, route.path, route.expectedTexts);
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
