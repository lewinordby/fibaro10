import ReactECharts from "echarts-for-react";
import { Button, Card, Col, DatePicker, Row, Space, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { useMemo, useState } from "react";
import dayjs from "dayjs";
import "dayjs/locale/nb";
import { fetchRevenueMonth, type RevenueDay } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { decimal, nok } from "../format";
import { useAsyncData } from "../hooks";

dayjs.locale("nb");

const columns: ColumnsType<RevenueDay> = [
  {
    title: "Dag",
    dataIndex: "dayLabel",
    render: (_, row) => (
      <span className={row.isToday ? "today-cell" : undefined}>
        {row.dayLabel} · {row.weekday}
      </span>
    ),
  },
  { title: "Soling", dataIndex: "sol", align: "right", render: (value) => `${nok(value)} kr` },
  { title: "Solinger", dataIndex: "solCount", align: "right" },
  { title: "Parkering", dataIndex: "parking", align: "right", render: (value) => `${nok(value)} kr` },
  { title: "Parkeringer", dataIndex: "parkingCount", align: "right" },
  { title: "Total", dataIndex: "total", align: "right", render: (value) => <strong>{nok(value)} kr</strong> },
];

export default function RevenueMonthPage() {
  const [month, setMonth] = useState<string | undefined>(undefined);
  const { data, loading, error } = useAsyncData(() => fetchRevenueMonth(month), [month]);

  const chartOption = useMemo(() => {
    const rows = data?.rows ?? [];
    return {
      color: ["#dc2626", "#2563eb"],
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        valueFormatter: (value: number) => `${nok(value)} kr`,
      },
      legend: { top: 0 },
      grid: { top: 42, left: 42, right: 18, bottom: 34 },
      xAxis: {
        type: "category",
        data: rows.map((row) => row.dayLabel),
        axisLabel: { interval: 0, rotate: rows.length > 24 ? 45 : 0 },
      },
      yAxis: {
        type: "value",
        axisLabel: { formatter: (value: number) => `${Math.round(value / 1000)}k` },
        splitLine: { lineStyle: { color: "#e5e7eb" } },
      },
      series: [
        {
          name: "Soling",
          type: "bar",
          stack: "total",
          data: rows.map((row) => row.sol),
          barMaxWidth: 30,
        },
        {
          name: "Parkering",
          type: "bar",
          stack: "total",
          data: rows.map((row) => row.parking),
          barMaxWidth: 30,
        },
      ],
    };
  }, [data]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const summary = data.summary;
  const monthValue = dayjs(`${summary.month}-01`);

  return (
    <Space direction="vertical" size={18} className="page-stack">
      <section className="section-head">
        <div>
          <Typography.Text className="eyebrow">Omsetning</Typography.Text>
          <Typography.Title level={1}>{summary.label}</Typography.Title>
        </div>
        <Space>
          <Button icon={<LeftOutlined />} onClick={() => setMonth(summary.previousMonth)}>
            Forrige
          </Button>
          <DatePicker
            picker="month"
            value={monthValue}
            format="MMMM YYYY"
            onChange={(value) => setMonth(value ? value.format("YYYY-MM") : undefined)}
            allowClear={false}
          />
          <Button onClick={() => setMonth(summary.currentMonth)}>Denne måneden</Button>
          <Button icon={<RightOutlined />} onClick={() => setMonth(summary.nextMonth)}>
            Neste
          </Button>
        </Space>
      </section>

      <Row gutter={[16, 16]}>
        <Col span={4}>
          <Card className="summary-card" title="Total">
            <strong>{nok(summary.total)} kr</strong>
          </Card>
        </Col>
        <Col span={4}>
          <Card className="summary-card" title="Soling">
            <strong>{nok(summary.sol)} kr</strong>
            <span>{summary.solCount} solinger</span>
          </Card>
        </Col>
        <Col span={4}>
          <Card className="summary-card" title="Parkering">
            <strong>{nok(summary.parking)} kr</strong>
            <span>{summary.parkingCount} parkeringer</span>
          </Card>
        </Col>
        <Col span={4}>
          <Card className="summary-card" title="Snitt per dag">
            <strong>{nok(summary.total / Math.max(1, data.rows.length))} kr</strong>
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
        <ReactECharts option={chartOption} style={{ height: 430 }} />
      </Card>

      <Card className="table-card">
        <Table
          rowKey="day"
          size="middle"
          columns={columns}
          dataSource={data.rows}
          pagination={false}
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
