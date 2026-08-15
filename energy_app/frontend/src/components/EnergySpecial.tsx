import { useState } from "react";
import { Chart, Panel, displayCell, mosaicChartColors, nok, type MosaicChartConfig } from "@lilletorget/microapp-ui";
import { domainApi } from "@lilletorget/microapp-ui/api";
import type { JsonRecord, ModuleResponse } from "@lilletorget/microapp-ui/types";
import type { EnergyCircuitLoadsData, EnergyElviaData, EnergySunbedsData } from "../types";
import { EnergyCircuitLoads } from "./EnergyCircuitLoads";

function value(value: unknown, suffix = "") {
  if (value == null || value === "") return "-";
  if (typeof value === "number") return `${nok(value, Number.isInteger(value) ? 0 : 1)}${suffix}`;
  return `${String(value)}${suffix}`;
}

function SimpleTable({ columns, rows }: { columns: Array<{ key: string; label: string }>; rows: JsonRecord[] }) {
  return <div className="overflow-x-auto"><table className="table-auto w-full dark:text-gray-300"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/50 dark:text-gray-500"><tr>{columns.map((column) => <th className="whitespace-nowrap px-4 py-3 text-left font-semibold" key={column.key}>{column.label}</th>)}</tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{rows.map((row, index) => <tr className="hover:bg-gray-50/70 dark:hover:bg-gray-700/20" key={String(row.id || index)}>{columns.map((column) => <td className={`${column.key === "message" ? "min-w-72 whitespace-normal" : "whitespace-nowrap"} px-4 py-3 tabular-nums`} key={column.key}>{displayCell(column.key, row[column.key])}</td>)}</tr>)}{!rows.length ? <tr><td className="px-5 py-10 text-center text-gray-400" colSpan={columns.length}>Ingen data i valgt utvalg</td></tr> : null}</tbody></table></div>;
}

export function EnergySunbedsSpecial({ data }: { data: EnergySunbedsData }) {
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
    <Panel title="Importhistorikk" subtitle={`${data.imports.length} importer`}><SimpleTable columns={[{key:"timestamp",label:"Tid"},{key:"source_file",label:"Fil"},{key:"ok",label:"Resultat"},{key:"period_first",label:"Fra"},{key:"period_last",label:"Til"},{key:"hours_count",label:"Timer"},{key:"total_kwh",label:"kWh"},{key:"message",label:"Melding"}]} rows={data.imports} /></Panel>
  </div>;
}


export function EnergyCircuitLoadsSpecial({ data, reload }: { data: EnergyCircuitLoadsData; reload: () => void }) {
  return <EnergyCircuitLoads data={data} reload={reload} />;
}
