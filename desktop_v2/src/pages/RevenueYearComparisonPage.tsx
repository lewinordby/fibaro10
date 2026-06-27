import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Card, Checkbox, Col, Row, Space, Typography } from "antd";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchRevenueYearComparison,
  type RevenueYearComparisonResponse,
  type RevenueYearComparisonSeries,
} from "../api";
import { chartAxisLine, chartLegend, chartSplitLine, chartTitleTextStyle, chartTooltip } from "../chartTheme";
import { AppChart } from "../components/AppChart";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PeriodLabel, PeriodNavigator } from "../components/PeriodNavigator";
import { domainColors } from "../domainColors";
import { nok } from "../format";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";

function dateLabel(value?: string | null) {
  if (!value) return "-";
  return new Date(`${value}T00:00:00`).toLocaleDateString("nb-NO", { day: "2-digit", month: "2-digit" });
}

function signedNok(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 kr";
  return `${value > 0 ? "+" : "-"}${nok(Math.abs(value))} kr`;
}

function deltaTone(value: number) {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

function amountValue(value: number) {
  return `${nok(value)} kr`;
}

function axisAmountValue(value: number) {
  if (Math.abs(value) >= 1000) return `${Math.round(value / 1000)}k`;
  return `${Math.round(value)}`;
}

function chartData(series: RevenueYearComparisonSeries): Array<[number, number]> {
  return series.points.map((point) => [point.day, point.cumulativeAmount]);
}

function defaultSelectedYears(data: RevenueYearComparisonResponse) {
  return [data.anchorYear, data.comparisonYear].filter((year, index, years) => years.indexOf(year) === index);
}

function activeYearsFromParams(data: RevenueYearComparisonResponse, yearsParam: string | null) {
  const available = new Set(data.availableYears);
  const parsed = (yearsParam || "")
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((year) => Number.isFinite(year) && available.has(year));
  const unique = parsed.filter((year, index, years) => years.indexOf(year) === index);
  return unique.length ? unique : defaultSelectedYears(data);
}

function monthLabel(data: RevenueYearComparisonResponse, value: number) {
  const day = Math.round(Number(value));
  const tick = data.axis.ticks.reduce<{ label: string; day: number } | null>((best, item) => {
    if (item.day <= day && (!best || item.day > best.day)) return item;
    return best;
  }, null);
  return tick?.label ?? "";
}

function cumulativeChartOption(data: RevenueYearComparisonResponse, activeYears: number[]) {
  const visibleSeries = data.series.filter((series) => activeYears.includes(series.year));
  const selected = data.selected;
  return {
    color: visibleSeries.map((series) => series.color),
    tooltip: {
      ...chartTooltip(),
      axisPointer: { type: "line" },
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        const first = items[0] as { value?: [number, number] } | undefined;
        const day = Math.max(1, Math.round(Number(first?.value?.[0] ?? 1)));
        const rows = items
          .map((item) => {
            const row = item as { marker?: string; seriesName?: string; value?: [number, number] };
            return `<div style="display:flex;justify-content:space-between;gap:20px;line-height:1.7">
              <span>${row.marker ?? ""}${row.seriesName ?? ""}</span>
              <strong>${amountValue(Number(row.value?.[1] ?? 0))}</strong>
            </div>`;
          })
          .join("");
        return `<div style="min-width:190px">
          <div style="margin-bottom:6px;font-weight:700;color:${domainColors.ink}">Dag ${day} · ${monthLabel(data, day)}</div>
          ${rows}
        </div>`;
      },
    },
    legend: chartLegend(),
    grid: { top: 48, left: 12, right: 18, bottom: 30, containLabel: true },
    xAxis: {
      type: "value",
      min: 1,
      max: data.axis.days,
      interval: 31,
      axisLabel: { formatter: (value: number) => monthLabel(data, value) },
      axisTick: { show: false },
      axisLine: chartAxisLine(),
      splitLine: chartSplitLine(domainColors.gridSoft),
    },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (value: number) => axisAmountValue(value) },
      splitLine: chartSplitLine(),
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
        data: chartData(series),
        markLine:
          series.year === data.anchorYear && series.asOfDay < series.daysInYear
            ? {
                symbol: "none",
                silent: true,
                lineStyle: { color: series.color, type: "dotted", width: 1.5 },
                label: { formatter: "Hittil", color: "#991b1b", fontSize: 11 },
                data: [{ xAxis: selected.asOfDay }],
              }
            : undefined,
      })),
    ],
    title: {
      text: "Akkumulert omsetning",
      top: 2,
      left: 0,
      textStyle: chartTitleTextStyle(),
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
  series: RevenueYearComparisonSeries;
  detail: string;
  delta?: { amount: number };
}) {
  return (
    <Card className="status-comparison-summary-card">
      <div className="status-comparison-summary-head">
        <div>
          <span>{title}</span>
          {delta ? (
            <em className={`status-comparison-card-delta ${deltaTone(delta.amount)}`}>
              {signedNok(delta.amount)}
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
          <span>Datadager</span>
          <strong>{series.daysWithData}</strong>
          <em>registrert</em>
        </div>
        <div>
          <span>Snitt</span>
          <strong>{nok(series.totalAmount / Math.max(1, series.daysWithData))} kr</strong>
          <em>per datadag</em>
        </div>
      </div>
    </Card>
  );
}

export default function RevenueYearComparisonPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const year = searchParams.get("year") || "";
  const { data, loading, error } = useApiQuery(queryKeys.revenueYearComparison(year), () => fetchRevenueYearComparison(year));
  const activeYears = useMemo(() => (data ? activeYearsFromParams(data, searchParams.get("years")) : []), [data, searchParams]);
  const activeYearKey = activeYears.join(",");
  const chartOption = useMemo(() => (data ? cumulativeChartOption(data, activeYears) : null), [data, activeYearKey]);

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
    <Space direction="vertical" size={14} className="page-stack status-page status-comparison-page revenue-year-comparison-page">
      <div className="status-comparison-top">
        <div>
          <Typography.Text className="eyebrow">Omsetning · årssammenligning</Typography.Text>
          <div className="status-comparison-title">
            <strong>{data.anchorYear} mot {data.comparisonYear}</strong>
            <span>Akkumulert omsetning gjennom året</span>
          </div>
        </div>
        <PeriodNavigator
          className="status-comparison-actions"
          previousLabel="Forrige"
          previousTitle={data.navigation.previousLabel}
          nextLabel="Neste"
          nextTitle={data.navigation.nextLabel}
          canNext={data.navigation.canNext}
          onPrevious={() => setYear(data.navigation.previousAnchor)}
          onNext={() => setYear(data.navigation.nextAnchor)}
          middle={<PeriodLabel>{data.navigation.label}</PeriodLabel>}
          extra={
          <Button icon={<ArrowLeftOutlined />}>
            <Link to="/omsetning/oversikt">Oversikt</Link>
          </Button>
          }
        />
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
            delta={{ amount: data.delta.amount }}
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

      <Card className="status-comparison-chart-card" title="Akkumulert omsetning">
        <div className="status-comparison-axis-meta">
          <span>Tidsakse fra januar til desember</span>
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
