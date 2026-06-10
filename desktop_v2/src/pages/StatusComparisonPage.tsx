import { ArrowLeftOutlined, LeftOutlined, RightOutlined } from "@ant-design/icons";
import { Button, Card, Col, Row, Segmented, Space, Typography } from "antd";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchStatusComparison,
  type StatusComparisonLane,
  type StatusComparisonResponse,
  type StatusComparisonSummary,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { domainColors } from "../domainColors";
import { nok } from "../format";
import { useAsyncData } from "../hooks";

type ComparisonMetric = "count" | "amount";
type ComparisonChartKind = StatusComparisonLane["kind"] | "total";

function signedNok(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 kr";
  return `${value > 0 ? "+" : "-"}${nok(Math.abs(value))} kr`;
}

function signedCount(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 stk";
  return `${value > 0 ? "+" : "-"}${Math.abs(value)} stk`;
}

function shortTimeText(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function axisText(data: StatusComparisonResponse, value: number) {
  if (!data.axis.start) return `${Math.round(value)}%`;
  const date = new Date(new Date(data.axis.start).getTime() + (data.axis.seconds * value * 1000) / 100);
  if (data.axis.seconds <= 36 * 3600) {
    return date.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("nb-NO", { day: "2-digit", month: "2-digit" });
}

function metricValue(value: number, metric: ComparisonMetric) {
  if (metric === "amount") return `${nok(value)} kr`;
  return `${Math.round(value)} stk`;
}

function axisValue(value: number, metric: ComparisonMetric) {
  if (metric === "amount") {
    if (Math.abs(value) >= 1000) return `${Math.round(value / 1000)}k`;
    return `${Math.round(value)}`;
  }
  return `${Math.round(value)}`;
}

function cumulativePoints(lanes: Array<StatusComparisonLane | undefined>, metric: ComparisonMetric): Array<[number, number]> {
  const events = lanes
    .flatMap((lane) => lane?.events ?? [])
    .filter((event) => Number.isFinite(event.left))
    .sort((left, right) => left.left - right.left);
  const points: Array<[number, number]> = [[0, 0]];
  let total = 0;
  let index = 0;
  while (index < events.length) {
    const left = Math.max(0, Math.min(100, events[index].left));
    let batch = 0;
    while (index < events.length && Math.abs(events[index].left - left) < 0.0001) {
      batch += metric === "amount" ? Number(events[index].amount || 0) : 1;
      index += 1;
    }
    total += batch;
    points.push([left, Math.round(total * 100) / 100]);
  }
  points.push([100, Math.round(total * 100) / 100]);
  return points;
}

function laneFor(data: StatusComparisonResponse, kind: StatusComparisonLane["kind"], source: StatusComparisonLane["source"]) {
  return data.lanes.find((lane) => lane.kind === kind && lane.source === source);
}

function lanesForChart(data: StatusComparisonResponse, kind: ComparisonChartKind, source: StatusComparisonLane["source"]) {
  if (kind === "total") return [laneFor(data, "sun", source), laneFor(data, "parking", source)];
  return [laneFor(data, kind, source)];
}

function cumulativeChartOption(data: StatusComparisonResponse, kind: ComparisonChartKind, metric: ComparisonMetric) {
  const currentLanes = lanesForChart(data, kind, "current");
  const comparisonLanes = lanesForChart(data, kind, "comparison");
  const primaryColor = kind === "parking" ? domainColors.parking : kind === "total" ? domainColors.revenue : domainColors.sun2;
  const title =
    metric === "amount"
      ? kind === "total"
        ? "Akkumulert sum"
        : kind === "sun"
          ? "Akkumulert solbeløp"
          : "Akkumulert parkeringsbeløp"
      : kind === "sun"
        ? "Akkumulerte solinger"
        : "Akkumulerte parkeringer";
  return {
    color: [primaryColor, domainColors.comparison],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line" },
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        const first = items[0] as { value?: [number, number] } | undefined;
        const x = Number(first?.value?.[0] ?? 0);
        const rows = items
          .map((item) => {
            const row = item as { marker?: string; seriesName?: string; value?: [number, number] };
            return `<div style="display:flex;justify-content:space-between;gap:20px;line-height:1.7">
              <span>${row.marker ?? ""}${row.seriesName ?? ""}</span>
              <strong>${metricValue(Number(row.value?.[1] ?? 0), metric)}</strong>
            </div>`;
          })
          .join("");
        return `<div style="min-width:180px">
          <div style="margin-bottom:6px;font-weight:700;color:${domainColors.ink}">${axisText(data, x)}</div>
          ${rows}
        </div>`;
      },
    },
    legend: { top: 0 },
    grid: { top: 42, left: 42, right: 18, bottom: 32 },
    xAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: { formatter: (value: number) => axisText(data, value) },
      splitLine: { lineStyle: { color: domainColors.gridSoft } },
    },
    yAxis: {
      type: "value",
      minInterval: metric === "amount" ? undefined : 1,
      axisLabel: { formatter: (value: number) => axisValue(value, metric) },
      splitLine: { lineStyle: { color: domainColors.grid } },
    },
    series: [
      {
        name: currentLanes.find(Boolean)?.periodLabel ?? data.current.label,
        type: "line",
        step: "end",
        symbol: "none",
        lineStyle: { width: 3 },
        areaStyle: { opacity: 0.06 },
        data: cumulativePoints(currentLanes, metric),
      },
      {
        name: comparisonLanes.find(Boolean)?.periodLabel ?? data.comparison.label,
        type: "line",
        step: "end",
        symbol: "none",
        lineStyle: { width: 2, type: "dashed" },
        data: cumulativePoints(comparisonLanes, metric),
      },
    ],
    title: {
      text: title,
      top: 2,
      left: 0,
      textStyle: { color: domainColors.ink, fontSize: 13, fontWeight: 760 },
    },
  };
}

function SummaryCard({
  title,
  summary,
}: {
  title: string;
  summary: StatusComparisonSummary;
}) {
  return (
    <Card className="status-comparison-summary-card">
      <div className="status-comparison-summary-head">
        <span>{title}</span>
        <strong>{nok(summary.total)} kr</strong>
      </div>
      <div className="status-comparison-summary-meta">
        <span>Sol {summary.solAsOfLabel}</span>
        <span>Parkering {summary.parkingAsOfLabel}</span>
      </div>
      <div className="status-comparison-summary-split">
        <div>
          <span>Soling</span>
          <strong>{nok(summary.sol)} kr</strong>
          <em>{summary.solCount} stk</em>
        </div>
        <div>
          <span>Parkering</span>
          <strong>{nok(summary.parking)} kr</strong>
          <em>{summary.parkingCount} stk</em>
        </div>
      </div>
    </Card>
  );
}

export default function StatusComparisonPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const period = searchParams.get("period") || "today";
  const compare = searchParams.get("compare") || "previous";
  const anchor = searchParams.get("anchor") || "";
  const metric: ComparisonMetric = searchParams.get("metric") === "amount" ? "amount" : "count";
  const { data, loading, error } = useAsyncData(() => fetchStatusComparison(period, compare, anchor), [period, compare, anchor]);
  const chartOptions = useMemo(() => {
    if (!data) return [];
    const chartKinds: ComparisonChartKind[] = metric === "amount" ? ["total", "sun", "parking"] : ["sun", "parking"];
    return chartKinds.map((kind) => ({ kind, option: cumulativeChartOption(data, kind, metric) }));
  }, [data, metric]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const setAnchor = (nextAnchor: string) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("anchor", nextAnchor);
    setSearchParams(nextParams);
  };

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-comparison-page">
      <div className="status-comparison-top">
        <div>
          <Typography.Text className="eyebrow">Status sammenligning</Typography.Text>
          <div className="status-comparison-title">
            <strong>{data.title}</strong>
            <span>{data.comparisonLabel}</span>
          </div>
        </div>
        <Space size={8} className="status-comparison-actions">
          <Button
            icon={<LeftOutlined />}
            onClick={() => setAnchor(data.navigation.previousAnchor)}
            title={data.navigation.previousLabel}
          >
            Forrige
          </Button>
          <div className="status-comparison-current-period">{data.navigation.label}</div>
          <Button
            disabled={!data.navigation.canNext}
            icon={<RightOutlined />}
            onClick={() => setAnchor(data.navigation.nextAnchor)}
            title={data.navigation.nextLabel}
          >
            Neste
          </Button>
          <Button icon={<ArrowLeftOutlined />}>
            <Link to="/status/oversikt">Oversikt</Link>
          </Button>
        </Space>
      </div>

      <Row gutter={[14, 14]}>
        <Col span={8}>
          <SummaryCard title={data.current.label} summary={data.current} />
        </Col>
        <Col span={8}>
          <SummaryCard title={data.comparison.label} summary={data.comparison} />
        </Col>
        <Col span={8}>
          <Card className="status-comparison-delta-card">
            <span>Differanse</span>
            <strong>{signedNok(data.delta.total)}</strong>
            <div>
              <em>Soling {signedNok(data.delta.sol)} / {signedCount(data.delta.solCount)}</em>
              <em>Parkering {signedNok(data.delta.parking)} / {signedCount(data.delta.parkingCount)}</em>
            </div>
          </Card>
        </Col>
      </Row>

      <Card
        className="status-comparison-chart-card"
        title="Akkumulert utvikling"
        extra={
          <Space size={12} className="status-comparison-chart-tools">
            <Segmented
              size="small"
              value={metric}
              options={[
                { label: "Antall", value: "count" },
                { label: "Beløp", value: "amount" },
              ]}
              onChange={(value) => {
                const nextParams = new URLSearchParams(searchParams);
                if (value === "amount") {
                  nextParams.set("metric", "amount");
                } else {
                  nextParams.delete("metric");
                }
                setSearchParams(nextParams, { replace: true });
              }}
            />
            <div className="status-comparison-legend">
              <span><i className="kind-current" />Valgt periode</span>
              <span><i className="kind-comparison" />Sammenligning</span>
            </div>
          </Space>
        }
      >
        <div className="status-comparison-axis-meta">
          <span>Relativ tidsakse fra {shortTimeText(data.axis.start)}</span>
          <span>til {shortTimeText(data.axis.end)}</span>
        </div>
        <div className="status-comparison-chart-stack">
          {chartOptions.map((item) => (
            <ReactECharts
              option={item.option}
              style={{ height: metric === "amount" ? 245 : 285 }}
              key={`${metric}-${item.kind}`}
            />
          ))}
        </div>
      </Card>
    </Space>
  );
}
