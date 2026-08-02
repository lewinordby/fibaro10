import { useMemo, useState } from "react";
import { api } from "../api";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "../components/Chart";
import { MetricCard, Panel, Segmented } from "../components/Mosaic";
import { ErrorState, Loading } from "../components/PageState";
import { nok } from "../format";
import { useApi } from "../hooks";
import { useAppLocation, useAppSearchParams } from "../router";

type Metric = "amount" | "minutes";
const colors = [mosaicChartColors.sky, mosaicChartColors.gray, mosaicChartColors.violet, mosaicChartColors.green, mosaicChartColors.yellow];

export default function WeeklyPage() {
  const { search } = useAppLocation();
  const [params, setParams] = useAppSearchParams();
  const [metric, setMetric] = useState<Metric>("amount");
  const periodParams = new URLSearchParams(search); periodParams.delete("years");
  const average = useApi(() => api.weeklyAverages(periodParams), `weekly-${periodParams.toString()}`);
  const years = useApi(() => api.weeklyYears(params.get("years") || undefined), `weekly-years-${params.get("years") || "default"}`);
  const weeklyConfig = useMemo<MosaicChartConfig>(() => ({ type: "line", labels: average.data?.weeks.map((item) => item.shortLabel) || [], tooltipUnit: metric === "amount" ? "kr" : "min", datasets: [{ label: metric === "amount" ? "Beløp pr parkering" : "Tid pr parkering", data: average.data?.weeks.map((item) => metric === "amount" ? item.avgPaidPerSession : item.avgMinutesPerSession) || [], color: metric === "amount" ? mosaicChartColors.sky : mosaicChartColors.green, fill: true }] }), [average.data, metric]);
  const yearConfig = useMemo<MosaicChartConfig>(() => ({ type: "line", labels: Array.from({ length: 53 }, (_, index) => `U${index + 1}`), tooltipUnit: metric === "amount" ? "kr" : "min", datasets: (years.data?.series || []).map((series, index) => ({ label: series.label, data: series.points.map((point) => metric === "amount" ? point.avgPaidPerSession : point.avgMinutesPerSession), color: colors[index % colors.length], dashed: series.year !== years.data?.currentYear })) }), [years.data, metric]);
  if (average.loading || years.loading) return <Loading />;
  if (average.error || !average.data) return <ErrorState error={average.error} onRetry={average.reload} />;
  if (years.error || !years.data) return <ErrorState error={years.error} onRetry={years.reload} />;
  const data = average.data;
  const chooseYears = (selected: number[]) => { const next = new URLSearchParams(params); selected.length ? next.set("years", selected.join(",")) : next.delete("years"); setParams(next, true); };
  return <div className="space-y-6">
    <Panel><div className="flex flex-wrap items-center justify-between gap-4 p-5"><Segmented value={params.get("period") || data.period.key} onChange={(value) => { const next = new URLSearchParams(params); next.set("period", value); setParams(next); }} options={data.period.options.map((item) => ({ value: item.key, label: item.label }))} /><Segmented value={metric} onChange={(value) => setMetric(value as Metric)} options={[{ value: "amount", label: "Beløp" }, { value: "minutes", label: "Tid" }]} /></div></Panel>
    <section className="grid grid-cols-2 xl:grid-cols-4 gap-6"><MetricCard label="Siste uke · beløp" value={nok(data.latest?.avgPaidPerSession || 0)} unit="kr" detail={data.latest?.rangeLabel || "Ingen data"} tone="sky" /><MetricCard label="Siste uke · tid" value={nok(data.latest?.avgMinutesPerSession || 0)} unit="min" detail={data.latest?.isPartial ? "Pågående uke" : "Fullført uke"} tone="green" /><MetricCard label="Periodesnitt" value={nok(data.summary.avgPaidPerSession)} unit="kr" detail={`${nok(data.summary.avgMinutesPerSession)} min pr parkering`} tone="sky" /><MetricCard label="Datagrunnlag" value={nok(data.summary.sessions)} unit="stk" detail={`${nok(data.summary.durationCoveragePct, 0)} % med tidsgrunnlag`} tone="gray" /></section>
    <Panel title="Ukevis utvikling" subtitle="Gjennomsnitt pr parkering i valgt periode"><div className="p-3"><Chart config={weeklyConfig} height={400} /></div></Panel>
    <Panel title="Sammenlign år" subtitle="Samme kalenderuke sammenlignes på tvers av alle tilgjengelige år"><div className="flex flex-wrap items-center gap-3 border-b border-gray-100 px-5 py-3 dark:border-gray-700/60">{years.data.availableYears.map((year) => <label className="inline-flex items-center gap-2 text-sm" key={year}><input className="form-checkbox text-sky-500" type="checkbox" checked={years.data!.selectedYears.includes(year)} onChange={() => chooseYears(years.data!.selectedYears.includes(year) ? years.data!.selectedYears.filter((value) => value !== year) : [...years.data!.selectedYears, year])} />{year}</label>)}<button className="btn ml-auto border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" onClick={() => chooseYears(years.data!.defaultYears)}>Standard</button></div><div className="p-3"><Chart config={yearConfig} height={420} /></div></Panel>
  </div>;
}
