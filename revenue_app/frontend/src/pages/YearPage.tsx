import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Chart, mosaicChartColors, type MosaicChartConfig } from "../components/Chart";
import { MosaicIcon } from "../components/MosaicIcon";
import { IconButton, MetricCard, Panel } from "../components/Mosaic";
import { ErrorState, Loading } from "../components/PageState";
import { nok, signedNok } from "../format";
import { useApi } from "../hooks";
import type { YearComparisonResponse } from "../types";
import { useAppSearchParams } from "../router";

const yearColors = [mosaicChartColors.violet, mosaicChartColors.sky, mosaicChartColors.yellow, mosaicChartColors.green, mosaicChartColors.gray];

function yearChart(data: YearComparisonResponse, activeYears: number[]): MosaicChartConfig {
  const visible = data.series.filter((series) => activeYears.includes(series.year));
  return {
    type: "line",
    xType: "linear",
    tooltipUnit: "kr",
    xTick: (day) => new Date(data.anchorYear, 0, Math.max(1, Math.round(Number(day)))).toLocaleDateString("nb-NO", { month: "short" }),
    yTick: (value) => `${Math.round(value / 1000)}k`,
    datasets: visible.map((series, index) => {
      const color = yearColors[index % yearColors.length];
      return {
        label: series.label,
        type: "line" as const,
        data: series.points.map((point) => ({ x: point.day, y: point.cumulativeAmount })),
        color,
        stepped: true,
        dashed: series.year !== data.anchorYear,
        fill: series.year === data.anchorYear,
      };
    }),
  };
}

export default function YearPage() {
  const [params, setParams] = useAppSearchParams();
  const year = params.get("year") || "";
  const { data, loading, error, reload } = useApi(() => api.year(year), `year-${year}`);
  const [activeYears, setActiveYears] = useState<number[]>([]);
  useEffect(() => {
    if (data) setActiveYears([data.anchorYear, data.comparisonYear]);
  }, [data?.anchorYear, data?.comparisonYear]);
  const config = useMemo<MosaicChartConfig>(() => data ? yearChart(data, activeYears) : { type: "line", datasets: [] }, [data, activeYears]);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;
  const setYear = (value: string) => { const next = new URLSearchParams(params); next.set("year", value); setParams(next); };
  const yearPicker = (
    <div className="flex max-w-155 flex-wrap justify-end gap-x-3 gap-y-2">
      {data.availableYears.map((item) => (
        <label className="flex cursor-pointer items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300" key={item}>
          <input className="form-checkbox" type="checkbox" checked={activeYears.includes(item)} onChange={() => setActiveYears((current) => current.includes(item) ? current.filter((value) => value !== item) : [...current, item])} />{item}
        </label>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <div className="flex items-center gap-2">
          <IconButton onClick={() => setYear(data.navigation.previousAnchor)} title="Forrige år"><MosaicIcon name="arrow-left" /></IconButton>
          <strong className="tabular-nums min-w-40 text-center text-sm text-gray-700 dark:text-gray-200">{data.navigation.label}</strong>
          <IconButton disabled={!data.navigation.canNext} onClick={() => setYear(data.navigation.nextAnchor)} title="Neste år"><MosaicIcon name="arrow-right" /></IconButton>
        </div>
      </div>
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <MetricCard label={`${data.anchorYear} hittil`} value={nok(data.selected.totalAmount)} unit="kr" detail={`${data.selected.daysWithData} dager med data`} tone="violet" />
        <MetricCard label={`${data.comparisonYear} samme punkt`} value={nok(data.comparison.totalAmount)} unit="kr" detail={`${signedNok(data.delta.amount)} mot ${data.comparisonYear}`} tone="sky" />
        <MetricCard label={`${data.comparisonYear} hele året`} value={nok(data.comparisonFull.totalAmount)} unit="kr" detail="Fullført referanseår" tone="gray" />
      </section>
      <Panel title="Akkumulert omsetning" subtitle="Alle historiske år kan slås av og på." actions={yearPicker}>
        <div className="px-3 pb-3 pt-3"><Chart config={config} height={480} /></div>
      </Panel>
    </div>
  );
}
