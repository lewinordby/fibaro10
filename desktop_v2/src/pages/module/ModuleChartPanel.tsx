import { CalendarOutlined } from "@ant-design/icons";
import { Button, Card, Input, Segmented, Space, Typography } from "antd";
import { useMemo, useState } from "react";
import type { ModuleChart } from "../../api";
import { chartAxisLabel, chartAxisLine, chartLegend, chartSplitLine, chartTooltip } from "../../chartTheme";
import { AppChart } from "../../components/AppChart";
import { PeriodNavigator } from "../../components/PeriodNavigator";

function timeAxisLabel(value: number | string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" });
}

export default function ModuleChartPanel({
  chart,
  onDayChange,
}: {
  chart: ModuleChart;
  onDayChange?: (day: string) => void;
}) {
  const metricOptions = chart.metrics ?? [];
  const defaultMetric = chart.defaultMetric ?? metricOptions[0]?.key ?? "";
  const [metricKey, setMetricKey] = useState(defaultMetric);
  const activeMetric = metricOptions.find((metric) => metric.key === metricKey) ?? metricOptions[0];
  const chartSeries = activeMetric?.series ?? chart.series;
  const option = useMemo(() => {
    const isTimeAxis = chart.xAxisType === "time";
    const showZoom = !chart.disableZoom && !isTimeAxis && chart.x.length > 80;
    const requestedVisible = new Set(chart.defaultVisibleSeries ?? []);
    const applyDefaultVisibility = requestedVisible.size > 0 && chartSeries.some((series) => requestedVisible.has(series.name));
    const selectedSeries: Record<string, boolean> | undefined = applyDefaultVisibility
      ? Object.fromEntries(chartSeries.map((series) => [series.name, requestedVisible.has(series.name)]))
      : undefined;

    return {
      tooltip: chartTooltip(),
      legend: chartLegend({ itemWidth: 16, selected: selectedSeries }),
      grid: { top: 50, left: 56, right: 18, bottom: showZoom ? 58 : 32 },
      dataZoom: showZoom
        ? [
            { type: "inside", start: Math.max(0, 100 - Math.round((80 / chart.x.length) * 100)), end: 100 },
            { type: "slider", height: 18, bottom: 12 },
          ]
        : undefined,
      xAxis: {
        type: isTimeAxis ? "time" : "category",
        data: isTimeAxis ? undefined : chart.x,
        min: isTimeAxis ? chart.xAxisMin : undefined,
        max: isTimeAxis ? chart.xAxisMax : undefined,
        boundaryGap: isTimeAxis ? false : chart.type === "bar",
        axisTick: { show: false },
        axisLine: chartAxisLine(),
        axisLabel: chartAxisLabel({
          hideOverlap: true,
          formatter: isTimeAxis ? timeAxisLabel : undefined,
        }),
      },
      yAxis: {
        type: "value",
        name: activeMetric?.unit,
        nameTextStyle: chartAxisLabel(),
        axisLabel: chartAxisLabel({ margin: 12 }),
        splitLine: chartSplitLine(),
      },
      series: chartSeries.map((series) => ({
        name: series.name,
        type: series.type ?? chart.type ?? "line",
        data: series.data,
        smooth: series.smooth ?? ((series.type ?? chart.type ?? "line") === "line" && !series.step),
        step: series.step,
        connectNulls: false,
        showSymbol: false,
        barMaxWidth: 44,
        barCategoryGap: "36%",
        itemStyle: series.color ? { color: series.color } : undefined,
        lineStyle: series.color ? { color: series.color, width: 2 } : undefined,
        areaStyle: chartSeries.length === 1 && (series.type ?? chart.type ?? "line") === "line" ? { opacity: 0.08 } : undefined,
        emphasis: { focus: "series" },
      })),
    };
  }, [activeMetric?.unit, chart, chartSeries]);

  return (
    <Card className="chart-card module-chart-card" title={chart.title}>
      <div className="module-chart-toolbar">
        {chart.subtitle ? <Typography.Text type="secondary">{chart.subtitle}</Typography.Text> : <span />}
        <Space size={10} className="module-chart-controls">
          {metricOptions.length > 1 ? (
            <Segmented
              size="small"
              value={activeMetric?.key ?? metricKey}
              options={metricOptions.map((metric) => ({ label: metric.label, value: metric.key }))}
              onChange={(next) => setMetricKey(String(next))}
            />
          ) : null}
          {chart.dayNavigation ? (
            <PeriodNavigator
              className="module-chart-day-nav"
              previousLabel="Forrige dag"
              nextLabel="Neste dag"
              onPrevious={() => onDayChange?.(chart.dayNavigation?.prevDay ?? "")}
              onNext={() => onDayChange?.(chart.dayNavigation?.nextDay ?? "")}
              middle={
                <Button size="small" onClick={() => onDayChange?.("")}>
                  I dag
                </Button>
              }
              extra={
                <Input
                  aria-label="Dato"
                  className="module-chart-date"
                  prefix={<CalendarOutlined />}
                  size="small"
                  type="date"
                  value={chart.dayNavigation.selectedDay}
                  onChange={(event) => onDayChange?.(event.target.value)}
                />
              }
            />
          ) : null}
        </Space>
      </div>
      <AppChart option={option} style={{ height: chart.height ?? 330 }} lazyUpdate />
    </Card>
  );
}
