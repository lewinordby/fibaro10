import { AppLink, MosaicIcon, type IconName } from "@lilletorget/microapp-ui";
import type {
  OperationsDashboardArea,
  OperationsDashboardItem,
  OperationsDashboardResponse,
} from "../types";

const areaStyle: Record<OperationsDashboardArea["key"], { icon: IconName; iconClass: string; lineClass: string }> = {
  ventilation: { icon: "ventilation", iconClass: "bg-sky-500/10 text-sky-600 dark:text-sky-300", lineClass: "bg-sky-500" },
  lights: { icon: "light", iconClass: "bg-amber-500/10 text-amber-600 dark:text-amber-300", lineClass: "bg-amber-500" },
  doors: { icon: "door", iconClass: "bg-teal-500/10 text-teal-600 dark:text-teal-300", lineClass: "bg-teal-500" },
  bollards: { icon: "building", iconClass: "bg-violet-500/10 text-violet-600 dark:text-violet-300", lineClass: "bg-violet-500" },
  cleaning: { icon: "robot", iconClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-300", lineClass: "bg-emerald-500" },
};

const statusStyle = {
  ok: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  active: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  warning: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
  error: "bg-red-500/10 text-red-700 dark:text-red-300",
  unknown: "bg-gray-500/10 text-gray-600 dark:text-gray-300",
};

function relativeStamp(value?: string | null) {
  if (!value) return "ikke registrert";
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(elapsed / 60_000);
  if (minutes < 1) return "akkurat nå";
  if (minutes < 60) return `${minutes} min siden`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} t siden`;
  return new Date(value).toLocaleString("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Oslo",
  });
}

function StatusBadge({ status, label }: { status: OperationsDashboardArea["status"]; label: string }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold ${statusStyle[status]}`}>
      <i className={`h-1.5 w-1.5 rounded-full ${status === "error" ? "bg-red-500" : status === "warning" ? "bg-amber-500" : status === "active" ? "bg-sky-500" : status === "ok" ? "bg-emerald-500" : "bg-gray-400"}`} />
      {label}
    </span>
  );
}

function itemTone(item: OperationsDashboardItem, area: OperationsDashboardArea["key"]) {
  if (item.state === "error") return "bg-red-500";
  if (item.state === "warning" || item.state === "pending") return "bg-amber-500";
  if (item.state === "unknown") return "bg-gray-400";
  if (item.state === "on" || item.state === "active" || item.state === "open") return areaStyle[area].lineClass;
  if (item.state === "ok" || item.state === "closed") return "bg-emerald-500";
  return "bg-gray-300 dark:bg-gray-600";
}

function AreaItem({ item, area }: { item: OperationsDashboardItem; area: OperationsDashboardArea["key"] }) {
  const content = (
    <>
      <span className="flex min-w-0 items-center gap-2.5">
        <i className={`h-2 w-2 shrink-0 rounded-full ${itemTone(item, area)}`} />
        <span className="truncate text-sm font-medium text-gray-700 dark:text-gray-200">{item.label}</span>
      </span>
      <span className="flex shrink-0 items-baseline gap-2 text-right">
        <strong className="text-sm font-semibold text-gray-800 dark:text-gray-100">{item.value}</strong>
        {item.detail ? <small className="text-xs text-gray-400">{item.detail}</small> : null}
      </span>
    </>
  );
  const classes = "flex min-h-10 items-center justify-between gap-4 border-b border-gray-100 px-5 py-2.5 last:border-b-0 dark:border-gray-700/60";
  return item.href ? <AppLink className={`${classes} hover:bg-gray-50/70 dark:hover:bg-gray-700/20`} to={item.href}>{content}</AppLink> : <div className={classes}>{content}</div>;
}

function AreaPanel({ area }: { area: OperationsDashboardArea }) {
  const style = areaStyle[area.key];
  const wide = area.key === "cleaning";
  return (
    <section className={`relative overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700/70 dark:bg-gray-800 ${wide ? "xl:col-span-2" : ""}`}>
      <i className={`absolute inset-y-0 left-0 w-1 ${style.lineClass}`} />
      <header className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${style.iconClass}`}><MosaicIcon name={style.icon} size={20} /></span>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">{area.label}</h2>
            <p className="truncate text-xs text-gray-400">{area.detail} · oppdatert {relativeStamp(area.updatedAt)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={area.status} label={area.statusLabel} />
          <AppLink className="inline-flex h-8 w-8 items-center justify-center rounded-md text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-700 dark:hover:text-gray-100" to={area.href}><span className="sr-only">Åpne {area.label}</span><MosaicIcon name="arrow-right" /></AppLink>
        </div>
      </header>
      <div className={`grid border-y border-gray-100 bg-gray-50/65 dark:border-gray-700/60 dark:bg-gray-900/20 ${area.metrics.length === 3 ? "grid-cols-3" : "grid-cols-2 sm:grid-cols-4"}`}>
        {area.metrics.map((metric) => (
          <div className="border-r border-gray-100 px-4 py-3 last:border-r-0 dark:border-gray-700/60" key={metric.label}>
            <span className="block text-[0.65rem] font-semibold uppercase text-gray-400">{metric.label}</span>
            <strong className="mt-0.5 block text-base font-semibold tabular-nums text-gray-900 dark:text-gray-100">{metric.value}</strong>
            {metric.detail ? <small className="block text-[0.7rem] text-gray-400">{metric.detail}</small> : null}
          </div>
        ))}
      </div>
      <div className={wide ? "grid sm:grid-cols-2 xl:grid-cols-3" : ""}>
        {area.items.length ? area.items.map((item, index) => <AreaItem area={area.key} item={item} key={`${item.label}-${index}`} />) : <div className="px-5 py-5 text-sm text-gray-400">Ingen detaljstatus er tilgjengelig.</div>}
      </div>
    </section>
  );
}

function SummaryStrip({ data }: { data: OperationsDashboardResponse }) {
  const overall = data.summary.status;
  const badgeStatus = overall === "error" ? "error" : overall === "warning" ? "warning" : "ok";
  return (
    <section className="grid overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm md:grid-cols-[minmax(15rem,1.45fr)_repeat(3,minmax(9rem,1fr))] dark:border-gray-700/70 dark:bg-gray-800">
      <div className="flex items-center gap-3 border-b border-gray-100 px-5 py-4 md:border-b-0 md:border-r dark:border-gray-700/60">
        <span className={`flex h-10 w-10 items-center justify-center rounded-lg ${badgeStatus === "error" ? "bg-red-500/10 text-red-600" : badgeStatus === "warning" ? "bg-amber-500/10 text-amber-600" : "bg-emerald-500/10 text-emerald-600"}`}><MosaicIcon name={badgeStatus === "ok" ? "dashboard" : "warning"} size={20} /></span>
        <div><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Driften nå</span><strong className="block text-base font-semibold text-gray-900 dark:text-gray-100">{data.summary.label}</strong></div>
      </div>
      <div className="border-b border-gray-100 px-5 py-4 md:border-b-0 md:border-r dark:border-gray-700/60"><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Åpning</span><strong className="mt-0.5 block text-base text-gray-900 dark:text-gray-100">{data.operatingWindow.label}</strong><small className="text-xs text-gray-400">{data.operatingWindow.detail}</small></div>
      <div className="border-b border-gray-100 px-5 py-4 md:border-b-0 md:border-r dark:border-gray-700/60"><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Systemstatus</span><strong className="mt-0.5 block text-base tabular-nums text-gray-900 dark:text-gray-100">{data.summary.normal} av {data.summary.total} normale</strong><small className="text-xs text-gray-400">{data.summary.attention} oppmerksomhet · {data.summary.critical} kritisk</small></div>
      <div className="px-5 py-4"><span className="block text-[0.65rem] font-semibold uppercase text-gray-400">Sist kontrollert</span><strong className="mt-0.5 block text-base text-gray-900 dark:text-gray-100">{relativeStamp(data.generatedAt)}</strong><small className="text-xs text-gray-400">{new Date(data.generatedAt).toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Europe/Oslo" })}</small></div>
    </section>
  );
}

function IncidentStrip({ data }: { data: OperationsDashboardResponse }) {
  if (!data.incidents.length) return (
    <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50/70 px-5 py-3 text-sm text-emerald-800 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-300">
      <span className="h-2 w-2 rounded-full bg-emerald-500" />
      <strong>Ingen aktive driftsavvik</strong>
      <span className="text-emerald-700/70 dark:text-emerald-300/70">Alle fem fagområder rapporterer normal eller forventet status.</span>
    </div>
  );
  return (
    <section className="overflow-hidden rounded-lg border border-amber-200 bg-white shadow-sm dark:border-amber-500/25 dark:bg-gray-800">
      <header className="flex items-center justify-between gap-4 border-b border-gray-100 px-5 py-3 dark:border-gray-700/60"><div className="flex items-center gap-2"><MosaicIcon name="warning" className="text-amber-500" /><strong className="text-sm text-gray-800 dark:text-gray-100">Prioritert oppfølging</strong></div><span className="text-xs tabular-nums text-gray-400">{data.incidents.length} forhold</span></header>
      <div className="divide-y divide-gray-100 dark:divide-gray-700/60">{data.incidents.slice(0, 6).map((incident, index) => <AppLink className="grid gap-1 px-5 py-3 hover:bg-gray-50/70 sm:grid-cols-[8rem_1fr_auto] sm:items-center dark:hover:bg-gray-700/20" to={incident.href} key={`${incident.area}-${index}`}><span className={`text-xs font-semibold ${incident.severity === "error" ? "text-red-600 dark:text-red-300" : "text-amber-600 dark:text-amber-300"}`}>{incident.area}</span><span className="text-sm text-gray-700 dark:text-gray-200">{incident.title}</span><MosaicIcon name="arrow-right" className="hidden text-gray-400 sm:block" /></AppLink>)}</div>
    </section>
  );
}

export function OperationsDashboard({ data }: { data: OperationsDashboardResponse }) {
  return <div className="space-y-5"><SummaryStrip data={data} /><IncidentStrip data={data} /><div className="grid gap-5 xl:grid-cols-2">{data.areas.map((area) => <AreaPanel area={area} key={area.key} />)}</div></div>;
}
