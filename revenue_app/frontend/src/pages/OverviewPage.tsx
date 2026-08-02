import { useMemo } from "react";
import { api } from "../api";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "../components/Chart";
import { DataTables } from "../components/DataTable";
import { MetricCard, Panel } from "../components/Mosaic";
import { ErrorState, Loading } from "../components/PageState";
import { useApi } from "../hooks";
import type { ModuleChart } from "../types";

const palette = [mosaicChartColors.violet, mosaicChartColors.sky, mosaicChartColors.yellow, mosaicChartColors.green, mosaicChartColors.gray];

function moduleChartConfig(chart: ModuleChart | undefined): MosaicChartConfig {
  if (!chart) return { type: "line", datasets: [] };
  return {
    type: chart.type === "bar" ? "bar" : "line",
    labels: chart.x,
    tooltipUnit: "kr",
    yTick: (value) => Math.abs(value) >= 1000 ? `${Math.round(value / 1000)}k` : String(value),
    datasets: chart.series.map((series, index) => ({
      label: series.name,
      type: (series.type || chart.type) === "bar" ? "bar" : "line",
      data: series.data.map((value) => Array.isArray(value) ? value[1] : value),
      color: palette[index % palette.length],
      stepped: Boolean(series.step),
    })),
  };
}

function metricTone(tone?: string): "red" | "yellow" | "sky" | "violet" | "gray" {
  if (tone === "revenue") return "violet";
  if (tone === "sun2" || tone === "sun") return "yellow";
  if (tone === "parking") return "sky";
  if (tone === "default") return "gray";
  return "violet";
}

export default function OverviewPage() {
  const { data, loading, error, reload } = useApi(api.overview, "overview");
  const chart = data?.charts?.[0];
  const config = useMemo(() => moduleChartConfig(chart), [chart]);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="space-y-6">
      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-6">
        {data.cards.slice(0, 5).map((card) => (
          <MetricCard key={card.title} label={card.title} value={card.value} unit={card.unit} detail={card.detail} tone={metricTone(card.tone)} />
        ))}
      </section>
      {chart ? (
        <Panel title={chart.title} subtitle={chart.subtitle}>
          <div className="px-3 pb-2 pt-3"><Chart config={config} height={390} /></div>
        </Panel>
      ) : null}
      <DataTables tables={data.tables} />
    </div>
  );
}
