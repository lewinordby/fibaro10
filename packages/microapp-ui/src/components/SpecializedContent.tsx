import { type FormEvent, useEffect, useMemo, useState } from "react";
import { domainApi } from "../api";
import { displayCell, nok } from "../format";
import { useAppSearchParams } from "../router";
import type { ControlSettings, EnergyCircuitLoadsData, EnergyElviaData, JsonRecord, ModuleResponse, SettingsData, VentilationData } from "../types";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "./Chart";
import { Panel } from "./Mosaic";
import { MosaicIcon } from "./MosaicIcon";
import { EnergyCircuitLoads } from "./EnergyCircuitLoads";

function value(value: unknown, suffix = "") {
  if (value == null || value === "") return "-";
  if (typeof value === "number") return `${nok(value, Number.isInteger(value) ? 0 : 1)}${suffix}`;
  return `${String(value)}${suffix}`;
}

function SimpleTable({ columns, rows }: { columns: Array<{ key: string; label: string }>; rows: JsonRecord[] }) {
  return <div className="overflow-x-auto"><table className="table-auto w-full dark:text-gray-300"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/50 dark:text-gray-500"><tr>{columns.map((column) => <th className="whitespace-nowrap px-4 py-3 text-left font-semibold" key={column.key}>{column.label}</th>)}</tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{rows.map((row, index) => <tr className="hover:bg-gray-50/70 dark:hover:bg-gray-700/20" key={String(row.id || index)}>{columns.map((column) => <td className="whitespace-nowrap px-4 py-3 tabular-nums" key={column.key}>{displayCell(column.key, row[column.key])}</td>)}</tr>)}{!rows.length ? <tr><td className="px-5 py-10 text-center text-gray-400" colSpan={columns.length}>Ingen data i valgt utvalg</td></tr> : null}</tbody></table></div>;
}

function minute(time: unknown) {
  const match = typeof time === "string" ? time.match(/^(\d{1,2}):(\d{2})/) : null;
  return match ? Number(match[1]) * 60 + Number(match[2]) : null;
}

function booleanValue(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value !== "string") return null;
  const normalized = value.trim().toLowerCase();
  if (["1", "true", "on", "paa", "p\u00e5"].includes(normalized)) return true;
  if (["0", "false", "off", "av"].includes(normalized)) return false;
  return null;
}

function fanSegments(samples: JsonRecord[], attribute: string | undefined, endPercent: number) {
  if (!attribute) return [];
  const points = samples.map((sample) => ({ minute: minute(sample.time), state: booleanValue(sample[attribute]) })).filter((item): item is { minute: number; state: boolean } => item.minute != null && item.state != null).sort((a, b) => a.minute - b.minute);
  const segments: Array<{ left: number; width: number }> = [];
  let start: number | null = null;
  for (const point of points) {
    const percent = Math.max(0, Math.min(100, point.minute / 14.4));
    if (point.state && start == null) start = percent;
    if (!point.state && start != null) { if (percent > start) segments.push({ left: start, width: percent - start }); start = null; }
  }
  if (start != null && endPercent > start) segments.push({ left: start, width: endPercent - start });
  return segments;
}

function SettingsEditor({ settings, reload }: { settings: SettingsData | ControlSettings; reload: () => void }) {
  const initial = useMemo(() => Object.fromEntries(settings.groups.flatMap((group) => group.fields.map((field) => [field.key, field.value]))), [settings]);
  const [values, setValues] = useState<JsonRecord>(initial);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => setValues(initial), [initial]);
  const save = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setMessage("");
    try { await domainApi.saveSettings(settings.updateEndpoint, values, reason || "Endret i mikroappen"); setMessage("Innstillingene er lagret"); setReason(""); reload(); }
    catch (error) { setMessage(error instanceof Error ? error.message : String(error)); }
    finally { setBusy(false); }
  };
  return <form className="space-y-5" onSubmit={save}><div className="grid gap-5 xl:grid-cols-2">{settings.groups.map((group) => <Panel title={group.title} subtitle={group.description} key={group.title}><div className="grid gap-4 p-5 sm:grid-cols-2">{group.fields.map((field) => <label className="text-sm font-medium text-gray-600 dark:text-gray-300" key={field.key}>{field.type === "bool" ? <span className="flex items-center gap-3"><input type="checkbox" className="form-checkbox" checked={Boolean(values[field.key])} onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.checked }))} />{field.label}</span> : <>{field.label}{field.unit ? ` (${field.unit})` : ""}<input className="form-input mt-1 w-full" type={field.type === "time" ? "time" : field.type === "int" || field.type === "float" ? "number" : "text"} step={field.type === "float" ? "0.1" : undefined} value={String(values[field.key] ?? "")} onChange={(event) => setValues((current) => ({ ...current, [field.key]: field.type === "int" || field.type === "float" ? Number(event.target.value) : event.target.value }))} />{field.help ? <small className="mt-1 block font-normal text-gray-400">{field.help}</small> : null}</>}</label>)}</div></Panel>)}</div><Panel title="Lagre endringer" subtitle={`Versjon ${settings.version} · sist endret av ${settings.updatedBy || "-"}`}><div className="flex flex-wrap items-center gap-3 p-5"><input className="form-input min-w-64 flex-1" placeholder="Kort endringsnotat" value={reason} onChange={(event) => setReason(event.target.value)} /><button type="submit" className="btn bg-sky-500 text-white hover:bg-sky-600" disabled={busy}>{busy ? "Lagrer ..." : "Lagre"}</button>{message ? <span className="text-sm text-gray-500">{message}</span> : null}</div></Panel>{settings.rules?.length ? <Panel title="Aktive regler"><ul className="grid gap-2 p-5 text-sm text-gray-600 dark:text-gray-300">{settings.rules.map((rule) => <li className="border-l-2 border-sky-400 pl-3" key={rule}>{rule}</li>)}</ul></Panel> : null}</form>;
}

function VentilationSnapshot({ ventilation }: { ventilation: VentilationData }) {
  return <Panel title="Siste ventilasjonssample" subtitle={`${ventilation.latest.bucketStart || "-"} · ${ventilation.latest.mode || "-"}`}><div className="grid gap-4 p-5 xl:grid-cols-[1fr_auto]"> <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{ventilation.latest.groups.flatMap((group) => group.fields).map((field) => <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-gray-700/35" key={field.key}><span className="block text-xs font-semibold uppercase text-gray-400">{field.label}</span><strong className="mt-1 block text-lg text-gray-800 dark:text-gray-100">{value(field.temperature, " °C")}</strong><small>{field.humidity != null ? `${value(field.humidity, " %")}` : field.detail || ""}</small></div>)}</div><div className="min-w-48 text-right"><strong className="text-gray-800 dark:text-gray-100">{ventilation.latest.weather.text || "-"}</strong><p className="mt-1 text-sm">{value(ventilation.latest.weather.airTemperature, " °C")} · {value(ventilation.latest.weather.relativeHumidity, " %")}</p><p className="text-xs text-gray-400">Vind {value(ventilation.latest.weather.windSpeed, " m/s")} · sky {value(ventilation.latest.weather.cloudAreaFraction, " %")}</p></div></div><div className="flex flex-wrap gap-2 border-t border-gray-100 px-5 py-3 dark:border-gray-700">{ventilation.latest.fans.map((fan) => <span className="inline-flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1.5 text-sm dark:bg-gray-700" key={fan.key}>{fan.label}<strong className={fan.state ? "text-green-500" : "text-gray-500"}>{fan.state == null ? "-" : fan.state ? "PÅ" : "AV"}</strong></span>)}</div></Panel>;
}

function VentilationChart({ ventilation }: { ventilation: VentilationData }) {
  const [focus, setFocus] = useState<"temperature" | "humidity">("temperature");
  const [, setParams] = useAppSearchParams();
  const day = ventilation.day;
  const series = day.series.filter((item) => (item.kind === "humidity" || item.key.startsWith("humidity_")) === (focus === "humidity"));
  const labels = day.samples.map((sample) => String(sample.time || ""));
  const config: MosaicChartConfig = { type: "line", labels, tooltipUnit: focus === "humidity" ? "%" : "°C", beginAtZero: false, datasets: series.map((item, index) => ({ label: item.label, data: day.samples.map((sample) => typeof sample[item.key] === "number" ? Number(sample[item.key]) : null), color: item.color || [mosaicChartColors.sky, mosaicChartColors.yellow, mosaicChartColors.green, mosaicChartColors.violet][index % 4], hidden: !item.default })) };
  const go = (selectedDay: string) => { const next = new URLSearchParams(window.location.search); selectedDay ? next.set("day", selectedDay) : next.delete("day"); setParams(next); };
  const endPercent = day.isToday && day.nowMarker != null ? day.nowMarker : 100;
  return <Panel title={focus === "humidity" ? "Dagslogg fuktighet" : "Dagslogg temperatur"} actions={<div className="flex rounded-lg bg-gray-100 p-1 dark:bg-gray-700"><button className={`rounded-md px-3 py-1 text-sm ${focus === "temperature" ? "bg-white font-semibold shadow-sm dark:bg-gray-800" : ""}`} onClick={() => setFocus("temperature")}>Temperatur</button><button className={`rounded-md px-3 py-1 text-sm ${focus === "humidity" ? "bg-white font-semibold shadow-sm dark:bg-gray-800" : ""}`} onClick={() => setFocus("humidity")}>Fuktighet</button></div>}><div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-3 dark:border-gray-700"><div className="flex gap-2"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go(day.prevDay)}><MosaicIcon name="arrow-left" /></button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go("")}>I dag</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go(day.nextDay)}><MosaicIcon name="arrow-right" /></button></div><strong>{day.selectedDayLabel}</strong><input className="form-input" type="date" value={day.selectedDay} onChange={(event) => go(event.target.value)} /></div><div className="px-3 py-3"><Chart config={config} height={350} /></div><div className="space-y-2 border-t border-gray-100 p-5 dark:border-gray-700">{day.fans.map((fan, index) => { const color = fan.color || [mosaicChartColors.green, mosaicChartColors.sky, mosaicChartColors.yellow, mosaicChartColors.violet][index % 4]; const events = day.fanEvents.filter((event) => event.fan_key === fan.key); return <div className="grid grid-cols-[5rem_1fr] items-center gap-3" key={fan.key}><strong className="text-xs">{fan.short || fan.name}</strong><div className="relative h-7 overflow-hidden rounded-md border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/30">{fanSegments(day.samples, fan.sample_attr, endPercent).map((segment, position) => <span className="absolute inset-y-1 rounded opacity-75" title={`${fan.name} på`} style={{ left: `${segment.left}%`, width: `${segment.width}%`, backgroundColor: color }} key={position} />)}{events.map((event, position) => <i className={`absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 ${event.class === "on" ? "bg-current" : "bg-white dark:bg-gray-800"}`} title={`${event.time} ${event.fan_name} ${event.action}${event.detail ? ` · ${event.detail}` : ""}`} style={{ left: `${event.x / 10}%`, borderColor: event.color || color, color: event.color || color }} key={`${event.time}-${position}`} />)}</div></div>; })}</div></Panel>;
}

export function VentilationSpecial({ data, view, reload }: { data: ModuleResponse; view: string; reload: () => void }) {
  const ventilation = data.ventilation;
  if (!ventilation) return null;
  if (view === "innstillinger" && ventilation.settings) return <SettingsEditor settings={ventilation.settings} reload={reload} />;
  const weatherRows = [...(data.tables[0]?.rows || [])].reverse();
  const weatherConfig: MosaicChartConfig | null = view === "yr-logg" && weatherRows.length ? { type: "line", labels: weatherRows.map((row) => String(row.bucket_start || "")), beginAtZero: false, datasets: [
    { label: "Temperatur", data: weatherRows.map((row) => Number(row.air_temperature ?? 0)), color: mosaicChartColors.sky },
    { label: "Fuktighet", data: weatherRows.map((row) => Number(row.relative_humidity ?? 0)), color: mosaicChartColors.green },
    { label: "Vind", data: weatherRows.map((row) => Number(row.wind_speed ?? 0)), color: mosaicChartColors.violet },
    { label: "Skydekke", data: weatherRows.map((row) => Number(row.cloud_area_fraction ?? 0)), color: mosaicChartColors.gray },
  ] } : null;
  return <div className="space-y-5"><VentilationSnapshot ventilation={ventilation} />{view === "dagslogg" ? <VentilationChart ventilation={ventilation} /> : null}{weatherConfig ? <Panel title="Yr utvikling"><div className="p-3"><Chart config={weatherConfig} height={330} /></div></Panel> : null}{view === "hendelser" ? <Panel title="Dagens viftehendelser"><div className="divide-y divide-gray-100 dark:divide-gray-700">{[...ventilation.day.fanEvents].reverse().slice(0, 40).map((event, index) => <div className="grid grid-cols-[4rem_1fr_auto] items-center gap-3 px-5 py-3 text-sm" key={`${event.time}-${index}`}><strong>{event.time}</strong><span>{event.fan_name} · {event.detail}</span><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${event.class === "on" ? "bg-green-500/15 text-green-600" : "bg-gray-100 text-gray-500 dark:bg-gray-700"}`}>{event.class === "on" ? "PÅ" : "AV"}</span></div>)}</div></Panel> : null}</div>;
}

export function ControlSettingsSpecial({ settings, reload }: { settings: ControlSettings; reload: () => void }) {
  return <SettingsEditor settings={settings} reload={reload} />;
}

export function EnergySunbedsSpecial({ data }: { data: NonNullable<ModuleResponse["energySunbeds"]> }) {
  const chart: MosaicChartConfig = { type: "bar", labels: data.rooms.map((room) => room.label), beginAtZero: true, tooltipUnit: "W", datasets: [{ label: "Estimert effekt", data: data.rooms.map((room) => room.estimate_w ?? null), type: "bar", color: mosaicChartColors.yellow }] };
  const roomRows = data.rooms.map((room) => ({ id: room.room_id || room.label, rom: room.label, sun2_id: room.sun2_bed_id, modell: room.bed_model, estimert_w: room.estimate_w, snitt_w: room.avg_w, normalomr\u00e5de: `${value(room.p25_w, " W")} - ${value(room.p75_w, " W")}`, pr\u00f8ver: room.samples_count, solinger: room.sessions_count, kwh_15_min: room.kwh_15_min, m\u00e5lt_kwh: room.estimated_kwh, tillit: room.confidence }));
  const observationRows = data.observations.map((row) => ({ id: row.session_id, tid: row.start, rom: row.label, varighet_min: row.duration_minutes, pr\u00f8ver: row.samples_count, estimert_w: row.avg_w, diff_m\u00e5lt_w: row.avg_observed_w, baseline_w: row.avg_baseline_w, kwh: row.estimated_kwh }));
  return <div className="space-y-5"><Panel title="Metode" subtitle={`${data.dateFrom} - ${data.dateTo}`}><div className="grid gap-3 p-5 text-sm text-gray-600 dark:text-gray-300 sm:grid-cols-2 xl:grid-cols-4"><span><strong>Oppvarming</strong><br />{value(data.summary.warmup_minutes, " min")}</span><span><strong>Nedkjøling</strong><br />{value(data.summary.cooldown_minutes, " min")}</span><span><strong>Sampleintervall</strong><br />{value(data.summary.sample_interval_seconds, " sek")}</span><span><strong>Energisamples</strong><br />{value(data.summary.energy_samples_total)}</span></div></Panel><Panel title="Estimert effekt per solseng"><div className="p-3"><Chart config={chart} height={300} /></div></Panel><Panel title="Estimert effekt per seng"><SimpleTable columns={[{key:"rom",label:"Rom"},{key:"sun2_id",label:"Sun2-ID"},{key:"modell",label:"Modell"},{key:"estimert_w",label:"Estimat"},{key:"snitt_w",label:"Snitt"},{key:"normalområde",label:"Normalområde"},{key:"prøver",label:"Prøver"},{key:"solinger",label:"Solinger"},{key:"kwh_15_min",label:"15 min"},{key:"målt_kwh",label:"Målt kWh"},{key:"tillit",label:"Tillit"}]} rows={roomRows} /></Panel><Panel title="Rene måleobservasjoner" subtitle={`${observationRows.length} observasjoner`}><SimpleTable columns={[{key:"tid",label:"Tid"},{key:"rom",label:"Rom"},{key:"varighet_min",label:"Varighet"},{key:"prøver",label:"Prøver"},{key:"estimert_w",label:"Estimert"},{key:"diff_målt_w",label:"Diff målt"},{key:"baseline_w",label:"Baseline"},{key:"kwh",label:"kWh"}]} rows={observationRows} /></Panel></div>;
}

export function EnergyElviaSpecial({ data, reload }: { data: EnergyElviaData; reload: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const total = data.summary.total;
  const upload = async () => {
    if (!file) return;
    setBusy(true); setMessage("");
    try {
      const result = await domainApi.upload(data.uploadEndpoint, file);
      setMessage(result.message || "Elvia-filen er lest inn");
      setFile(null);
      reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };
  const summaryRows = [
    { id: "period", label: "Periode", value: `${data.summary.firstAt || "-"} - ${data.summary.lastAt || "-"}` },
    { id: "consumption", label: "Forbruk", value: `${value(total.consumption_kwh, " kWh")}` },
    { id: "production", label: "Produksjon", value: `${value(total.production_kwh, " kWh")}` },
    { id: "hours", label: "Timer", value: total.hours_count, detail: total.estimated_hours_count ? `${total.estimated_hours_count} estimerte` : "Alle faktiske" },
  ];
  const periodRows = data.yearly.map((row, index) => ({ id: index, periode: row.period_label || row.period, forbruk_kwh: row.consumption_kwh, produksjon_kwh: row.production_kwh, timer: row.hours_count, estimerte: row.estimated_hours_count, dager: row.days_count }));
  return <div className="space-y-5">
    <Panel title="Elvia-grunnlag" subtitle="Originalfiler beholdes, mens timeverdiene importeres og kontrolleres"><div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4">{summaryRows.map((row) => <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-gray-700/35" key={row.id}><span className="text-xs font-semibold uppercase text-gray-400">{row.label}</span><strong className="mt-1 block text-lg text-gray-800 dark:text-gray-100">{row.value}</strong>{row.detail ? <small className="text-gray-400">{row.detail}</small> : null}</div>)}</div></Panel>
    <Panel title="Last opp Elvia-fil" subtitle="CSV- og regnearkfiler behandles i bakgrunnen"><div className="flex flex-wrap items-center gap-3 p-5"><input className="form-input min-w-64 flex-1" type="file" accept=".csv,.xlsx,.xls" onChange={(event) => setFile(event.target.files?.[0] || null)} /><button className="btn bg-green-600 text-white hover:bg-green-700" disabled={!file || busy} onClick={upload}>{busy ? "Leser inn ..." : "Last opp og les inn"}</button>{message ? <span className="text-sm text-gray-500">{message}</span> : null}</div></Panel>
    <Panel title="Forbruk per år"><SimpleTable columns={[{key:"periode",label:"År"},{key:"forbruk_kwh",label:"Forbruk kWh"},{key:"produksjon_kwh",label:"Produksjon kWh"},{key:"timer",label:"Timer"},{key:"estimerte",label:"Estimerte"},{key:"dager",label:"Dager"}]} rows={periodRows} /></Panel>
    <div className="grid gap-5 xl:grid-cols-2"><Panel title="Største dager"><SimpleTable columns={[{key:"period_label",label:"Dag"},{key:"consumption_kwh",label:"Forbruk kWh"},{key:"production_kwh",label:"Produksjon kWh"},{key:"hours_count",label:"Timer"}]} rows={data.topDays} /></Panel><Panel title="Største måneder"><SimpleTable columns={[{key:"period_label",label:"Måned"},{key:"consumption_kwh",label:"Forbruk kWh"},{key:"production_kwh",label:"Produksjon kWh"},{key:"hours_count",label:"Timer"}]} rows={data.topMonths} /></Panel></div>
    <Panel title="Importhistorikk" subtitle={`${data.imports.length} importer`}><SimpleTable columns={[{key:"created_at",label:"Tid"},{key:"filename",label:"Fil"},{key:"status",label:"Status"},{key:"rows_imported",label:"Rader"},{key:"message",label:"Melding"}]} rows={data.imports} /></Panel>
  </div>;
}


export function EnergyCircuitLoadsSpecial({ data, reload }: { data: EnergyCircuitLoadsData; reload: () => void }) {
  return <EnergyCircuitLoads data={data} reload={reload} />;
}
