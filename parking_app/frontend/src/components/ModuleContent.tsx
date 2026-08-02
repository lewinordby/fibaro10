import { type FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { displayCell, nok, valueLabel } from "../format";
import { AppLink, useAppLocation, useAppSearchParams } from "../router";
import type { ModuleAction, ModuleChart, ModuleFilter, ModuleResponse, ModuleRow, ModuleTable, ParkingTimeline } from "../types";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "./Chart";
import { MetricCard, Panel } from "./Mosaic";
import { MosaicIcon } from "./MosaicIcon";

const palette = [mosaicChartColors.sky, mosaicChartColors.violet, mosaicChartColors.yellow, mosaicChartColors.green, mosaicChartColors.red, mosaicChartColors.gray];

export function localParkingPath(path?: string | null) {
  if (!path) return null;
  const parsed = new URL(path, window.location.origin);
  const pathname = parsed.pathname;
  const routes: Record<string, string> = {
    "/parkering/oversikt": "/",
    "/parkering/parkeringer": "/parkeringer",
    "/parkering/dagslinje": "/dagslinje",
    "/parkering/kjoretoy": "/kjoretoy",
    "/parkering/omrade": "/omrade",
    "/parkering/prognose": "/prognose",
    "/parkering/oppgjor": "/oppgjor",
    "/parkering/oppslag": "/oppslag",
    "/parkering/bilstatistikk": "/bilstatistikk",
    "/parkering/sammenligning": "/arsutvikling",
    "/parkering/tidspunkt": "/tidspunkt",
    "/parkering/ukesnitt": "/ukesnitt",
  };
  const vehicle = pathname.match(/^\/parkering\/kjoretoy\/([^/]+)$/);
  if (vehicle) return `/kjoretoy/${vehicle[1]}${parsed.search}`;
  const settlement = pathname.match(/^\/parkering\/oppgjor\/(\d+)$/);
  if (settlement) return `/oppgjor/${settlement[1]}${parsed.search}`;
  return routes[pathname] ? `${routes[pathname]}${parsed.search}` : null;
}

function cardTone(tone?: string) {
  if (tone === "parking") return "sky" as const;
  if (tone === "revenue") return "violet" as const;
  return "gray" as const;
}

function cardValue(value: string | number, unit?: string) {
  if (typeof value === "number") return nok(value, Number.isInteger(value) ? 0 : 2);
  if (unit && /^[+-]?\d[\d\s]*(?:\.\d+)?$/.test(value.trim())) {
    const parsed = Number(value.replaceAll(" ", ""));
    if (Number.isFinite(parsed)) return nok(parsed, Number.isInteger(parsed) ? 0 : 2);
  }
  return value;
}

export function ModuleCards({ cards }: { cards: ModuleResponse["cards"] }) {
  if (!cards.length) return null;
  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6 gap-6">
      {cards.map((card) => {
        const body = <MetricCard label={card.title} value={cardValue(card.value, card.unit)} unit={card.unit} detail={card.detail} tone={cardTone(card.tone)} />;
        const local = localParkingPath(card.href);
        return local ? <AppLink key={card.title} to={local} className="block transition hover:-translate-y-0.5">{body}</AppLink> : <div key={card.title}>{body}</div>;
      })}
    </section>
  );
}

export function moduleChartConfig(chart: ModuleChart): MosaicChartConfig {
  const unit = chart.series.find((series) => series.unit)?.unit || "";
  return {
    type: chart.type === "bar" ? "bar" : "line",
    labels: chart.x,
    tooltipUnit: unit,
    yTick: (value) => Math.abs(value) >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value)),
    datasets: chart.series.map((series, index) => ({
      label: series.name,
      type: (series.type || chart.type) === "bar" ? "bar" : "line",
      data: series.data.map((value) => Array.isArray(value) ? value[1] : value),
      color: series.color || palette[index % palette.length],
      stepped: Boolean(series.step),
    })),
  };
}

export function ModuleCharts({ charts = [] }: { charts?: ModuleChart[] }) {
  return <>{charts.map((chart) => <Panel key={chart.title} title={chart.title} subtitle={chart.subtitle}><div className="px-3 py-3"><Chart config={moduleChartConfig(chart)} height={Math.min(460, Math.max(280, chart.height || 340))} /></div></Panel>)}</>;
}

function RowLink({ path, fibaroUrl, children }: { path: string; fibaroUrl: string; children: React.ReactNode }) {
  const local = localParkingPath(path);
  if (local) return <AppLink to={local} className="font-medium text-sky-600 hover:text-sky-700 dark:text-sky-400">{children}</AppLink>;
  const href = /^https?:\/\//.test(path) ? path : `${fibaroUrl}${path}`;
  return <a href={href} className="font-medium text-sky-600 hover:text-sky-700 dark:text-sky-400" target={/^https?:\/\//.test(path) ? "_blank" : undefined} rel="noreferrer">{children}</a>;
}

function TableCell({ column, row, fibaroUrl }: { column: string; row: ModuleRow; fibaroUrl: string }) {
  const value = row[column];
  const rowPath = typeof row.path === "string" ? row.path : "";
  if ((column === "plate" || column === "car_license_number" || column === "period_label") && rowPath) return <RowLink path={rowPath} fibaroUrl={fibaroUrl}>{displayCell(column, value)}</RowLink>;
  if (column === "path" && typeof value === "string") return <RowLink path={value} fibaroUrl={fibaroUrl}>Åpne</RowLink>;
  if (column === "start_time" && typeof row.unifi_start_url === "string" && row.unifi_start_url) return <span className="inline-flex items-center gap-2"><span>{displayCell(column, value)}</span><a href={row.unifi_start_url} target="_blank" rel="noreferrer" title="Åpne start i UniFi Protect"><MosaicIcon name="external" className="text-sky-500" /></a></span>;
  if (column === "end_time" && typeof row.unifi_end_url === "string" && row.unifi_end_url) return <span className="inline-flex items-center gap-2"><span>{displayCell(column, value)}</span><a href={row.unifi_end_url} target="_blank" rel="noreferrer" title="Åpne slutt i UniFi Protect"><MosaicIcon name="external" className="text-sky-500" /></a></span>;
  if (column === "status") {
    const label = displayCell(column, value);
    const active = String(value || "").toLowerCase().includes("ongoing") || String(value || "").toLowerCase().includes("pågående");
    return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${active ? "bg-green-500/15 text-green-600 dark:text-green-400" : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"}`}>{label}</span>;
  }
  return <>{displayCell(column, value)}</>;
}

export function DataTable({ table, fibaroUrl }: { table: ModuleTable; fibaroUrl: string }) {
  const [, setParams] = useAppSearchParams();
  const meta = table.meta;
  const changePage = (page: number) => {
    const next = new URLSearchParams(window.location.search);
    next.set("page", String(Math.max(1, page)));
    setParams(next);
  };
  return (
    <Panel title={table.title} subtitle={meta?.totalRows != null ? `${meta.totalRows.toLocaleString("nb-NO")} rader` : undefined}>
      <div className="overflow-x-auto">
        <table className="table-auto w-full dark:text-gray-300">
          <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50">
            <tr>{table.columns.map((column) => <th className="px-4 py-3 whitespace-nowrap text-left font-semibold" key={column}>{valueLabel(column)}</th>)}</tr>
          </thead>
          <tbody className="text-sm divide-y divide-gray-100 dark:divide-gray-700/60">
            {table.rows.map((row, index) => <tr className="hover:bg-gray-50/70 dark:hover:bg-gray-700/20" key={String(row.id || row.plate || row.path || index)}>{table.columns.map((column) => <td className="px-4 py-3 whitespace-nowrap tabular-nums" key={column}><TableCell column={column} row={row} fibaroUrl={fibaroUrl} /></td>)}</tr>)}
            {!table.rows.length ? <tr><td className="px-5 py-10 text-center text-gray-400" colSpan={Math.max(1, table.columns.length)}>Ingen rader i valgt utvalg</td></tr> : null}
          </tbody>
        </table>
      </div>
      {meta && !meta.disablePagination && (meta.hasPrevious || meta.hasMore) ? <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3 dark:border-gray-700/60"><span className="text-xs text-gray-500">{meta.firstRow || 0}-{meta.lastRow || table.rows.length} av {meta.totalRows || table.rows.length}</span><div className="flex gap-2"><button className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" disabled={!meta.hasPrevious} onClick={() => changePage((meta.page || 1) - 1)}>Forrige</button><button className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" disabled={!meta.hasMore} onClick={() => changePage((meta.page || 1) + 1)}>Neste</button></div></div> : null}
    </Panel>
  );
}

export function DataTables({ tables, fibaroUrl }: { tables: ModuleTable[]; fibaroUrl: string }) {
  return <div className="space-y-6">{tables.map((table, index) => <DataTable key={`${table.title}-${index}`} table={table} fibaroUrl={fibaroUrl} />)}</div>;
}

function FilterInput({ filter, value, onChange }: { filter: ModuleFilter; value: string; onChange: (value: string) => void }) {
  const common = { id: `filter-${filter.key}`, value, onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => onChange(event.target.value), className: "form-input w-full min-w-36" };
  if (filter.type === "select") return <select {...common} className="form-select w-full min-w-36"><option value="">Alle</option>{filter.options?.map((option) => <option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select>;
  return <input {...common} type={filter.type === "datetime" ? "datetime-local" : filter.type} placeholder={filter.placeholder} />;
}

export function ModuleFilters({ filters = [] }: { filters?: ModuleFilter[] }) {
  const [params, setParams] = useAppSearchParams();
  const initial = useMemo(() => Object.fromEntries(filters.map((filter) => [filter.key, params.get(filter.key) ?? String(filter.value ?? "")])), [filters, params]);
  const [values, setValues] = useState<Record<string, string>>(initial);
  useEffect(() => setValues(initial), [initial]);
  if (!filters.length) return null;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const next = new URLSearchParams(params);
    filters.forEach((filter) => values[filter.key] ? next.set(filter.key, values[filter.key]) : next.delete(filter.key));
    next.delete("page");
    setParams(next);
  };
  return <Panel><form className="flex flex-wrap items-end gap-4 p-5" onSubmit={submit}>{filters.filter((filter) => filter.key !== "page").map((filter) => <label className="min-w-36 flex-1 text-xs font-semibold text-gray-500 dark:text-gray-400" key={filter.key}>{filter.label}<span className="mt-1 block"><FilterInput filter={filter} value={values[filter.key] || ""} onChange={(value) => setValues((current) => ({ ...current, [filter.key]: value }))} /></span></label>)}<button className="btn bg-sky-500 text-white hover:bg-sky-600" type="submit">Søk</button></form></Panel>;
}

export function ModuleActions({ actions = [], onComplete }: { actions?: ModuleAction[]; onComplete: () => void }) {
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState<{ text: string; error: boolean } | null>(null);
  if (!actions.length) return null;
  const run = async (action: ModuleAction) => {
    if (action.confirm && !window.confirm(action.confirm)) return;
    setBusy(action.key); setNotice(null);
    try {
      const result = await api.action(action);
      setNotice({ text: result.message || "Handlingen er startet", error: false });
      window.setTimeout(onComplete, 700);
    } catch (error) {
      setNotice({ text: error instanceof Error ? error.message : String(error), error: true });
    } finally { setBusy(""); }
  };
  return <div className="flex flex-wrap items-center gap-3">{actions.map((action) => <button className={`btn ${action.tone === "primary" ? "bg-sky-500 text-white hover:bg-sky-600" : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"}`} disabled={Boolean(busy)} key={action.key} onClick={() => run(action)}>{busy === action.key ? <MosaicIcon name="refresh" className="animate-spin" /> : null}{action.label}</button>)}{notice ? <span className={`text-sm ${notice.error ? "text-red-500" : "text-green-600 dark:text-green-400"}`}>{notice.text}</span> : null}</div>;
}

export function DayNavigation({ data }: { data: NonNullable<ModuleResponse["dayNavigation"]> }) {
  const [params, setParams] = useAppSearchParams();
  const go = (day: string) => { const next = new URLSearchParams(params); next.set("day", day); setParams(next); };
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  return <Panel><div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4"><div className="flex items-center gap-2"><button className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" onClick={() => go(data.prevDay)} title="Forrige dag"><MosaicIcon name="arrow-left" /></button><button className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" onClick={() => go(today)}>I dag</button><button className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" onClick={() => go(data.nextDay)} title="Neste dag"><MosaicIcon name="arrow-right" /></button></div><label className="flex items-center gap-3 text-sm text-gray-500"><strong className="text-gray-800 dark:text-gray-100">{data.selectedDayLabel}</strong><input className="form-input" type="date" value={data.selectedDay} onChange={(event) => go(event.target.value)} /></label>{data.context ? <div className="text-right text-xs text-gray-500"><strong className="block text-sm text-gray-800 dark:text-gray-100">{data.context.label}: {data.context.value}</strong>{data.context.detail}</div> : null}</div></Panel>;
}

export function ParkingTimelineView({ timeline }: { timeline: ParkingTimeline }) {
  return <Panel title="Belegg gjennom dagen" subtitle={`Fast kapasitet ${timeline.capacity} plasser · skala til ${timeline.occupancyScaleMax} biler`}>
    <div className="p-5 space-y-5">
      <div className="relative h-32 overflow-hidden rounded-lg border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/30">
        {timeline.ticks.map((tick) => <div className="absolute inset-y-0 border-l border-gray-200 dark:border-gray-700" style={{ left: `${tick.left}%` }} key={tick.label}><span className="absolute top-1 ml-1 text-[10px] text-gray-400">{tick.label}</span></div>)}
        <div className="absolute inset-x-0 bottom-0 flex h-24 items-end">{timeline.occupancy.map((item, index) => <div className={`absolute bottom-0 min-w-px ${item.count > 23 ? "bg-red-500" : item.count > 20 ? "bg-yellow-400" : "bg-sky-400"}`} key={index} style={{ left: `${item.left}%`, width: `${item.width}%`, height: `${Math.max(2, item.height)}%` }} title={item.title} />)}</div>
        {timeline.nowMarker != null ? <div className="absolute inset-y-0 border-l-2 border-red-500" style={{ left: `${timeline.nowMarker}%` }} /> : null}
      </div>
      {timeline.spaceRows.flatMap((group) => group.spaces).map((space) => <div className="grid grid-cols-[5rem_1fr] items-center gap-3" key={space.spaceId}><strong className="text-xs text-gray-500">{space.label}</strong><div className="relative h-8 overflow-hidden rounded-md border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/30">{timeline.ticks.map((tick) => <span className="absolute inset-y-0 border-l border-gray-200/70 dark:border-gray-700/70" style={{ left: `${tick.left}%` }} key={tick.label} />)}{space.sessions.map((item) => <div className={`absolute inset-y-1 rounded ${item.kind === "ongoing" ? "bg-green-500" : item.kind === "overflow" ? "bg-red-500" : "bg-sky-500"}`} style={{ left: `${item.left}%`, width: `${item.width}%` }} title={item.title} key={item.id} />)}</div></div>)}
    </div>
  </Panel>;
}

export function ModuleContent({ data, reload, fibaroUrl, showTimeline = true }: { data: ModuleResponse; reload: () => void; fibaroUrl: string; showTimeline?: boolean }) {
  const timelineNavigation = data.parkingTimeline ? {
    selectedDay: data.parkingTimeline.selectedDay,
    selectedDayLabel: data.parkingTimeline.selectedDayLabel,
    prevDay: data.parkingTimeline.prevDay,
    nextDay: data.parkingTimeline.nextDay,
  } : null;
  const navigation = data.dayNavigation || timelineNavigation;
  return <div className="space-y-6"><ModuleActions actions={data.actions} onComplete={reload} /><ModuleFilters filters={data.filters} />{navigation ? <DayNavigation data={navigation} /> : null}<ModuleCards cards={data.cards} />{showTimeline && data.parkingTimeline ? <ParkingTimelineView timeline={data.parkingTimeline} /> : null}<ModuleCharts charts={data.charts} /><DataTables tables={data.tables} fibaroUrl={fibaroUrl} /></div>;
}
