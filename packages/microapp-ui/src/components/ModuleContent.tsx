import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { domainApi } from "../api";
import { displayCell, nok, valueLabel } from "../format";
import { AppLink, useAppSearchParams } from "../router";
import { resolveCorePath } from "../navigation";
import { filterTableRows, sortTableRows, type TableSort } from "../table";
import type { Accent, DomainUiConfig, JsonRecord, ModuleAction, ModuleChart, ModuleEditConfig, ModuleEditField, ModuleFilter, ModuleResponse, ModuleRow, ModuleTable } from "../types";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "./Chart";
import { IconButton, MetricCard, Panel, Segmented } from "./Mosaic";
import { MosaicIcon } from "./MosaicIcon";

const palette = [mosaicChartColors.sky, mosaicChartColors.violet, mosaicChartColors.yellow, mosaicChartColors.green, mosaicChartColors.red, mosaicChartColors.gray];
const buttonClasses: Record<Accent, string> = { violet: "bg-violet-500 hover:bg-violet-600", sky: "bg-sky-500 hover:bg-sky-600", yellow: "bg-yellow-500 hover:bg-yellow-600", green: "bg-green-500 hover:bg-green-600", red: "bg-red-500 hover:bg-red-600" };
const linkClasses: Record<Accent, string> = { violet: "text-violet-600 dark:text-violet-400", sky: "text-sky-600 dark:text-sky-400", yellow: "text-yellow-600 dark:text-yellow-400", green: "text-green-600 dark:text-green-400", red: "text-red-600 dark:text-red-400" };

function localPath(path: string | undefined, config: DomainUiConfig) {
  return resolveCorePath(path, config.appId);
}
function tone(value: string | undefined, fallback: Accent) {
  if (value === "parking") return "sky" as const;
  if (value === "sun" || value === "sun2" || value === "solar") return "yellow" as const;
  if (value === "energy" || value === "maintenance" || value === "success") return "green" as const;
  if (value === "revenue") return "violet" as const;
  if (value === "danger" || value === "alarm") return "red" as const;
  return fallback;
}

function cardValue(value: string | number, unit?: string) {
  if (typeof value === "number") return nok(value, Number.isInteger(value) ? 0 : 2);
  if (unit && /^[+-]?\d[\d\s]*(?:[.,]\d+)?$/.test(value.trim())) {
    const parsed = Number(value.replaceAll(" ", "").replace(",", "."));
    if (Number.isFinite(parsed)) return nok(parsed, Number.isInteger(parsed) ? 0 : 2);
  }
  return value;
}

function ModuleCards({ data, config }: { data: ModuleResponse["cards"]; config: DomainUiConfig }) {
  if (!data.length) return null;
  const desktopColumns = data.length === 5 ? "xl:grid-cols-5" : "xl:grid-cols-4";
  return <section className={`grid grid-cols-1 gap-4 sm:grid-cols-2 ${desktopColumns}`}>{data.map((card) => {
    const content = <MetricCard label={card.title} value={cardValue(card.value, card.unit)} unit={card.unit} detail={card.detail} tone={tone(card.tone, config.accent)} />;
    const local = localPath(card.href, config);
    return local ? <AppLink key={card.title} to={local} className="block rounded-lg transition-shadow hover:shadow-md">{content}</AppLink> : <div key={card.title}>{content}</div>;
  })}</section>;
}

function chartConfig(chart: ModuleChart, series: ModuleChart["series"], metricUnit = ""): MosaicChartConfig {
  const timeAxis = chart.xAxisType === "time";
  const requestedVisible = new Set(chart.defaultVisibleSeries || []);
  const useRequestedVisibility = requestedVisible.size > 0 && series.some((item) => requestedVisible.has(item.name));
  const primaryUnit = metricUnit || series.find((item) => (item.yAxisIndex || 0) === 0 && item.unit)?.unit || "";
  const secondaryUnits = Array.from(new Set(series.filter((item) => item.yAxisIndex === 1).map((item) => item.unit).filter(Boolean))) as string[];
  const parseTime = (value: string) => {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : 0;
  };
  return {
    type: chart.type === "bar" ? "bar" : "line",
    labels: timeAxis ? undefined : chart.x,
    xType: timeAxis ? "linear" : "category",
    xMin: timeAxis && chart.xAxisMin ? parseTime(chart.xAxisMin) : undefined,
    xMax: timeAxis && chart.xAxisMax ? parseTime(chart.xAxisMax) : undefined,
    xTick: timeAxis ? (value) => new Date(Number(value)).toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" }) : undefined,
    yUnit: primaryUnit,
    y1Unit: secondaryUnits.length === 1 ? secondaryUnits[0] : secondaryUnits.length ? "Vær / sol" : undefined,
    y1Min: secondaryUnits.length ? 0 : undefined,
    y1Max: secondaryUnits.length === 1 && secondaryUnits[0] === "%" ? 100 : undefined,
    tooltipUnit: primaryUnit,
    yTick: (value) => Math.abs(value) >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value)),
    datasets: series.map((item, index) => ({
      label: item.name,
      type: (item.type || chart.type) === "bar" ? "bar" : "line",
      data: item.data.map((value, pointIndex) => Array.isArray(value)
        ? (timeAxis ? (value[1] == null ? null : { x: parseTime(value[0]), y: value[1] }) : value[1])
        : (timeAxis ? (value == null ? null : { x: pointIndex, y: value }) : value)),
      color: item.color || palette[index % palette.length],
      unit: item.unit || primaryUnit,
      yAxisID: item.yAxisIndex === 1 ? "y1" : "y",
      stepped: Boolean(item.step),
      hidden: useRequestedVisibility ? !requestedVisible.has(item.name) : item.hidden,
    })),
  };
}

function ModuleChartPanel({ chart }: { chart: ModuleChart }) {
  const metrics = chart.metrics || [];
  const [metricKey, setMetricKey] = useState(chart.defaultMetric || metrics[0]?.key || "");
  const [params, setParams] = useAppSearchParams();
  const activeMetric = metrics.find((metric) => metric.key === metricKey) || metrics[0];
  const activeSeries = activeMetric?.series || chart.series;
  const config = useMemo(() => chartConfig(chart, activeSeries, activeMetric?.unit), [chart, activeMetric, activeSeries]);
  const go = (day: string) => {
    const next = new URLSearchParams(params);
    if (day) next.set("day", day); else next.delete("day");
    setParams(next);
  };
  const day = chart.dayNavigation;
  const actions = metrics.length > 1 || day ? <div className="flex flex-wrap items-center justify-end gap-3">
    {metrics.length > 1 ? <Segmented options={metrics.map((metric) => ({ value: metric.key, label: metric.label }))} value={activeMetric?.key || metricKey} onChange={setMetricKey} /> : null}
    {day ? <div className="flex items-center gap-2">
      <IconButton aria-label="Forrige dag" onClick={() => go(day.prevDay)}><MosaicIcon name="arrow-left" /></IconButton>
      <button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" type="button" onClick={() => go("")}>I dag</button>
      <IconButton aria-label="Neste dag" disabled={day.isToday} onClick={() => go(day.nextDay)}><MosaicIcon name="arrow-right" /></IconButton>
      <input aria-label="Dato" className="form-input w-36" type="date" value={day.selectedDay} onChange={(event) => go(event.target.value)} />
    </div> : null}
  </div> : undefined;
  return <Panel title={chart.title} subtitle={chart.subtitle} actions={actions}><div className="px-3 py-3"><Chart config={config} height={Math.min(460, Math.max(280, chart.height || 340))} /></div></Panel>;
}

function ModuleCharts({ charts = [] }: { charts?: ModuleChart[] }) {
  return <>{charts.map((chart) => <ModuleChartPanel chart={chart} key={chart.title} />)}</>;
}

function RowLink({ path, config, coreUrl, children }: { path: string; config: DomainUiConfig; coreUrl: string; children: React.ReactNode }) {
  const local = localPath(path, config);
  const classes = `font-medium ${linkClasses[config.accent]} hover:underline`;
  if (local) return <AppLink to={local} className={classes}>{children}</AppLink>;
  const href = /^[a-z][a-z0-9+.-]*:\/\//i.test(path) ? path : `${coreUrl}${path}`;
  return <a href={href} className={classes} target="_blank" rel="noreferrer">{children}</a>;
}

function TableCell({ column, row, config, coreUrl }: { column: string; row: ModuleRow; config: DomainUiConfig; coreUrl: string }) {
  const value = row[column];
  const rowPath = typeof row.path === "string" ? row.path : "";
  const columnPath = typeof row[`${column}_url`] === "string" ? String(row[`${column}_url`]) : "";
  if (columnPath) return <RowLink path={columnPath} config={config} coreUrl={coreUrl}>{displayCell(column, value)}</RowLink>;
  if (rowPath && (column === "plate" || column === "car_license_number" || column === "period_label" || column === "title" || column === "name" || column === "build" || column === "headline")) return <RowLink path={rowPath} config={config} coreUrl={coreUrl}>{displayCell(column, value)}</RowLink>;
  if (column === "path" && typeof value === "string") return <RowLink path={value} config={config} coreUrl={coreUrl}>Åpne</RowLink>;
  if (typeof value === "string" && (/^[a-z][a-z0-9+.-]*:\/\//i.test(value) || value.startsWith("/")) && /(?:url|lenke|abonner|historikk|forhåndsvisning|forhandsvisning|health)/i.test(column)) return <RowLink path={value} config={config} coreUrl={coreUrl}>Åpne</RowLink>;
  if (column === "status") {
    const label = displayCell(column, value);
    const normalized = String(value || "").toLowerCase();
    const positive = ["ok", "active", "på", "åpen", "ferdig", "success"].some((part) => normalized.includes(part));
    const negative = ["feil", "alarm", "stopp", "mangler"].some((part) => normalized.includes(part));
    return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${negative ? "bg-red-500/15 text-red-600 dark:text-red-400" : positive ? "bg-green-500/15 text-green-600 dark:text-green-400" : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"}`}>{label}</span>;
  }
  return <>{displayCell(column, value)}</>;
}

function initialFieldValue(field: ModuleEditField, row: ModuleRow, create: boolean) {
  const value = create ? field.defaultValue : row[field.key] ?? field.defaultValue;
  if (field.type === "boolean") return Boolean(value);
  if (field.type === "tags" && Array.isArray(value)) return value.join(", ");
  return value == null ? "" : String(value);
}

const wrappingColumns = new Set([
  "summary", "description", "detail", "message", "status_text", "follow_up_text",
  "role", "problem", "recommended_action", "assessment", "note",
]);

function EditDialog({ edit, row, create, close, saved }: { edit: ModuleEditConfig; row: ModuleRow; create: boolean; close: () => void; saved: () => void }) {
  const fields = create ? edit.createFields || edit.fields : edit.fields;
  const [values, setValues] = useState<JsonRecord>(() => Object.fromEntries(fields.map((field) => [field.key, initialFieldValue(field, row, create)])));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const update = (field: ModuleEditField, value: unknown) => setValues((current) => ({ ...current, [field.key]: value }));
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    const payload = Object.fromEntries(fields.map((field) => [field.key, field.type === "number" && values[field.key] !== "" ? Number(values[field.key]) : field.type === "tags" ? String(values[field.key] || "").split(",").map((item) => item.trim()).filter(Boolean) : values[field.key]]));
    try { await domainApi.edit(edit, row, payload, create); saved(); close(); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } finally { setBusy(false); }
  };
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/55 p-4" role="dialog" aria-modal="true"><form className="max-h-[90dvh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white shadow-xl dark:bg-gray-800" onSubmit={submit}><header className="flex items-center justify-between border-b border-gray-100 px-6 py-4 dark:border-gray-700"><h2 className="font-semibold text-gray-800 dark:text-gray-100">{create ? "Ny" : "Rediger"} {edit.title.toLowerCase()}</h2><button type="button" className="text-gray-400" onClick={close}>Lukk</button></header><div className={`grid gap-4 p-6 ${edit.layout === "split" ? "md:grid-cols-2" : "grid-cols-1"}`}>{fields.map((field) => <label className={`text-sm font-medium text-gray-600 dark:text-gray-300 ${field.type === "textarea" && field.section === "main" ? "md:row-span-3" : ""}`} key={field.key}>{field.type === "boolean" ? <span className="flex items-center gap-3"><input className="form-checkbox" type="checkbox" checked={Boolean(values[field.key])} onChange={(event) => update(field, event.target.checked)} />{field.label}</span> : <>{field.label}{field.type === "textarea" ? <textarea className="form-textarea mt-1 w-full" rows={field.rows || 5} required={field.required} placeholder={field.placeholder} value={String(values[field.key] || "")} onChange={(event) => update(field, event.target.value)} /> : field.type === "select" ? <select className="form-select mt-1 w-full" required={field.required} value={String(values[field.key] ?? "")} onChange={(event) => update(field, event.target.value)}><option value="">Velg</option>{field.options?.map((option) => <option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select> : <input className="form-input mt-1 w-full" type={field.type === "datetime" ? "datetime-local" : field.type === "password" ? "password" : field.type === "number" ? "number" : "text"} required={field.required} placeholder={field.placeholder} value={String(values[field.key] ?? "")} onChange={(event) => update(field, event.target.value)} />}</>}</label>)}</div>{error ? <p className="px-6 pb-2 text-sm text-red-500">{error}</p> : null}<footer className="flex justify-end gap-3 border-t border-gray-100 px-6 py-4 dark:border-gray-700"><button className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" type="button" onClick={close}>Avbryt</button><button className="btn bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900" disabled={busy} type="submit">{busy ? "Lagrer ..." : "Lagre"}</button></footer></form></div>;
}

export function DataTable({ table, config, coreUrl, reload }: { table: ModuleTable; config: DomainUiConfig; coreUrl: string; reload: () => void }) {
  const [, setParams] = useAppSearchParams();
  const [editing, setEditing] = useState<{ row: ModuleRow; create: boolean } | null>(null);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<TableSort>(null);
  const [localPage, setLocalPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const meta = table.meta;
  const serverPaged = Boolean(meta?.pageSize && typeof meta.totalRows === "number");
  const filteredRows = useMemo(
    () => serverPaged ? table.rows : filterTableRows(table.rows, table.columns, query),
    [query, serverPaged, table.columns, table.rows],
  );
  const sortedRows = useMemo(() => sortTableRows(filteredRows, sort), [filteredRows, sort]);
  const clientPaged = !serverPaged && !meta?.disablePagination;
  const pageCount = Math.max(1, Math.ceil(sortedRows.length / pageSize));
  const safeLocalPage = Math.min(localPage, pageCount);
  const visibleRows = clientPaged ? sortedRows.slice((safeLocalPage - 1) * pageSize, safeLocalPage * pageSize) : sortedRows;
  const firstRow = sortedRows.length ? (clientPaged ? (safeLocalPage - 1) * pageSize : 0) + 1 : 0;
  const lastRow = clientPaged ? Math.min(safeLocalPage * pageSize, sortedRows.length) : sortedRows.length;
  useEffect(() => setLocalPage(1), [pageSize, query, sort]);
  const changePage = (page: number) => { const next = new URLSearchParams(window.location.search); next.set("page", String(Math.max(1, page))); setParams(next); };
  const toggleSort = (column: string) => setSort((current) => current?.column === column
    ? current.direction === "asc" ? { column, direction: "desc" } : null
    : { column, direction: "asc" });
  const showClientSearch = !serverPaged && table.rows.length >= 8;
  const canCreate = Boolean(table.edit?.createEndpoint);
  const totalLabel = serverPaged ? meta?.totalRows || table.rows.length : table.rows.length;
  const subtitle = query && !serverPaged
    ? `${filteredRows.length.toLocaleString("nb-NO")} av ${totalLabel.toLocaleString("nb-NO")} rader`
    : `${totalLabel.toLocaleString("nb-NO")} rader`;
  const toolbar = showClientSearch || canCreate ? <div className="flex flex-wrap items-center justify-end gap-2">
    {showClientSearch ? <label className="relative"><span className="sr-only">Søk i {table.title}</span><input className="form-input w-52" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Søk i tabellen" /></label> : null}
    {canCreate ? <button className={`btn text-white ${buttonClasses[config.accent]}`} onClick={() => setEditing({ row: {}, create: true })}>Ny</button> : null}
  </div> : undefined;
  return <><Panel title={table.title} subtitle={subtitle} actions={toolbar}><div className="overflow-x-auto"><table className="table-auto w-full dark:text-gray-300"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/50 dark:text-gray-500"><tr>{table.columns.map((column) => <th className="whitespace-nowrap px-4 py-3 text-left font-semibold" key={column}><button className="inline-flex items-center gap-1.5 uppercase hover:text-gray-700 dark:hover:text-gray-200" type="button" onClick={() => toggleSort(column)} title={`Sorter etter ${valueLabel(column)}`}>{valueLabel(column)}{sort?.column === column ? <MosaicIcon name={sort.direction === "asc" ? "arrow-up" : "arrow-down"} size={12} /> : null}</button></th>)}{table.edit ? <th className="px-4 py-3 text-right">Handling</th> : null}</tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{visibleRows.map((row, index) => <tr className="hover:bg-gray-50/70 dark:hover:bg-gray-700/20" key={`${String(row.id ?? row.path ?? "row")}-${firstRow + index}`}>{table.columns.map((column) => <td className={`${wrappingColumns.has(column) ? "min-w-64 max-w-xl whitespace-normal leading-5" : "whitespace-nowrap"} px-4 py-3 tabular-nums`} key={column}><TableCell column={column} row={row} config={config} coreUrl={coreUrl} /></td>)}{table.edit ? <td className="px-4 py-3 text-right"><button className={`text-sm font-medium ${linkClasses[config.accent]}`} onClick={() => setEditing({ row, create: false })}>Rediger</button></td> : null}</tr>)}{!visibleRows.length ? <tr><td className="px-5 py-10 text-center text-gray-400" colSpan={table.columns.length + (table.edit ? 1 : 0)}>{query ? "Ingen treff for søket" : "Ingen rader i valgt utvalg"}</td></tr> : null}</tbody></table></div>{serverPaged && meta && !meta.disablePagination && (meta.hasPrevious || meta.hasMore) ? <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3 dark:border-gray-700"><span className="text-xs text-gray-500">{meta.firstRow || 0}-{meta.lastRow || table.rows.length} av {meta.totalRows || table.rows.length}</span><div className="flex gap-2"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={!meta.hasPrevious} onClick={() => changePage((meta.page || 1) - 1)}>Forrige</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={!meta.hasMore} onClick={() => changePage((meta.page || 1) + 1)}>Neste</button></div></div> : clientPaged && sortedRows.length > 25 ? <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 px-5 py-3 dark:border-gray-700"><span className="text-xs text-gray-500">{firstRow}-{lastRow} av {sortedRows.length.toLocaleString("nb-NO")}</span><div className="flex items-center gap-2"><select className="form-select py-1 text-sm" aria-label="Rader per side" value={pageSize} onChange={(event) => setPageSize(Number(event.target.value))}>{[25, 50, 100].map((size) => <option value={size} key={size}>{size} per side</option>)}</select><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={safeLocalPage <= 1} onClick={() => setLocalPage((page) => Math.max(1, page - 1))}>Forrige</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={safeLocalPage >= pageCount} onClick={() => setLocalPage((page) => Math.min(pageCount, page + 1))}>Neste</button></div></div> : null}</Panel>{editing && table.edit ? <EditDialog edit={table.edit} row={editing.row} create={editing.create} close={() => setEditing(null)} saved={reload} /> : null}</>;
}

function FilterInput({ filter, value, onChange }: { filter: ModuleFilter; value: string; onChange: (value: string) => void }) {
  if (filter.type === "select") return <select className="form-select w-full min-w-36" value={value} onChange={(event) => onChange(event.target.value)}><option value="">Alle</option>{filter.options?.map((option) => <option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select>;
  return <input className="form-input w-full min-w-36" value={value} onChange={(event) => onChange(event.target.value)} type={filter.type === "datetime" ? "datetime-local" : filter.type} placeholder={filter.placeholder} />;
}

function ModuleFilters({ filters = [], accent }: { filters?: ModuleFilter[]; accent: Accent }) {
  const [params, setParams] = useAppSearchParams();
  const initial = useMemo(() => Object.fromEntries(filters.map((filter) => [filter.key, params.get(filter.key) ?? String(filter.value ?? "")])), [filters, params]);
  const [values, setValues] = useState<Record<string, string>>(initial);
  useEffect(() => setValues(initial), [initial]);
  if (!filters.length) return null;
  const submit = (event: FormEvent) => { event.preventDefault(); const next = new URLSearchParams(params); filters.forEach((filter) => values[filter.key] ? next.set(filter.key, values[filter.key]) : next.delete(filter.key)); next.delete("page"); setParams(next); };
  return <Panel><form className="flex flex-wrap items-end gap-4 p-5" onSubmit={submit}>{filters.filter((filter) => filter.key !== "page").map((filter) => <label className="min-w-36 flex-1 text-xs font-semibold text-gray-500 dark:text-gray-400" key={filter.key}>{filter.label}<span className="mt-1 block"><FilterInput filter={filter} value={values[filter.key] || ""} onChange={(value) => setValues((current) => ({ ...current, [filter.key]: value }))} /></span></label>)}<button className={`btn text-white ${buttonClasses[accent]}`} type="submit">Søk</button></form></Panel>;
}

function ModuleActions({ actions = [], reload, accent }: { actions?: ModuleAction[]; reload: () => void; accent: Accent }) {
  const [busy, setBusy] = useState(""); const [notice, setNotice] = useState("");
  if (!actions.length) return null;
  const run = async (action: ModuleAction) => { if (action.confirm && !window.confirm(action.confirm)) return; setBusy(action.key); setNotice(""); try { const result = await domainApi.action(action); setNotice(result.message || "Handlingen er startet"); window.setTimeout(reload, 500); } catch (reason) { setNotice(reason instanceof Error ? reason.message : String(reason)); } finally { setBusy(""); } };
  return <div className="flex flex-wrap items-center gap-3">{actions.map((action) => <button className={`btn ${action.tone === "primary" ? `${buttonClasses[accent]} text-white` : "border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"}`} disabled={Boolean(busy)} key={action.key} onClick={() => run(action)}>{busy === action.key ? <MosaicIcon name="refresh" className="animate-spin" /> : null}{action.label}</button>)}{notice ? <span className="text-sm text-gray-500">{notice}</span> : null}</div>;
}

function DayNavigation({ data }: { data: NonNullable<ModuleResponse["dayNavigation"]> }) {
  const [params, setParams] = useAppSearchParams();
  const go = (day: string) => { const next = new URLSearchParams(params); next.set("day", day); setParams(next); };
  return <Panel><div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4"><div className="flex items-center gap-2"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go(data.prevDay)}><MosaicIcon name="arrow-left" /></button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go("")}>I dag</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go(data.nextDay)}><MosaicIcon name="arrow-right" /></button></div><label className="flex items-center gap-3 text-sm text-gray-500"><strong className="text-gray-800 dark:text-gray-100">{data.selectedDayLabel}</strong><input className="form-input" type="date" value={data.selectedDay} onChange={(event) => go(event.target.value)} /></label></div></Panel>;
}

function UploadPanel({ endpoint, reload, accent }: { endpoint: string; reload: () => void; accent: Accent }) {
  const [file, setFile] = useState<File | null>(null); const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const upload = async () => { if (!file) return; setBusy(true); setMessage(""); try { const result = await domainApi.upload(endpoint, file); setMessage(result.message || "Filen er lastet opp"); setFile(null); reload(); } catch (reason) { setMessage(reason instanceof Error ? reason.message : String(reason)); } finally { setBusy(false); } };
  return <Panel title="Last opp fil"><div className="flex flex-wrap items-center gap-3 p-5"><input className="form-input min-w-64 flex-1" type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} /><button className={`btn text-white ${buttonClasses[accent]}`} disabled={!file || busy} onClick={upload}>{busy ? "Laster opp ..." : "Last opp"}</button>{message ? <span className="text-sm text-gray-500">{message}</span> : null}</div></Panel>;
}

export type ModuleAppContent = {
  content: ReactNode;
  hideActions?: boolean;
  hideFilters?: boolean;
  hideDayNavigation?: boolean;
  hideUpload?: boolean;
  hideCards?: boolean;
  hideCharts?: boolean;
  hideTables?: boolean;
  tables?: ModuleTable[];
};

export function ModuleContent({ data, config, reload, coreUrl, appContent }: { data: ModuleResponse; config: DomainUiConfig; reload: () => void; coreUrl: string; module: string; view: string; appContent?: ModuleAppContent | null }) {
  const empty = !data.cards.length && !(data.charts?.length) && !data.tables.length;
  const visibleTables = appContent?.tables || data.tables;
  return <div className="space-y-6">
    {!appContent?.hideActions ? <ModuleActions actions={data.actions} reload={reload} accent={config.accent} /> : null}
    {!appContent?.hideFilters ? <ModuleFilters filters={data.filters} accent={config.accent} /> : null}
    {!appContent?.hideDayNavigation && data.dayNavigation ? <DayNavigation data={data.dayNavigation} /> : null}
    {!appContent?.hideUpload && data.uploadEndpoint ? <UploadPanel endpoint={data.uploadEndpoint} reload={reload} accent={config.accent} /> : null}
    {!appContent?.hideCards ? <ModuleCards data={data.cards} config={config} /> : null}
    {appContent?.content}
    {!appContent?.hideCharts ? <ModuleCharts charts={data.charts} /> : null}
    {!appContent?.hideTables ? visibleTables.map((table, index) => <DataTable key={`${table.title}-${index}`} table={table} config={config} coreUrl={coreUrl} reload={reload} />) : null}
    {empty && !appContent?.content ? <Panel title={data.title}><div className="p-6 text-sm text-gray-500 dark:text-gray-400">{data.subtitle || "Denne visningen har ingen data i valgt utvalg."}</div></Panel> : null}
  </div>;
}
