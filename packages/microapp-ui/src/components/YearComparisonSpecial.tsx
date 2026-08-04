import { useMemo, useState } from "react";
import { domainApi } from "../api";
import { nok } from "../format";
import { useApi } from "../hooks";
import { useAppSearchParams } from "../router";
import type { YearComparisonSeries } from "../types";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "./Chart";
import { MetricCard, Panel, Segmented } from "./Mosaic";
import { ErrorState, Loading } from "./PageState";

type Metric = "amount" | "count" | "minutes";
const colors = [mosaicChartColors.yellow, mosaicChartColors.gray, mosaicChartColors.sky, mosaicChartColors.green, mosaicChartColors.violet, mosaicChartColors.red];

function total(series: YearComparisonSeries, metric: Metric) {
  return metric === "amount" ? series.totalAmount : metric === "minutes" ? series.totalMinutes : series.totalCount;
}

export function YearComparisonSpecial({ domain = "soling" }: { domain?: "soling" | "parkering" }) {
  const [params, setParams] = useAppSearchParams();
  const anchor = params.get("year") || "";
  const metric = (params.get("metric") as Metric) || "count";
  const result = useApi(() => domainApi.yearComparison(domain, anchor), `${domain}-year-${anchor}`);
  const [localYears, setLocalYears] = useState<number[] | null>(null);
  const data = result.data;
  const selectedYears = localYears || (data ? [data.anchorYear, data.comparisonYear] : []);
  const config = useMemo<MosaicChartConfig>(() => ({
    type: "line", xType: "linear", beginAtZero: true,
    tooltipUnit: metric === "amount" ? "kr" : metric === "minutes" ? "min" : "stk",
    xTick: (value) => ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Des"][Math.min(11, Math.max(0, Math.floor((Number(value) - 1) / 30.5)))] || "",
    yTick: (value) => Math.abs(value) >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value)),
    datasets: (data?.series || []).filter((series) => selectedYears.includes(series.year)).map((series, index) => ({ label: series.label, data: series.points.map((point) => ({ x: point.day, y: metric === "amount" ? point.cumulativeAmount : metric === "minutes" ? point.cumulativeMinutes : point.cumulativeCount })), color: colors[index % colors.length], fill: series.year === data?.anchorYear, dashed: series.year !== data?.anchorYear, stepped: true })),
  }), [data, metric, selectedYears.join(",")]);
  if (result.loading) return <Loading />;
  if (result.error || !data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const unit = metric === "amount" ? "kr" : metric === "minutes" ? "min" : "stk";
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); next.set(key, value); if (key === "year") setLocalYears(null); setParams(next, key === "metric"); };
  return <div className="space-y-6"><div className="flex flex-wrap items-center justify-between gap-4"><div className="flex gap-2"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => update("year", data.navigation.previousAnchor)}>Forrige år</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={!data.navigation.canNext} onClick={() => update("year", data.navigation.nextAnchor)}>Neste år</button></div><Segmented value={metric} onChange={(value) => update("metric", value)} options={[{ value: "count", label: "Antall" }, { value: "amount", label: "Beløp" }, { value: "minutes", label: "Tid" }]} /></div><section className="grid grid-cols-1 gap-6 sm:grid-cols-3"><MetricCard label={`${data.anchorYear} hittil`} value={nok(total(data.selected, metric))} unit={unit} detail={`${data.selected.daysWithData} dager med data`} tone="yellow" /><MetricCard label={`${data.comparisonYear} samme punkt`} value={nok(total(data.comparison, metric))} unit={unit} detail={`Differanse ${nok(total(data.selected, metric) - total(data.comparison, metric))} ${unit}`} tone="gray" /><MetricCard label={`${data.comparisonYear} hele året`} value={nok(total(data.comparisonFull, metric))} unit={unit} detail="Fullført referanseår" tone="gray" /></section><Panel title="Akkumulert utvikling" subtitle="Inneværende år og fjoråret vises ved åpning. Alle år kan slås av og på."><div className="flex flex-wrap items-center gap-3 border-b border-gray-100 px-5 py-3 dark:border-gray-700/60">{data.availableYears.map((year) => <label className="inline-flex items-center gap-2 text-sm" key={year}><input className="form-checkbox text-yellow-500" type="checkbox" checked={selectedYears.includes(year)} onChange={() => setLocalYears((current) => { const source = current || [data.anchorYear, data.comparisonYear]; return source.includes(year) ? source.filter((item) => item !== year) : [...source, year].sort((a, b) => b - a); })} />{year}</label>)}<button className="btn ml-auto border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => setLocalYears([data.anchorYear, data.comparisonYear])}>Standard</button></div><div className="p-3"><Chart config={config} height={470} /></div></Panel></div>;
}
