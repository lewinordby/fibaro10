import { useMemo, useState } from "react";
import { api } from "../api";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "../components/Chart";
import { MetricCard, Panel, Segmented } from "../components/Mosaic";
import { ErrorState, Loading } from "../components/PageState";
import { useApi } from "../hooks";
import { nok } from "../format";
import { useAppLocation, useAppSearchParams } from "../router";
import type { ParkingTimeCell } from "../types";

type Metric = "paid" | "minutes" | "sessions";
const metricLabel = { paid: "Omsetning", minutes: "Parkeringstid", sessions: "Antall" };

export default function TimeDistributionPage() {
  const { search } = useAppLocation();
  const [params, setParams] = useAppSearchParams();
  const [metric, setMetric] = useState<Metric>("paid");
  const result = useApi(() => api.timeDistribution(new URLSearchParams(search)), `time-distribution-${search}`);
  const data = result.data;
  const value = (row: ParkingTimeCell) => Number(row[metric] || 0);
  const config = useMemo<MosaicChartConfig>(() => ({ type: "bar", labels: data?.hours.map((row) => row.hourLabel) || [], tooltipUnit: metric === "paid" ? "kr" : metric === "minutes" ? "min" : "stk", datasets: [{ label: metricLabel[metric], data: data?.hours.map(value) || [], color: mosaicChartColors.sky, type: "bar" }] }), [data, metric]);
  if (result.loading) return <Loading />;
  if (result.error || !data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const setPeriod = (period: string) => { const next = new URLSearchParams(params); next.set("period", period); setParams(next); };
  const max = Math.max(1, ...data.weekdays.flatMap((weekday) => weekday.hours.map(value)));
  return <div className="space-y-6">
    <Panel><div className="flex flex-wrap items-center justify-between gap-4 p-5"><Segmented value={params.get("period") || data.period.key} onChange={setPeriod} options={data.period.options.map((item) => ({ value: item.key, label: item.label }))} /><div className="flex items-center gap-2"><input className="form-input" type="date" value={params.get("date_from") || data.period.dateFrom} onChange={(event) => { const next = new URLSearchParams(params); next.set("period", "custom"); next.set("date_from", event.target.value); setParams(next); }} /><input className="form-input" type="date" value={params.get("date_to") || data.period.dateTo} onChange={(event) => { const next = new URLSearchParams(params); next.set("period", "custom"); next.set("date_to", event.target.value); setParams(next); }} /></div></div></Panel>
    <section className="grid grid-cols-2 xl:grid-cols-4 gap-6"><MetricCard label="Omsetning" value={nok(data.summary.paid)} unit="kr" detail={`${nok(data.summary.avgPaidPerSession)} kr pr parkering`} tone="sky" /><MetricCard label="Parkeringer" value={nok(data.summary.sessions)} unit="stk" detail={`${nok(data.summary.avgSessionsPerDay, 1)} pr dag`} tone="sky" /><MetricCard label="Parkeringstid" value={nok(data.summary.hours, 1)} unit="timer" detail={`${nok(data.summary.avgMinutesPerSession)} min pr parkering`} tone="sky" /><MetricCard label="Periode" value={data.period.daysCount} unit="dager" detail={data.period.detail} tone="gray" /></section>
    <Panel title="Fordeling på ukedag og klokkeslett" actions={<Segmented value={metric} onChange={(value) => setMetric(value as Metric)} options={[{ value: "paid", label: "Beløp" }, { value: "minutes", label: "Tid" }, { value: "sessions", label: "Antall" }]} />}><div className="overflow-x-auto p-5"><div className="min-w-[850px] space-y-2">{data.weekdays.map((weekday) => <div className="grid grid-cols-[5rem_repeat(24,minmax(28px,1fr))] gap-1" key={weekday.weekday}><strong className="self-center text-xs text-gray-500">{weekday.weekday}</strong>{weekday.hours.map((cell) => <div className="flex h-9 items-center justify-center rounded text-[10px] font-semibold text-gray-800 dark:text-gray-100" style={{ backgroundColor: `rgba(103,191,255,${Math.max(0.05, value(cell) / max)})` }} title={`${weekday.weekday} ${cell.hourLabel}: ${nok(value(cell))}`} key={cell.hour}>{value(cell) > 0 ? nok(value(cell)) : ""}</div>)}</div>)}<div className="grid grid-cols-[5rem_repeat(24,minmax(28px,1fr))] gap-1"><span />{Array.from({ length: 24 }, (_, hour) => <span className="text-center text-[10px] text-gray-400" key={hour}>{hour}</span>)}</div></div></div></Panel>
    <Panel title="Timeprofil" subtitle={`${data.period.label} · ${data.period.dateFrom} til ${data.period.dateTo}`}><div className="p-3"><Chart config={config} height={300} /></div></Panel>
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6"><Panel title="Ukedager"><div className="divide-y divide-gray-100 p-5 dark:divide-gray-700/60">{data.weekdays.map((row) => <div className="grid grid-cols-4 gap-3 py-3 text-sm" key={row.weekday}><strong>{row.weekday}</strong><span className="text-right tabular-nums">{nok(row.sessions)} stk</span><span className="text-right tabular-nums">{nok(row.paid)} kr</span><span className="text-right tabular-nums">{nok(row.minutes / 60, 1)} t</span></div>)}</div></Panel><Panel title="Topp tidspunkt"><div className="divide-y divide-gray-100 p-5 dark:divide-gray-700/60">{data.topSlots.slice(0, 12).map((row) => <div className="grid grid-cols-4 gap-3 py-3 text-sm" key={`${row.weekday}-${row.hour}`}><strong>{row.weekday} {row.hourLabel}</strong><span className="text-right tabular-nums">{nok(row.sessions)} stk</span><span className="text-right tabular-nums">{nok(row.paid)} kr</span><span className="text-right tabular-nums">{nok(row.minutes / 60, 1)} t</span></div>)}</div></Panel></div>
  </div>;
}
