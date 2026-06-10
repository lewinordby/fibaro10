import { ArrowRightOutlined } from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import { Card, Segmented, Tag, Typography } from "antd";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { ModuleCard, ModuleChart } from "../../api";
import { moduleMetricFallbackHref, toneLabel } from "../../domainModel";
import { modulePath } from "../../moduleViews";
import { appPath } from "../../navigation";

export function ModuleMetric({
  card,
  module,
  view,
}: {
  card: ModuleCard;
  module: string;
  view: string;
}) {
  const rawHref = card.href || moduleMetricFallbackHref(module, view, card);
  const href = rawHref === modulePath(module, view) ? undefined : rawHref;
  const internalPath = appPath(href);
  const content = (
    <Card className={`metric-card module-metric tone-${card.tone ?? "status"}`} hoverable={Boolean(href)}>
      <div className="metric-card-top">
        <Typography.Text className="metric-title">{card.title}</Typography.Text>
        <Tag className="metric-tag">{toneLabel(card.tone, module)}</Tag>
      </div>
      <div className="metric-value-row">
        <span className="metric-value">{card.value}</span>
        {card.unit ? <span className="metric-unit">{card.unit}</span> : null}
      </div>
      <div className="metric-detail">
        <span>{card.detail || "\u00a0"}</span>
        {href ? <ArrowRightOutlined /> : null}
      </div>
    </Card>
  );

  if (!href) return content;
  if (internalPath) {
    return (
      <Link className="card-link" to={internalPath}>
        {content}
      </Link>
    );
  }
  return (
    <a className="card-link" href={href}>
      {content}
    </a>
  );
}

export function ModuleChartPanel({ chart }: { chart: ModuleChart }) {
  const defaultMetric = chart.defaultMetric ?? chart.metrics?.[0]?.key ?? "";
  const [metricKey, setMetricKey] = useState(defaultMetric);
  const activeMetric = chart.metrics?.find((metric) => metric.key === metricKey) ?? chart.metrics?.[0];
  const chartSeries = activeMetric?.series ?? chart.series;
  const requestedVisible = new Set(chart.defaultVisibleSeries ?? []);
  const applyDefaultVisibility = requestedVisible.size > 0 && chartSeries.some((series) => requestedVisible.has(series.name));
  const selectedSeries: Record<string, boolean> | undefined = applyDefaultVisibility
    ? Object.fromEntries(chartSeries.map((series) => [series.name, requestedVisible.has(series.name)]))
    : undefined;

  const option = {
    tooltip: { trigger: "axis" },
    legend: { top: 0, selected: selectedSeries },
    grid: { top: 46, left: 46, right: 24, bottom: chart.x.length > 80 ? 58 : 34 },
    dataZoom:
      chart.x.length > 80
        ? [
            { type: "inside", start: Math.max(0, 100 - Math.round((80 / chart.x.length) * 100)), end: 100 },
            { type: "slider", height: 18, bottom: 12 },
          ]
        : undefined,
    xAxis: {
      type: "category",
      data: chart.x,
      boundaryGap: chart.type === "bar",
      axisLabel: { hideOverlap: true },
    },
    yAxis: { type: "value", name: activeMetric?.unit },
    series: chartSeries.map((series) => ({
      name: series.name,
      type: series.type ?? chart.type ?? "line",
      data: series.data,
      smooth: (series.type ?? chart.type ?? "line") === "line",
      connectNulls: false,
      showSymbol: false,
      itemStyle: series.color ? { color: series.color } : undefined,
      lineStyle: series.color ? { color: series.color, width: 2 } : undefined,
      areaStyle: chartSeries.length === 1 && (series.type ?? chart.type ?? "line") === "line" ? { opacity: 0.08 } : undefined,
    })),
  };

  return (
    <Card className="chart-card module-chart-card" title={chart.title}>
      <div className="module-chart-toolbar">
        {chart.subtitle ? <Typography.Text type="secondary">{chart.subtitle}</Typography.Text> : <span />}
        {chart.metrics?.length ? (
          <Segmented
            size="small"
            value={activeMetric?.key ?? metricKey}
            options={chart.metrics.map((metric) => ({ label: metric.label, value: metric.key }))}
            onChange={(next) => setMetricKey(String(next))}
          />
        ) : null}
      </div>
      <ReactECharts option={option} style={{ height: chart.height ?? 330 }} />
    </Card>
  );
}
