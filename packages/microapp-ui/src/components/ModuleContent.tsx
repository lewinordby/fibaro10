import { lazy, Suspense, type ComponentProps, type FormEvent, useEffect, useMemo, useState } from "react";
import { domainApi } from "../api";
import { displayCell, nok, valueLabel } from "../format";
import { AppLink, useAppSearchParams } from "../router";
import type { Accent, DomainUiConfig, JsonRecord, ModuleAction, ModuleChart, ModuleEditConfig, ModuleEditField, ModuleFilter, ModuleResponse, ModuleRow, ModuleTable, SunTimeline } from "../types";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "./Chart";
import { MetricCard, Panel } from "./Mosaic";
import { MosaicIcon } from "./MosaicIcon";

const VentilationSpecialAsync = lazy(() => import("./SpecializedContent").then((module) => ({ default: module.VentilationSpecial })));
const EnergySunbedsSpecialAsync = lazy(() => import("./SpecializedContent").then((module) => ({ default: module.EnergySunbedsSpecial })));
const EnergyElviaSpecialAsync = lazy(() => import("./SpecializedContent").then((module) => ({ default: module.EnergyElviaSpecial })));
const EnergyCircuitLoadsSpecialAsync = lazy(() => import("./SpecializedContent").then((module) => ({ default: module.EnergyCircuitLoadsSpecial })));
const ControlSettingsSpecialAsync = lazy(() => import("./SpecializedContent").then((module) => ({ default: module.ControlSettingsSpecial })));
const SunSessionsSpecialAsync = lazy(() => import("./SunSessionsSpecial").then((module) => ({ default: module.SunSessionsSpecial })));
const LinkReviewSpecialAsync = lazy(() => import("./LinkReviewSpecial").then((module) => ({ default: module.LinkReviewSpecial })));
const BollardsSpecialAsync = lazy(() => import("./BollardsSpecial").then((module) => ({ default: module.BollardsSpecial })));
const DoorsSpecialAsync = lazy(() => import("./DoorsSpecial").then((module) => ({ default: module.DoorsSpecial })));
const MobilePreviewSpecialAsync = lazy(() => import("./MobilePreviewSpecial").then((module) => ({ default: module.MobilePreviewSpecial })));

function SpecializedFallback() {
  return <Panel><div className="p-6 text-sm text-gray-400">Klargjør detaljvisning ...</div></Panel>;
}

function VentilationSpecial(props: ComponentProps<typeof VentilationSpecialAsync>) {
  return <Suspense fallback={<SpecializedFallback />}><VentilationSpecialAsync {...props} /></Suspense>;
}

function EnergySunbedsSpecial(props: ComponentProps<typeof EnergySunbedsSpecialAsync>) {
  return <Suspense fallback={<SpecializedFallback />}><EnergySunbedsSpecialAsync {...props} /></Suspense>;
}

function EnergyElviaSpecial(props: ComponentProps<typeof EnergyElviaSpecialAsync>) {
  return <Suspense fallback={<SpecializedFallback />}><EnergyElviaSpecialAsync {...props} /></Suspense>;
}

function EnergyCircuitLoadsSpecial(props: ComponentProps<typeof EnergyCircuitLoadsSpecialAsync>) {
  return <Suspense fallback={<SpecializedFallback />}><EnergyCircuitLoadsSpecialAsync {...props} /></Suspense>;
}

function ControlSettingsSpecial(props: ComponentProps<typeof ControlSettingsSpecialAsync>) {
  return <Suspense fallback={<SpecializedFallback />}><ControlSettingsSpecialAsync {...props} /></Suspense>;
}

function SunSessionsSpecial(props: ComponentProps<typeof SunSessionsSpecialAsync>) {
  return <Suspense fallback={<SpecializedFallback />}><SunSessionsSpecialAsync {...props} /></Suspense>;
}

function LinkReviewSpecial(props: ComponentProps<typeof LinkReviewSpecialAsync>) {
  return <Suspense fallback={<SpecializedFallback />}><LinkReviewSpecialAsync {...props} /></Suspense>;
}

function BollardsSpecial() {
  return <Suspense fallback={<SpecializedFallback />}><BollardsSpecialAsync /></Suspense>;
}

function DoorsSpecial(props: ComponentProps<typeof DoorsSpecialAsync>) {
  return <Suspense fallback={<SpecializedFallback />}><DoorsSpecialAsync {...props} /></Suspense>;
}

function MobilePreviewSpecial(props: ComponentProps<typeof MobilePreviewSpecialAsync>) {
  return <Suspense fallback={<SpecializedFallback />}><MobilePreviewSpecialAsync {...props} /></Suspense>;
}

const palette = [mosaicChartColors.sky, mosaicChartColors.violet, mosaicChartColors.yellow, mosaicChartColors.green, mosaicChartColors.red, mosaicChartColors.gray];
const buttonClasses: Record<Accent, string> = { violet: "bg-violet-500 hover:bg-violet-600", sky: "bg-sky-500 hover:bg-sky-600", yellow: "bg-yellow-500 hover:bg-yellow-600", green: "bg-green-500 hover:bg-green-600", red: "bg-red-500 hover:bg-red-600" };
const linkClasses: Record<Accent, string> = { violet: "text-violet-600 dark:text-violet-400", sky: "text-sky-600 dark:text-sky-400", yellow: "text-yellow-600 dark:text-yellow-400", green: "text-green-600 dark:text-green-400", red: "text-red-600 dark:text-red-400" };

function localPath(path: string | undefined, config: DomainUiConfig) {
  if (!path) return null;
  const parsed = new URL(path, window.location.origin);
  const entries = config.navigation.flatMap((group) => group.items);
  const exact = entries.find((entry) => (entry.corePath || `/${entry.module}/${entry.view}`) === parsed.pathname);
  if (exact) return `${exact.to}${parsed.search}`;
  const nested = entries
    .map((entry) => ({ entry, corePath: entry.corePath || `/${entry.module}/${entry.view}` }))
    .filter(({ corePath }) => parsed.pathname.startsWith(`${corePath}/`))
    .sort((left, right) => right.corePath.length - left.corePath.length)[0];
  if (!nested) return null;
  const suffix = parsed.pathname.slice(nested.corePath.length);
  const base = nested.entry.to === "/" ? "" : nested.entry.to;
  return `${base}${suffix}${parsed.search}` || "/";
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
  return <section className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">{data.map((card) => {
    const content = <MetricCard label={card.title} value={cardValue(card.value, card.unit)} unit={card.unit} detail={card.detail} tone={tone(card.tone, config.accent)} />;
    const local = localPath(card.href, config);
    return local ? <AppLink key={card.title} to={local} className="block transition hover:-translate-y-0.5">{content}</AppLink> : <div key={card.title}>{content}</div>;
  })}</section>;
}

function chartConfig(chart: ModuleChart): MosaicChartConfig {
  const unit = chart.series.find((series) => series.unit)?.unit || "";
  return { type: chart.type === "bar" ? "bar" : "line", labels: chart.x, tooltipUnit: unit, yTick: (value) => Math.abs(value) >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value)), datasets: chart.series.map((series, index) => ({ label: series.name, type: (series.type || chart.type) === "bar" ? "bar" : "line", data: series.data.map((value) => Array.isArray(value) ? value[1] : value), color: series.color || palette[index % palette.length], stepped: Boolean(series.step), hidden: series.hidden })) };
}

function ModuleCharts({ charts = [] }: { charts?: ModuleChart[] }) {
  return <>{charts.map((chart) => <Panel key={chart.title} title={chart.title} subtitle={chart.subtitle}><div className="px-3 py-3"><Chart config={chartConfig(chart)} height={Math.min(460, Math.max(280, chart.height || 340))} /></div></Panel>)}</>;
}

function RowLink({ path, config, coreUrl, children }: { path: string; config: DomainUiConfig; coreUrl: string; children: React.ReactNode }) {
  const local = localPath(path, config);
  const classes = `font-medium ${linkClasses[config.accent]} hover:underline`;
  if (local) return <AppLink to={local} className={classes}>{children}</AppLink>;
  const href = /^https?:\/\//.test(path) ? path : `${coreUrl}${path}`;
  return <a href={href} className={classes} target="_blank" rel="noreferrer">{children}</a>;
}

function TableCell({ column, row, config, coreUrl }: { column: string; row: ModuleRow; config: DomainUiConfig; coreUrl: string }) {
  const value = row[column];
  const rowPath = typeof row.path === "string" ? row.path : "";
  const columnPath = typeof row[`${column}_url`] === "string" ? String(row[`${column}_url`]) : "";
  if (columnPath) return <RowLink path={columnPath} config={config} coreUrl={coreUrl}>{displayCell(column, value)}</RowLink>;
  if (rowPath && (column === "plate" || column === "car_license_number" || column === "period_label" || column === "title" || column === "name" || column === "build" || column === "headline")) return <RowLink path={rowPath} config={config} coreUrl={coreUrl}>{displayCell(column, value)}</RowLink>;
  if (column === "path" && typeof value === "string") return <RowLink path={value} config={config} coreUrl={coreUrl}>Åpne</RowLink>;
  if (typeof value === "string" && (/^https?:\/\//.test(value) || value.startsWith("/")) && /(?:url|lenke|abonner|historikk|forhåndsvisning|forhandsvisning|health)/i.test(column)) return <RowLink path={value} config={config} coreUrl={coreUrl}>Åpne</RowLink>;
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
  const meta = table.meta;
  const changePage = (page: number) => { const next = new URLSearchParams(window.location.search); next.set("page", String(Math.max(1, page))); setParams(next); };
  return <><Panel title={table.title} subtitle={meta?.totalRows != null ? `${meta.totalRows.toLocaleString("nb-NO")} rader` : undefined} actions={table.edit?.createEndpoint ? <button className={`btn text-white ${buttonClasses[config.accent]}`} onClick={() => setEditing({ row: {}, create: true })}>Ny</button> : undefined}><div className="overflow-x-auto"><table className="table-auto w-full dark:text-gray-300"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/50 dark:text-gray-500"><tr>{table.columns.map((column) => <th className="px-4 py-3 whitespace-nowrap text-left font-semibold" key={column}>{valueLabel(column)}</th>)}{table.edit ? <th className="px-4 py-3 text-right">Handling</th> : null}</tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{table.rows.map((row, index) => <tr className="hover:bg-gray-50/70 dark:hover:bg-gray-700/20" key={String(row.id || row.path || index)}>{table.columns.map((column) => <td className="px-4 py-3 whitespace-nowrap tabular-nums" key={column}><TableCell column={column} row={row} config={config} coreUrl={coreUrl} /></td>)}{table.edit ? <td className="px-4 py-3 text-right"><button className={`text-sm font-medium ${linkClasses[config.accent]}`} onClick={() => setEditing({ row, create: false })}>Rediger</button></td> : null}</tr>)}{!table.rows.length ? <tr><td className="px-5 py-10 text-center text-gray-400" colSpan={table.columns.length + (table.edit ? 1 : 0)}>Ingen rader i valgt utvalg</td></tr> : null}</tbody></table></div>{meta && !meta.disablePagination && (meta.hasPrevious || meta.hasMore) ? <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3 dark:border-gray-700"><span className="text-xs text-gray-500">{meta.firstRow || 0}-{meta.lastRow || table.rows.length} av {meta.totalRows || table.rows.length}</span><div className="flex gap-2"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={!meta.hasPrevious} onClick={() => changePage((meta.page || 1) - 1)}>Forrige</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={!meta.hasMore} onClick={() => changePage((meta.page || 1) + 1)}>Neste</button></div></div> : null}</Panel>{editing && table.edit ? <EditDialog edit={table.edit} row={editing.row} create={editing.create} close={() => setEditing(null)} saved={reload} /> : null}</>;
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

function SunTimelineView({ timeline, config }: { timeline: SunTimeline; config: DomainUiConfig }) {
  const [, setParams] = useAppSearchParams();
  const go = (day: string) => { const next = new URLSearchParams(window.location.search); day ? next.set("day", day) : next.delete("day"); setParams(next); };
  const itemClass = (kind: string) => kind === "member" ? "bg-yellow-500" : kind === "no-member" ? "bg-red-400" : "bg-sky-500";
  return <div className="space-y-5"><Panel><div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4"><div className="flex gap-2"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go(timeline.prevDay)}><MosaicIcon name="arrow-left" /></button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go("")}>I dag</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go(timeline.nextDay)}><MosaicIcon name="arrow-right" /></button></div><strong className="text-sm text-gray-800 dark:text-gray-100">{timeline.selectedDayLabel}</strong><input className="form-input" type="date" value={timeline.selectedDay} onChange={(event) => go(event.target.value)} /></div></Panel><Panel title="Rom gjennom døgnet" subtitle={`${timeline.totals.sessionsCount} solinger · ${nok(timeline.totals.paidAmountKr)} kr · ${nok(timeline.totals.durationMinutes)} min`}><div className="overflow-x-auto p-5"><div className="min-w-[760px] space-y-2"><div className="grid grid-cols-[7rem_1fr_5rem] gap-3"><span /><div className="relative h-5">{timeline.ticks.map((tick) => <span className="absolute text-[10px] text-gray-400" style={{ left: `${tick.left}%` }} key={tick.label}>{tick.label}</span>)}</div><span /></div>{timeline.rooms.map((room) => <div className="grid grid-cols-[7rem_1fr_5rem] items-center gap-3" key={room.roomId}><strong className="text-xs text-gray-600 dark:text-gray-300">{room.label}</strong><div className="relative h-8 overflow-hidden rounded-md border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/30">{timeline.ticks.map((tick) => <span className="absolute inset-y-0 border-l border-gray-200 dark:border-gray-700" style={{ left: `${tick.left}%` }} key={tick.label} />)}{room.sessions.map((item, index) => { const href = localPath(item.href, config); const block = <span className={`absolute inset-y-1 min-w-px rounded ${itemClass(item.kind)}`} style={{ left: `${item.left}%`, width: `${item.width}%` }} title={item.title} />; return href ? <AppLink to={href} key={`${item.left}-${index}`}>{block}</AppLink> : <span key={`${item.left}-${index}`}>{block}</span>; })}{timeline.nowMarker != null ? <span className="absolute inset-y-0 border-l-2 border-red-500" style={{ left: `${timeline.nowMarker}%` }} /> : null}</div><span className="text-right text-xs tabular-nums text-gray-500">{room.count} / {room.minutes}m</span></div>)}</div></div></Panel></div>;
}

function UploadPanel({ endpoint, reload, accent }: { endpoint: string; reload: () => void; accent: Accent }) {
  const [file, setFile] = useState<File | null>(null); const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const upload = async () => { if (!file) return; setBusy(true); setMessage(""); try { const result = await domainApi.upload(endpoint, file); setMessage(result.message || "Filen er lastet opp"); setFile(null); reload(); } catch (reason) { setMessage(reason instanceof Error ? reason.message : String(reason)); } finally { setBusy(false); } };
  return <Panel title="Last opp fil"><div className="flex flex-wrap items-center gap-3 p-5"><input className="form-input min-w-64 flex-1" type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} /><button className={`btn text-white ${buttonClasses[accent]}`} disabled={!file || busy} onClick={upload}>{busy ? "Laster opp ..." : "Last opp"}</button>{message ? <span className="text-sm text-gray-500">{message}</span> : null}</div></Panel>;
}

export function ModuleContent({ data, config, reload, coreUrl, module, view }: { data: ModuleResponse; config: DomainUiConfig; reload: () => void; coreUrl: string; module: string; view: string }) {
  const empty = !data.cards.length && !(data.charts?.length) && !data.tables.length && !data.sunTimeline;
  const ventilationSpecial = module === "ventilasjon" && data.ventilation;
  const sunbedSpecial = module === "energi" && view === "forbruk-per-seng" && data.energySunbeds;
  const elviaSpecial = module === "energi" && view === "elvia" && data.energyElvia;
  const circuitSpecial = module === "energi" && view === "kurs-last" && data.energyCircuitLoads;
  const settingsSpecial = Boolean(data.controlSettings);
  const sunSessionsSpecial = module === "soling" && view === "enkeltimer";
  const linkSpecial = module === "koble" && data.kobleReview;
  const linkCustomView = Boolean(linkSpecial && ["oversikt", "kandidater", "biltreff", "sun2", "sun2-kontroll"].includes(view));
  const bollardsSpecial = module === "pullerter";
  const doorsSpecial = module === "dorer" && ["oversikt", "solrom", "romkontroll-ny2"].includes(view);
  const mobileSpecial = module === "mobil";
  const visibleTables = module !== "koble"
    ? data.tables
    : view === "treffgrunnlag"
      ? data.tables.filter((table) => table.title === "Treffgrunnlag")
      : view === "jobb"
        ? data.tables.filter((table) => ["Jobbparametere", "Sist behandlet"].includes(table.title))
        : [];
  const hidesGenericTables = Boolean(sunSessionsSpecial || sunbedSpecial || elviaSpecial || circuitSpecial || settingsSpecial || linkCustomView || bollardsSpecial || doorsSpecial || mobileSpecial || (ventilationSpecial && view === "innstillinger"));
  const showActions = module !== "koble" || view === "jobb";
  const showCards = !elviaSpecial && !(linkSpecial && view !== "oversikt");
  const showUpload = Boolean(data.uploadEndpoint && !elviaSpecial);
  return <div className="space-y-6">{showActions ? <ModuleActions actions={data.actions} reload={reload} accent={config.accent} /> : null}{!doorsSpecial ? <ModuleFilters filters={data.filters} accent={config.accent} /> : null}{data.dayNavigation && !data.sunTimeline ? <DayNavigation data={data.dayNavigation} /> : null}{showUpload ? <UploadPanel endpoint={data.uploadEndpoint!} reload={reload} accent={config.accent} /> : null}{showCards && !bollardsSpecial && !doorsSpecial ? <ModuleCards data={data.cards} config={config} /> : null}{data.sunTimeline ? <SunTimelineView timeline={data.sunTimeline} config={config} /> : null}{ventilationSpecial ? <VentilationSpecial data={data} view={view} reload={reload} /> : null}{sunSessionsSpecial ? <SunSessionsSpecial table={data.tables.find((table) => table.title === "Enkeltimer")} reload={reload} /> : null}{elviaSpecial ? <EnergyElviaSpecial data={elviaSpecial} reload={reload} /> : null}{sunbedSpecial ? <EnergySunbedsSpecial data={sunbedSpecial} /> : null}{circuitSpecial ? <EnergyCircuitLoadsSpecial data={circuitSpecial} reload={reload} /> : null}{data.controlSettings ? <ControlSettingsSpecial settings={data.controlSettings} reload={reload} /> : null}{linkSpecial ? <LinkReviewSpecial review={linkSpecial} view={view} reload={reload} /> : null}{bollardsSpecial ? <BollardsSpecial /> : null}{doorsSpecial ? <DoorsSpecial view={view} /> : null}{mobileSpecial ? <MobilePreviewSpecial table={data.tables[0]} /> : null}{!ventilationSpecial && !elviaSpecial && !bollardsSpecial && !doorsSpecial && !mobileSpecial ? <ModuleCharts charts={data.charts} /> : null}{!hidesGenericTables ? visibleTables.map((table, index) => <DataTable key={`${table.title}-${index}`} table={table} config={config} coreUrl={coreUrl} reload={reload} />) : null}{empty && !ventilationSpecial && !sunSessionsSpecial && !sunbedSpecial && !elviaSpecial && !circuitSpecial && !settingsSpecial && !linkSpecial && !bollardsSpecial && !doorsSpecial && !mobileSpecial ? <Panel title={data.title}><div className="p-6 text-sm text-gray-500 dark:text-gray-400">{data.subtitle || "Denne visningen har ingen data i valgt utvalg."}</div></Panel> : null}</div>;
}
