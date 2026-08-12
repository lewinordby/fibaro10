import { domainApi } from "../api";
import { displayCell, valueLabel } from "../format";
import { useApi } from "../hooks";
import { AppLink, useAppLocation } from "../router";
import type {
  JsonRecord,
  RoborockDailySummary,
  RoborockJobSummary,
  RoborockModuleData,
  RoborockOverviewSummary,
  RoborockReadinessSummary,
  RoborockRobotDetail,
  RoborockRobotSummary,
} from "../types";
import { Panel } from "./Mosaic";
import { MosaicIcon } from "./MosaicIcon";

const emptyDay: RoborockDailySummary = {
  job_count: 0,
  completed_count: 0,
  running_count: 0,
  error_count: 0,
  duration_minutes: 0,
  cleaned_area_m2: 0,
};

function parsedDate(value: unknown) {
  if (!value) return null;
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function stamp(value: unknown) {
  const parsed = parsedDate(value);
  return parsed
    ? parsed.toLocaleString("nb-NO", { dateStyle: "short", timeStyle: "medium", timeZone: "Europe/Oslo" })
    : value ? String(value) : "-";
}

function jobTime(value: unknown) {
  const parsed = parsedDate(value);
  return parsed ? parsed.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Oslo" }) : "-";
}

function relativeStamp(value: unknown) {
  const parsed = parsedDate(value);
  if (!parsed) return "Ikke mottatt";
  const minutes = Math.max(0, Math.round((Date.now() - parsed.getTime()) / 60_000));
  if (minutes < 1) return "akkurat nå";
  if (minutes < 60) return `${minutes} min siden`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} t siden`;
  return stamp(value);
}

function decimal(value: unknown, digits = 0) {
  const number = Number(value || 0);
  return number.toLocaleString("nb-NO", { maximumFractionDigits: digits });
}

const roborockStateLabels: Record<string, string> = {
  charging: "Lader",
  cleaning: "Rengjør",
  docking: "Dokker",
  emptying: "Tømmer støvbeholder",
  emptying_dust_container: "Tømmer støvbeholder",
  error: "Feil",
  going_to_target: "Går til målpunkt",
  idle: "Klar",
  mapping: "Kartlegger",
  paused: "Pause",
  returning: "Returnerer til dokk",
  returning_home: "Returnerer til dokk",
  segment_cleaning: "Rengjør rom",
  sleeping: "Hviler",
  spot_cleaning: "Flekkrengjøring",
  updating: "Oppdaterer",
  washing_mop: "Vasker mopp",
  washing_the_mop: "Vasker mopp",
  zone_cleaning: "Sonerengjøring",
};

const compactColumnLabels: Record<string, string> = {
  battery: "Batteri",
  begin_at: "Start",
  charge_label: "Lading",
  cleaned_area_m2: "Areal",
  clear_water_label: "Rentvann",
  current_label: "Til",
  dirty_water_label: "Skittent vann",
  dock_error_label: "Dokk",
  duration_minutes: "Tid",
  dust_bag_label: "Støvpose",
  end_at: "Slutt",
  error_label: "Feil",
  fan_label: "Sugekraft",
  field: "Felt",
  local_ip: "Lokal IP",
  mop_label: "Mopp",
  previous_label: "Fra",
  rounds_label: "Runder",
  severity: "Nivå",
  signal_label: "Signal",
  state_label: "Tilstand",
  status_label: "Status",
  timestamp: "Tidspunkt",
  title: "Hendelse",
  value: "Verdi",
};

function robotStateLabel(value: unknown) {
  const text = String(value || "").trim();
  return roborockStateLabels[text.toLowerCase()] || text || "Ingen status";
}

function Field({ label, value }: { label: string; value: unknown }) {
  return <div className="flex items-start justify-between gap-4 border-b border-gray-100 py-2.5 text-sm last:border-0 dark:border-gray-700/70"><span className="text-gray-400">{label}</span><strong className="max-w-[65%] text-right font-medium text-gray-700 dark:text-gray-200">{displayCell(label, value)}</strong></div>;
}

function telemetryTone(value: unknown) {
  const text = String(value ?? "").toLocaleLowerCase("nb-NO");
  if (["ikke støttet", "-"].includes(text)) return "text-gray-400";
  if (["ok", "ingen feil", "nei", "0"].includes(text)) return "text-green-600 dark:text-green-400";
  if (text.includes("full") || text.includes("tom") || text.includes("feil") || text.includes("mangler")) return "text-red-500";
  return "text-gray-700 dark:text-gray-200";
}

function readinessStyle(status: RoborockReadinessSummary["status"] | undefined) {
  if (status === "attention") return { badge: "bg-red-500/10 text-red-600 dark:text-red-400", dot: "bg-red-500", icon: "bg-red-500/10 text-red-500" };
  if (status === "offline") return { badge: "bg-gray-500/10 text-gray-600 dark:text-gray-300", dot: "bg-gray-400", icon: "bg-gray-500/10 text-gray-500" };
  if (status === "active") return { badge: "bg-sky-500/10 text-sky-700 dark:text-sky-400", dot: "bg-sky-500", icon: "bg-sky-500/10 text-sky-600 dark:text-sky-400" };
  return { badge: "bg-green-500/10 text-green-700 dark:text-green-400", dot: "bg-green-500", icon: "bg-green-500/10 text-green-600 dark:text-green-400" };
}

function TelemetryFields({ fields }: { fields: RoborockRobotDetail["telemetryFields"] }) {
  const groups = [...new Set(fields.map((field) => field.category))];
  return <div className="grid gap-x-8 px-5 py-3 lg:grid-cols-2">{groups.map((group) => <section key={group}><h3 className="border-b border-gray-100 py-3 text-xs font-semibold uppercase text-gray-400 dark:border-gray-700/70">{group}</h3>{fields.filter((field) => field.category === group).map((field) => <div className="flex items-start justify-between gap-4 border-b border-gray-100 py-2.5 text-sm last:border-0 dark:border-gray-700/70" key={field.field}><span className="text-gray-500 dark:text-gray-400">{field.label}</span><span className={`max-w-[58%] text-right font-medium ${field.supported ? telemetryTone(field.valueLabel) : "text-gray-400"}`}>{field.valueLabel}</span></div>)}</section>)}</div>;
}

function JsonValue({ value }: { value: unknown }) {
  const text = value == null ? "-" : typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded bg-gray-50 p-3 text-xs text-gray-600 dark:bg-gray-900/50 dark:text-gray-300">{text}</pre>;
}

function TelemetryProbes({ probes }: { probes: RoborockRobotDetail["telemetryProbes"] }) {
  return <div className="divide-y divide-gray-100 dark:divide-gray-700/60">{probes.map((probe) => <details className="group py-3" key={probe.command}><summary className="grid cursor-pointer list-none grid-cols-[1fr_auto] items-center gap-3 text-sm"><span><strong className="font-medium text-gray-700 dark:text-gray-200">{probe.command}</strong><small className="mt-0.5 block text-gray-400">{probe.checkedAt ? stamp(probe.checkedAt) : "Ikke kontrollert"}{probe.resultType ? ` · ${probe.resultType}` : ""}</small></span><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${probe.supported ? "bg-green-500/10 text-green-600 dark:text-green-400" : probe.status === "Ikke støttet" ? "bg-gray-500/10 text-gray-500" : "bg-red-500/10 text-red-500"}`}>{probe.status}</span></summary><div className="mt-3">{probe.error ? <p className="mb-2 text-sm text-red-500">{probe.error}</p> : null}<JsonValue value={probe.value} /></div></details>)}</div>;
}

function CompactTable({ columns, rows }: { columns: string[]; rows: JsonRecord[] }) {
  return <div className="overflow-x-auto"><table className="w-full table-auto"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/40"><tr>{columns.map((column) => <th className="whitespace-nowrap px-4 py-3 text-left font-semibold" key={column}>{compactColumnLabels[column] || valueLabel(column)}</th>)}</tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{rows.map((row, index) => <tr className="hover:bg-gray-50/60 dark:hover:bg-gray-700/20" key={String(row.id || index)}>{columns.map((column) => <td className="whitespace-nowrap px-4 py-3 tabular-nums" key={column}>{column.endsWith("_at") || column === "timestamp" || column === "begin_at" || column === "end_at" ? stamp(row[column]) : displayCell(column, row[column])}</td>)}</tr>)}{!rows.length ? <tr><td className="px-5 py-8 text-center text-sm text-gray-400" colSpan={columns.length}>Ingen data mottatt</td></tr> : null}</tbody></table></div>;
}

function jobTone(job?: RoborockJobSummary | null) {
  if (job?.status === "error") return "text-red-600 dark:text-red-400";
  if (job?.status === "running") return "text-sky-700 dark:text-sky-400";
  if (job?.status === "stopped") return "text-amber-700 dark:text-amber-400";
  return "text-green-700 dark:text-green-400";
}

function DayActivity({ label, day, latest }: { label: string; day?: RoborockDailySummary | null; latest?: RoborockJobSummary | null }) {
  const summary = day || emptyDay;
  const countLabel = summary.job_count === 1 ? "1 jobb" : `${summary.job_count} jobber`;
  return <div className="min-w-0 px-4 py-3 first:border-r first:border-gray-100 dark:first:border-gray-700/60">
    <div className="flex items-center justify-between gap-3"><strong className="text-sm font-semibold text-gray-700 dark:text-gray-200">{label}</strong><span className="text-xs font-medium tabular-nums text-gray-400">{countLabel}</span></div>
    {summary.job_count ? <><div className="mt-1.5 text-sm tabular-nums text-gray-600 dark:text-gray-300">{decimal(summary.duration_minutes)} min · {decimal(summary.cleaned_area_m2, 1)} m²</div><div className={`mt-1 text-xs font-medium ${jobTone(latest)}`}>Siste {latest?.begin_at ? `kl. ${jobTime(latest.begin_at)} · ` : ""}{latest?.status_label || "registrert"}</div></> : <p className="mt-2 text-sm text-gray-400">Ingen rengjøring</p>}
  </div>;
}

function ResourceValue({ label, value }: { label: string; value?: string | null }) {
  return <div className="min-w-0"><span className="block text-[0.68rem] font-semibold uppercase text-gray-400">{label}</span><strong className={`mt-0.5 block truncate text-xs font-medium ${telemetryTone(value)}`} title={value || "Ikke mottatt"}>{value || "-"}</strong></div>;
}

function RobotCard({ robot }: { robot: RoborockRobotSummary }) {
  const fallbackProblem = Boolean(robot.last_error || (robot.error_code && robot.error_code !== 0) || robot.cloud_online === false);
  const readiness = robot.readiness || {
    status: fallbackProblem ? "attention" : "ready",
    label: fallbackProblem ? "Krever tilsyn" : "Klar",
    issues: robot.last_error ? [robot.last_error] : [],
  } as RoborockReadinessSummary;
  const style = readinessStyle(readiness.status);
  const consumables = robot.consumables;
  const nextPlan = robot.schedules?.next_label
    ? `${robot.schedules.next_label}${robot.schedules.active_count > 1 ? ` · ${robot.schedules.active_count} aktive` : ""}`
    : "Ingen aktiv plan";
  return <AppLink className="group flex h-full flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xs transition hover:border-green-400 hover:shadow-md dark:border-gray-700/60 dark:bg-gray-800 dark:hover:border-green-500/70" to={`/renhold/robot/${encodeURIComponent(robot.duid)}`}>
    <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-5 py-4 dark:border-gray-700/60">
      <span className="flex min-w-0 items-center gap-3"><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${style.icon}`}><MosaicIcon name="robot" size={20} /></span><span className="min-w-0"><strong className="block truncate text-base font-semibold text-gray-800 dark:text-gray-100">{robot.name}</strong><small className="block truncate text-gray-400">{robot.model || "Ukjent modell"}</small></span></span>
      <span className={`mt-1 inline-flex shrink-0 items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold ${style.badge}`}><span className={`h-2 w-2 rounded-full ${style.dot}`} />{readiness.label}</span>
    </div>
    <div className="grid grid-cols-[1fr_auto_auto] items-center gap-5 border-b border-gray-100 px-5 py-3 dark:border-gray-700/60">
      <div className="min-w-0"><span className="block text-xs font-semibold uppercase text-gray-400">Status</span><strong className="mt-0.5 block truncate text-sm font-medium text-gray-700 dark:text-gray-200">{robotStateLabel(robot.state_name)}</strong></div>
      <div><span className="block text-xs font-semibold uppercase text-gray-400">Batteri</span><strong className="mt-0.5 block text-sm font-medium tabular-nums text-gray-700 dark:text-gray-200">{robot.battery == null ? "-" : `${robot.battery} %`}</strong></div>
      <div className="text-right"><span className="block text-xs font-semibold uppercase text-gray-400">Sist lest</span><strong className="mt-0.5 block whitespace-nowrap text-sm font-medium text-gray-700 dark:text-gray-200">{relativeStamp(readiness.telemetry_at || robot.status_at || robot.last_seen_at)}</strong></div>
    </div>
    {readiness.issues.length ? <div className="flex items-start gap-2 border-b border-red-100 bg-red-50 px-5 py-2.5 text-xs text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"><MosaicIcon className="mt-0.5" name="warning" size={14} /><span>{readiness.issues.join(" · ")}</span></div> : null}
    <div className="grid grid-cols-2 border-b border-gray-100 dark:border-gray-700/60"><DayActivity label="I dag" day={robot.today} latest={robot.latest_job_today} /><DayActivity label="I går" day={robot.yesterday} latest={robot.latest_job_yesterday} /></div>
    <div className="grid grid-cols-4 gap-3 border-b border-gray-100 bg-gray-50/70 px-5 py-3 dark:border-gray-700/60 dark:bg-gray-900/20">
      <ResourceValue label="Rentvann" value={readiness.clear_water_label} />
      <ResourceValue label="Skittent" value={readiness.dirty_water_label} />
      <ResourceValue label="Støvpose" value={readiness.dust_bag_label} />
      <ResourceValue label="Dokk" value={readiness.dock_error_label} />
    </div>
    <div className="grid grid-cols-3 gap-4 border-b border-gray-100 px-5 py-3 dark:border-gray-700/60">
      <ResourceValue label="Hovedbørste" value={consumables?.main_brush} />
      <ResourceValue label="Sidebørste" value={consumables?.side_brush} />
      <ResourceValue label="Filter" value={consumables?.filter} />
    </div>
    <div className="mt-auto flex items-center justify-between gap-4 px-5 py-3 text-xs"><span className="min-w-0 truncate text-gray-500 dark:text-gray-400" title={nextPlan}><strong className="mr-1.5 font-semibold text-gray-600 dark:text-gray-300">Neste</strong>{nextPlan}</span><span className="flex shrink-0 items-center gap-1 font-medium text-green-700 dark:text-green-400">Åpne <MosaicIcon name="arrow-right" size={14} /></span></div>
  </AppLink>;
}

function OverviewStrip({ summary }: { summary?: RoborockOverviewSummary | null }) {
  if (!summary) return null;
  const attention = summary.attention_count + summary.offline_count;
  return <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xs dark:border-gray-700/60 dark:bg-gray-800">
    <div className="grid sm:grid-cols-2 xl:grid-cols-4">
      <div className="border-b border-gray-100 px-5 py-4 sm:border-r xl:border-b-0 dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Driftsstatus</span><strong className={`mt-1 block text-lg font-semibold ${attention ? "text-red-600 dark:text-red-400" : "text-green-700 dark:text-green-400"}`}>{attention ? `${attention} krever tilsyn` : `${summary.ready_count} klare`}</strong><small className="text-gray-400">{summary.active_count ? `${summary.active_count} rengjør nå` : "Ingen aktive feil"}</small></div>
      <div className="border-b border-gray-100 px-5 py-4 xl:border-b-0 xl:border-r dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Jobber i dag</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{summary.jobs_today}</strong><small className="text-gray-400">Alle robotene</small></div>
      <div className="border-b border-gray-100 px-5 py-4 sm:border-b-0 sm:border-r dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Rengjøringstid</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{decimal(summary.duration_today)} min</strong><small className="text-gray-400">Samlet i dag</small></div>
      <div className="px-5 py-4"><span className="text-xs font-semibold uppercase text-gray-400">Rengjort areal</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{decimal(summary.area_today, 1)} m²</strong><small className="text-gray-400">Oppdatert {relativeStamp(summary.updated_at)}</small></div>
    </div>
  </section>;
}

function RobotOverview({ data }: { data: RoborockModuleData }) {
  const robots = data.robots || [];
  return <div className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Robotvaskere</h2><p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Driftsstatus, siste jobber og neste plan for alle robotene.</p></div><span className="text-sm font-medium tabular-nums text-gray-500 dark:text-gray-400">{robots.length} registrert</span></div>
    <OverviewStrip summary={data.summary} />
    <div className="grid items-stretch gap-5 md:grid-cols-2">{robots.map((robot) => <RobotCard robot={robot} key={robot.duid} />)}</div>
    {!robots.length ? <Panel><div className="p-8 text-sm text-gray-400">Ingen roboter er registrert.</div></Panel> : null}
  </div>;
}

function DetailDayRows({ summary }: { summary?: RoborockRobotSummary }) {
  return <div className="grid grid-cols-2 divide-x divide-gray-100 dark:divide-gray-700/60"><DayActivity label="I dag" day={summary?.today} latest={summary?.latest_job_today} /><DayActivity label="I går" day={summary?.yesterday} latest={summary?.latest_job_yesterday} /></div>;
}

function ReadinessGrid({ readiness }: { readiness?: RoborockReadinessSummary | null }) {
  const values = [
    ["Rentvann", readiness?.clear_water_label],
    ["Skittent vann", readiness?.dirty_water_label],
    ["Støvpose", readiness?.dust_bag_label],
    ["Dokk", readiness?.dock_error_label],
    ["Lading", readiness?.charge_label],
    ["Signal", readiness?.signal_label],
  ];
  return <div className="grid grid-cols-2 gap-x-8 px-5 py-2 sm:grid-cols-3">{values.map(([label, value]) => <div className="border-b border-gray-100 py-3 dark:border-gray-700/60" key={label}><span className="block text-xs font-semibold uppercase text-gray-400">{label}</span><strong className={`mt-1 block truncate text-sm font-medium ${telemetryTone(value)}`} title={value || "Ikke mottatt"}>{value || "-"}</strong></div>)}</div>;
}

function ScheduleRows({ schedules }: { schedules: JsonRecord[] }) {
  return <div className="divide-y divide-gray-100 px-5 dark:divide-gray-700/60">{schedules.map((row, index) => <div className={`grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center ${row.enabled === false ? "opacity-50" : ""}`} key={String(row.schedule_id || index)}><div className="min-w-0"><strong className="block truncate text-sm font-medium text-gray-700 dark:text-gray-200">{String(row.schedule_label || row.cron || "Ukjent plan")}</strong><small className="mt-0.5 block truncate text-gray-400">{[row.rounds_label, row.fan_label, row.mop_label, row.water_label].filter(Boolean).join(" · ")}</small></div><span className={`text-xs font-semibold ${row.enabled === false ? "text-gray-400" : "text-green-700 dark:text-green-400"}`}>{row.enabled === false ? "Av" : "Aktiv"}</span></div>)}{!schedules.length ? <div className="py-6 text-sm text-gray-400">Ingen planer er mottatt.</div> : null}</div>;
}

function ConsumableGrid({ consumables }: { consumables: JsonRecord }) {
  const values: Array<[string, unknown]> = [
    ["Hovedbørste brukt", consumables.main_brush],
    ["Sidebørste brukt", consumables.side_brush],
    ["Filter brukt", consumables.filter],
    ["Sensor siden rens", consumables.sensor],
    ["Støvtømminger", consumables.dust_collection],
  ];
  return <div className="grid grid-cols-2 gap-x-8 px-5 py-2">{values.map(([label, value]) => <div className="border-b border-gray-100 py-3 dark:border-gray-700/60" key={String(label)}><span className="block text-xs font-semibold uppercase text-gray-400">{label}</span><strong className="mt-1 block text-sm font-medium tabular-nums text-gray-700 dark:text-gray-200">{displayCell(String(label), value)}</strong></div>)}</div>;
}

function RobotDetail({ duid, summary }: { duid: string; summary?: RoborockRobotSummary }) {
  const result = useApi(() => domainApi.get<RoborockRobotDetail>(`/api/renhold/robots/${encodeURIComponent(duid)}`), `roborock-${duid}`);
  if (result.loading && !result.data) return <Panel><div className="p-8 text-sm text-gray-400">Henter robotdetaljer ...</div></Panel>;
  if (result.error || !result.data) return <Panel><div className="flex items-center justify-between gap-3 p-6 text-sm text-red-500"><span>{result.error?.message || "Kunne ikke hente roboten"}</span><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={result.reload}>Prøv igjen</button></div></Panel>;
  const data = result.data;
  const robot = data.robot;
  const status = data.latestStatus || {};
  const metadata = data.metadata || {};
  const network = data.network || {};
  const consumables = data.consumables || {};
  const telemetry = data.latestTelemetry || {};
  const telemetryFields = data.telemetryFields || [];
  const readiness = summary?.readiness;
  const style = readinessStyle(readiness?.status);
  const supportedProbes = (data.telemetryProbes || []).filter((probe) => probe.supported).length;
  const latestJob = summary?.latest_job_today || data.jobs[0];
  return <div className="space-y-5">
    <AppLink className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-green-700 dark:text-gray-400 dark:hover:text-green-400" to="/renhold"><MosaicIcon name="arrow-left" size={14} />Alle robotvaskere</AppLink>
    <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700/60 dark:bg-gray-800">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-100 px-5 py-4 dark:border-gray-700/60">
        <div className="flex min-w-0 items-center gap-3"><span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${style.icon}`}><MosaicIcon name="robot" size={22} /></span><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h2 className="truncate text-lg font-semibold text-gray-800 dark:text-gray-100">{String(robot.name || summary?.name || "Robot")}</h2><span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold ${style.badge}`}><span className={`h-2 w-2 rounded-full ${style.dot}`} />{readiness?.label || "Status mottatt"}</span></div><p className="mt-0.5 text-sm text-gray-400">{String(robot.model || metadata.model || "Ukjent modell")} · sist lest {relativeStamp(telemetry.timestamp || robot.last_seen_at)}</p></div></div>
        <button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={result.reload}><MosaicIcon name="refresh" />Oppdater</button>
      </header>
      {readiness?.issues.length ? <div className="flex items-start gap-2 border-b border-red-100 bg-red-50 px-5 py-3 text-sm text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"><MosaicIcon className="mt-0.5" name="warning" /><span>{readiness.issues.join(" · ")}</span></div> : null}
      <div className="grid grid-cols-2 lg:grid-cols-4">
        <div className="border-b border-r border-gray-100 px-5 py-4 lg:border-b-0 dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Status</span><strong className="mt-1 block text-lg font-semibold text-gray-800 dark:text-gray-100">{String(telemetry.state_label || status.state_label || status.state_name || "-")}</strong><small className="text-gray-400">{String(telemetry.charge_label || status.charge_label || "Ladestatus ukjent")}</small></div>
        <div className="border-b border-gray-100 px-5 py-4 lg:border-b-0 lg:border-r dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Batteri</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{telemetry.battery == null ? status.battery == null ? "-" : `${status.battery} %` : `${telemetry.battery} %`}</strong><small className="text-gray-400">{String(readiness?.signal_label || telemetry.signal_label || "Signal ukjent")}</small></div>
        <div className="border-r border-gray-100 px-5 py-4 dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Siste jobb</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{latestJob?.begin_at ? jobTime(latestJob.begin_at) : "Ingen i dag"}</strong><small className={jobTone(latestJob as RoborockJobSummary)}>{String((latestJob as RoborockJobSummary | undefined)?.status_label || "-")}</small></div>
        <div className="px-5 py-4"><span className="text-xs font-semibold uppercase text-gray-400">Neste plan</span><strong className="mt-1 block truncate text-lg font-semibold text-gray-800 dark:text-gray-100">{summary?.schedules?.next_label || "Ingen aktiv"}</strong><small className="text-gray-400">{summary?.schedules?.active_count ? `${summary.schedules.active_count} aktive planer` : "Ingen planer"}</small></div>
      </div>
    </section>
    <div className="grid gap-5 xl:grid-cols-2">
      <Panel title="Rengjøring" subtitle="Samlet aktivitet i dag og i går"><DetailDayRows summary={summary} /></Panel>
      <Panel title="Driftsklar" subtitle={readiness?.telemetry_at ? `Kontrollert ${stamp(readiness.telemetry_at)}` : "Siste telemetri"}><ReadinessGrid readiness={readiness} /></Panel>
    </div>
    <div className="grid gap-5 xl:grid-cols-2">
      <Panel title="Planlagte jobber" subtitle={`${data.schedules.filter((row) => row.enabled !== false).length} aktive planer`}><ScheduleRows schedules={data.schedules} /></Panel>
      <Panel title="Forbruksdeler" subtitle={consumables.timestamp ? `Målt ${stamp(consumables.timestamp)}` : "Ikke mottatt"}><ConsumableGrid consumables={consumables} /></Panel>
    </div>
    <Panel title="Siste rengjøringer" subtitle="Nyeste jobb øverst"><CompactTable columns={["begin_at", "end_at", "duration_minutes", "cleaned_area_m2", "rounds_label", "status_label", "error_label"]} rows={data.jobs} /></Panel>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(22rem,0.7fr)]">
      <Panel title="Siste kart" subtitle={data.latestMap ? `${stamp(data.latestMap.timestamp)} · ${displayCell("rooms", data.latestMap.rooms)} rom` : "Ikke mottatt"}><div className="p-5">{data.latestMap?.imageDataUrl ? <img className="max-h-[34rem] w-full rounded-lg bg-gray-900 object-contain" src={data.latestMap.imageDataUrl} alt={`Kart for ${String(robot.name || "robot")}`} /> : <div className="flex h-56 items-center justify-center rounded-lg bg-gray-50 text-sm text-gray-400 dark:bg-gray-900/30">Ingen kart er mottatt</div>}</div></Panel>
      <Panel title="Nøkkelverdier" subtitle={telemetry.timestamp ? `Sist lest ${stamp(telemetry.timestamp)}` : "Venter på telemetri"}><div className="px-5 py-2"><Field label="Sugekraft" value={status.fan_label} /><Field label="Mopp" value={status.mop_label} /><Field label="Rengjøringstid" value={status.clean_time_seconds == null ? "-" : `${Math.round(Number(status.clean_time_seconds) / 60)} min`} /><Field label="Areal" value={status.clean_area_m2 == null ? "-" : `${status.clean_area_m2} m²`} /><Field label="Lokal IP" value={robot.local_ip || status.local_ip} /></div></Panel>
    </div>
    <Panel title="Alle telemetriverdier" subtitle={telemetry.timestamp ? `Sist lest ${stamp(telemetry.timestamp)}` : "Venter på første telemetrimåling"}>{telemetryFields.length ? <TelemetryFields fields={telemetryFields} /> : <div className="p-8 text-sm text-gray-400">Ingen telemetri er mottatt ennå.</div>}</Panel>
    <Panel title="Tilstandsendringer" subtitle={`${data.telemetryEvents.length} siste hendelser`}><CompactTable columns={["timestamp", "title", "previous_label", "current_label", "severity"]} rows={data.telemetryEvents} /></Panel>
    <Panel title="Telemetrilogg" subtitle={`${data.telemetrySamples.length} minuttmålinger`}><CompactTable columns={["timestamp", "state_label", "battery", "charge_label", "clear_water_label", "dirty_water_label", "dust_bag_label", "dock_error_label"]} rows={data.telemetrySamples.slice(0, 120)} /></Panel>
    <details className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700/60 dark:bg-gray-800">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-sm font-semibold text-gray-700 dark:text-gray-200"><span className="flex items-center gap-2"><MosaicIcon name="settings" />Teknisk informasjon og API-diagnostikk</span><span className="flex items-center gap-2 text-xs font-medium text-gray-400">{supportedProbes}/{data.telemetryProbes.length} lesekall støttes <MosaicIcon name="chevron-down" /></span></summary>
      <div className="space-y-6 border-t border-gray-100 p-5 dark:border-gray-700/60">
        <div className="grid gap-x-10 xl:grid-cols-2"><section><h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-200">Robotidentitet</h3><Field label="Navn" value={robot.name} /><Field label="DUID" value={robot.duid} /><Field label="Serienummer" value={robot.serial_number || metadata.sn} /><Field label="Produkt-ID" value={metadata.product_id || robot.product} /><Field label="Modell" value={robot.model || metadata.model} /><Field label="Firmware" value={robot.firmware || metadata.fv} /><Field label="Protokoll" value={robot.protocol_version || metadata.pv} /><Field label="Tidssone" value={robot.time_zone_id || metadata.time_zone_id} /><Field label="Cloud" value={robot.cloud_label} /><Field label="Delt" value={robot.shared_label} /></section><section><h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-200">Nettverk</h3><Field label="Lokal IP" value={robot.local_ip || status.local_ip} /><Field label="SSID" value={network.ssid} /><Field label="MAC" value={network.mac} /><Field label="Aksesspunkt" value={network.bssid} /><Field label="Sist lokal" value={stamp(robot.last_local_at)} /></section></div>
        <section><h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-200">API-dekning</h3>{data.telemetryProbes.length ? <TelemetryProbes probes={data.telemetryProbes} /> : <p className="py-4 text-sm text-gray-400">Venter på første fullstendige API-kontroll.</p>}</section>
        <details className="border-t border-gray-100 pt-4 dark:border-gray-700/60"><summary className="cursor-pointer text-sm font-semibold text-gray-700 dark:text-gray-200">Komplett råstatus ({data.rawStatusFields.length} felter)</summary><div className="mt-3"><CompactTable columns={["field", "value"]} rows={data.rawStatusFields} /></div></details>
        <details className="border-t border-gray-100 pt-4 dark:border-gray-700/60"><summary className="cursor-pointer text-sm font-semibold text-gray-700 dark:text-gray-200">Statushistorikk ({data.statuses.length} målinger)</summary><div className="mt-3"><CompactTable columns={["timestamp", "state_label", "battery", "fan_label", "mop_label", "signal_label", "local_ip"]} rows={data.statuses.slice(0, 30)} /></div></details>
      </div>
    </details>
  </div>;
}

export function RoborockSpecial({ data }: { data: RoborockModuleData }) {
  const { pathname } = useAppLocation();
  const robots = data.robots || [];
  const match = pathname.match(/^\/renhold\/robot\/([^/]+)$/);
  const selected = match ? decodeURIComponent(match[1]) : "";
  const summary = robots.find((robot) => robot.duid === selected);
  if (!selected) return <RobotOverview data={data} />;
  if (!summary) return <Panel title="Robot ikke funnet"><div className="p-8 text-sm text-gray-400">Roboten finnes ikke lenger i den registrerte robotlisten.</div></Panel>;
  return <RobotDetail duid={selected} summary={summary} />;
}
