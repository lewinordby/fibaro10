import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Card, Input, Segmented, Space, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchParkingTimeDistribution, type ParkingTimeCell, type ParkingTimeWeekday } from "../api";
import {
  chartAxisLabel,
  chartAxisLine,
  chartSeriesColor,
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
import "../styles/parking-time-distribution.css";

type MetricKey = "paid" | "minutes" | "sessions" | "avgPaidPerDay" | "avgMinutesPerDay";

const metricOptions: Array<{ key: MetricKey; label: string; unit: string }> = [
  { key: "paid", label: "Omsetning", unit: "kr" },
  { key: "minutes", label: "Parkeringstid", unit: "min" },
  { key: "sessions", label: "Antall", unit: "stk" },
  { key: "avgPaidPerDay", label: "Snitt kr", unit: "kr/dag" },
  { key: "avgMinutesPerDay", label: "Snitt tid", unit: "min/dag" },
];

function metricValue(cell: ParkingTimeCell, metric: MetricKey): number {
  return Number(cell[metric] ?? 0);
}

function formatMetricValue(value: number, metric: MetricKey): string {
  if (metric === "paid" || metric === "avgPaidPerDay") return `${nok(value)} kr`;
  if (metric === "minutes" || metric === "avgMinutesPerDay") return `${decimal(value / 60, 1)} t`;
  return `${nok(value)} stk`;
}

function formatShortMetricValue(value: number, metric: MetricKey): string {
  if (metric === "paid" || metric === "avgPaidPerDay") return `${nok(value)} kr`;
  if (metric === "minutes" || metric === "avgMinutesPerDay") return `${decimal(value / 60, 1)} t`;
  return nok(value);
}

function metricIntensity(value: number, maxValue: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(maxValue) || maxValue <= 0 || value <= 0) return 0;
  return Math.max(0.08, Math.min(1, value / maxValue));
}

function periodDateLabel(dateValue: string): string {
  const [year, month, day] = dateValue.split("-");
  if (!year || !month || !day) return dateValue;
  return `${day}.${month}.${year}`;
}

function hourChartOption(data: ParkingTimeCell[], metric: MetricKey) {
  const metricDef = metricOptions.find((item) => item.key === metric) ?? metricOptions[0];
  const values = data.map((row) => metricValue(row, metric));
  return {
    color: [chartSeriesColor(domainColors.parking, 0)],
    tooltip: {
      ...chartTooltip(),
      formatter: (params: unknown) => {
        const item = Array.isArray(params) ? params[0] : params;
        const row = item as { dataIndex?: number; marker?: string };
        const source = data[Number(row.dataIndex ?? 0)] ?? data[0];
        return `<div style="min-width:190px">
          <div style="font-weight:750;margin-bottom:6px;color:${domainColors.ink}">${source.hourLabel}</div>
          <div style="display:flex;justify-content:space-between;gap:18px"><span>${row.marker ?? ""}${metricDef.label}</span><strong>${formatMetricValue(metricValue(source, metric), metric)}</strong></div>
          <div style="margin-top:5px;color:${domainColors.comparison};font-size:12px">${source.sessions} parkeringer · ${nok(source.paid)} kr · ${decimal(source.minutes / 60, 1)} timer</div>
        </div>`;
      },
    },
    grid: { top: 20, right: 12, bottom: 28, left: 44 },
    xAxis: {
      type: "category",
      data: data.map((row) => row.hourLabel.replace(":00", "")),
      axisTick: { show: false },
      axisLine: chartAxisLine(),
      axisLabel: chartAxisLabel(),
    },
    yAxis: {
      type: "value",
      name: metricDef.unit,
      nameTextStyle: chartAxisLabel(),
      axisLabel: chartAxisLabel({
        formatter: (value: number) => (metric === "sessions" ? `${Math.round(value)}` : `${Math.round(value)}`),
      }),
      splitLine: chartSplitLine(),
    },
    series: [
      {
        name: metricDef.label,
        type: "bar",
        data: values,
        barMaxWidth: 36,
        itemStyle: {
          color: chartSeriesColor(domainColors.parking, 0),
          borderRadius: [5, 5, 0, 0],
        },
      },
    ],
  };
}

function updateSearchParams(
  searchParams: URLSearchParams,
  setSearchParams: ReturnType<typeof useSearchParams>[1],
  entries: Record<string, string>,
) {
  const nextParams = new URLSearchParams(searchParams);
  Object.entries(entries).forEach(([key, value]) => {
    if (value) nextParams.set(key, value);
    else nextParams.delete(key);
  });
  setSearchParams(nextParams, { replace: true });
}

export default function ParkingTimeDistributionPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [metric, setMetric] = useState<MetricKey>("paid");
  const filterKey = searchParams.toString();
  const { data, loading, error } = useApiQuery(
    queryKeys.parkingTimeDistribution(filterKey),
    () => fetchParkingTimeDistribution(searchParams),
  );
  const themeKey = chartThemeKey();
  const chartOption = useMemo(() => (data ? hourChartOption(data.hours, metric) : null), [data, metric, themeKey]);

  if (loading) return <LoadingBlock />;
  if (error || !data || !chartOption) return <ErrorBlock error={error} />;

  const selectedMetric = metricOptions.find((item) => item.key === metric) ?? metricOptions[0];
  const maxValue = Number(data.max[metric] ?? 1);
  const periodOptions = data.period.options.map((item) => ({ label: item.label, value: item.key }));
  const periodKey = searchParams.get("period") || data.period.key;

  const weekdayColumns: ColumnsType<ParkingTimeWeekday> = [
    { title: "Ukedag", dataIndex: "weekday" },
    { title: "Dager", dataIndex: "days", align: "right" },
    { title: "Parkeringer", dataIndex: "sessions", align: "right", render: (value: number) => nok(value) },
    { title: "Omsetning", dataIndex: "paid", align: "right", render: (value: number) => `${nok(value)} kr` },
    { title: "Tid", dataIndex: "hours", align: "right", render: (_value, row) => `${decimal(row.minutes / 60, 1)} t` },
    { title: "Snitt kr/dag", dataIndex: "avgPaidPerDay", align: "right", render: (value: number) => `${nok(value)} kr` },
    { title: "Snitt stk/dag", dataIndex: "avgSessionsPerDay", align: "right", render: (value: number) => decimal(value, 1) },
    { title: "Snitt pr parkering", dataIndex: "avgPaidPerSession", align: "right", render: (value: number) => `${nok(value)} kr` },
  ];

  const topSlotColumns: ColumnsType<ParkingTimeCell> = [
    { title: "Ukedag", dataIndex: "weekday" },
    { title: "Tid", dataIndex: "hourLabel" },
    { title: "Omsetning", dataIndex: "paid", align: "right", render: (value: number) => `${nok(value)} kr` },
    { title: "Parkeringer", dataIndex: "sessions", align: "right", render: (value: number) => nok(value) },
    { title: "Tid", dataIndex: "minutes", align: "right", render: (value: number) => `${decimal(value / 60, 1)} t` },
    { title: "Snitt kr/dag", dataIndex: "avgPaidPerDay", align: "right", render: (value: number) => `${nok(value)} kr` },
  ];

  return (
    <Space direction="vertical" size={14} className="page-stack parking-time-page">
      <div className="parking-time-top">
        <div>
          <Typography.Text className="eyebrow">Parkering · tidspunkt</Typography.Text>
          <div className="parking-time-title">
            <strong>Ukedag og starttidspunkt</strong>
            <span>{periodDateLabel(data.period.dateFrom)} - {periodDateLabel(data.period.dateTo)} · {data.period.detail}</span>
          </div>
        </div>
        <Button icon={<ArrowLeftOutlined />}>
          <Link to="/parkering/oversikt">Parkering</Link>
        </Button>
      </div>

      <Card className="work-card parking-time-filter-card">
        <div className="parking-time-filter-row">
          <Segmented
            size="small"
            value={periodKey}
            options={periodOptions}
            onChange={(value) => {
              const nextPeriod = String(value);
              const entries: Record<string, string> = { period: nextPeriod };
              if (nextPeriod !== "custom") {
                entries.date_from = "";
                entries.date_to = "";
              } else {
                entries.date_from = data.period.dateFrom;
                entries.date_to = data.period.dateTo;
              }
              updateSearchParams(searchParams, setSearchParams, entries);
            }}
          />
          <div className="parking-time-date-range">
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

      <div className="parking-time-summary-grid">
        <Card className="summary-card tone-parking" title="Omsetning">
          <strong>{nok(data.summary.paid)} kr</strong>
          <span>{nok(data.summary.sessions)} parkeringer</span>
        </Card>
        <Card className="summary-card tone-parking" title="Parkeringstid">
          <strong>{decimal(data.summary.hours, 1)} t</strong>
          <span>{decimal(data.summary.avgMinutesPerSession, 0)} min snitt</span>
        </Card>
        <Card className="summary-card tone-parking" title="Snitt pr dag">
          <strong>{nok(data.summary.avgPaidPerDay)} kr</strong>
          <span>{decimal(data.summary.avgSessionsPerDay, 1)} parkeringer</span>
        </Card>
        <Card className="summary-card tone-parking" title="Snitt pr parkering">
          <strong>{nok(data.summary.avgPaidPerSession)} kr</strong>
          <span>{decimal(data.summary.avgMinutesPerSession, 0)} min</span>
        </Card>
      </div>

      <Card className="chart-card parking-time-heatmap-card" title="Fordeling ukedag / tidspunkt">
        <div className="parking-time-toolbar">
          <Typography.Text type="secondary">Viser {selectedMetric.label.toLowerCase()} fordelt etter starttidspunkt.</Typography.Text>
          <Segmented
            size="small"
            value={metric}
            options={metricOptions.map((item) => ({ label: item.label, value: item.key }))}
            onChange={(value) => setMetric(value as MetricKey)}
          />
        </div>
        <div className="parking-time-heatmap" style={{ ["--parking-time-columns" as string]: 24 }}>
          <div className="parking-time-corner" />
          {Array.from({ length: 24 }, (_, hour) => (
            <div className="parking-time-hour-head" key={`h-${hour}`}>{String(hour).padStart(2, "0")}</div>
          ))}
          {data.weekdays.map((weekday) => (
            <div className="parking-time-row" key={weekday.weekday}>
              <div className="parking-time-weekday">
                <strong>{weekday.weekday}</strong>
                <span>{weekday.days} dager</span>
              </div>
              {weekday.hours.map((cell) => {
                const value = metricValue(cell, metric);
                return (
                  <div
                    className="parking-time-cell"
                    key={`${weekday.weekday}-${cell.hour}`}
                    style={{ ["--heat-level" as string]: metricIntensity(value, maxValue) }}
                    title={`${weekday.weekday} ${cell.hourLabel}: ${formatMetricValue(value, metric)} | ${cell.sessions} parkeringer | ${nok(cell.paid)} kr | ${decimal(cell.minutes / 60, 1)} timer`}
                  >
                    <span>{value > 0 ? formatShortMetricValue(value, metric) : ""}</span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </Card>

      <Card className="chart-card parking-time-hour-card" title="Timeprofil">
        <AppChart option={chartOption} style={{ height: 260 }} lazyUpdate />
      </Card>

      <div className="parking-time-table-grid">
        <Card className="table-card" title="Ukedager">
          <Table
            size="small"
            rowKey="weekday"
            columns={weekdayColumns}
            dataSource={data.weekdays}
            pagination={false}
          />
        </Card>
        <Card className="table-card" title="Topp tidspunkt">
          <Table
            size="small"
            rowKey={(row) => `${row.weekday}-${row.hour}`}
            columns={topSlotColumns}
            dataSource={data.topSlots}
            pagination={false}
          />
        </Card>
      </div>
    </Space>
  );
}
