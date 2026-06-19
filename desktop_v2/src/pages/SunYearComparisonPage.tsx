import { ArrowLeftOutlined, LeftOutlined, RightOutlined } from "@ant-design/icons";
import { Button, Card, Checkbox, Col, Row, Segmented, Space, Typography } from "antd";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchSunYearComparison,
  type SunYearComparisonResponse,
  type SunYearComparisonSeries,
} from "../api";
import { AppChart } from "../components/AppChart";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { domainColors } from "../domainColors";
import { decimal, nok } from "../format";
import { useAsyncData } from "../hooks";

type SunYearMetric = "amount" | "count";

function dateLabel(value?: string | null) {
  if (!value) return "-";
  return new Date(`${value}T00:00:00`).toLocaleDateString("nb-NO", { day: "2-digit", month: "2-digit" });
}

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

function metricValue(value: number, metric: SunYearMetric) {
  if (metric === "amount") return `${nok(value)} kr`;
  return `${Math.round(value)} stk`;
}

function metricAxisValue(value: number, metric: SunYearMetric) {
  if (metric === "amount") {
    if (Math.abs(value) >= 1000) return `${Math.round(value / 1000)}k`;
    return `${Math.round(value)}`;
  }
  return `${Math.round(value)}`;
}

function pointValue(point: SunYearComparisonSeries["points"][number], metric: SunYearMetric) {
  return metric === "amount" ? point.cumulativeAmount : point.cumulativeCount;
}

function chartData(series: SunYearComparisonSeries, metric: SunYearMetric): Array<[number, number]> {
  return series.points.map((point) => [point.day, pointValue(point, metric)]);
}

function defaultSelectedYears(data: SunYearComparisonResponse) {
  return [data.anchorYear, data.comparisonYear].filter((year, index, years) => years.indexOf(year) === index);
}

function activeYearsFromParams(data: SunYearComparisonResponse, yearsParam: string | null) {
  const available = new Set(data.availableYears);
  const parsed = (yearsParam || "")
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((year) => Number.isFinite(year) && available.has(year));
  const unique = parsed.filter((year, index, years) => years.indexOf(year) === index);
  return unique.length ? unique : defaultSelectedYears(data);
}

function monthLabel(data: SunYearComparisonResponse, value: number) {
  const day = Math.round(Number(value));
  const tick = data.axis.ticks.reduce<{ label: string; day: number } | null>((best, item) => {
    if (item.day <= day && (!best || item.day > best.day)) return item;
    return best;
  }, null);
  return tick?.label ?? "";
}

function cumulativeChartOption(data: SunYearComparisonResponse, metric: SunYearMetric, activeYears: number[]) {
  const visibleSeries = data.series.filter((series) => activeYears.includes(series.year));
  const selected = data.selected;
  const yTitle = metric === "amount" ? "Akkumulert omsetning" : "Akkumulerte solinger";
  return {
    color: visibleSeries.map((series) => series.color),
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line" },
      backgroundColor: "rgba(255,255,255,0.96)",
      borderColor: "#dbe3ee",
      borderWidth: 1,
      textStyle: { color: "#111827", fontSize: 12 },
      extraCssText: "box-shadow:0 12px 28px rgba(15,23,42,.12);border-radius:8px;",
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        const first = items[0] as { value?: [number, number] } | undefined;
        const day = Math.max(1, Math.round(Number(first?.value?.[0] ?? 1)));
        const rows = items
          .map((item) => {
            const row = item as { marker?: string; seriesName?: string; value?: [number, number] };
            return `<div style="display:flex;justify-content:space-between;gap:20px;line-height:1.7">
              <span>${row.marker ?? ""}${row.seriesName ?? ""}</span>
              <strong>${metricValue(Number(row.value?.[1] ?? 0), metric)}</strong>
            </div>`;
          })
          .join("");
        return `<div style="min-width:190px">
          <div style="margin-bottom:6px;font-weight:700;color:${domainColors.ink}">Dag ${day} · ${monthLabel(data, day)}</div>
          ${rows}
        </div>`;
      },
    },
    legend: {
      top: 0,
      icon: "roundRect",
      itemWidth: 18,
      itemHeight: 8,
      textStyle: { color: "#475569", fontSize: 12, fontWeight: 650 },
    },
    grid: { top: 48, left: 12, right: 18, bottom: 30, containLabel: true },
    xAxis: {
      type: "value",
      min: 1,
      max: data.axis.days,
      interval: 31,
      axisLabel: { formatter: (value: number) => monthLabel(data, value) },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "#cbd5e1" } },
      splitLine: { lineStyle: { color: domainColors.gridSoft } },
    },
    yAxis: {
      type: "value",
      minInterval: metric === "amount" ? undefined : 1,
      axisLabel: { formatter: (value: number) => metricAxisValue(value, metric) },
      splitLine: { lineStyle: { color: "#e8edf4" } },
    },
    series: [
      ...visibleSeries.map((series) => ({
        name: series.label,
        type: "line",
        step: "end",
        symbol: "none",
        lineStyle: { width: series.year === data.anchorYear ? 3 : 2, type: series.year === data.anchorYear ? "solid" : "dashed" },
        areaStyle: series.year === data.anchorYear ? { opacity: 0.08 } : undefined,
        emphasis: { focus: "series" },
        data: chartData(series, metric),
        markLine:
          series.year === data.anchorYear && series.asOfDay < series.daysInYear
            ? {
                symbol: "none",
                silent: true,
                lineStyle: { color: series.color, type: "dotted", width: 1.5 },
                label: { formatter: "Hittil", color: "#92400e", fontSize: 11 },
                data: [{ xAxis: selected.asOfDay }],
              }
            : undefined,
      })),
    ],
    title: {
      text: yTitle,
      top: 2,
      left: 0,
      textStyle: { color: domainColors.ink, fontSize: 13, fontWeight: 760 },
    },
  };
}

function YearSummaryCard({
  title,
  series,
  detail,
  delta,
}: {
  title: string;
  series: SunYearComparisonSeries;
  detail: string;
  delta?: { amount: number; count: number };
}) {
  return (
    <Card className="status-comparison-summary-card">
      <div className="status-comparison-summary-head">
        <div>
          <span>{title}</span>
          {delta ? (
            <em className={`status-comparison-card-delta ${deltaTone(delta.amount)}`}>
              {signedNok(delta.amount)} / {signedCount(delta.count)}
            </em>
          ) : null}
        </div>
        <strong>{nok(series.totalAmount)} kr</strong>
      </div>
      <div className="status-comparison-summary-meta">
        <span>{detail}</span>
        <span>{series.daysWithData} dager med data</span>
      </div>
      <div className="status-comparison-summary-split">
        <div>
          <span>Solinger</span>
          <strong>{series.totalCount} stk</strong>
          <em>{decimal(series.totalMinutes / 60, 1)} timer</em>
        </div>
        <div>
          <span>Snitt</span>
          <strong>{nok(series.totalAmount / Math.max(1, series.totalCount))} kr</strong>
          <em>per soling</em>
        </div>
      </div>
    </Card>
  );
}

export default function SunYearComparisonPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const year = searchParams.get("year") || "";
  const metric: SunYearMetric = searchParams.get("metric") === "count" ? "count" : "amount";
  const { data, loading, error } = useAsyncData(() => fetchSunYearComparison(year), [year]);
  const activeYears = useMemo(() => (data ? activeYearsFromParams(data, searchParams.get("years")) : []), [data, searchParams]);
  const activeYearKey = activeYears.join(",");
  const chartOption = useMemo(() => (data ? cumulativeChartOption(data, metric, activeYears) : null), [data, metric, activeYearKey]);

  if (loading) return <LoadingBlock />;
  if (error || !data || !chartOption) return <ErrorBlock error={error} />;

  const setYear = (nextYear: string) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("year", nextYear);
    setSearchParams(nextParams);
  };
  const setActiveYears = (values: Array<string | number | boolean>) => {
    const years = values.map((value) => Number(value)).filter((value) => Number.isFinite(value));
    const nextParams = new URLSearchParams(searchParams);
    if (years.length) {
      nextParams.set("years", years.join(","));
    } else {
      nextParams.delete("years");
    }
    setSearchParams(nextParams, { replace: true });
  };
  const resetActiveYears = () => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete("years");
    setSearchParams(nextParams, { replace: true });
  };

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-comparison-page sun-year-comparison-page">
      <div className="status-comparison-top">
        <div>
          <Typography.Text className="eyebrow">Soling sammenligning</Typography.Text>
          <div className="status-comparison-title">
            <strong>{data.anchorYear} mot {data.comparisonYear}</strong>
            <span>Akkumulert utvikling gjennom året</span>
          </div>
        </div>
        <Space size={8} className="status-comparison-actions">
          <Button
            icon={<LeftOutlined />}
            onClick={() => setYear(data.navigation.previousAnchor)}
            title={data.navigation.previousLabel}
          >
            Forrige
          </Button>
          <div className="status-comparison-current-period">{data.navigation.label}</div>
          <Button
            disabled={!data.navigation.canNext}
            icon={<RightOutlined />}
            onClick={() => setYear(data.navigation.nextAnchor)}
            title={data.navigation.nextLabel}
          >
            Neste
          </Button>
          <Button icon={<ArrowLeftOutlined />}>
            <Link to="/soling/oversikt">Oversikt</Link>
          </Button>
        </Space>
      </div>

      <Row gutter={[14, 14]}>
        <Col span={8}>
          <YearSummaryCard
            title={`${data.anchorYear}`}
            series={data.selected}
            detail={`${data.asOf.selectedLabel} · ${dateLabel(data.asOf.selectedDate)}`}
          />
        </Col>
        <Col span={8}>
          <YearSummaryCard
            title={`${data.comparisonYear} samme punkt`}
            series={data.comparison}
            detail={`${data.asOf.comparisonLabel} · ${dateLabel(data.asOf.comparisonDate)}`}
            delta={{ amount: data.delta.amount, count: data.delta.count }}
          />
        </Col>
        <Col span={8}>
          <YearSummaryCard
            title={`${data.comparisonYear} hele året`}
            series={data.comparisonFull}
            detail="Fullført år som kontekst"
          />
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
          <span>Årsakse fra januar til desember</span>
          <span>valgt år mot forrige år</span>
        </div>
        <div className="status-comparison-year-picker">
          <Checkbox.Group
            value={activeYears.map(String)}
            options={data.availableYears.map((item) => ({ label: String(item), value: String(item) }))}
            onChange={setActiveYears}
          />
          <Space size={6}>
            <Button size="small" onClick={() => setActiveYears(data.availableYears.map(String))}>Alle år</Button>
            <Button size="small" onClick={resetActiveYears}>Standard</Button>
          </Space>
        </div>
        <div className="status-comparison-chart-stack">
          <AppChart option={chartOption} style={{ height: 460 }} />
        </div>
      </Card>
    </Space>
  );
}
