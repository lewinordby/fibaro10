import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Card, Checkbox, Input, Segmented, Space, Typography } from "antd";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchParkingWeeklyAverages,
  fetchParkingWeeklyYearComparison,
  type ParkingWeeklyAveragePoint,
  type ParkingWeeklyYearComparisonResponse,
  type ParkingWeeklyYearSeries,
} from "../api";
import {
  chartAreaOpacity,
  chartAxisLabel,
  chartAxisLine,
  chartLegend,
  chartSeriesColor,
  chartSeriesLineWidth,
  chartSplitLine,
  chartThemeKey,
  chartTooltip,
} from "../chartTheme";
import { AppChart } from "../components/AppChart";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { domainColors } from "../domainColors";
import { decimal, nok } from "../format";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/parking-weekly-averages.css";

function periodDateLabel(value: string): string {
  const [year, month, day] = value.split("-");
  return year && month && day ? `${day}.${month}.${year}` : value;
}

function deltaLabel(value: number | null): string {
  if (value == null) return "Ingen forrige uke";
  const sign = value > 0 ? "+" : "";
  return `${sign}${decimal(value, 1)} % fra forrige uke`;
}

function deltaTone(value: number | null): string {
  if (value == null || Math.abs(value) < 0.05) return "neutral";
  return value > 0 ? "positive" : "negative";
}

function pointValue(value: number | null, isPartial: boolean) {
  if (value == null) return null;
  return {
    value,
    symbol: isPartial ? "emptyCircle" : "circle",
    symbolSize: isPartial ? 9 : 6,
  };
}

function weeklyChartOption(weeks: ParkingWeeklyAveragePoint[], periodPaidAverage: number, periodMinutesAverage: number) {
  const paidColor = chartSeriesColor(domainColors.parking, 0);
  const minutesColor = chartSeriesColor("#0f766e", 1);
  return {
    color: [paidColor, minutesColor],
    legend: chartLegend({ data: ["Beløp pr parkering", "Tid pr parkering"] }),
    tooltip: {
      ...chartTooltip(),
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        const first = items[0] as { dataIndex?: number } | undefined;
        const point = weeks[Number(first?.dataIndex ?? 0)] ?? weeks[0];
        if (!point) return "";
        const paid = point.avgPaidPerSession == null ? "–" : `${nok(point.avgPaidPerSession)} kr`;
        const minutes = point.avgMinutesPerSession == null ? "–" : `${decimal(point.avgMinutesPerSession, 0)} min`;
        return `<div style="min-width:230px">
          <div style="font-weight:760;margin-bottom:2px;color:${domainColors.ink}">${point.label} · ${point.isoYear}${point.isPartial ? " · pågående/avkortet" : ""}</div>
          <div style="margin-bottom:8px;color:${domainColors.comparison};font-size:12px">${point.rangeLabel}</div>
          <div style="display:flex;justify-content:space-between;gap:24px"><span>Beløp pr parkering</span><strong>${paid}</strong></div>
          <div style="display:flex;justify-content:space-between;gap:24px;margin-top:4px"><span>Tid pr parkering</span><strong>${minutes}</strong></div>
          <div style="margin-top:8px;color:${domainColors.comparison};font-size:12px">${nok(point.sessions)} parkeringer · ${nok(point.paid)} kr totalt · ${decimal(point.durationCoveragePct, 0)} % med tidsgrunnlag</div>
        </div>`;
      },
    },
    grid: { top: 50, right: 66, bottom: 38, left: 60 },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: weeks.map((point) => point.key),
      axisTick: { show: false },
      axisLine: chartAxisLine(),
      axisLabel: chartAxisLabel({
        hideOverlap: true,
        formatter: (_value: string, index: number) => weeks[index]?.shortLabel ?? "",
      }),
    },
    yAxis: [
      {
        type: "value",
        name: "kr",
        min: 0,
        nameTextStyle: chartAxisLabel(),
        axisLabel: chartAxisLabel({ formatter: (value: number) => `${Math.round(value)}` }),
        axisLine: { show: true, ...chartAxisLine() },
        splitLine: chartSplitLine(),
      },
      {
        type: "value",
        name: "min",
        min: 0,
        position: "right",
        nameTextStyle: chartAxisLabel(),
        axisLabel: chartAxisLabel({ formatter: (value: number) => `${Math.round(value)}` }),
        axisLine: { show: true, ...chartAxisLine() },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "Beløp pr parkering",
        type: "line",
        yAxisIndex: 0,
        connectNulls: false,
        smooth: 0.18,
        showSymbol: true,
        lineStyle: { width: chartSeriesLineWidth(true), color: paidColor },
        itemStyle: { color: paidColor, borderWidth: 2 },
        areaStyle: { color: paidColor, opacity: chartAreaOpacity(true) },
        data: weeks.map((point) => pointValue(point.avgPaidPerSession, point.isPartial)),
        markLine: {
          silent: true,
          symbol: "none",
          label: { show: false },
          lineStyle: { color: paidColor, type: "dashed", opacity: 0.5 },
          data: [{ yAxis: periodPaidAverage }],
        },
      },
      {
        name: "Tid pr parkering",
        type: "line",
        yAxisIndex: 1,
        connectNulls: false,
        smooth: 0.18,
        showSymbol: true,
        lineStyle: { width: chartSeriesLineWidth(), color: minutesColor },
        itemStyle: { color: minutesColor, borderWidth: 2 },
        data: weeks.map((point) => pointValue(point.avgMinutesPerSession, point.isPartial)),
        markLine: {
          silent: true,
          symbol: "none",
          label: { show: false },
          lineStyle: { color: minutesColor, type: "dashed", opacity: 0.5 },
          data: [{ yAxis: periodMinutesAverage }],
        },
      },
    ],
  };
}

type WeeklyYearMetric = "amount" | "minutes";

function weeklyYearMetricValue(series: ParkingWeeklyYearSeries, weekIndex: number, metric: WeeklyYearMetric) {
  const point = series.points[weekIndex];
  return metric === "amount" ? point?.avgPaidPerSession : point?.avgMinutesPerSession;
}

function weeklyYearChartOption(data: ParkingWeeklyYearComparisonResponse, metric: WeeklyYearMetric) {
  const amountMetric = metric === "amount";
  const seriesColors = data.series.map((series, index) => chartSeriesColor(series.color, index));
  return {
    color: seriesColors,
    legend: chartLegend({ data: data.series.map((series) => series.label) }),
    tooltip: {
      ...chartTooltip(),
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        const first = items[0] as { dataIndex?: number } | undefined;
        const weekIndex = Number(first?.dataIndex ?? 0);
        const week = weekIndex + 1;
        const rows = items.map((item) => {
          const row = item as { marker?: string; seriesName?: string; seriesIndex?: number };
          const source = data.series[Number(row.seriesIndex ?? 0)];
          const point = source?.points[weekIndex];
          const value = amountMetric
            ? (point?.avgPaidPerSession == null ? "-" : `${nok(point.avgPaidPerSession)} kr`)
            : (point?.avgMinutesPerSession == null ? "-" : `${decimal(point.avgMinutesPerSession, 0)} min`);
          const basis = point?.sessions ? `${nok(point.sessions)} parkeringer` : "Ingen parkeringer";
          return `<div style="display:flex;justify-content:space-between;gap:24px;line-height:1.65">
            <span>${row.marker ?? ""}${row.seriesName ?? ""}</span><strong>${value}</strong>
          </div><div style="margin-left:16px;color:${domainColors.comparison};font-size:11px">${basis}${point?.rangeLabel ? ` · ${point.rangeLabel}` : ""}</div>`;
        }).join("");
        return `<div style="min-width:250px"><div style="font-weight:760;margin-bottom:6px;color:${domainColors.ink}">Uke ${week}</div>${rows}</div>`;
      },
    },
    grid: { top: 48, right: 18, bottom: 32, left: 52 },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: Array.from({ length: 53 }, (_, index) => `U${index + 1}`),
      axisTick: { show: false },
      axisLine: chartAxisLine(),
      axisLabel: chartAxisLabel({ hideOverlap: true, interval: 3 }),
    },
    yAxis: {
      type: "value",
      min: 0,
      name: amountMetric ? "kr" : "min",
      nameTextStyle: chartAxisLabel(),
      axisLabel: chartAxisLabel({ formatter: (value: number) => `${Math.round(value)}` }),
      splitLine: chartSplitLine(),
    },
    series: data.series.map((series, index) => ({
      name: series.label,
      type: "line",
      connectNulls: false,
      smooth: 0.16,
      showSymbol: false,
      lineStyle: {
        color: seriesColors[index],
        width: chartSeriesLineWidth(series.year === data.currentYear),
        type: series.year === data.currentYear ? "solid" : "dashed",
      },
      itemStyle: { color: seriesColors[index] },
      emphasis: { focus: "series" },
      data: series.points.map((_point, weekIndex) => weeklyYearMetricValue(series, weekIndex, metric)),
    })),
  };
}

function updateSearchParams(
  searchParams: URLSearchParams,
  setSearchParams: ReturnType<typeof useSearchParams>[1],
  entries: Record<string, string>,
) {
  const next = new URLSearchParams(searchParams);
  Object.entries(entries).forEach(([key, value]) => {
    if (value) next.set(key, value);
    else next.delete(key);
  });
  setSearchParams(next, { replace: true });
}

function ParkingWeeklyYearComparison({
  searchParams,
  setSearchParams,
}: {
  searchParams: URLSearchParams;
  setSearchParams: ReturnType<typeof useSearchParams>[1];
}) {
  const yearsParam = searchParams.get("years") || "";
  const { data, loading, error } = useApiQuery(
    queryKeys.parkingWeeklyYearComparison(yearsParam),
    () => fetchParkingWeeklyYearComparison(yearsParam),
    { staleTime: 10 * 60_000 },
  );
  const themeKey = chartThemeKey();
  const amountOption = useMemo(
    () => data ? weeklyYearChartOption(data, "amount") : null,
    [data, themeKey],
  );
  const minutesOption = useMemo(
    () => data ? weeklyYearChartOption(data, "minutes") : null,
    [data, themeKey],
  );

  const setYears = (years: number[]) => {
    const next = new URLSearchParams(searchParams);
    if (years.length) next.set("years", years.join(","));
    else next.delete("years");
    setSearchParams(next, { replace: true });
  };

  if (loading) {
    return <Card className="chart-card parking-weekly-year-card" title="Sammenlign år"><LoadingBlock /></Card>;
  }
  if (error || !data || !amountOption || !minutesOption) {
    return <Card className="chart-card parking-weekly-year-card" title="Sammenlign år"><ErrorBlock error={error} /></Card>;
  }

  return (
    <Card className="chart-card parking-weekly-year-card" title="Sammenlign år">
      <div className="parking-weekly-year-toolbar">
        <div>
          <Typography.Text strong>Velg sammenligningsår</Typography.Text>
          <Typography.Text type="secondary">Samme sjudagersperiode i kalenderåret sammenlignes på tvers av år.</Typography.Text>
        </div>
        <div className="parking-weekly-year-actions">
          <Checkbox.Group
            value={data.selectedYears.map(String)}
            options={data.availableYears.map((year) => ({ label: String(year), value: String(year) }))}
            onChange={(values) => setYears(values.map(Number).filter(Number.isFinite))}
          />
          <Space size={6}>
            <Button size="small" onClick={() => setYears(data.availableYears)}>Alle år</Button>
            <Button size="small" onClick={() => setYears(data.defaultYears)}>Standard</Button>
          </Space>
        </div>
      </div>
      <div className="parking-weekly-year-summary">
        {data.series.map((series, index) => (
          <span key={series.year}>
            <i style={{ background: chartSeriesColor(series.color, index) }} />
            <strong>{series.year}</strong>
            {nok(series.avgPaidPerSession)} kr · {decimal(series.avgMinutesPerSession, 0)} min · {nok(series.sessions)} parkeringer
          </span>
        ))}
      </div>
      <div className="parking-weekly-year-grid">
        <section>
          <Typography.Title level={5}>Beløp pr parkering</Typography.Title>
          <AppChart option={amountOption} style={{ height: 340 }} lazyUpdate />
        </section>
        <section>
          <Typography.Title level={5}>Tid pr parkering</Typography.Title>
          <AppChart option={minutesOption} style={{ height: 340 }} lazyUpdate />
        </section>
      </div>
    </Card>
  );
}

export default function ParkingWeeklyAveragesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const periodSearchParams = new URLSearchParams(searchParams);
  periodSearchParams.delete("years");
  const filterKey = periodSearchParams.toString();
  const { data, loading, error } = useApiQuery(
    queryKeys.parkingWeeklyAverages(filterKey),
    () => fetchParkingWeeklyAverages(periodSearchParams),
    { staleTime: 5 * 60_000 },
  );
  const themeKey = chartThemeKey();
  const chartOption = useMemo(
    () => data ? weeklyChartOption(data.weeks, data.summary.avgPaidPerSession, data.summary.avgMinutesPerSession) : null,
    [data, themeKey],
  );

  if (loading) return <LoadingBlock />;
  if (error || !data || !chartOption) return <ErrorBlock error={error} />;

  const periodKey = searchParams.get("period") || data.period.key;
  const latest = data.latest;
  const latestWeekDetail = latest
    ? `${latest.label} · ${latest.rangeLabel}${latest.isPartial ? " · pågående/avkortet" : ""}`
    : "Ingen parkeringer i perioden";

  return (
    <Space direction="vertical" size={14} className="page-stack parking-weekly-page">
      <div className="parking-weekly-top">
        <div>
          <Typography.Text className="eyebrow">Parkering · ukesnitt</Typography.Text>
          <div className="parking-weekly-title">
            <strong>Gjennomsnitt pr parkering</strong>
            <span>{periodDateLabel(data.period.dateFrom)} - {periodDateLabel(data.period.dateTo)} · {data.period.detail}</span>
          </div>
        </div>
        <Button icon={<ArrowLeftOutlined />}>
          <Link to="/parkering/oversikt">Parkering</Link>
        </Button>
      </div>

      <Card className="work-card parking-weekly-filter-card">
        <div className="parking-weekly-filter-row">
          <Segmented
            size="small"
            value={periodKey}
            options={data.period.options.map((item) => ({ label: item.label, value: item.key }))}
            onChange={(value) => {
              const period = String(value);
              updateSearchParams(searchParams, setSearchParams, {
                period,
                date_from: period === "custom" ? data.period.dateFrom : "",
                date_to: period === "custom" ? data.period.dateTo : "",
              });
            }}
          />
          <div className="parking-weekly-date-range">
            <Input
              aria-label="Fra dato"
              size="small"
              type="date"
              value={searchParams.get("date_from") || data.period.dateFrom}
              onChange={(event) => updateSearchParams(searchParams, setSearchParams, { period: "custom", date_from: event.target.value })}
            />
            <Input
              aria-label="Til dato"
              size="small"
              type="date"
              value={searchParams.get("date_to") || data.period.dateTo}
              onChange={(event) => updateSearchParams(searchParams, setSearchParams, { period: "custom", date_to: event.target.value })}
            />
          </div>
        </div>
      </Card>

      <div className="parking-weekly-summary-grid">
        <Card className="summary-card tone-parking" title="Beløp siste uke">
          <strong>{latest?.avgPaidPerSession == null ? "–" : `${nok(latest.avgPaidPerSession)} kr`}</strong>
          <span className={`parking-weekly-delta ${deltaTone(data.delta.paidPct)}`}>{deltaLabel(data.delta.paidPct)}</span>
        </Card>
        <Card className="summary-card tone-parking" title="Tid siste uke">
          <strong>{latest?.avgMinutesPerSession == null ? "–" : `${decimal(latest.avgMinutesPerSession, 0)} min`}</strong>
          <span className={`parking-weekly-delta ${deltaTone(data.delta.minutesPct)}`}>{deltaLabel(data.delta.minutesPct)}</span>
        </Card>
        <Card className="summary-card tone-parking" title="Periodesnitt">
          <strong>{nok(data.summary.avgPaidPerSession)} kr</strong>
          <span>{decimal(data.summary.avgMinutesPerSession, 0)} min pr parkering</span>
        </Card>
        <Card className="summary-card tone-parking" title="Datagrunnlag">
          <strong>{nok(data.summary.sessions)} parkeringer</strong>
          <span>{data.summary.weeksWithData} uker · {decimal(data.summary.durationCoveragePct, 0)} % med tid</span>
        </Card>
      </div>

      <Card className="chart-card parking-weekly-chart-card" title="Ukevis utvikling">
        <div className="parking-weekly-chart-meta">
          <Typography.Text type="secondary">{latestWeekDetail}</Typography.Text>
          <Typography.Text type="secondary">Stiplet linje viser snittet for valgt periode.</Typography.Text>
        </div>
        <AppChart option={chartOption} style={{ height: 430 }} lazyUpdate />
      </Card>

      <ParkingWeeklyYearComparison searchParams={searchParams} setSearchParams={setSearchParams} />
    </Space>
  );
}
