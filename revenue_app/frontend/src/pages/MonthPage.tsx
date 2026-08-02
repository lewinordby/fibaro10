import { useMemo, useState } from "react";
import { nok } from "@lilletorget/microapp-ui/format";
import { useApi } from "@lilletorget/microapp-ui/hooks";
import { Chart, ErrorState, IconButton, Loading, MetricCard, MosaicIcon, Panel, mosaicChartColors, type MosaicChartConfig } from "@lilletorget/microapp-ui/primitives";
import { api } from "../api";

export default function MonthPage() {
  const [month, setMonth] = useState("");
  const { data, loading, error, reload } = useApi(() => api.month(month), `month-${month}`);
  const config = useMemo<MosaicChartConfig>(() => ({
    type: "bar",
    labels: data?.rows.map((row) => row.dayLabel) ?? [],
    stacked: true,
    tooltipUnit: "kr",
    yTick: (value) => `${Math.round(value / 1000)}k`,
    datasets: [
      { label: "Soling", type: "bar", stack: "total", color: mosaicChartColors.yellow, data: data?.rows.map((row) => row.sol) ?? [] },
      { label: "Parkering", type: "bar", stack: "total", color: mosaicChartColors.sky, data: data?.rows.map((row) => row.parking) ?? [] },
    ],
  }), [data]);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;
  const summary = data.summary;
  const monthActions = (
    <div className="flex items-center gap-2">
      <IconButton onClick={() => setMonth(summary.previousMonth)} title="Forrige måned"><MosaicIcon name="arrow-left" /></IconButton>
      <strong className="tabular-nums min-w-36 text-center text-sm text-gray-700 dark:text-gray-200">{summary.label}</strong>
      <IconButton onClick={() => setMonth(summary.nextMonth)} title="Neste måned"><MosaicIcon name="arrow-right" /></IconButton>
      <input className="form-input h-9 w-39 py-1.5" type="month" value={summary.month} onChange={(event) => setMonth(event.target.value)} />
    </div>
  );
  return (
    <div className="space-y-6">
      <div className="flex justify-end">{monthActions}</div>
      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-6">
        <MetricCard label="Total" value={nok(summary.total)} unit="kr" detail={`${summary.averageDayCount} dager i snittgrunnlaget`} tone="violet" />
        <MetricCard label="Soling" value={nok(summary.sol)} unit="kr" detail={`${summary.solCount} solinger`} tone="yellow" />
        <MetricCard label="Parkering" value={nok(summary.parking)} unit="kr" detail={`${summary.parkingCount} parkeringer`} tone="sky" />
        <MetricCard label="Snitt per dag" value={nok(summary.averagePerDay)} unit="kr" detail="Til og med valgt datagrunnlag" tone="gray" />
        <MetricCard label="Beste dag" value={summary.topDay ? nok(summary.topDay.total) : "-"} unit="kr" detail={summary.topDay ? `${summary.topDay.dayLabel} · ${summary.topDay.weekday}` : "Ingen data"} tone="green" />
      </section>
      <Panel title="Omsetning per dag" subtitle="Fordelt mellom soling og parkering.">
        <div className="px-3 pb-2 pt-3"><Chart config={config} height={410} /></div>
      </Panel>
      <Panel>
        <div className="overflow-auto">
          <table className="table-auto w-full dark:text-gray-300 tabular-nums">
            <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 rounded-xs">
              <tr>{["Dag", "Sum", "Parkering", "Antall parkering", "Soling", "Antall soling"].map((label, index) => <th className="p-2" key={label}><div className={`font-semibold whitespace-nowrap ${index ? "text-right" : "text-left"}`}>{label}</div></th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60">
              {data.rows.map((row) => (
                <tr className={row.isToday ? "bg-violet-500/[0.07]" : row.isWeekend ? "bg-gray-50/60 dark:bg-gray-700/20" : ""} key={row.day}>
                  <td className="p-2 text-gray-800 whitespace-nowrap dark:text-gray-100">{row.dayLabel} · {row.weekday}</td>
                  <td className="p-2 text-right font-semibold text-gray-800 dark:text-gray-100">{nok(row.total)} kr</td>
                  <td className="p-2 text-right">{nok(row.parking)} kr</td><td className="p-2 text-right">{row.parkingCount}</td>
                  <td className="p-2 text-right">{nok(row.sol)} kr</td><td className="p-2 text-right">{row.solCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
