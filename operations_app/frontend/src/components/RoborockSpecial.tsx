import { useEffect, useState } from "react";
import { domainApi } from "@lilletorget/microapp-ui/api";
import { displayCell, valueLabel } from "@lilletorget/microapp-ui/format";
import { useApi } from "@lilletorget/microapp-ui/hooks";
import { AppLink, useAppLocation } from "@lilletorget/microapp-ui/router";
import type {
  JsonRecord,
} from "@lilletorget/microapp-ui/types";
import type {
  RoborockActiveCycleSummary,
  RoborockDailySummary,
  RoborockJobSummary,
  RoborockModuleData,
  RoborockNightJob,
  RoborockNightReport,
  RoborockNightRobot,
  RoborockOverviewSummary,
  RoborockReadinessSummary,
  RoborockRobotDetail,
  RoborockRobotSummary,
} from "../roborock-types";
import { MosaicIcon, Panel } from "@lilletorget/microapp-ui";

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

function durationLabel(value: unknown) {
  const minutes = Math.max(0, Math.round(Number(value || 0)));
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (!hours) return `${remainder} min`;
  return remainder ? `${hours} t ${remainder} min` : `${hours} t`;
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

function ActiveCycleBand({ cycle, compact = false }: { cycle: RoborockActiveCycleSummary; compact?: boolean }) {
  const timing = [
    cycle.started_at ? `Start ca. ${jobTime(cycle.started_at)}` : null,
    cycle.dock_since ? `i dokk siden ca. ${jobTime(cycle.dock_since)}` : cycle.last_floor_at ? `sist på gulvet ca. ${jobTime(cycle.last_floor_at)}` : null,
  ].filter(Boolean).join(" · ");
  const measures = [
    cycle.active_minutes == null ? null : `${decimal(cycle.active_minutes)} min aktiv tid`,
    cycle.cleaned_area_m2 == null ? null : `${decimal(cycle.cleaned_area_m2, 1)} m²`,
    cycle.progress_percent == null ? null : `${cycle.progress_percent} %`,
  ].filter(Boolean).join(" · ");
  return <div className={`flex flex-wrap items-center justify-between gap-x-5 gap-y-2 border-sky-200 bg-sky-50/80 text-sky-950 dark:border-sky-500/20 dark:bg-sky-500/10 dark:text-sky-100 ${compact ? "border-b px-5 py-2.5" : "border-b px-5 py-3"}`}>
    <div className="flex min-w-0 items-center gap-3"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sky-500/15 text-sky-700 dark:text-sky-300"><MosaicIcon name="robot" size={16} /></span><span className="min-w-0"><strong className="block text-sm font-semibold">Pågående rengjøringssyklus</strong><small className="block text-sky-700 dark:text-sky-300">{cycle.phase_label}{timing ? ` · ${timing}` : ""}</small></span></div>
    {measures ? <span className="shrink-0 text-xs font-medium tabular-nums text-sky-700 dark:text-sky-300">{measures}</span> : null}
  </div>;
}

function DayActivity({ label, day, latest }: { label: string; day?: RoborockDailySummary | null; latest?: RoborockJobSummary | null }) {
  const summary = day || emptyDay;
  const countLabel = summary.job_count === 1 ? "1 jobb" : `${summary.job_count} jobber`;
  return <div className="min-w-0 px-4 py-3 first:border-r first:border-gray-100 dark:first:border-gray-700/60">
    <div className="flex items-center justify-between gap-3"><strong className="text-sm font-semibold text-gray-700 dark:text-gray-200">{label}</strong><span className="text-xs font-medium tabular-nums text-gray-400">{countLabel}</span></div>
    {summary.job_count ? <><div className="mt-1.5 text-sm tabular-nums text-gray-600 dark:text-gray-300">{decimal(summary.duration_minutes)} min · {decimal(summary.cleaned_area_m2, 1)} m²</div><div className={`mt-1 text-xs font-medium ${jobTone(latest)}`}>{latest?.status === "complete" ? "Siste ferdige" : "Siste registrerte"} {latest?.begin_at ? `kl. ${jobTime(latest.begin_at)} · ` : ""}{latest?.status_label || "registrert"}</div></> : <p className="mt-2 text-sm text-gray-400">Ingen rengjøring</p>}
  </div>;
}

function isSupportedResource(value: unknown) {
  const text = String(value || "").trim().toLocaleLowerCase("nb-NO");
  return Boolean(text && text !== "-" && text !== "ikke støttet");
}

function ResourceValue({ label, value }: { label: string; value?: string | null }) {
  return <div className="min-w-0"><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">{label}</span><strong className={`mt-0.5 block truncate text-xs font-medium ${telemetryTone(value)}`} title={value || "Ikke mottatt"}>{value || "-"}</strong></div>;
}

function OverviewDayActivity({ robot }: { robot: RoborockRobotSummary }) {
  const today = robot.today || emptyDay;
  const yesterday = robot.yesterday || emptyDay;
  const todayJobs = today.job_count === 1 ? "1 jobb" : `${today.job_count} jobber`;
  const yesterdayJobs = yesterday.job_count === 1 ? "1 jobb" : `${yesterday.job_count} jobber`;
  const latest = robot.latest_job_today;
  return <div className="border-b border-gray-100 dark:border-gray-700/60">
    <div className="px-5 py-3.5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <strong className="text-sm font-semibold text-gray-800 dark:text-gray-100">I dag</strong>
        <span className="text-xs font-medium tabular-nums text-gray-400">{todayJobs}</span>
      </div>
      {today.job_count ? <>
        <div className="mt-1.5 flex flex-wrap items-baseline gap-x-4 gap-y-1 tabular-nums"><strong className="text-lg font-semibold text-gray-800 dark:text-gray-100">{durationLabel(today.duration_minutes)}</strong><span className="text-sm font-medium text-gray-500 dark:text-gray-300">{decimal(today.cleaned_area_m2, 1)} m²</span></div>
        <p className={`mt-1 text-xs font-medium ${jobTone(latest)}`}>{latest?.status === "complete" ? "Siste ferdige" : "Siste registrerte"}{latest?.begin_at ? ` kl. ${jobTime(latest.begin_at)}` : ""}{latest?.status_label ? ` · ${latest.status_label}` : ""}</p>
      </> : <p className="mt-2 text-sm text-gray-400">Ingen rengjøring registrert i dag</p>}
    </div>
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 bg-gray-50/70 px-5 py-2.5 text-xs dark:bg-gray-900/20">
      <span className="font-semibold text-gray-500 dark:text-gray-300">I går <span className="ml-1 font-normal text-gray-400">{yesterdayJobs}</span></span>
      <span className="tabular-nums text-gray-500 dark:text-gray-400">{yesterday.job_count ? `${durationLabel(yesterday.duration_minutes)} · ${decimal(yesterday.cleaned_area_m2, 1)} m²` : "Ingen rengjøring"}</span>
    </div>
  </div>;
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
  const resources = [
    ["Rentvann", readiness.clear_water_label],
    ["Skittent vann", readiness.dirty_water_label],
    ["Støvpose", readiness.dust_bag_label],
    ["Dokk", readiness.dock_error_label],
  ].filter(([, value]) => isSupportedResource(value));
  const nextPlan = robot.schedules?.next_label
    ? `${robot.schedules.next_label}${robot.schedules.active_count > 1 ? ` · ${robot.schedules.active_count} planer` : ""}`
    : "Ingen aktiv plan";
  return <AppLink className="group flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xs transition hover:border-green-400 hover:shadow-md dark:border-gray-700/60 dark:bg-gray-800 dark:hover:border-green-500/70" to={`/renhold/robot/${encodeURIComponent(robot.duid)}`}>
    <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-5 py-3.5 dark:border-gray-700/60">
      <span className="flex min-w-0 items-center gap-3"><span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${style.icon}`}><MosaicIcon name="robot" size={18} /></span><span className="min-w-0"><strong className="block truncate text-base font-semibold text-gray-800 dark:text-gray-100">{robot.name}</strong><small className="block truncate text-xs text-gray-400" title={robot.model || undefined}>Oppdatert {relativeStamp(readiness.telemetry_at || robot.status_at || robot.last_seen_at)}</small></span></span>
      <span className={`inline-flex shrink-0 items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold ${style.badge}`}><span className={`h-2 w-2 rounded-full ${style.dot}`} />{readiness.label}</span>
    </div>
    <div className="grid grid-cols-[minmax(0,0.8fr)_auto_minmax(0,1.35fr)] gap-5 border-b border-gray-100 px-5 py-3 dark:border-gray-700/60">
      <div className="min-w-0"><span className="block text-[0.68rem] font-semibold uppercase text-gray-400">Nå</span><strong className="mt-0.5 block truncate text-sm font-medium text-gray-700 dark:text-gray-200">{robotStateLabel(robot.state_name)}</strong></div>
      <div><span className="block text-[0.68rem] font-semibold uppercase text-gray-400">Batteri</span><strong className="mt-0.5 block text-sm font-medium tabular-nums text-gray-700 dark:text-gray-200">{robot.battery == null ? "-" : `${robot.battery} %`}</strong></div>
      <div className="min-w-0 text-right"><span className="block text-[0.68rem] font-semibold uppercase text-gray-400">Neste plan</span><strong className="mt-0.5 block truncate text-sm font-medium text-gray-700 dark:text-gray-200" title={nextPlan}>{nextPlan}</strong></div>
    </div>
    {readiness.issues.length ? <div className="flex items-start gap-2 border-b border-red-100 bg-red-50 px-5 py-2.5 text-xs text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"><MosaicIcon className="mt-0.5" name="warning" size={14} /><span>{readiness.issues.join(" · ")}</span></div> : null}
    {robot.active_cycle ? <ActiveCycleBand cycle={robot.active_cycle} compact /> : null}
    <OverviewDayActivity robot={robot} />
    {resources.length ? <div className={`grid gap-3 border-b border-gray-100 px-5 py-2.5 dark:border-gray-700/60 ${resources.length >= 4 ? "grid-cols-4" : resources.length === 3 ? "grid-cols-3" : "grid-cols-2"}`}>{resources.map(([label, value]) => <ResourceValue key={label} label={String(label)} value={value} />)}</div> : null}
    {consumables ? <div className="flex flex-wrap gap-x-4 gap-y-1 border-b border-gray-100 bg-gray-50/70 px-5 py-2 text-[0.7rem] text-gray-400 dark:border-gray-700/60 dark:bg-gray-900/20"><strong className="font-semibold text-gray-500 dark:text-gray-300">Forbruksdeler brukt</strong><span>H.børste {consumables.main_brush || "-"}</span><span>S.børste {consumables.side_brush || "-"}</span><span>Filter {consumables.filter || "-"}</span></div> : null}
    <div className="mt-auto flex items-center justify-end px-5 py-2.5 text-xs"><span className="flex items-center gap-1 font-medium text-green-700 dark:text-green-400">Se robot <MosaicIcon name="arrow-right" size={14} /></span></div>
  </AppLink>;
}

function OverviewStrip({ summary, robots }: { summary?: RoborockOverviewSummary | null; robots: RoborockRobotSummary[] }) {
  if (!summary) return null;
  const attention = summary.attention_count + summary.offline_count;
  const activeNames = robots.filter((robot) => robot.readiness?.status === "active" || robot.active_cycle).map((robot) => robot.name);
  return <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xs dark:border-gray-700/60 dark:bg-gray-800">
    <div className="grid sm:grid-cols-2 xl:grid-cols-4">
      <div className="border-b border-gray-100 px-5 py-3.5 sm:border-r xl:border-b-0 dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Driftsstatus</span><strong className={`mt-1 block text-lg font-semibold ${attention ? "text-red-600 dark:text-red-400" : "text-green-700 dark:text-green-400"}`}>{attention ? `${attention} krever tilsyn` : "Alle rapporterer"}</strong><small className="text-gray-400">{summary.robot_count} roboter · oppdatert {relativeStamp(summary.updated_at)}</small></div>
      <div className="border-b border-gray-100 px-5 py-3.5 xl:border-b-0 xl:border-r dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Rengjør nå</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-sky-700 dark:text-sky-400">{summary.active_count}</strong><small className="block truncate text-gray-400" title={activeNames.join(", ")}>{activeNames.length ? activeNames.join(", ") : "Ingen aktive jobber"}</small></div>
      <div className="border-b border-gray-100 px-5 py-3.5 sm:border-b-0 sm:border-r dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Jobber i dag</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{summary.jobs_today}</strong><small className="text-gray-400">{decimal(summary.area_today, 1)} m² rengjort</small></div>
      <div className="px-5 py-3.5"><span className="text-xs font-semibold uppercase text-gray-400">Samlet rengjøringstid</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{durationLabel(summary.duration_today)}</strong><small className="text-gray-400">Alle robotene i dag</small></div>
    </div>
  </section>;
}

function RobotOverview({ data }: { data: RoborockModuleData }) {
  const robots = data.robots || [];
  return <div className="space-y-4">
    <OverviewStrip summary={data.summary} robots={robots} />
    <div className="grid items-start gap-5 md:grid-cols-2">{robots.map((robot) => <RobotCard robot={robot} key={robot.duid} />)}</div>
    {!robots.length ? <Panel><div className="p-8 text-sm text-gray-400">Ingen roboter er registrert.</div></Panel> : null}
  </div>;
}

function norwayDay() {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Oslo" }).format(new Date());
}

function reportDayLabel(value: string) {
  const parsed = new Date(`${value}T12:00:00`);
  const label = parsed.toLocaleDateString("nb-NO", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function reportTime(value: string | null | undefined) {
  const parsed = parsedDate(value);
  return parsed ? parsed.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Oslo" }) : "-";
}

function reportTone(status: string) {
  if (status === "error") return { panel: "border-red-200 bg-red-50/70 dark:border-red-500/30 dark:bg-red-500/10", text: "text-red-700 dark:text-red-300", dot: "bg-red-500" };
  if (status === "warning") return { panel: "border-amber-200 bg-amber-50/70 dark:border-amber-500/30 dark:bg-amber-500/10", text: "text-amber-800 dark:text-amber-300", dot: "bg-amber-500" };
  if (status === "ok") return { panel: "border-green-200 bg-green-50/70 dark:border-green-500/30 dark:bg-green-500/10", text: "text-green-800 dark:text-green-300", dot: "bg-green-500" };
  return { panel: "border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/20", text: "text-gray-600 dark:text-gray-300", dot: "bg-gray-400" };
}

function jobBarColor(job: RoborockNightJob) {
  if (job.status === "error") return "bg-red-500";
  if (job.status === "warning") return "bg-amber-500";
  if (job.cleaningType === "mop") return "bg-emerald-500";
  if (job.cleaningType === "vacuum_mop") return "bg-violet-500";
  return "bg-sky-500";
}

function timelinePosition(value: string | null | undefined, startAt: string, endAt: string) {
  const valueDate = parsedDate(value);
  const start = parsedDate(startAt);
  const end = parsedDate(endAt);
  if (!valueDate || !start || !end || end <= start) return 0;
  return Math.max(0, Math.min(100, ((valueDate.getTime() - start.getTime()) / (end.getTime() - start.getTime())) * 100));
}

function NightTimeline({ report }: { report: RoborockNightReport }) {
  const hourLabels = ["20", "22", "00", "02", "04", "06", "08"];
  const readyPosition = timelinePosition(report.window.readyBy, report.window.startAt, report.window.endAt);
  return <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xs dark:border-gray-700/60 dark:bg-gray-800">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-3 dark:border-gray-700/60">
      <div><h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Nattforløp</h2><p className="mt-0.5 text-xs text-gray-400">Registrerte jobber og frist før åpning kl. {reportTime(report.window.readyBy)}</p></div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-300"><span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-sm bg-sky-500" />Støvsuging</span><span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />Vask</span><span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-sm bg-violet-500" />Begge</span><span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-sm bg-amber-500" />Varsel</span></div>
    </header>
    <div className="px-5 py-4">
      <div className="mb-1 grid grid-cols-[6.5rem_minmax(0,1fr)] gap-3 text-[0.65rem] font-medium text-gray-400"><span /><div className="flex justify-between">{hourLabels.map((hour) => <span key={hour}>{hour}:00</span>)}</div></div>
      <div className="space-y-2.5">{report.robots.map((robot) => <div className="grid grid-cols-[6.5rem_minmax(0,1fr)] items-center gap-3" key={robot.duid}><strong className="truncate text-xs font-semibold text-gray-600 dark:text-gray-200" title={robot.name}>{robot.name}</strong><div className="relative h-7 overflow-hidden rounded-md border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/30">
        <span className="absolute inset-y-0 z-10 border-l border-dashed border-red-400/80" style={{ left: `${readyPosition}%` }} title={`Åpning ${reportTime(report.window.readyBy)}`} />
        {robot.jobs.map((job) => { const left = timelinePosition(job.startedAt, report.window.startAt, report.window.endAt); const right = timelinePosition(job.endedAt || job.startedAt, report.window.startAt, report.window.endAt); return <span className={`absolute inset-y-1 rounded-sm ${jobBarColor(job)}`} key={job.recordId} style={{ left: `${left}%`, width: `${Math.max(0.7, right - left)}%` }} title={`${reportTime(job.startedAt)}–${reportTime(job.endedAt)} · ${job.cleaningTypeLabel} · ${decimal(job.areaM2, 1)} m²`} />; })}
      </div></div>)}</div>
    </div>
  </section>;
}

function batteryRange(job: RoborockNightJob) {
  if (job.batteryStart == null && job.batteryEnd == null) return "-";
  if (job.batteryStart == null) return `${job.batteryEnd} %`;
  if (job.batteryEnd == null) return `${job.batteryStart} %`;
  return `${job.batteryStart} → ${job.batteryEnd} %`;
}

function washCountLabel(job: RoborockNightJob) {
  if (job.cleaningType === "vacuum") return "-";
  if (job.washCount == null) return "Ikke mottatt";
  return job.expectedWashCount == null ? `${job.washCount}` : `${job.washCount} / ca. ${job.expectedWashCount}`;
}

function NightRobotReport({ robot, readyBy }: { robot: RoborockNightRobot; readyBy: string }) {
  const tone = reportTone(robot.status);
  const settings = robot.settings.supported
    ? `${robot.settings.modeLabel || "Moppevask"}${robot.settings.intervalMinutes ? ` · hvert ${robot.settings.intervalMinutes}. min` : ""}${robot.settings.automatic ? " · automatisk" : ""}`
    : "Ikke støttet på denne roboten";
  return <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xs dark:border-gray-700/60 dark:bg-gray-800">
    <header className="grid gap-4 border-b border-gray-100 px-5 py-4 md:grid-cols-[minmax(12rem,1fr)_auto_auto] md:items-center dark:border-gray-700/60">
      <div className="flex min-w-0 items-center gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-green-500/10 text-green-700 dark:text-green-400"><MosaicIcon name="robot" size={18} /></span><div className="min-w-0"><h2 className="truncate text-base font-semibold text-gray-800 dark:text-gray-100">{robot.name}</h2><p className="truncate text-xs text-gray-400">{robot.model || "Modell ikke registrert"}</p></div></div>
      <div className="text-sm tabular-nums text-gray-500 dark:text-gray-300"><strong className="font-semibold text-gray-800 dark:text-gray-100">{robot.totals.jobs} {robot.totals.jobs === 1 ? "jobb" : "jobber"}</strong> · {durationLabel(robot.totals.durationMinutes)} · {decimal(robot.totals.areaM2, 1)} m²</div>
      <span className={`inline-flex w-fit items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${tone.panel} ${tone.text}`}><i className={`h-2 w-2 rounded-full ${tone.dot}`} />{robot.statusLabel}</span>
    </header>
    <div className="grid border-b border-gray-100 bg-gray-50/60 sm:grid-cols-3 dark:border-gray-700/60 dark:bg-gray-900/20">
      <div className="border-b px-5 py-3 sm:border-b-0 sm:border-r dark:border-gray-700/60"><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Siste jobb ferdig</span><strong className="mt-1 block text-sm font-semibold tabular-nums text-gray-700 dark:text-gray-200">{reportTime(robot.readiness.lastJobEndedAt)}</strong><small className={robot.readiness.readyBeforeOpening ? "text-green-700 dark:text-green-400" : "text-amber-700 dark:text-amber-400"}>{robot.jobs.length ? robot.readiness.readyBeforeOpening ? `Før åpning ${reportTime(readyBy)}` : `Etter åpning ${reportTime(readyBy)}` : "Ingen jobb"}</small></div>
      <div className="border-b px-5 py-3 sm:border-b-0 sm:border-r dark:border-gray-700/60"><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Batteri ved åpning</span><strong className="mt-1 block text-sm font-semibold tabular-nums text-gray-700 dark:text-gray-200">{robot.readiness.batteryAtOpening == null ? "-" : `${robot.readiness.batteryAtOpening} %`}</strong><small className="text-gray-400">{robot.readiness.fullChargeAt ? `Fullt kl. ${reportTime(robot.readiness.fullChargeAt)}` : "Ikke fullt før rapportslutt"}</small></div>
      <div className="px-5 py-3"><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Innstilling moppevask</span><strong className="mt-1 block text-sm font-semibold text-gray-700 dark:text-gray-200">{settings}</strong><small className="text-gray-400">Sist registrerte innstilling denne natten</small></div>
    </div>
    <div className="overflow-x-auto"><table className="w-full min-w-[58rem] table-auto"><thead className="bg-white text-[0.65rem] uppercase text-gray-400 dark:bg-gray-800"><tr><th className="px-5 py-3 text-left font-semibold">Tid</th><th className="px-4 py-3 text-left font-semibold">Rengjøring</th><th className="px-4 py-3 text-right font-semibold">Aktiv tid</th><th className="px-4 py-3 text-right font-semibold">Areal</th><th className="px-4 py-3 text-right font-semibold">Batteri</th><th className="px-4 py-3 text-right font-semibold">Moppevask</th><th className="px-5 py-3 text-left font-semibold">Resultat</th></tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{robot.jobs.map((job) => { const jobToneValue = reportTone(job.status); return <tr className="align-top hover:bg-gray-50/60 dark:hover:bg-gray-700/20" key={job.recordId}><td className="whitespace-nowrap px-5 py-3 font-medium tabular-nums text-gray-700 dark:text-gray-200">{reportTime(job.startedAt)}–{reportTime(job.endedAt)}</td><td className="px-4 py-3"><strong className="block font-medium text-gray-700 dark:text-gray-200">{job.cleaningTypeLabel}</strong><small className="block text-gray-400">{job.modeLabel}</small></td><td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">{durationLabel(job.durationMinutes)}</td><td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">{decimal(job.areaM2, 1)} m²</td><td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">{batteryRange(job)}</td><td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">{washCountLabel(job)}</td><td className="px-5 py-3"><span className={`inline-flex items-center gap-1.5 font-semibold ${jobToneValue.text}`}><i className={`h-2 w-2 rounded-full ${jobToneValue.dot}`} />{job.statusLabel}</span>{job.issues.length ? <small className="mt-1 block max-w-xs text-gray-500 dark:text-gray-400">{job.issues.join(" · ")}</small> : null}</td></tr>; })}{!robot.jobs.length ? <tr><td className="px-5 py-7 text-center text-sm text-gray-400" colSpan={7}>Ingen rengjøringsjobber i nattvinduet.</td></tr> : null}</tbody></table></div>
    {robot.findings.length ? <div className="flex flex-wrap gap-x-5 gap-y-1 border-t border-gray-100 bg-gray-50/60 px-5 py-3 text-xs text-gray-500 dark:border-gray-700/60 dark:bg-gray-900/20 dark:text-gray-300">{robot.findings.map((finding) => <span className="flex items-start gap-1.5" key={finding}><i className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${tone.dot}`} />{finding}</span>)}</div> : null}
  </section>;
}

function NightReport() {
  const { search, navigate } = useAppLocation();
  const today = norwayDay();
  const selectedDay = new URLSearchParams(search).get("day") || today;
  const result = useApi(() => domainApi.get<RoborockNightReport>(`/api/renhold/night-report?day=${encodeURIComponent(selectedDay)}`), `roborock-night-report-${selectedDay}`);
  const go = (day: string) => navigate(`/renhold/rapport?day=${encodeURIComponent(day)}`);
  if (result.loading && !result.data) return <Panel><div className="p-8 text-sm text-gray-400">Bygger nattrapport ...</div></Panel>;
  if (result.error || !result.data) return <Panel><div className="flex items-center justify-between gap-3 p-6 text-sm text-red-500"><span>{result.error?.message || "Kunne ikke bygge rapporten"}</span><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={result.reload}>Prøv igjen</button></div></Panel>;
  const report = result.data;
  const tone = reportTone(report.conclusion.status);
  return <div className="space-y-4">
    <section className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-xs dark:border-gray-700/60 dark:bg-gray-800">
      <div className="flex items-center gap-2"><button aria-label="Forrige dag" className="btn h-9 w-9 border-gray-200 bg-white p-0 dark:border-gray-700 dark:bg-gray-800" onClick={() => go(report.previousDay)} title="Forrige dag"><MosaicIcon name="arrow-left" /></button><button className="btn h-9 border-gray-200 bg-white px-3 dark:border-gray-700 dark:bg-gray-800" onClick={() => go(today)}>Siste natt</button><button aria-label="Neste dag" className="btn h-9 w-9 border-gray-200 bg-white p-0 dark:border-gray-700 dark:bg-gray-800" disabled={report.nextDay > today} onClick={() => go(report.nextDay)} title="Neste dag"><MosaicIcon name="arrow-right" /></button></div>
      <div className="text-center"><h1 className="text-base font-semibold text-gray-800 dark:text-gray-100">Natt til {reportDayLabel(report.day).toLocaleLowerCase("nb-NO")}</h1><p className="mt-0.5 text-xs text-gray-400">Kl. {reportTime(report.window.startAt)}–{reportTime(report.window.endAt)} · maskinelt generert {stamp(report.generatedAt)}</p></div>
      <label className="flex items-center gap-2 text-xs font-medium text-gray-400"><MosaicIcon name="calendar" /><input className="form-input h-9 py-1.5 text-sm" max={today} type="date" value={report.day} onChange={(event) => event.target.value && go(event.target.value)} /></label>
    </section>
    <section className={`overflow-hidden rounded-lg border ${tone.panel}`}>
      <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4"><div className="flex min-w-0 items-start gap-3"><span className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/70 ${tone.text} dark:bg-gray-900/30`}><MosaicIcon name={report.conclusion.status === "ok" ? "robot" : "warning"} size={18} /></span><div><h2 className={`text-base font-semibold ${tone.text}`}>{report.conclusion.title}</h2><p className="mt-0.5 text-sm text-gray-600 dark:text-gray-300">{report.conclusion.detail}</p></div></div><span className={`inline-flex items-center gap-2 text-xs font-semibold ${tone.text}`}><i className={`h-2 w-2 rounded-full ${tone.dot}`} />{report.summary.errors ? `${report.summary.errors} feil` : report.summary.warnings ? `${report.summary.warnings} varsler` : "Ingen registrerte avvik"}</span></div>
      <div className="grid border-t border-black/5 bg-white/50 sm:grid-cols-2 xl:grid-cols-4 dark:border-white/10 dark:bg-gray-900/20"><div className="border-b px-5 py-3 sm:border-r xl:border-b-0 dark:border-gray-700/40"><span className="text-[0.65rem] font-semibold uppercase text-gray-400">Jobber</span><strong className="mt-0.5 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{report.summary.completed}/{report.summary.jobs}</strong><small className="text-gray-500 dark:text-gray-400">fullført</small></div><div className="border-b px-5 py-3 xl:border-b-0 xl:border-r dark:border-gray-700/40"><span className="text-[0.65rem] font-semibold uppercase text-gray-400">Rengjøringstid</span><strong className="mt-0.5 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{durationLabel(report.summary.durationMinutes)}</strong><small className="text-gray-500 dark:text-gray-400">aktiv tid</small></div><div className="border-b px-5 py-3 sm:border-b-0 sm:border-r dark:border-gray-700/40"><span className="text-[0.65rem] font-semibold uppercase text-gray-400">Areal</span><strong className="mt-0.5 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{decimal(report.summary.areaM2, 1)} m²</strong><small className="text-gray-500 dark:text-gray-400">samlet registrert</small></div><div className="px-5 py-3"><span className="text-[0.65rem] font-semibold uppercase text-gray-400">Ferdig før åpning</span><strong className="mt-0.5 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{report.summary.readyBeforeOpening}/{report.summary.activeRobots}</strong><small className="text-gray-500 dark:text-gray-400">aktive roboter</small></div></div>
    </section>
    <NightTimeline report={report} />
    {report.robots.map((robot) => <NightRobotReport key={robot.duid} robot={robot} readyBy={report.window.readyBy} />)}
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

const controlActionLabels: Record<string, string> = {
  dry_run: "Tilkoblingskontroll",
  start: "Start",
  pause: "Pause",
  resume: "Fortsett",
  stop: "Stopp og dokk",
  dock: "Til dokk",
  test_start_stop: "Kort kontrolltest",
  clean_zone: "Vask sone",
};

function controlStateLabel(value: JsonRecord | null | undefined) {
  return robotStateLabel(value?.state_name || value?.state_code);
}

function RobotControls({ duid, data, reload }: { duid: string; data: RoborockRobotDetail; reload: () => void }) {
  const [running, setRunning] = useState("");
  const [message, setMessage] = useState("");
  if (!data.canControl) return null;

  async function run(action: string) {
    const label = controlActionLabels[action] || action;
    const question = action === "dry_run"
      ? "Kontrollere forbindelsen uten å bevege roboten?"
      : action === "test_start_stop"
        ? "Roboten starter i 5 sekunder og returnerer deretter til dokken. Er gulvet fritt?"
        : `${label} roboten nå?`;
    if (!window.confirm(question)) return;
    setRunning(action);
    setMessage("");
    try {
      const response = await domainApi.mutate<{ message?: string }>(
        `/api/renhold/robots/${encodeURIComponent(duid)}/control`,
        "POST",
        { action, test_duration_seconds: 5 },
      );
      setMessage(response.message || `${label} er utført.`);
      reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setRunning("");
    }
  }

  const latest = data.controlHistory?.[0];
  const buttons = [
    ["dry_run", "Kontroller"],
    ["start", "Start"],
    ["pause", "Pause"],
    ["resume", "Fortsett"],
    ["stop", "Stopp og dokk"],
    ["test_start_stop", "Test start/stopp"],
  ];
  return <Panel title="Manuell styring" subtitle="Kun master · alle kommandoer logges med status før og etter">
    <div className="space-y-4 p-5">
      <div className="flex flex-wrap gap-2">
        {buttons.map(([action, label]) => <button
          className={`btn ${action === "test_start_stop" ? "bg-green-600 text-white hover:bg-green-700" : action === "stop" ? "border-red-200 text-red-600 dark:border-red-500/30 dark:text-red-400" : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"}`}
          disabled={Boolean(running)}
          key={action}
          onClick={() => run(action)}
          title={controlActionLabels[action]}
        >{running === action ? "Utfører ..." : label}</button>)}
      </div>
      {message ? <div className={`rounded-md px-3 py-2 text-sm ${message.toLowerCase().includes("feil") ? "bg-red-500/10 text-red-600 dark:text-red-400" : "bg-green-500/10 text-green-700 dark:text-green-400"}`}>{message}</div> : null}
      {latest ? <div className="grid gap-3 border-t border-gray-100 pt-4 text-sm sm:grid-cols-[minmax(9rem,0.8fr)_1fr_1fr_auto] dark:border-gray-700/60">
        <div><span className="block text-xs font-semibold uppercase text-gray-400">Siste kommando</span><strong className="block font-medium text-gray-700 dark:text-gray-200">{controlActionLabels[latest.action] || latest.action}</strong>{latest.profile?.name ? <small className="text-gray-400">{String(latest.profile.name)}</small> : null}</div>
        <div><span className="block text-xs font-semibold uppercase text-gray-400">Før</span><strong className="font-medium text-gray-700 dark:text-gray-200">{controlStateLabel(latest.before_state)}</strong></div>
        <div><span className="block text-xs font-semibold uppercase text-gray-400">Etter</span><strong className="font-medium text-gray-700 dark:text-gray-200">{controlStateLabel(latest.after_state)}</strong></div>
        <div className="sm:text-right"><span className="block text-xs font-semibold uppercase text-gray-400">Tidspunkt</span><strong className="font-medium text-gray-700 dark:text-gray-200">{stamp(latest.requested_at)}</strong></div>
      </div> : <p className="text-sm text-gray-400">Ingen styringskommandoer er kjørt ennå.</p>}
    </div>
  </Panel>;
}

type CleaningProfile = RoborockRobotDetail["cleaningProfiles"][number];

type CleaningProfileDraft = {
  name: string;
  description: string;
  cleaning_type: "vacuum" | "mop" | "vacuum_mop";
  fan_power: number;
  water_box_mode: number;
  mop_mode: number;
  repeat: number;
  active: boolean;
};

function profileDraft(profile?: CleaningProfile): CleaningProfileDraft {
  return profile ? {
    name: profile.name,
    description: profile.description,
    cleaning_type: profile.cleaningType,
    fan_power: profile.fanPower,
    water_box_mode: profile.waterBoxMode,
    mop_mode: profile.mopMode,
    repeat: profile.repeat,
    active: profile.active,
  } : {
    name: "",
    description: "",
    cleaning_type: "vacuum_mop",
    fan_power: 102,
    water_box_mode: 202,
    mop_mode: 300,
    repeat: 1,
    active: true,
  };
}

function ProfileEditor({ data, editing, close, reload }: {
  data: RoborockRobotDetail;
  editing: CleaningProfile | "new";
  close: () => void;
  reload: () => void;
}) {
  const profile = editing === "new" ? undefined : editing;
  const [draft, setDraft] = useState<CleaningProfileDraft>(() => profileDraft(profile));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const options = data.cleaningProfileOptions;
  const fieldClass = "form-input w-full";

  function changeType(cleaningType: CleaningProfileDraft["cleaning_type"]) {
    setDraft((current) => ({
      ...current,
      cleaning_type: cleaningType,
      fan_power: cleaningType === "mop" ? 105 : current.fan_power === 105 ? 102 : current.fan_power,
      water_box_mode: cleaningType === "vacuum" ? 200 : current.water_box_mode === 200 ? 202 : current.water_box_mode,
    }));
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      await domainApi.mutate(
        profile ? `/api/renhold/cleaning-profiles/${profile.id}` : "/api/renhold/cleaning-profiles",
        profile ? "PUT" : "POST",
        draft,
      );
      close();
      reload();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!profile || profile.builtin || !window.confirm(`Slette profilen ${profile.name}?`)) return;
    setSaving(true);
    setError("");
    try {
      await domainApi.mutate(`/api/renhold/cleaning-profiles/${profile.id}`, "DELETE");
      close();
      reload();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setSaving(false);
    }
  }

  return <div className="border-t border-gray-100 bg-gray-50/70 p-5 dark:border-gray-700/60 dark:bg-gray-900/30">
    <div className="mb-4 flex items-center justify-between gap-3">
      <div><strong className="block text-sm text-gray-800 dark:text-gray-100">{profile ? `Rediger ${profile.name}` : "Ny rengjøringsprofil"}</strong><small className="text-gray-400">Profilen kan brukes både manuelt og i senere automatiske planer.</small></div>
      <button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={close}>Lukk</button>
    </div>
    <div className="grid gap-4 lg:grid-cols-4">
      <label className="lg:col-span-2"><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Navn</span><input autoFocus className={fieldClass} maxLength={80} onChange={(event) => setDraft({ ...draft, name: event.target.value })} value={draft.name} /></label>
      <label><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Renholdstype</span><select className={fieldClass} onChange={(event) => changeType(event.target.value as CleaningProfileDraft["cleaning_type"])} value={draft.cleaning_type}>{options.cleaningTypes.map((row) => <option key={row.value} value={row.value}>{row.label}</option>)}</select></label>
      <label><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Runder</span><select className={fieldClass} onChange={(event) => setDraft({ ...draft, repeat: Number(event.target.value) })} value={draft.repeat}>{options.repeat.map((row) => <option key={row.value} value={row.value}>{row.label}</option>)}</select></label>
      <label><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Sugekraft</span><select className={fieldClass} disabled={draft.cleaning_type === "mop"} onChange={(event) => setDraft({ ...draft, fan_power: Number(event.target.value) })} value={draft.fan_power}>{options.fanPower.filter((row) => draft.cleaning_type === "mop" ? row.value === 105 : row.value !== 105).map((row) => <option key={row.value} value={row.value}>{row.label}</option>)}</select></label>
      <label><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Vannmengde</span><select className={fieldClass} disabled={draft.cleaning_type === "vacuum"} onChange={(event) => setDraft({ ...draft, water_box_mode: Number(event.target.value) })} value={draft.water_box_mode}>{options.waterBoxMode.filter((row) => draft.cleaning_type === "vacuum" ? row.value === 200 : row.value !== 200).map((row) => <option key={row.value} value={row.value}>{row.label}</option>)}</select></label>
      <label><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Vaskemønster</span><select className={fieldClass} disabled={draft.cleaning_type === "vacuum"} onChange={(event) => setDraft({ ...draft, mop_mode: Number(event.target.value) })} value={draft.mop_mode}>{options.mopMode.map((row) => <option key={row.value} value={row.value}>{row.label}</option>)}</select></label>
      <label className="flex items-end pb-2"><span className="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-300"><input checked={draft.active} onChange={(event) => setDraft({ ...draft, active: event.target.checked })} type="checkbox" />Aktiv profil</span></label>
      <label className="lg:col-span-4"><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Beskrivelse</span><input className={fieldClass} maxLength={300} onChange={(event) => setDraft({ ...draft, description: event.target.value })} value={draft.description} /></label>
    </div>
    {error ? <p className="mt-3 rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</p> : null}
    <div className="mt-4 flex items-center justify-between gap-3">
      <div>{profile?.builtin ? <small className="text-gray-400">Standardprofilen kan redigeres, men ikke slettes.</small> : profile ? <button className="btn border-red-200 bg-white text-red-600 dark:border-red-500/30 dark:bg-gray-800 dark:text-red-400" disabled={saving} onClick={remove}>Slett</button> : null}</div>
      <button className="btn bg-green-600 text-white hover:bg-green-700" disabled={saving || draft.name.trim().length < 2} onClick={save}>{saving ? "Lagrer ..." : "Lagre profil"}</button>
    </div>
  </div>;
}

function CleaningZones({ duid, data, reload }: { duid: string; data: RoborockRobotDetail; reload: () => void }) {
  const [importing, setImporting] = useState(false);
  const [runningZone, setRunningZone] = useState<number | null>(null);
  const [watchingZone, setWatchingZone] = useState<{ number: number; name: string; profileName: string; startedAt: number; initialState: string } | null>(null);
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(() => {
    const stored = window.localStorage.getItem(`roborock-profile-${duid}`);
    return stored ? Number(stored) : null;
  });
  const [editingProfile, setEditingProfile] = useState<CleaningProfile | "new" | null>(null);
  const [showProfiles, setShowProfiles] = useState(false);
  const [message, setMessage] = useState("");
  const zones = data.cleaningZones || [];
  const activeProfiles = (data.cleaningProfiles || []).filter((profile) => profile.active);
  const selectedProfile = activeProfiles.find((profile) => profile.id === selectedProfileId) || null;
  const automaticImport = data.cleaningZoneImport;
  const telemetryAt = parsedDate(data.latestTelemetry?.timestamp)?.getTime() || 0;
  const telemetryState = String(data.latestTelemetry?.state_name || data.latestStatus?.state_name || "").toLowerCase();
  const watchedState = watchingZone && telemetryAt >= watchingZone.startedAt - 3_000
    ? telemetryState
    : watchingZone?.initialState || telemetryState;

  useEffect(() => {
    if (selectedProfile) return;
    const fallback = activeProfiles.find((profile) => profile.slug === "vacuum-mop-normal") || activeProfiles[0];
    if (fallback) setSelectedProfileId(fallback.id);
  }, [activeProfiles.map((profile) => `${profile.id}:${profile.active}`).join(","), selectedProfile]);

  function selectProfile(profileId: number) {
    setSelectedProfileId(profileId);
    window.localStorage.setItem(`roborock-profile-${duid}`, String(profileId));
  }

  function zoneProgressText(zoneName: string, state: string) {
    if (["washing_the_mop", "washing_the_mop_2", "going_to_wash_the_mop"].includes(state)) return `Moppbehandling i dokken · ${zoneName}`;
    if (["segment_cleaning", "segment_mopping", "segment_clean_mop_cleaning", "segment_clean_mop_mopping"].includes(state)) return `Vasker ${zoneName} nå`;
    if (["returning_home", "returning", "returning_to_dock"].includes(state)) return `${zoneName} · returnerer til dokk`;
    if (["charging", "charging_complete", "fully_charged"].includes(state)) return `${zoneName} er fullført · roboten lader`;
    return `${zoneName} er startet · ${robotStateLabel(state)}`;
  }

  useEffect(() => {
    if (!watchingZone) return undefined;
    const refresh = window.setInterval(reload, 8_000);
    const stop = window.setTimeout(() => setWatchingZone(null), 10 * 60_000);
    return () => {
      window.clearInterval(refresh);
      window.clearTimeout(stop);
    };
  }, [reload, watchingZone]);

  useEffect(() => {
    if (!watchingZone || telemetryAt < watchingZone.startedAt - 3_000 || !telemetryState) return;
    setMessage(zoneProgressText(watchingZone.name, telemetryState));
    if (["charging", "charging_complete", "fully_charged"].includes(telemetryState)) setWatchingZone(null);
  }, [telemetryAt, telemetryState, watchingZone]);

  async function importZones() {
    if (!window.confirm("Lese deaktiverte testplaner kl. 12:01-12:59 og oppdatere sonene for denne roboten?")) return;
    setImporting(true);
    setMessage("");
    try {
      const response = await domainApi.mutate<{ message?: string }>(
        `/api/renhold/robots/${encodeURIComponent(duid)}/cleaning-zones/import-test-schedules`,
        "POST",
      );
      setMessage(response.message || "Sonene er lest inn.");
      reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setImporting(false);
    }
  }

  async function cleanZone(zoneNumber: number, zoneName: string) {
    const robotName = String(data.robot?.name || "roboten");
    if (!selectedProfile) {
      setMessage("Velg en aktiv rengjøringsprofil først.");
      return;
    }
    if (!window.confirm(`Starte ${selectedProfile.name} i ${zoneName} på ${robotName}?\n\n${selectedProfile.summary}`)) return;
    setRunningZone(zoneNumber);
    setMessage("");
    try {
      const response = await domainApi.mutate<{ message?: string; after?: JsonRecord | null }>(
        `/api/renhold/robots/${encodeURIComponent(duid)}/control`,
        "POST",
        { action: "clean_zone", zone_number: zoneNumber, profile_id: selectedProfile.id },
      );
      const initialState = String(response.after?.state_name || "starting").toLowerCase();
      setWatchingZone({ number: zoneNumber, name: zoneName, profileName: selectedProfile.name, startedAt: Date.now(), initialState });
      setMessage(zoneProgressText(zoneName, initialState));
      reload();
    } catch (error) {
      setWatchingZone(null);
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setRunningZone(null);
    }
  }

  return <Panel title="Soner" subtitle="Velg renholdsprofil og start et av robotens kartområder">
    <div className="divide-y divide-gray-100 dark:divide-gray-700/60">
      <div className="px-5 py-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-[16rem] flex-1"><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Renholdsprofil</span><select className="form-input w-full" disabled={!activeProfiles.length || Boolean(watchingZone)} onChange={(event) => selectProfile(Number(event.target.value))} value={selectedProfile?.id || ""}><option disabled value="">Velg profil</option>{activeProfiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</select></label>
          {data.canManageCleaningZones ? <button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => setShowProfiles((value) => !value)}><MosaicIcon name="settings" />{showProfiles ? "Skjul profiler" : "Administrer profiler"}</button> : null}
          {data.canManageCleaningZones ? <button className="btn bg-green-600 text-white hover:bg-green-700" onClick={() => { setShowProfiles(true); setEditingProfile("new"); }}>Ny profil</button> : null}
        </div>
        {selectedProfile ? <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md bg-green-50 px-3 py-2 dark:bg-green-500/10"><strong className="text-sm font-semibold text-green-800 dark:text-green-300">{selectedProfile.summary}</strong>{selectedProfile.description ? <span className="text-sm text-green-700/70 dark:text-green-300/70">{selectedProfile.description}</span> : null}</div> : <p className="mt-3 text-sm text-red-500">Ingen aktiv rengjøringsprofil er tilgjengelig.</p>}
      </div>
      {showProfiles ? <div className="overflow-x-auto"><table className="w-full"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/40"><tr><th className="px-5 py-3 text-left font-semibold">Profil</th><th className="px-5 py-3 text-left font-semibold">Eksakte innstillinger</th><th className="px-5 py-3 text-right font-semibold">Status</th><th className="px-5 py-3 text-right font-semibold">Handling</th></tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{data.cleaningProfiles.map((profile) => <tr className={profile.active ? "" : "opacity-55"} key={profile.id}><td className="px-5 py-3"><strong className="block font-semibold text-gray-700 dark:text-gray-200">{profile.name}</strong><small className="text-gray-400">{profile.cleaningTypeLabel}</small></td><td className="px-5 py-3 text-gray-500 dark:text-gray-400">{profile.summary}</td><td className="px-5 py-3 text-right"><span className={profile.active ? "text-green-700 dark:text-green-400" : "text-gray-400"}>{profile.active ? "Aktiv" : "Av"}</span></td><td className="px-5 py-2 text-right"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => setEditingProfile(profile)}>Rediger</button></td></tr>)}</tbody></table></div> : null}
      {editingProfile ? <ProfileEditor data={data} editing={editingProfile} key={editingProfile === "new" ? "new" : editingProfile.id} close={() => setEditingProfile(null)} reload={reload} /> : null}
      <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
        <p className="max-w-3xl text-sm text-gray-500 dark:text-gray-400"><strong className="font-semibold text-gray-700 dark:text-gray-200">12:01 = Sone 1</strong>, 12:02 = Sone 2 osv. Bare deaktiverte planer med nøyaktig ett segment leses automatisk ved Roborock-synkronisering.</p>
        {data.canManageCleaningZones ? <button className="btn shrink-0 border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={importing || runningZone !== null} onClick={importZones}><MosaicIcon name="refresh" />{importing ? "Leser ..." : "Les testplaner"}</button> : null}
      </div>
      {automaticImport?.status === "error" ? <div className="mx-5 my-3 rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">Automatisk innlesing ble avvist: {automaticImport.message || "Kontroller testplanene"}</div> : null}
      {message ? <div aria-live="polite" className={`mx-5 my-3 flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${message.toLowerCase().includes("fant ingen") || message.toLowerCase().includes("må ") || message.toLowerCase().includes("allerede") || message.toLowerCase().includes("feil") ? "bg-red-500/10 text-red-600 dark:text-red-400" : "bg-green-500/10 text-green-700 dark:text-green-400"}`}>{watchingZone ? <MosaicIcon className="animate-spin" name="refresh" /> : <MosaicIcon name={message.toLowerCase().includes("feil") || message.toLowerCase().includes("allerede") ? "warning" : "robot"} />}{message}</div> : null}
      {zones.length ? <div className="overflow-x-auto"><table className="w-full"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/40"><tr><th className="px-5 py-3 text-left font-semibold">Sone</th><th className="px-5 py-3 text-left font-semibold">Robotsegment</th><th className="px-5 py-3 text-left font-semibold">Testplan</th><th className="px-5 py-3 text-right font-semibold">Lest inn</th>{data.canControl ? <th className="px-5 py-3 text-right font-semibold">Handling</th> : null}</tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{zones.map((zone) => <tr className={watchingZone?.number === zone.zoneNumber ? "bg-green-50/60 dark:bg-green-500/5" : ""} key={zone.zoneNumber}><td className="px-5 py-3 font-semibold text-gray-700 dark:text-gray-200">{zone.name}{watchingZone?.number === zone.zoneNumber ? <small className="mt-0.5 block font-medium text-green-700 dark:text-green-400">{zoneProgressText(zone.name, watchedState)} · {watchingZone.profileName}</small> : null}</td><td className="px-5 py-3 font-mono tabular-nums text-gray-600 dark:text-gray-300">{zone.segmentId}</td><td className="px-5 py-3 text-gray-500 dark:text-gray-400">12:{String(zone.zoneNumber).padStart(2, "0")} <span className="text-gray-300 dark:text-gray-600">·</span> {zone.sourceScheduleId || "-"}</td><td className="whitespace-nowrap px-5 py-3 text-right text-gray-400">{stamp(zone.importedAt)}</td>{data.canControl ? <td className="whitespace-nowrap px-5 py-2 text-right"><button className={`btn ${watchingZone?.number === zone.zoneNumber ? "border-green-600 bg-green-600 text-white" : "border-green-200 bg-green-50 text-green-700 hover:bg-green-100 dark:border-green-500/30 dark:bg-green-500/10 dark:text-green-300"}`} disabled={importing || runningZone !== null || watchingZone !== null || !selectedProfile} onClick={() => cleanZone(zone.zoneNumber, zone.name)}>{runningZone === zone.zoneNumber ? "Sender ..." : watchingZone?.number === zone.zoneNumber ? "Pågår ..." : "Start renhold"}</button></td> : null}</tr>)}</tbody></table></div> : <p className="px-5 py-6 text-sm text-gray-400">Ingen soner er registrert for denne roboten ennå.</p>}
    </div>
  </Panel>;
}

function ScheduleRows({ schedules }: { schedules: JsonRecord[] }) {
  return <div className="divide-y divide-gray-100 px-5 dark:divide-gray-700/60">{schedules.map((row, index) => <div className={`grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center ${row.enabled === false ? "opacity-50" : ""}`} key={String(row.schedule_id || index)}><div className="min-w-0"><strong className="block truncate text-sm font-medium text-gray-700 dark:text-gray-200">{String(row.schedule_label || row.cron || "Ukjent plan")}</strong><small className="mt-0.5 block truncate text-gray-400">{[row.next_label, row.rounds_label, row.fan_label, row.mop_label, row.water_label].filter(Boolean).join(" · ")}</small></div><span className={`text-xs font-semibold ${row.enabled === false ? "text-gray-400" : "text-green-700 dark:text-green-400"}`}>{row.enabled === false ? "Av" : "Aktiv"}</span></div>)}{!schedules.length ? <div className="py-6 text-sm text-gray-400">Ingen planer er mottatt.</div> : null}</div>;
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

function DoorAutomation({ duid, data, reload }: { duid: string; data: RoborockRobotDetail; reload: () => void }) {
  const automation = data.doorAutomation;
  const [enabled, setEnabled] = useState(Boolean(automation?.enabled));
  const [openingThreshold, setOpeningThreshold] = useState(automation?.openingThreshold || 10);
  const [minimumIntervalMinutes, setMinimumIntervalMinutes] = useState(automation?.minimumIntervalMinutes || 60);
  const [zoneNumbers, setZoneNumbers] = useState<number[]>(automation?.zoneNumbers || []);
  const [profileId, setProfileId] = useState(automation?.profileId || 0);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  if (!automation) return null;

  const progress = Math.min(100, Math.round((automation.openingCount / Math.max(1, automation.openingThreshold)) * 100));
  const statusTone = automation.status === "configuration_error" || automation.lastError
    ? "border-red-200 bg-red-50 text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
    : automation.pendingStart
      ? "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300"
    : automation.enabled
      ? "border-green-200 bg-green-50 text-green-700 dark:border-green-500/30 dark:bg-green-500/10 dark:text-green-300"
      : "border-gray-200 bg-gray-50 text-gray-600 dark:border-gray-700 dark:bg-gray-900/30 dark:text-gray-300";
  const vacuumProfiles = data.cleaningProfiles.filter((profile) => profile.active && profile.cleaningType === "vacuum");
  const selectableZones = [
    ...data.cleaningZones.map((zone) => ({ zoneNumber: zone.zoneNumber, name: zone.name, mapped: true })),
    ...automation.configuredZones
      .filter((zone) => !data.cleaningZones.some((candidate) => candidate.zoneNumber === zone.zoneNumber))
      .map((zone) => ({ zoneNumber: zone.zoneNumber, name: zone.name, mapped: zone.mapped })),
  ].sort((left, right) => left.zoneNumber - right.zoneNumber);

  function toggleZone(zoneNumber: number, checked: boolean) {
    setZoneNumbers((current) => {
      if (!checked) return current.filter((value) => value !== zoneNumber);
      if (current.includes(zoneNumber)) return current;
      return [...current, zoneNumber];
    });
  }

  async function save() {
    setSaving(true);
    setMessage("");
    try {
      const response = await domainApi.mutate<{ message?: string }>(
        `/api/renhold/robots/${encodeURIComponent(duid)}/door-automation`,
        "PUT",
        {
          enabled,
          opening_threshold: openingThreshold,
          minimum_interval_minutes: minimumIntervalMinutes,
          zone_numbers: zoneNumbers,
          profile_id: profileId,
        },
      );
      setMessage(response.message || "Automatikken er lagret.");
      reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

  async function resetCounter() {
    if (!window.confirm("Nullstille dagens teller for inngangsdøren?")) return;
    setSaving(true);
    setMessage("");
    try {
      const response = await domainApi.mutate<{ message?: string }>(
        `/api/renhold/robots/${encodeURIComponent(duid)}/door-automation/reset-counter`,
        "POST",
      );
      setMessage(response.message || "Telleren er nullstilt.");
      reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

  return <Panel title="Inngangsstyrt støvsuging" subtitle={`Kun i åpningstiden ${automation.openingHours.openFrom}-${automation.openingHours.closeAtLabel}`}>
    <div className="space-y-4 p-5">
      <div className="grid gap-4 lg:grid-cols-[minmax(16rem,0.8fr)_minmax(0,1.2fr)]">
        <div className={`rounded-lg border p-4 ${statusTone}`}>
          <div className="flex items-start justify-between gap-4"><div><span className="block text-xs font-semibold uppercase opacity-70">Status</span><strong className="mt-1 block text-base">{automation.statusLabel}</strong><p className="mt-1 text-sm opacity-80">{automation.statusDetail}</p></div><strong className="whitespace-nowrap text-lg tabular-nums">{automation.openingCount} / {automation.openingThreshold}</strong></div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-black/10 dark:bg-white/10"><div className="h-full rounded-full bg-current transition-[width]" style={{ width: `${progress}%` }} /></div>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3 xl:grid-cols-6">
          <div><span className="block text-xs font-semibold uppercase text-gray-400">Soner</span><strong className="mt-1 block text-gray-700 dark:text-gray-200">{automation.configuredZones.map((zone) => zone.name).join(" + ") || "Ikke valgt"}</strong></div>
          <div><span className="block text-xs font-semibold uppercase text-gray-400">Profil</span><strong className="mt-1 block text-gray-700 dark:text-gray-200">{String(automation.profile?.name || "Ikke valgt")}</strong></div>
          <div><span className="block text-xs font-semibold uppercase text-gray-400">Teller fra</span><strong className="mt-1 block text-gray-700 dark:text-gray-200">{automation.counterStartedAt ? stamp(automation.counterStartedAt) : automation.openingHours.openFrom}</strong></div>
          <div><span className="block text-xs font-semibold uppercase text-gray-400">Siste åpning</span><strong className="mt-1 block text-gray-700 dark:text-gray-200">{automation.lastOpeningAt ? stamp(automation.lastOpeningAt) : "Ingen i perioden"}</strong></div>
          <div><span className="block text-xs font-semibold uppercase text-gray-400">Sist startet</span><strong className="mt-1 block text-gray-700 dark:text-gray-200">{automation.lastStartedAt ? stamp(automation.lastStartedAt) : "Aldri"}</strong></div>
          <div><span className="block text-xs font-semibold uppercase text-gray-400">Neste tillatte start</span><strong className="mt-1 block text-gray-700 dark:text-gray-200">{automation.nextAllowedAt ? stamp(automation.nextAllowedAt) : "Kan starte første gang"}</strong></div>
        </div>
      </div>
      {automation.validationIssues.length ? <div className="rounded-md bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">{automation.validationIssues.join(" · ")}</div> : null}
      {automation.lastError ? <div className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">Siste feil: {automation.lastError}</div> : null}
      {data.canManageCleaningZones ? <details className="rounded-lg border border-gray-200 dark:border-gray-700/60">
        <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-semibold text-gray-700 dark:text-gray-200"><span>Innstillinger</span><span className="text-xs font-medium text-gray-400">Telleren beholdes ved lagring</span></summary>
        <div className="grid gap-4 border-t border-gray-100 p-4 sm:grid-cols-2 xl:grid-cols-4 dark:border-gray-700/60">
          <label className="flex items-center gap-2 self-end pb-2 text-sm font-medium text-gray-700 dark:text-gray-200"><input checked={enabled} onChange={(event) => setEnabled(event.target.checked)} type="checkbox" />Aktiver automatikk</label>
          <label><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Døråpninger</span><input className="form-input w-full" max={100} min={1} onChange={(event) => setOpeningThreshold(Number(event.target.value))} type="number" value={openingThreshold} /></label>
          <label><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Minimum mellom støvsuginger</span><div className="relative"><input className="form-input w-full pr-12" max={1440} min={1} onChange={(event) => setMinimumIntervalMinutes(Number(event.target.value))} step={5} type="number" value={minimumIntervalMinutes} /><span className="pointer-events-none absolute right-3 top-2.5 text-sm text-gray-400">min</span></div><small className="mt-1 block text-gray-400">Første start venter like lenge fra dagens åpning.</small></label>
          <label><span className="mb-1 block text-xs font-semibold uppercase text-gray-400">Støvsugingsprofil</span><select className="form-input w-full" onChange={(event) => setProfileId(Number(event.target.value))} value={profileId}>{vacuumProfiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</select></label>
          <fieldset className="sm:col-span-2 xl:col-span-4"><legend className="mb-2 text-xs font-semibold uppercase text-gray-400">Velg én eller flere soner</legend><div className="flex flex-wrap gap-2">{selectableZones.map((zone) => <label className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${zoneNumbers.includes(zone.zoneNumber) ? "border-green-400 bg-green-50 text-green-800 dark:border-green-500/60 dark:bg-green-500/10 dark:text-green-300" : "border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-300"}`} key={zone.zoneNumber}><input checked={zoneNumbers.includes(zone.zoneNumber)} onChange={(event) => toggleZone(zone.zoneNumber, event.target.checked)} type="checkbox" />{zone.name}{!zone.mapped ? <small className="text-amber-600 dark:text-amber-300">ikke kartlagt</small> : null}</label>)}</div></fieldset>
          <div className="flex flex-wrap items-center justify-between gap-3 sm:col-span-2 xl:col-span-4"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={saving} onClick={resetCounter}>Nullstill teller</button><button className="btn bg-green-600 text-white hover:bg-green-700" disabled={saving || zoneNumbers.length < 1 || !profileId} onClick={save}>{saving ? "Lagrer ..." : "Lagre automatikk"}</button></div>
        </div>
      </details> : null}
      {message ? <p className="text-sm text-gray-500 dark:text-gray-300">{message}</p> : null}
    </div>
  </Panel>;
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
  const activeCycle = data.activeCycle || summary?.active_cycle;
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
        <div className="border-b border-r border-gray-100 px-5 py-4 lg:border-b-0 dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Status</span><strong className="mt-1 block text-lg font-semibold text-gray-800 dark:text-gray-100">{String(activeCycle?.phase_label || telemetry.state_label || status.state_label || status.state_name || "-")}</strong><small className="text-gray-400">{String(telemetry.charge_label || status.charge_label || "Ladestatus ukjent")}</small></div>
        <div className="border-b border-gray-100 px-5 py-4 lg:border-b-0 lg:border-r dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">Batteri</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{telemetry.battery == null ? status.battery == null ? "-" : `${status.battery} %` : `${telemetry.battery} %`}</strong><small className="text-gray-400">{String(readiness?.signal_label || telemetry.signal_label || "Signal ukjent")}</small></div>
        <div className="border-r border-gray-100 px-5 py-4 dark:border-gray-700/60"><span className="text-xs font-semibold uppercase text-gray-400">{activeCycle ? "Pågående jobb" : "Siste ferdige jobb"}</span><strong className="mt-1 block text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{activeCycle?.started_at ? `ca. ${jobTime(activeCycle.started_at)}` : latestJob?.begin_at ? jobTime(latestJob.begin_at) : "Ingen i dag"}</strong><small className={activeCycle ? "text-sky-700 dark:text-sky-400" : jobTone(latestJob as RoborockJobSummary)}>{activeCycle?.phase_label || String((latestJob as RoborockJobSummary | undefined)?.status_label || "-")}</small></div>
        <div className="px-5 py-4"><span className="text-xs font-semibold uppercase text-gray-400">Neste plan</span><strong className="mt-1 block truncate text-lg font-semibold text-gray-800 dark:text-gray-100">{summary?.schedules?.next_label || "Ingen aktiv"}</strong><small className="text-gray-400">{summary?.schedules?.active_count ? `${summary.schedules.active_count} aktive planer` : "Ingen planer"}</small></div>
      </div>
    </section>
    <RobotControls duid={duid} data={data} reload={result.reload} />
    <DoorAutomation duid={duid} data={data} key={`${data.doorAutomation?.updatedAt || "none"}-${data.doorAutomation?.openingCount || 0}`} reload={result.reload} />
    <CleaningZones duid={duid} data={data} reload={result.reload} />
    <div className="grid gap-5 xl:grid-cols-2">
      <Panel title="Rengjøring" subtitle="Samlet aktivitet i dag og i går"><DetailDayRows summary={summary} /></Panel>
      <Panel title="Driftsklar" subtitle={readiness?.telemetry_at ? `Kontrollert ${stamp(readiness.telemetry_at)}` : "Siste telemetri"}><ReadinessGrid readiness={readiness} /></Panel>
    </div>
    <div className="grid gap-5 xl:grid-cols-2">
      <Panel title="Planlagte jobber" subtitle={`${data.schedules.filter((row) => row.enabled !== false).length} aktive planer`}><ScheduleRows schedules={data.schedules} /></Panel>
      <Panel title="Forbruksdeler" subtitle={consumables.timestamp ? `Registrert bruk siden nullstilling · målt ${stamp(consumables.timestamp)}` : "Ikke mottatt"}><ConsumableGrid consumables={consumables} /></Panel>
    </div>
    <Panel title="Rengjøringshistorikk" subtitle="Ferdige jobber, nyeste først">{activeCycle ? <ActiveCycleBand cycle={activeCycle} /> : null}<CompactTable columns={["begin_at", "end_at", "duration_minutes", "cleaned_area_m2", "rounds_label", "status_label", "error_label"]} rows={data.jobs} /></Panel>
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
  if (pathname === "/renhold/rapport") return <NightReport />;
  const match = pathname.match(/^\/renhold\/robot\/([^/]+)$/);
  const selected = match ? decodeURIComponent(match[1]) : "";
  const summary = robots.find((robot) => robot.duid === selected);
  if (!selected) return <RobotOverview data={data} />;
  if (!summary) return <Panel title="Robot ikke funnet"><div className="p-8 text-sm text-gray-400">Roboten finnes ikke lenger i den registrerte robotlisten.</div></Panel>;
  return <RobotDetail duid={selected} summary={summary} />;
}
