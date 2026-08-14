import { AppLink, MosaicIcon, type IconName } from "@lilletorget/microapp-ui";
import type {
  OperationsDashboardArea,
  OperationsDashboardItem,
  OperationsDashboardJob,
  OperationsDashboardResponse,
} from "../types";

type AreaVisual = {
  icon: IconName;
  iconClass: string;
  lineClass: string;
  borderClass: string;
  headerClass: string;
  textClass: string;
};

const areaStyle: Record<OperationsDashboardArea["key"], AreaVisual> = {
  ventilation: {
    icon: "ventilation",
    iconClass: "bg-sky-500/12 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300",
    lineClass: "bg-sky-500",
    borderClass: "border-t-sky-500",
    headerClass: "bg-sky-50/55 dark:bg-sky-500/[0.035]",
    textClass: "text-sky-700 dark:text-sky-300",
  },
  lights: {
    icon: "light",
    iconClass: "bg-yellow-500/14 text-yellow-800 dark:bg-yellow-500/15 dark:text-yellow-300",
    lineClass: "bg-yellow-500",
    borderClass: "border-t-yellow-500",
    headerClass: "bg-yellow-50/55 dark:bg-yellow-500/[0.035]",
    textClass: "text-yellow-800 dark:text-yellow-300",
  },
  doors: {
    icon: "door",
    iconClass: "bg-teal-500/12 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300",
    lineClass: "bg-teal-500",
    borderClass: "border-t-teal-500",
    headerClass: "bg-teal-50/55 dark:bg-teal-500/[0.035]",
    textClass: "text-teal-700 dark:text-teal-300",
  },
  bollards: {
    icon: "building",
    iconClass: "bg-violet-500/12 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300",
    lineClass: "bg-violet-500",
    borderClass: "border-t-violet-500",
    headerClass: "bg-violet-50/55 dark:bg-violet-500/[0.035]",
    textClass: "text-violet-700 dark:text-violet-300",
  },
  cleaning: {
    icon: "robot",
    iconClass: "bg-green-500/12 text-green-800 dark:bg-green-500/15 dark:text-green-300",
    lineClass: "bg-green-500",
    borderClass: "border-t-green-500",
    headerClass: "bg-green-50/55 dark:bg-green-500/[0.035]",
    textClass: "text-green-800 dark:text-green-300",
  },
};

const statusStyle = {
  ok: "bg-green-500/10 text-green-800 dark:text-green-300",
  active: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  warning: "bg-yellow-500/12 text-yellow-800 dark:text-yellow-300",
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

function timeStamp(value: string) {
  return new Date(value).toLocaleTimeString("nb-NO", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "Europe/Oslo",
  });
}

function displayDetail(value: string) {
  const normalized = value.trim().toLocaleLowerCase("nb-NO");
  if (normalized === "kjoling") return "Kjøling";
  if (normalized === "normal") return "Normal drift";
  if (normalized === "lux") return "Automatisk etter lux";
  return value;
}

function displayValue(value: string) {
  const normalized = value.trim().toLocaleLowerCase("nb-NO");
  const translations: Record<string, string> = {
    charging: "Lader",
    cleaning: "Rengjør",
    working: "Rengjør",
    idle: "Klar",
    docked: "I dock",
    suspected: "Mulig endring",
  };
  return translations[normalized] || value;
}

function statusDot(status: OperationsDashboardArea["status"]) {
  if (status === "error") return "bg-red-500";
  if (status === "warning") return "bg-yellow-500";
  if (status === "active") return "bg-sky-500";
  if (status === "ok") return "bg-green-500";
  return "bg-gray-400";
}

function StatusBadge({ status, label }: { status: OperationsDashboardArea["status"]; label: string }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold tracking-normal ring-1 ring-inset ring-current/10 ${statusStyle[status]}`}>
      <i className={`h-1.5 w-1.5 rounded-full ${statusDot(status)}`} />
      {label}
    </span>
  );
}

function itemTone(item: OperationsDashboardItem, area: OperationsDashboardArea["key"]) {
  if (item.state === "error") return "bg-red-500";
  if (item.state === "warning" || item.state === "pending") return "bg-yellow-500";
  if (item.state === "unknown") return "bg-gray-400";
  if (item.state === "on" || item.state === "active" || item.state === "open") return areaStyle[area].lineClass;
  if (item.state === "ok" || item.state === "closed") return "bg-green-500";
  return "bg-gray-300 dark:bg-gray-600";
}

function AreaItem({ item, area }: { item: OperationsDashboardItem; area: OperationsDashboardArea["key"] }) {
  const content = (
    <>
      <span className="flex min-w-0 items-center gap-2.5">
        <i className={`h-2 w-2 shrink-0 rounded-full ${itemTone(item, area)}`} />
        <span className="truncate text-sm font-medium tracking-normal text-gray-700 dark:text-gray-200">{item.label}</span>
      </span>
      <span className="flex shrink-0 items-baseline gap-2 text-right">
        <strong className="text-sm font-semibold tracking-normal text-gray-900 dark:text-gray-100">{displayValue(item.value)}</strong>
        {item.detail ? <small className="text-xs tracking-normal text-gray-400">{item.detail}</small> : null}
      </span>
    </>
  );
  const classes = "flex min-h-10 items-center justify-between gap-4 border-b border-gray-100 px-5 py-2.5 last:border-b-0 dark:border-gray-700/60";
  return item.href
    ? <AppLink className={`${classes} transition-colors hover:bg-gray-50/70 dark:hover:bg-gray-700/20`} to={item.href}>{content}</AppLink>
    : <div className={classes}>{content}</div>;
}

function jobStamp(value?: string | null) {
  if (!value) return "Tidspunkt mangler";
  const date = new Date(value);
  const now = new Date();
  const day = date.toLocaleDateString("nb-NO", { timeZone: "Europe/Oslo" });
  const today = now.toLocaleDateString("nb-NO", { timeZone: "Europe/Oslo" });
  const yesterday = new Date(now.getTime() - 86_400_000).toLocaleDateString("nb-NO", { timeZone: "Europe/Oslo" });
  const time = date.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Oslo" });
  return `${day === today ? "I dag" : day === yesterday ? "I går" : day} kl. ${time}`;
}

function jobStatusClass(status: OperationsDashboardJob["status"]) {
  if (status === "complete") return "bg-green-500/10 text-green-700 dark:text-green-300";
  if (status === "running") return "bg-sky-500/10 text-sky-700 dark:text-sky-300";
  if (status === "error") return "bg-red-500/10 text-red-700 dark:text-red-300";
  return "bg-yellow-500/12 text-yellow-800 dark:text-yellow-300";
}

function CleaningJob({ job }: { job: OperationsDashboardJob }) {
  const details = [
    job.durationMinutes == null ? null : `${Math.round(job.durationMinutes)} min`,
    job.areaM2 == null ? null : `${Number(job.areaM2).toLocaleString("nb-NO", { maximumFractionDigits: 1 })} m²`,
  ].filter(Boolean).join(" · ");
  return (
    <AppLink className="grid min-h-12 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-gray-100 px-5 py-2.5 transition-colors last:border-b-0 hover:bg-gray-50/70 dark:border-gray-700/60 dark:hover:bg-gray-700/20" to={job.href}>
      <span className="min-w-0">
        <strong className="block truncate text-sm font-medium text-gray-700 dark:text-gray-200">{job.robotName}</strong>
        <small className="block truncate text-xs tabular-nums text-gray-400">{jobStamp(job.startedAt)}{details ? ` · ${details}` : ""}</small>
      </span>
      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${jobStatusClass(job.status)}`}>{job.statusLabel}</span>
    </AppLink>
  );
}

function CleaningDetails({ area }: { area: OperationsDashboardArea }) {
  const jobs = area.recentJobs || [];
  return (
    <div className="grid lg:grid-cols-2">
      <section>
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-2.5 dark:border-gray-700/60">
          <strong className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Roboter</strong>
          <span className="text-xs tabular-nums text-gray-400">{area.items.length} stk</span>
        </div>
        {area.items.length
          ? area.items.map((item, index) => <AreaItem area={area.key} item={item} key={`${item.label}-${index}`} />)
          : <div className="px-5 py-5 text-sm text-gray-400">Ingen robotstatus er tilgjengelig.</div>}
      </section>
      <section className="border-t border-gray-100 lg:border-l lg:border-t-0 dark:border-gray-700/60">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-2.5 dark:border-gray-700/60">
          <strong className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Siste jobber</strong>
          <span className="text-xs text-gray-400">Nyeste først</span>
        </div>
        {jobs.length
          ? jobs.map((job, index) => <CleaningJob job={job} key={`${job.robotName}-${job.startedAt}-${index}`} />)
          : <div className="px-5 py-5 text-sm text-gray-400">Ingen renholdsjobber er registrert.</div>}
      </section>
    </div>
  );
}

function AreaPanel({ area }: { area: OperationsDashboardArea }) {
  const style = areaStyle[area.key];
  const wide = area.key === "cleaning";
  return (
    <section className={`group overflow-hidden rounded-lg border border-t-2 border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md dark:border-gray-700/70 dark:bg-gray-800 ${style.borderClass} ${wide ? "xl:col-span-2" : ""}`}>
      <header className={`flex flex-wrap items-center justify-between gap-4 border-b border-gray-100 px-5 py-4 dark:border-gray-700/60 ${style.headerClass}`}>
        <div className="flex min-w-0 items-center gap-3">
          <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset ring-current/10 ${style.iconClass}`}>
            <MosaicIcon name={style.icon} size={21} />
          </span>
          <div className="min-w-0">
            <h2 className="text-base font-semibold tracking-normal text-gray-950 dark:text-white">{area.label}</h2>
            <p className="truncate text-xs tracking-normal text-gray-500 dark:text-gray-400">{displayDetail(area.detail)} · oppdatert {relativeStamp(area.updatedAt)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={area.status} label={area.statusLabel} />
          <AppLink className={`inline-flex h-8 w-8 items-center justify-center rounded-md bg-white/70 ring-1 ring-inset ring-gray-200 transition-colors hover:text-gray-950 dark:bg-gray-800/60 dark:ring-gray-700 dark:hover:text-white ${style.textClass}`} to={area.href}>
            <span className="sr-only">Åpne {area.label}</span>
            <MosaicIcon name="arrow-right" />
          </AppLink>
        </div>
      </header>
      <div className={`grid bg-gray-50/70 dark:bg-gray-900/20 ${area.metrics.length === 3 ? "grid-cols-3" : "grid-cols-2 sm:grid-cols-4"}`}>
        {area.metrics.map((metric) => (
          <div className="min-w-0 border-r border-gray-100 px-4 py-3.5 last:border-r-0 dark:border-gray-700/60" key={metric.label}>
            <span className="block truncate text-[0.65rem] font-semibold uppercase tracking-normal text-gray-500 dark:text-gray-400">{metric.label}</span>
            <strong className="mt-0.5 block text-lg font-semibold tracking-normal tabular-nums text-gray-950 dark:text-white">{metric.value}</strong>
            {metric.detail ? <small className="block truncate text-[0.7rem] tracking-normal text-gray-400">{metric.detail}</small> : null}
          </div>
        ))}
      </div>
      {wide ? <CleaningDetails area={area} /> : <div>
        {area.items.length
          ? area.items.map((item, index) => <AreaItem area={area.key} item={item} key={`${item.label}-${index}`} />)
          : <div className="px-5 py-5 text-sm tracking-normal text-gray-400">Ingen detaljstatus er tilgjengelig.</div>}
      </div>}
    </section>
  );
}

function SummaryStrip({ data }: { data: OperationsDashboardResponse }) {
  const overall = data.summary.status;
  const badgeStatus = overall === "error" ? "error" : overall === "warning" ? "warning" : "ok";
  const statusSurface = badgeStatus === "error"
    ? "bg-red-50/75 dark:bg-red-500/[0.06]"
    : badgeStatus === "warning"
      ? "bg-yellow-50/80 dark:bg-yellow-500/[0.06]"
      : "bg-green-50/75 dark:bg-green-500/[0.05]";
  const statusIcon = badgeStatus === "error"
    ? "bg-red-500 text-white"
    : badgeStatus === "warning"
      ? "bg-yellow-500 text-yellow-950"
      : "bg-green-500 text-white";
  return (
    <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700/70 dark:bg-gray-800">
      <div className="grid md:grid-cols-[minmax(16rem,1.5fr)_repeat(3,minmax(9rem,1fr))]">
        <div className={`flex items-center gap-4 border-b border-gray-100 px-5 py-4 md:border-b-0 md:border-r dark:border-gray-700/60 ${statusSurface}`}>
          <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg shadow-sm ${statusIcon}`}>
            <MosaicIcon name={badgeStatus === "ok" ? "dashboard" : "warning"} size={21} />
          </span>
          <div className="min-w-0">
            <span className="block text-[0.65rem] font-semibold uppercase tracking-normal text-gray-500 dark:text-gray-400">Driften nå</span>
            <strong className="block text-lg font-semibold tracking-normal text-gray-950 dark:text-white">{data.summary.label}</strong>
            <small className="block truncate text-xs tracking-normal text-gray-500 dark:text-gray-400">{data.incidents.length ? `${data.incidents.length} forhold krever oppfølging` : "Ingen aktive driftsavvik"}</small>
          </div>
        </div>
        <div className="border-b border-gray-100 px-5 py-4 md:border-b-0 md:border-r dark:border-gray-700/60">
          <span className="block text-[0.65rem] font-semibold uppercase tracking-normal text-gray-500 dark:text-gray-400">Åpning</span>
          <strong className="mt-0.5 block text-base font-semibold tracking-normal text-gray-950 dark:text-white">{data.operatingWindow.label}</strong>
          <small className="text-xs tracking-normal text-gray-400">{data.operatingWindow.detail}</small>
        </div>
        <div className="border-b border-gray-100 px-5 py-4 md:border-b-0 md:border-r dark:border-gray-700/60">
          <span className="block text-[0.65rem] font-semibold uppercase tracking-normal text-gray-500 dark:text-gray-400">Systemstatus</span>
          <strong className="mt-0.5 block text-base font-semibold tracking-normal tabular-nums text-gray-950 dark:text-white">{data.summary.normal} av {data.summary.total} normale</strong>
          <small className="text-xs tracking-normal text-gray-400">{data.summary.attention} oppmerksomhet · {data.summary.critical} kritisk</small>
        </div>
        <div className="px-5 py-4">
          <span className="block text-[0.65rem] font-semibold uppercase tracking-normal text-gray-500 dark:text-gray-400">Sist kontrollert</span>
          <strong className="mt-0.5 block text-base font-semibold tracking-normal text-gray-950 dark:text-white">{relativeStamp(data.generatedAt)}</strong>
          <small className="text-xs tracking-normal text-gray-400">kl. {timeStamp(data.generatedAt)}</small>
        </div>
      </div>
      <nav aria-label="Status for driftsområder" className="grid grid-cols-2 border-t border-gray-100 sm:grid-cols-5 dark:border-gray-700/60">
        {data.areas.map((area) => {
          const style = areaStyle[area.key];
          return (
            <AppLink className="flex min-w-0 items-center gap-2.5 border-b border-r border-gray-100 px-4 py-3 transition-colors hover:bg-gray-50/80 sm:border-b-0 dark:border-gray-700/60 dark:hover:bg-gray-700/25" to={area.href} key={area.key}>
              <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${style.iconClass}`}><MosaicIcon name={style.icon} size={14} /></span>
              <span className="min-w-0">
                <strong className="block truncate text-xs font-semibold tracking-normal text-gray-800 dark:text-gray-100">{area.label}</strong>
                <small className={`flex items-center gap-1.5 truncate text-[0.68rem] tracking-normal ${area.status === "error" ? "text-red-600 dark:text-red-300" : area.status === "warning" ? "text-yellow-800 dark:text-yellow-300" : "text-gray-500 dark:text-gray-400"}`}>
                  <i className={`h-1.5 w-1.5 shrink-0 rounded-full ${statusDot(area.status)}`} />
                  {area.statusLabel}
                </small>
              </span>
            </AppLink>
          );
        })}
      </nav>
    </section>
  );
}

function IncidentStrip({ data }: { data: OperationsDashboardResponse }) {
  if (!data.incidents.length) return null;
  return (
    <section className="overflow-hidden rounded-lg border border-yellow-200 bg-white shadow-sm dark:border-yellow-500/25 dark:bg-gray-800">
      <header className="flex items-center justify-between gap-4 border-b border-gray-100 px-5 py-3 dark:border-gray-700/60">
        <div className="flex items-center gap-2"><MosaicIcon name="warning" className="text-yellow-600 dark:text-yellow-300" /><strong className="text-sm tracking-normal text-gray-900 dark:text-gray-100">Prioritert oppfølging</strong></div>
        <span className="text-xs tracking-normal tabular-nums text-gray-400">{data.incidents.length} forhold</span>
      </header>
      <div className="divide-y divide-gray-100 dark:divide-gray-700/60">
        {data.incidents.slice(0, 6).map((incident, index) => (
          <AppLink className="grid gap-1 px-5 py-3 transition-colors hover:bg-gray-50/70 sm:grid-cols-[8rem_1fr_auto] sm:items-center dark:hover:bg-gray-700/20" to={incident.href} key={`${incident.area}-${index}`}>
            <span className={`text-xs font-semibold tracking-normal ${incident.severity === "error" ? "text-red-600 dark:text-red-300" : "text-yellow-800 dark:text-yellow-300"}`}>{incident.area}</span>
            <span className="text-sm tracking-normal text-gray-700 dark:text-gray-200">{incident.title}</span>
            <MosaicIcon name="arrow-right" className="hidden text-gray-400 sm:block" />
          </AppLink>
        ))}
      </div>
    </section>
  );
}

export function OperationsDashboard({ data }: { data: OperationsDashboardResponse }) {
  return (
    <div className="space-y-5 tracking-normal">
      <SummaryStrip data={data} />
      <IncidentStrip data={data} />
      <div className="grid gap-5 xl:grid-cols-2">
        {data.areas.map((area) => <AreaPanel area={area} key={area.key} />)}
      </div>
    </div>
  );
}
