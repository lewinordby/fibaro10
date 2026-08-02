import { useMemo } from "react";
import { api } from "../api";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "../components/Chart";
import { MosaicIcon } from "../components/MosaicIcon";
import { IconButton, Panel, Segmented } from "../components/Mosaic";
import { ErrorState, Loading } from "../components/PageState";
import { nok, signedNok } from "../format";
import { useApi } from "../hooks";
import type { ComparisonDelta, ComparisonLane, ComparisonResponse, ComparisonSummary } from "../types";
import { useAppSearchParams } from "../router";

type Metric = "amount" | "count";
type Kind = "total" | "sun" | "parking";

function cumulative(lanes: Array<ComparisonLane | undefined>, metric: Metric): Array<[number, number]> {
  const events = lanes.flatMap((lane) => lane?.events ?? []).sort((left, right) => left.left - right.left);
  const points: Array<[number, number]> = [[0, 0]];
  let total = 0;
  for (const event of events) {
    total += metric === "amount" ? Number(event.amount || 0) : 1;
    points.push([Math.max(0, Math.min(100, event.left)), Math.round(total * 100) / 100]);
  }
  const end = Math.max(...lanes.map((lane) => Number(lane?.endLeft || 0)), points.at(-1)?.[0] || 0);
  if (end > (points.at(-1)?.[0] || 0)) points.push([end, total]);
  return points;
}

function lanesFor(data: ComparisonResponse, source: ComparisonLane["source"], kind: Kind, lanes = data.lanes) {
  if (kind === "total") return ["sun", "parking"].map((item) => lanes.find((lane) => lane.source === source && lane.kind === item));
  return [lanes.find((lane) => lane.source === source && lane.kind === kind)];
}

function chartConfig(data: ComparisonResponse, kind: Kind, metric: Metric): MosaicChartConfig {
  const primary = kind === "sun" ? mosaicChartColors.yellow : kind === "parking" ? mosaicChartColors.sky : mosaicChartColors.violet;
  const referenceColors = kind === "total"
    ? [mosaicChartColors.green, mosaicChartColors.sky]
    : [mosaicChartColors.green, mosaicChartColors.violet];
  const references = data.referenceComparisons ?? [];
  return {
    type: "line",
    xType: "linear",
    tooltipUnit: metric === "amount" ? "kr" : "stk",
    yInteger: metric === "count",
    xTick: (value) => {
      if (!data.axis.start) return `${value}%`;
      const date = new Date(new Date(data.axis.start).getTime() + data.axis.seconds * (Number(value) / 100) * 1000);
      return data.axis.seconds <= 36 * 3600
        ? date.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" })
        : date.toLocaleDateString("nb-NO", { day: "2-digit", month: "2-digit" });
    },
    yTick: (value) => Math.abs(value) >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value)),
    datasets: [
      {
        label: data.current.label,
        type: "line",
        data: cumulative(lanesFor(data, "current", kind), metric).map(([x, y]) => ({ x, y })),
        color: primary,
        stepped: true,
        fill: true,
      },
      {
        label: data.comparison.label,
        type: "line",
        data: cumulative(lanesFor(data, "comparison", kind), metric).map(([x, y]) => ({ x, y })),
        color: mosaicChartColors.gray,
        stepped: true,
        dashed: true,
      },
      ...references.map((reference, index) => ({
        label: reference.label,
        type: "line" as const,
        data: cumulative(lanesFor(data, "reference", kind, reference.lanes), metric).map(([x, y]) => ({ x, y })),
        color: referenceColors[index % referenceColors.length],
        stepped: true,
        dotted: true,
      })),
    ],
  };
}

function Delta({ value }: { value: number }) {
  const color = value > 0 ? "text-green-700 dark:text-green-400" : value < 0 ? "text-red-700 dark:text-red-400" : "text-gray-500 dark:text-gray-400";
  return <em className={`tabular-nums text-xs font-semibold not-italic ${color}`}>{signedNok(value)}</em>;
}

function SummaryCard({ title, summary, delta }: { title: string; summary: ComparisonSummary; delta?: ComparisonDelta }) {
  return (
    <article className="overflow-hidden bg-white dark:bg-gray-800 shadow-sm rounded-xl">
      <header className="flex items-start justify-between gap-4 px-5 pb-3 pt-5">
        <span className="text-xs font-semibold uppercase text-gray-400 dark:text-gray-500">{title}</span>
        <strong className="tabular-nums whitespace-nowrap text-xl font-bold text-gray-800 dark:text-gray-100">{nok(summary.total)} kr</strong>
      </header>
      <p className="px-5 pb-4 text-xs text-gray-400 dark:text-gray-500">Sol {summary.solAsOfLabel} · parkering {summary.parkingAsOfLabel}</p>
      <div className="grid grid-cols-2 border-t border-gray-100 bg-gray-50/60 dark:border-gray-700/60 dark:bg-gray-900/20">
        <span className="grid gap-1 px-5 py-3">
          <b className="text-[10px] font-semibold uppercase text-yellow-700 dark:text-yellow-400">Soling</b>
          <strong className="tabular-nums text-sm text-gray-800 dark:text-gray-100">{nok(summary.sol)} kr</strong>
          <small className="text-[10px] text-gray-400 dark:text-gray-500">{summary.solCount} stk</small>
          {delta ? <Delta value={delta.sol} /> : null}
        </span>
        <span className="grid gap-1 border-l border-gray-200 px-5 py-3 dark:border-gray-700/60">
          <b className="text-[10px] font-semibold uppercase text-sky-700 dark:text-sky-400">Parkering</b>
          <strong className="tabular-nums text-sm text-gray-800 dark:text-gray-100">{nok(summary.parking)} kr</strong>
          <small className="text-[10px] text-gray-400 dark:text-gray-500">{summary.parkingCount} stk</small>
          {delta ? <Delta value={delta.parking} /> : null}
        </span>
      </div>
      {delta ? <div className="flex justify-between border-t border-gray-100 px-5 py-2 dark:border-gray-700/60"><span className="text-[10px] uppercase text-gray-400">Samlet differanse</span><Delta value={delta.total} /></div> : null}
    </article>
  );
}

export default function ComparisonPage() {
  const [searchParams, setSearchParams] = useAppSearchParams();
  const period = searchParams.get("period") || "today";
  const metric = (searchParams.get("metric") === "count" ? "count" : "amount") as Metric;
  const anchor = searchParams.get("anchor") || "";
  const query = new URLSearchParams({ period, compare: "previous" });
  if (anchor) query.set("anchor", anchor);
  const { data, loading, error, reload } = useApi(() => api.comparison(query), query.toString());
  const charts = useMemo(() => data ? (metric === "amount" ? ["total", "sun", "parking"] : ["sun", "parking"]).map((kind) => ({
    kind: kind as Kind,
    title: ({ total: "Samlet omsetning", sun: "Soling", parking: "Parkering" } as Record<Kind, string>)[kind as Kind],
    config: chartConfig(data, kind as Kind, metric),
  })) : [], [data, metric]);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    next.set(key, value);
    if (key === "period") next.delete("anchor");
    if (key === "metric" && value === "amount") next.delete("metric");
    setSearchParams(next);
  }

  const chartActions = <Segmented options={[{ value: "amount", label: "Omsetning" }, { value: "count", label: "Antall" }]} value={metric} onChange={(value) => setParam("metric", value)} />;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-5">
        <Segmented options={[{ value: "today", label: "Dag" }, { value: "week", label: "Uke" }, { value: "month", label: "Måned" }]} value={period} onChange={(value) => setParam("period", value)} />
        <div className="flex items-center gap-2">
          <IconButton onClick={() => setParam("anchor", data.navigation.previousAnchor)} title="Forrige periode"><MosaicIcon name="arrow-left" /></IconButton>
          <strong className="tabular-nums min-w-44 text-center text-sm text-gray-700 dark:text-gray-200">{data.navigation.label}</strong>
          <IconButton disabled={!data.navigation.canNext} onClick={() => setParam("anchor", data.navigation.nextAnchor)} title="Neste periode"><MosaicIcon name="arrow-right" /></IconButton>
        </div>
      </div>
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SummaryCard title={data.current.label} summary={data.current} />
        <SummaryCard title={data.comparison.label} summary={data.comparison} delta={data.delta} />
        {(data.referenceComparisons ?? []).slice(0, 1).map((reference) => <SummaryCard key={reference.key} title={reference.label} summary={reference.summary} delta={reference.delta} />)}
      </section>
      <Panel title="Akkumulert utvikling" subtitle={data.comparisonLabel} actions={chartActions}>
        <div className="space-y-3 px-3 pb-3 pt-3">
          {charts.map((item) => (
            <section className="rounded-lg border border-gray-100 dark:border-gray-700/60" key={`${metric}-${item.kind}`}>
              <h3 className="px-4 pt-3 text-sm font-semibold text-gray-800 dark:text-gray-100">{item.title}</h3>
              <Chart config={item.config} height={metric === "amount" ? 230 : 270} />
            </section>
          ))}
        </div>
      </Panel>
    </div>
  );
}
