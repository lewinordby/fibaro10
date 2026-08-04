import { useMemo } from "react";
import { domainApi } from "../api";
import { nok, percentDelta } from "../format";
import { useApi } from "../hooks";
import { useAppSearchParams } from "../router";
import type { BusinessComparisonLane, BusinessComparisonReference, BusinessComparisonResponse, BusinessComparisonSummary } from "../types";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "./Chart";
import { IconButton, MetricCard, Panel, Segmented } from "./Mosaic";
import { MosaicIcon } from "./MosaicIcon";
import { ErrorState, Loading } from "./PageState";

type Domain = "parking" | "sun";
type Metric = "count" | "amount";

function domainValue(summary: BusinessComparisonSummary, domain: Domain, metric: Metric) {
  if (domain === "parking") return metric === "count" ? summary.parkingCount : summary.parking;
  return metric === "count" ? summary.solCount : summary.sol;
}

function cumulative(lanes: BusinessComparisonLane[], metric: Metric) {
  const events = lanes.flatMap((lane) => lane.events || []).sort((left, right) => left.left - right.left);
  const points: Array<{ x: number; y: number }> = [{ x: 0, y: 0 }];
  let total = 0;
  for (const event of events) { total += metric === "amount" ? Number(event.amount || 0) : 1; points.push({ x: Math.max(0, Math.min(100, event.left)), y: Math.round(total * 100) / 100 }); }
  const end = Math.max(...lanes.map((lane) => Number(lane.endLeft || 0)), points.at(-1)?.x || 0);
  if (end > (points.at(-1)?.x || 0)) points.push({ x: end, y: total });
  return points;
}

function chartConfig(data: BusinessComparisonResponse, domain: Domain, metric: Metric, references: BusinessComparisonReference[], includePrevious: boolean): MosaicChartConfig {
  const kind = domain === "parking" ? "parking" : "sun";
  const lanes = (source: BusinessComparisonLane["source"], sourceLanes = data.lanes) => sourceLanes.filter((lane) => lane.source === source && lane.kind === kind);
  return {
    type: "line", xType: "linear", yInteger: metric === "count", tooltipUnit: metric === "count" ? "stk" : "kr",
    xTick: (value) => { if (!data.axis.start) return `${value}%`; const date = new Date(new Date(data.axis.start).getTime() + data.axis.seconds * (Number(value) / 100) * 1000); return data.axis.seconds <= 36 * 3600 ? date.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" }) : date.toLocaleDateString("nb-NO", { day: "2-digit", month: "2-digit" }); },
    yTick: (value) => Math.abs(value) >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value)),
    datasets: [
      { label: data.current.label, data: cumulative(lanes("current"), metric), color: domain === "parking" ? mosaicChartColors.sky : mosaicChartColors.yellow, stepped: true, fill: true },
      ...(includePrevious ? [{ label: data.comparison.label, data: cumulative(lanes("comparison"), metric), color: mosaicChartColors.gray, stepped: true, dashed: true }] : []),
      ...references.map((reference, index) => ({ label: reference.label, data: cumulative(lanes("reference", reference.lanes), metric), color: [mosaicChartColors.green, mosaicChartColors.violet][index % 2], stepped: true, dashed: true })),
    ],
  };
}

export function CountComparisonSpecial({ domain }: { domain: Domain }) {
  const [params, setParams] = useAppSearchParams();
  const period = params.get("period") || "today";
  const metric = (params.get("metric") === "amount" ? "amount" : "count") as Metric;
  const anchor = params.get("anchor") || "";
  const referenceIndex = params.has("reference") ? Number(params.get("reference")) : null;
  const query = new URLSearchParams({ period, compare: "previous" }); if (anchor) query.set("anchor", anchor);
  const result = useApi(() => domainApi.businessComparison(query), `${domain}-${query.toString()}`);
  const references = useMemo(() => {
    if (!result.data || referenceIndex === 0) return [];
    const all = result.data.referenceComparisons || [];
    return referenceIndex == null ? all : all.slice(Math.max(0, referenceIndex - 1), Math.max(0, referenceIndex - 1) + 1);
  }, [result.data, referenceIndex]);
  const includePrevious = referenceIndex == null || referenceIndex === 0;
  const config = useMemo(() => result.data ? chartConfig(result.data, domain, metric, references, includePrevious) : ({ type: "line", datasets: [] } as MosaicChartConfig), [result.data, domain, metric, references, includePrevious]);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  const selectedReference = referenceIndex === 0 ? data.comparison : references[0]?.summary || data.comparison;
  const current = domainValue(data.current, domain, metric); const reference = domainValue(selectedReference, domain, metric); const unit = metric === "count" ? "stk" : "kr";
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); next.set(key, value); if (key === "period") { next.delete("anchor"); next.delete("reference"); } setParams(next, key === "metric"); };
  return <div className="space-y-6"><div className="flex flex-wrap items-center justify-between gap-4"><Segmented options={[{ value: "today", label: "Dag" }, { value: "week", label: "Uke" }, { value: "month", label: "Måned" }]} value={period} onChange={(value) => update("period", value)} /><div className="flex items-center gap-2"><IconButton onClick={() => update("anchor", data.navigation.previousAnchor)} title="Forrige periode"><MosaicIcon name="arrow-left" /></IconButton><strong className="min-w-44 text-center text-sm tabular-nums text-gray-700 dark:text-gray-200">{data.navigation.label}</strong><IconButton disabled={!data.navigation.canNext} onClick={() => update("anchor", data.navigation.nextAnchor)} title="Neste periode"><MosaicIcon name="arrow-right" /></IconButton></div></div><section className="grid grid-cols-1 gap-6 sm:grid-cols-3"><MetricCard label={data.current.label} value={nok(current)} unit={unit} detail={domain === "parking" ? data.current.parkingAsOfLabel : data.current.solAsOfLabel} tone={domain === "parking" ? "sky" : "yellow"} /><MetricCard label={selectedReference.label} value={nok(reference)} unit={unit} detail={`${current - reference >= 0 ? "+" : ""}${nok(current - reference)} ${unit} · ${percentDelta(current, reference)}`} tone="gray" /><MetricCard label={metric === "count" ? "Omsetning hittil" : "Antall hittil"} value={nok(domainValue(data.current, domain, metric === "count" ? "amount" : "count"))} unit={metric === "count" ? "kr" : "stk"} detail="Samme valgte periode" tone="gray" /></section><Panel title={domain === "parking" ? "Akkumulert parkering" : "Akkumulert soling"} subtitle={data.comparisonLabel} actions={<Segmented options={[{ value: "count", label: "Antall" }, { value: "amount", label: "Beløp" }]} value={metric} onChange={(value) => update("metric", value)} />}><div className="p-3"><Chart config={config} height={420} /></div></Panel></div>;
}
