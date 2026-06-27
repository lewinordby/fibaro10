import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Card, Col, Row, Segmented, Space, Typography } from "antd";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchStatusComparison,
  type StatusComparisonLane,
  type StatusComparisonReference,
  type StatusComparisonResponse,
  type StatusComparisonSummary,
} from "../api";
import { chartAxisLine, chartLegend, chartSplitLine, chartTitleTextStyle, chartTooltip } from "../chartTheme";
import { AppChart } from "../components/AppChart";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PeriodLabel, PeriodNavigator } from "../components/PeriodNavigator";
import { domainColors } from "../domainColors";
import { nok } from "../format";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";

type ComparisonMetric = "count" | "amount";
type ComparisonChartKind = StatusComparisonLane["kind"] | "total";
type ComparisonSource = StatusComparisonLane["source"];
type SummaryDelta = StatusComparisonReference["delta"];

const referenceColors = ["#0f766e", "#7c3aed", "#be123c"];

function signedNok(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 kr";
  return `${value > 0 ? "+" : "-"}${nok(Math.abs(value))} kr`;
}

function signedCount(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 stk";
  return `${value > 0 ? "+" : "-"}${Math.abs(value)} stk`;
}

function deltaTone(value: number) {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
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
  const endLeft = lanes.reduce((max, lane) => {
    const laneEnd = Number(lane?.endLeft);
    if (!Number.isFinite(laneEnd)) return max;
    return Math.max(max, Math.max(0, Math.min(100, laneEnd)));
  }, 0);
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
  const finalLeft = Math.max(endLeft, points[points.length - 1]?.[0] ?? 0);
  if (finalLeft > (points[points.length - 1]?.[0] ?? 0)) {
    points.push([finalLeft, Math.round(total * 100) / 100]);
  }
  return points;
}

function laneFor(lanes: StatusComparisonLane[], kind: StatusComparisonLane["kind"], source: ComparisonSource) {
  return lanes.find((lane) => lane.kind === kind && lane.source === source);
}

function lanesForChart(lanes: StatusComparisonLane[], kind: ComparisonChartKind, source: ComparisonSource) {
  if (kind === "total") return [laneFor(lanes, "sun", source), laneFor(lanes, "parking", source)];
  return [laneFor(lanes, kind, source)];
}

function cumulativeChartOption(data: StatusComparisonResponse, kind: ComparisonChartKind, metric: ComparisonMetric) {
  const references: StatusComparisonReference[] = data.referenceComparisons ?? [];
  const currentLanes = lanesForChart(data.lanes, kind, "current");
  const comparisonLanes = lanesForChart(data.lanes, kind, "comparison");
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
    color: [primaryColor, domainColors.comparison, ...references.map((_, index) => referenceColors[index % referenceColors.length])],
    tooltip: {
      ...chartTooltip(),
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
    legend: chartLegend(),
    grid: { top: 48, left: 12, right: 16, bottom: 30, containLabel: true },
    xAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: { formatter: (value: number) => axisText(data, value) },
      axisTick: { show: false },
      axisLine: chartAxisLine(),
      splitLine: chartSplitLine(domainColors.gridSoft),
    },
    yAxis: {
      type: "value",
      minInterval: metric === "amount" ? undefined : 1,
      axisLabel: { formatter: (value: number) => axisValue(value, metric) },
      splitLine: chartSplitLine(),
    },
    series: [
      {
        name: currentLanes.find(Boolean)?.periodLabel ?? data.current.label,
        type: "line",
        step: "end",
        symbol: "none",
        lineStyle: { width: 3 },
        areaStyle: { opacity: 0.06 },
        emphasis: { focus: "series" },
        data: cumulativePoints(currentLanes, metric),
      },
      {
        name: comparisonLanes.find(Boolean)?.periodLabel ?? data.comparison.label,
        type: "line",
        step: "end",
        symbol: "none",
        lineStyle: { width: 2, type: "dashed" },
        emphasis: { focus: "series" },
        data: cumulativePoints(comparisonLanes, metric),
      },
      ...references.map((reference, index) => ({
        name: reference.label,
        type: "line",
        step: "end",
        symbol: "none",
        lineStyle: { width: 2, type: "dotted" },
        emphasis: { focus: "series" },
        data: cumulativePoints(lanesForChart(reference.lanes, kind, "reference"), metric),
        itemStyle: { color: referenceColors[index % referenceColors.length] },
      })),
    ],
    title: {
      text: title,
      top: 2,
      left: 0,
      textStyle: chartTitleTextStyle(),
    },
  };
}

function SummaryCard({
  title,
  summary,
  delta,
  deltaLabel,
}: {
  title: string;
  summary: StatusComparisonSummary;
  delta?: SummaryDelta;
  deltaLabel?: string;
}) {
  const totalDeltaTone = delta ? deltaTone(delta.total) : "";
  return (
    <Card className="status-comparison-summary-card">
      <div className="status-comparison-summary-head">
        <div>
          <span>{title}</span>
          {delta ? (
            <em className={`status-comparison-card-delta ${totalDeltaTone}`}>
              {deltaLabel ?? "Valgt periode"} {signedNok(delta.total)}
            </em>
          ) : null}
        </div>
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
          {delta ? <small className={deltaTone(delta.sol)}>{signedNok(delta.sol)} / {signedCount(delta.solCount)}</small> : null}
        </div>
        <div>
          <span>Parkering</span>
          <strong>{nok(summary.parking)} kr</strong>
          <em>{summary.parkingCount} stk</em>
          {delta ? <small className={deltaTone(delta.parking)}>{signedNok(delta.parking)} / {signedCount(delta.parkingCount)}</small> : null}
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
  const metric: ComparisonMetric = searchParams.get("metric") === "count" ? "count" : "amount";
  const { data, loading, error } = useApiQuery(
    queryKeys.statusComparison(period, compare, anchor),
    () => fetchStatusComparison(period, compare, anchor),
  );
  const chartOptions = useMemo(() => {
    if (!data) return [];
    const chartKinds: ComparisonChartKind[] = metric === "amount" ? ["total", "sun", "parking"] : ["sun", "parking"];
    return chartKinds.map((kind) => ({ kind, option: cumulativeChartOption(data, kind, metric) }));
  }, [data, metric]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const sameWeekdayReference = (data.referenceComparisons ?? []).find((reference) => reference.key === "same-weekday-last-week");
  const summaryCards = [
    { title: data.current.label, summary: data.current },
    { title: data.comparison.label, summary: data.comparison, delta: data.delta, deltaLabel: "Valgt periode" },
    ...(sameWeekdayReference
      ? [
          {
            title: sameWeekdayReference.summary.label || sameWeekdayReference.label,
            summary: sameWeekdayReference.summary,
            delta: sameWeekdayReference.delta,
            deltaLabel: "Valgt periode",
          },
        ]
      : []),
  ];
  const summaryColSpan = summaryCards.length >= 3 ? 8 : 12;

  const setAnchor = (nextAnchor: string) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("anchor", nextAnchor);
    setSearchParams(nextParams);
  };

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-comparison-page">
      <div className="status-comparison-top">
        <div>
          <Typography.Text className="eyebrow">Omsetning · periodesammenligning</Typography.Text>
          <div className="status-comparison-title">
            <strong>{data.title}</strong>
            <span>{data.comparisonLabel}</span>
          </div>
        </div>
        <PeriodNavigator
          className="status-comparison-actions"
          previousLabel="Forrige"
          previousTitle={data.navigation.previousLabel}
          nextLabel="Neste"
          nextTitle={data.navigation.nextLabel}
          canNext={data.navigation.canNext}
          onPrevious={() => setAnchor(data.navigation.previousAnchor)}
          onNext={() => setAnchor(data.navigation.nextAnchor)}
          middle={<PeriodLabel>{data.navigation.label}</PeriodLabel>}
          extra={
          <Button icon={<ArrowLeftOutlined />}>
            <Link to="/omsetning/oversikt">Oversikt</Link>
          </Button>
          }
        />
      </div>

      <Row gutter={[14, 14]}>
        {summaryCards.map((card) => (
          <Col span={summaryColSpan} key={card.title}>
            <SummaryCard
              title={card.title}
              summary={card.summary}
              delta={card.delta}
              deltaLabel={card.deltaLabel}
            />
          </Col>
        ))}
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
                { label: "Omsetning", value: "amount" },
                { label: "Antall", value: "count" },
              ]}
              onChange={(value) => {
                const nextParams = new URLSearchParams(searchParams);
                if (value === "amount") {
                  nextParams.delete("metric");
                } else {
                  nextParams.set("metric", "count");
                }
                setSearchParams(nextParams, { replace: true });
              }}
            />
          </Space>
        }
      >
        <div className="status-comparison-axis-meta">
          <span>Relativ tidsakse fra {shortTimeText(data.axis.start)}</span>
          <span>til {shortTimeText(data.axis.end)}</span>
        </div>
        <div className="status-comparison-chart-stack">
          {chartOptions.map((item) => (
            <AppChart
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
