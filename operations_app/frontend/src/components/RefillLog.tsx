import { MosaicIcon, Panel } from "@lilletorget/microapp-ui";
import { domainApi } from "@lilletorget/microapp-ui/api";
import { useApi } from "@lilletorget/microapp-ui/hooks";
import { useAppLocation } from "@lilletorget/microapp-ui/router";
import type { RoborockRefillLog } from "../roborock-types";


function parsedDate(value: string | null | undefined) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function stamp(value: string | null | undefined, includeDate = true) {
  const parsed = parsedDate(value);
  if (!parsed) return "-";
  return includeDate
    ? parsed.toLocaleString("nb-NO", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Oslo" })
    : parsed.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Oslo" });
}

function dayLabel(value: string) {
  return new Date(`${value}T12:00:00`).toLocaleDateString("nb-NO", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
}

function weekLabel(fromDay: string, toDay: string, week: number) {
  const from = new Date(`${fromDay}T12:00:00`);
  const to = new Date(`${toDay}T12:00:00`);
  const fromText = from.toLocaleDateString("nb-NO", { day: "numeric", month: "short" });
  const toText = to.toLocaleDateString("nb-NO", { day: "numeric", month: "short", year: "numeric" });
  return `Uke ${week} · ${fromText}–${toText}`;
}

function durationLabel(value: number | null | undefined) {
  if (value == null) return "-";
  const minutes = Math.max(0, Math.round(value));
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const rest = minutes % 60;
  if (days) return `${days} d ${hours} t`;
  if (hours) return rest ? `${hours} t ${rest} min` : `${hours} t`;
  return `${rest} min`;
}

function cycleDay(cycle: RoborockRefillLog["cycles"][number]) {
  return String(cycle.emptyAt || cycle.refilledAt || "").slice(0, 10);
}

function cycleStamp(value: string | null | undefined, groupDay: string) {
  if (!value) return "-";
  return value.slice(0, 10) === groupDay ? stamp(value, false) : stamp(value);
}

export function RefillLog() {
  const { search, navigate } = useAppLocation();
  const selectedWeek = new URLSearchParams(search).get("week") || "";
  const suffix = selectedWeek ? `?week=${encodeURIComponent(selectedWeek)}` : "";
  const result = useApi(
    () => domainApi.get<RoborockRefillLog>(`/api/renhold/refill-log${suffix}`),
    `roborock-refill-${selectedWeek || "current"}`,
  );
  const go = (week = "") => navigate(`/renhold/pafylling${week ? `?week=${encodeURIComponent(week)}` : ""}`);

  if (result.loading && !result.data) return <Panel><div className="p-8 text-sm text-gray-400">Henter vannloggen ...</div></Panel>;
  if (result.error || !result.data) return <Panel><div className="flex items-center justify-between gap-3 p-6 text-sm text-red-500"><span>{result.error?.message || "Kunne ikke hente vannloggen"}</span><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={result.reload}>Prøv igjen</button></div></Panel>;

  const report = result.data;
  const grouped = report.cycles.reduce<Record<string, typeof report.cycles>>((days, cycle) => {
    const key = cycleDay(cycle);
    (days[key] ||= []).push(cycle);
    return days;
  }, {});

  return <div className="space-y-4">
    <section className="grid items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-xs sm:grid-cols-[auto_1fr_auto] dark:border-gray-700/60 dark:bg-gray-800">
      <div className="flex items-center gap-2">
        <button aria-label="Forrige uke" className="btn h-9 w-9 border-gray-200 bg-white p-0 dark:border-gray-700 dark:bg-gray-800" onClick={() => go(report.period.previousWeek)} title="Forrige uke"><MosaicIcon name="arrow-left" /></button>
        <button className="btn h-9 border-gray-200 bg-white px-3 dark:border-gray-700 dark:bg-gray-800" onClick={() => go()}>Denne uken</button>
        <button aria-label="Neste uke" className="btn h-9 w-9 border-gray-200 bg-white p-0 dark:border-gray-700 dark:bg-gray-800" disabled={!report.period.canNext} onClick={() => go(report.period.nextWeek)} title="Neste uke"><MosaicIcon name="arrow-right" /></button>
      </div>
      <div className="text-center"><h1 className="text-base font-semibold text-gray-800 dark:text-gray-100">{weekLabel(report.period.fromDay, report.period.toDay, report.period.weekNumber)}</h1><p className="mt-0.5 text-xs text-gray-400">Når rentvannstanken blir tom og fylles igjen</p></div>
      <label className="flex items-center justify-self-start gap-2 text-xs font-medium text-gray-400 sm:justify-self-end"><MosaicIcon name="calendar" /><input className="form-input h-9 py-1.5 text-sm" max={report.period.currentWeek} type="week" value={report.period.week} onChange={(event) => event.target.value && go(event.target.value)} /></label>
    </section>

    <section className="grid overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xs sm:grid-cols-2 xl:grid-cols-4 dark:border-gray-700/60 dark:bg-gray-800">
      <div className="border-b px-5 py-4 sm:border-r xl:border-b-0 dark:border-gray-700/60"><span className="text-[0.65rem] font-semibold uppercase text-gray-400">Ble tom</span><strong className="mt-1 block text-xl font-semibold tabular-nums text-gray-800 dark:text-gray-100">{report.summary.empties}</strong><small className="text-gray-400">hendelser i valgt uke</small></div>
      <div className="border-b px-5 py-4 xl:border-b-0 xl:border-r dark:border-gray-700/60"><span className="text-[0.65rem] font-semibold uppercase text-gray-400">Påfyllinger</span><strong className="mt-1 block text-xl font-semibold tabular-nums text-gray-800 dark:text-gray-100">{report.summary.fills}</strong><small className="text-gray-400">sist {stamp(report.summary.latestFillAt)}</small></div>
      <div className="border-b px-5 py-4 sm:border-b-0 sm:border-r dark:border-gray-700/60"><span className="text-[0.65rem] font-semibold uppercase text-gray-400">Venter på fylling</span><strong className={`mt-1 block text-xl font-semibold tabular-nums ${report.summary.pending ? "text-amber-600 dark:text-amber-300" : "text-gray-800 dark:text-gray-100"}`}>{report.summary.pending}</strong><small className="text-gray-400">av {report.summary.robots} vanndokker</small></div>
      <div className="px-5 py-4"><span className="text-[0.65rem] font-semibold uppercase text-gray-400">Snitt tomtid</span><strong className="mt-1 block text-xl font-semibold tabular-nums text-gray-800 dark:text-gray-100">{durationLabel(report.summary.averageEmptyMinutes)}</strong><small className="text-gray-400">fra tom til fylt igjen</small></div>
    </section>

    <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xs dark:border-gray-700/60 dark:bg-gray-800">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-4 dark:border-gray-700/60"><div><h2 className="text-base font-semibold text-gray-800 dark:text-gray-100">Tom og fylt</h2><p className="mt-0.5 text-xs text-gray-400">Nyeste syklus øverst · tidspunkt og varighet per dokk</p></div><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={result.reload}><MosaicIcon name="refresh" />Oppdater</button></header>
      {Object.entries(grouped).map(([day, cycles]) => <div className="border-b border-gray-100 last:border-b-0 dark:border-gray-700/60" key={day}>
        <div className="bg-gray-50/80 px-5 py-2.5 text-xs font-semibold capitalize text-gray-500 dark:bg-gray-900/30 dark:text-gray-300">{dayLabel(day)}</div>
        <div className="divide-y divide-gray-100 dark:divide-gray-700/60">{cycles.map((cycle) => <div className={`grid items-center gap-3 px-5 py-3.5 sm:grid-cols-[minmax(10rem,0.9fr)_minmax(7rem,0.7fr)_minmax(7rem,0.7fr)_minmax(10rem,0.8fr)] ${cycle.status === "pending" ? "bg-amber-50/60 dark:bg-amber-500/5" : ""}`} key={cycle.id}>
          <div className="flex min-w-0 items-center gap-2.5"><span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${cycle.status === "pending" ? "bg-amber-500/10 text-amber-600 dark:text-amber-300" : "bg-sky-500/10 text-sky-600 dark:text-sky-300"}`}><MosaicIcon name="robot" size={16} /></span><strong className="truncate text-sm text-gray-700 dark:text-gray-200">{cycle.robotName}</strong></div>
          <div><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Ble tom</span><strong className="mt-0.5 block text-base font-semibold tabular-nums text-gray-800 dark:text-gray-100">{cycle.emptyAt ? cycleStamp(cycle.emptyAt, day) : "Før uken"}</strong></div>
          <div><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Fylt igjen</span><strong className={`mt-0.5 block text-base font-semibold tabular-nums ${cycle.status === "pending" ? "text-amber-600 dark:text-amber-300" : "text-gray-800 dark:text-gray-100"}`}>{cycle.refilledAt ? cycleStamp(cycle.refilledAt, day) : "Venter"}</strong></div>
          <div className="sm:text-right"><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Tomtid</span><strong className={`mt-0.5 block text-sm font-semibold tabular-nums ${cycle.status === "pending" ? "text-amber-600 dark:text-amber-300" : "text-gray-600 dark:text-gray-300"}`}>{cycle.status === "pending" ? `Tom i ${durationLabel(cycle.emptyMinutes)}` : durationLabel(cycle.emptyMinutes)}</strong></div>
        </div>)}</div>
      </div>)}
      {!report.cycles.length ? <div className="flex flex-col items-center px-5 py-12 text-center"><span className="flex h-11 w-11 items-center justify-center rounded-full bg-sky-500/10 text-sky-600 dark:text-sky-300"><MosaicIcon name="robot" size={20} /></span><strong className="mt-3 text-sm text-gray-700 dark:text-gray-200">Ingen vannhendelser registrert denne uken</strong><p className="mt-1 max-w-md text-xs leading-5 text-gray-400">Listen fylles når en vanndokk rapporterer at rentvannstanken blir tom eller fylles igjen.</p></div> : null}
      <footer className="border-t border-gray-100 bg-gray-50/60 px-5 py-3 text-xs leading-5 text-gray-500 dark:border-gray-700/60 dark:bg-gray-900/20 dark:text-gray-400">{report.measurementNote}</footer>
    </section>

    <Panel title="Per robot" subtitle="Vannstatus i valgt uke"><div className="grid gap-px bg-gray-100 sm:grid-cols-2 xl:grid-cols-3 dark:bg-gray-700/60">{report.robots.map((robot) => <div className="bg-white px-5 py-4 dark:bg-gray-800" key={robot.duid}>
      <div className="flex items-center justify-between gap-3"><strong className="truncate text-sm text-gray-700 dark:text-gray-200">{robot.name}</strong><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${robot.pending ? "bg-amber-500/10 text-amber-700 dark:text-amber-300" : "bg-green-500/10 text-green-700 dark:text-green-300"}`}>{robot.pending ? "Tom nå" : "OK"}</span></div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-xs"><span className="text-gray-400">Ble tom <strong className="ml-1 text-gray-700 dark:text-gray-200">{robot.empties}</strong></span><span className="text-gray-400">Fylt <strong className="ml-1 text-gray-700 dark:text-gray-200">{robot.fills}</strong></span></div>
      <p className="mt-2 text-xs text-gray-400">{robot.pending ? `Tom siden ${stamp(robot.currentEmptySince)}` : robot.lastFillAt ? `Sist fylt ${stamp(robot.lastFillAt)}` : "Ingen vannhendelser i uken"}</p>
    </div>)}</div></Panel>
  </div>;
}
