import { Button, Card, Col, DatePicker, Row, Space, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { useMemo, useState } from "react";
import dayjs from "dayjs";
import "dayjs/locale/nb";
import { fetchRevenueMonth, type RevenueDay } from "../api";
import { AppChart } from "../components/AppChart";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { domainColors } from "../domainColors";
import { decimal, nok } from "../format";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";

dayjs.locale("nb");

const columns: ColumnsType<RevenueDay> = [
  {
    title: "Dag",
    dataIndex: "dayLabel",
    sorter: (left, right) => left.day.localeCompare(right.day),
    render: (_, row) => (
      <span className={row.isToday ? "today-cell" : undefined}>
        {row.dayLabel} · {row.weekday}
      </span>
    ),
  },
  { title: "Soling", dataIndex: "sol", align: "right", sorter: (left, right) => left.sol - right.sol, render: (value) => `${nok(value)} kr` },
  { title: "Solinger", dataIndex: "solCount", align: "right", sorter: (left, right) => left.solCount - right.solCount },
  { title: "Parkering", dataIndex: "parking", align: "right", sorter: (left, right) => left.parking - right.parking, render: (value) => `${nok(value)} kr` },
  { title: "Parkeringer", dataIndex: "parkingCount", align: "right", sorter: (left, right) => left.parkingCount - right.parkingCount },
  { title: "Total", dataIndex: "total", align: "right", sorter: (left, right) => left.total - right.total, render: (value) => <strong>{nok(value)} kr</strong> },
];

function countLabel(value: number, singular: string, plural: string): string {
  return `${value} ${value === 1 ? singular : plural}`;
}

function tooltipMarker(color: string): string {
  return `<span style="display:inline-block;width:9px;height:9px;margin-right:7px;border-radius:50%;background:${color};"></span>`;
}

export default function RevenueMonthPage() {
  const [month, setMonth] = useState<string | undefined>(undefined);
  const { data, loading, error } = useApiQuery(queryKeys.revenueMonth(month), () => fetchRevenueMonth(month));

  const chartOption = useMemo(() => {
    const rows = data?.rows ?? [];
    return {
      color: [domainColors.sun2, domainColors.parking],
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "rgba(255,255,255,0.96)",
        borderColor: "#dbe3ee",
        borderWidth: 1,
        textStyle: { color: "#111827", fontSize: 12 },
        extraCssText: "box-shadow:0 12px 28px rgba(15,23,42,.12);border-radius:8px;",
        formatter: (params: unknown) => {
          const items = Array.isArray(params) ? params : [params];
          const firstItem = items[0] as { dataIndex?: number } | undefined;
          const row = rows[firstItem?.dataIndex ?? -1];
          if (!row) return "";
          return `
            <div style="min-width:190px">
              <div style="margin-bottom:6px;font-weight:700;color:#111827">${row.dayLabel} · ${row.weekday}</div>
              <div style="display:flex;justify-content:space-between;gap:16px;line-height:1.65">
                <span>${tooltipMarker(domainColors.sun2)}Soling</span>
                <strong>${nok(row.sol)} kr</strong>
              </div>
              <div style="margin:0 0 4px 16px;color:#6b7280;font-size:12px">${countLabel(row.solCount, "soling", "solinger")}</div>
              <div style="display:flex;justify-content:space-between;gap:16px;line-height:1.65">
                <span>${tooltipMarker(domainColors.parking)}Parkering</span>
                <strong>${nok(row.parking)} kr</strong>
              </div>
              <div style="margin:0 0 7px 16px;color:#6b7280;font-size:12px">${countLabel(row.parkingCount, "parkering", "parkeringer")}</div>
              <div style="display:flex;justify-content:space-between;gap:16px;padding-top:7px;border-top:1px solid #e5e7eb;line-height:1.6">
                <span style="font-weight:700">Sum</span>
                <strong>${nok(row.total)} kr</strong>
              </div>
            </div>
          `;
        },
      },
      legend: {
        top: 0,
        icon: "roundRect",
        itemWidth: 16,
        itemHeight: 8,
        textStyle: { color: "#475569", fontSize: 12, fontWeight: 650 },
      },
      grid: { top: 48, left: 12, right: 16, bottom: 34, containLabel: true },
      xAxis: {
        type: "category",
        data: rows.map((row) => row.dayLabel),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        axisLabel: { interval: 0, rotate: rows.length > 24 ? 45 : 0, color: "#64748b", fontSize: 11 },
      },
      yAxis: {
        type: "value",
        axisLabel: { formatter: (value: number) => `${Math.round(value / 1000)}k` },
        splitLine: { lineStyle: { color: "#e8edf4" } },
      },
      series: [
        {
          name: "Soling",
          type: "bar",
          stack: "total",
          data: rows.map((row) => row.sol),
          barMaxWidth: 30,
          itemStyle: { borderRadius: [4, 4, 0, 0] },
          emphasis: { focus: "series" },
        },
        {
          name: "Parkering",
          type: "bar",
          stack: "total",
          data: rows.map((row) => row.parking),
          barMaxWidth: 30,
          itemStyle: { borderRadius: [4, 4, 0, 0] },
          emphasis: { focus: "series" },
        },
      ],
    };
  }, [data]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const summary = data.summary;
  const monthValue = dayjs(`${summary.month}-01`);

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-revenue-page">
      <div className="status-toolbar">
        <div>
          <Typography.Text className="eyebrow">Omsetning</Typography.Text>
          <div className="status-toolbar-title">{summary.label}</div>
        </div>
        <Space className="status-toolbar-actions">
          <Button size="small" icon={<LeftOutlined />} onClick={() => setMonth(summary.previousMonth)}>
            Forrige
          </Button>
          <DatePicker
            size="small"
            picker="month"
            value={monthValue}
            format="MMMM YYYY"
            onChange={(value) => setMonth(value ? value.format("YYYY-MM") : undefined)}
            allowClear={false}
          />
          <Button size="small" onClick={() => setMonth(summary.currentMonth)}>Denne måneden</Button>
          <Button size="small" icon={<RightOutlined />} onClick={() => setMonth(summary.nextMonth)}>
            Neste
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col span={4}>
          <Card className="summary-card tone-revenue" title="Total">
            <strong>{nok(summary.total)} kr</strong>
          </Card>
        </Col>
        <Col span={4}>
          <Card className="summary-card tone-sun2" title="Soling">
            <strong>{nok(summary.sol)} kr</strong>
            <span>{summary.solCount} solinger</span>
          </Card>
        </Col>
        <Col span={4}>
          <Card className="summary-card tone-parking" title="Parkering">
            <strong>{nok(summary.parking)} kr</strong>
            <span>{summary.parkingCount} parkeringer</span>
          </Card>
        </Col>
        <Col span={4}>
          <Card className="summary-card" title="Snitt per dag">
            <strong>{nok(summary.averagePerDay)} kr</strong>
            <span>{summary.averageDayCount ? `${summary.averageDayCount} dager` : "Ingen dager"}</span>
          </Card>
        </Col>
        <Col span={4}>
          <Card className="summary-card" title="Beste dag">
            <strong>{summary.topDay ? `${nok(summary.topDay.total)} kr` : "-"}</strong>
            <span>{summary.topDay?.dayLabel ?? ""}</span>
          </Card>
        </Col>
        <Col span={4}>
          <Card className="summary-card" title="I dag">
            <strong>{summary.todayRow ? `${nok(summary.todayRow.total)} kr` : "-"}</strong>
            <span>{summary.todayRow ? `${summary.todayRow.solCount + summary.todayRow.parkingCount} hendelser` : ""}</span>
          </Card>
        </Col>
      </Row>

      <Card className="chart-card">
        <AppChart option={chartOption} style={{ height: 430 }} />
      </Card>

      <Card className="table-card">
        <Table
          rowKey="day"
          size="middle"
          columns={columns}
          dataSource={data.rows}
          pagination={false}
          locale={{ emptyText: "Ingen omsetningsrader å vise" }}
          rowClassName={(row) => [row.isToday ? "row-today" : "", row.isWeekend ? "row-weekend" : ""].join(" ")}
          summary={(rows) => (
            <Table.Summary fixed>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0}>
                  <strong>Sum</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={1} align="right">
                  {nok(rows.reduce((sum, row) => sum + row.sol, 0))} kr
                </Table.Summary.Cell>
                <Table.Summary.Cell index={2} align="right">
                  {rows.reduce((sum, row) => sum + row.solCount, 0)}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={3} align="right">
                  {nok(rows.reduce((sum, row) => sum + row.parking, 0))} kr
                </Table.Summary.Cell>
                <Table.Summary.Cell index={4} align="right">
                  {rows.reduce((sum, row) => sum + row.parkingCount, 0)}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right">
                  <strong>{nok(rows.reduce((sum, row) => sum + row.total, 0))} kr</strong>
                </Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
        <Typography.Text type="secondary" className="table-note">
          Høyeste dagsomsetning: {decimal(summary.maxTotal, 0)} kr.
        </Typography.Text>
      </Card>
    </Space>
  );
}
