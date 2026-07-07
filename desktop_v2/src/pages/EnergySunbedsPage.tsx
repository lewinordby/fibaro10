import { Alert, Card, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { EnergySunbedObservation, EnergySunbedRoom, ModuleResponse } from "../api";
import { chartAxisLabel, chartAxisLine, chartColors, chartSplitLine, chartTooltip } from "../chartTheme";
import { AppChart } from "../components/AppChart";
import { domainColors } from "../domainColors";
import { decimal } from "../format";
import { ModuleMetric } from "./module/ModuleMetric";
import "../styles/energy.css";

function numberText(value: number | null | undefined, digits = 0) {
  return decimal(value, digits);
}

function wattText(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "-";
  return `${numberText(value)} W`;
}

function kwhText(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "-";
  return `${numberText(value, 2)} kWh`;
}

function timeText(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("nb-NO", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function confidenceColor(value: string) {
  const normalized = value.toLocaleLowerCase("nb-NO");
  if (normalized.includes("høy")) return "green";
  if (normalized.includes("lav")) return "red";
  return "gold";
}

function effectChartOption(rooms: EnergySunbedRoom[]) {
  return {
    tooltip: chartTooltip(),
    grid: { top: 28, left: 54, right: 18, bottom: 42 },
    xAxis: {
      type: "category",
      data: rooms.map((room) => room.label),
      axisTick: { show: false },
      axisLabel: chartAxisLabel(),
      axisLine: chartAxisLine(),
    },
    yAxis: {
      type: "value",
      name: "W",
      nameTextStyle: { color: chartColors.axisText, fontSize: 11 },
      axisLabel: chartAxisLabel(),
      splitLine: chartSplitLine(),
    },
    series: [
      {
        name: "Estimert W",
        type: "bar",
        barMaxWidth: 38,
        itemStyle: { color: domainColors.sun2, borderRadius: [4, 4, 0, 0] },
        data: rooms.map((room) => Math.round(Number(room.estimate_w ?? 0))),
      },
    ],
  };
}

function PowerBar({ value, max }: { value?: number | null; max: number }) {
  const width = max > 0 ? Math.max(2, Math.min(100, (Number(value ?? 0) / max) * 100)) : 0;
  return (
    <div className="sunbed-power-cell">
      <span>{wattText(value)}</span>
      <div className="sunbed-power-track">
        <div className="sunbed-power-fill" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

export default function EnergySunbedsPage({ data }: { data: ModuleResponse }) {
  const sunbeds = data.energySunbeds;
  if (!sunbeds) return null;
  const summary = sunbeds.summary;
  const maxPower = sunbeds.maxPower || Math.max(...sunbeds.rooms.map((room) => Number(room.estimate_w ?? 0)), 1);

  const roomColumns: ColumnsType<EnergySunbedRoom> = [
    {
      title: "Rom",
      dataIndex: "label",
      key: "label",
      fixed: "left",
      render: (value, row) => (
        <div className="sunbed-room-name">
          <strong>{value}</strong>
          <span>{row.sun2_bed_id || "-"}{row.bed_model ? ` · ${row.bed_model}` : ""}</span>
        </div>
      ),
    },
    {
      title: "Estimat",
      dataIndex: "estimate_w",
      key: "estimate_w",
      sorter: (a, b) => Number(a.estimate_w ?? 0) - Number(b.estimate_w ?? 0),
      render: (value) => <PowerBar value={Number(value)} max={maxPower} />,
    },
    {
      title: "Snitt",
      dataIndex: "avg_w",
      key: "avg_w",
      align: "right",
      sorter: (a, b) => Number(a.avg_w ?? 0) - Number(b.avg_w ?? 0),
      render: (value) => wattText(Number(value)),
    },
    {
      title: "Normalområde",
      key: "range",
      align: "right",
      render: (_value, row) => `${wattText(row.p25_w)} - ${wattText(row.p75_w)}`,
    },
    {
      title: "Prøver",
      dataIndex: "samples_count",
      key: "samples_count",
      align: "right",
      sorter: (a, b) => Number(a.samples_count ?? 0) - Number(b.samples_count ?? 0),
    },
    {
      title: "Solinger",
      dataIndex: "sessions_count",
      key: "sessions_count",
      align: "right",
      sorter: (a, b) => Number(a.sessions_count ?? 0) - Number(b.sessions_count ?? 0),
    },
    {
      title: "15 min",
      dataIndex: "kwh_15_min",
      key: "kwh_15_min",
      align: "right",
      render: (value) => kwhText(Number(value)),
    },
    {
      title: "Målt kWh",
      dataIndex: "estimated_kwh",
      key: "estimated_kwh",
      align: "right",
      sorter: (a, b) => Number(a.estimated_kwh ?? 0) - Number(b.estimated_kwh ?? 0),
      render: (value) => kwhText(Number(value)),
    },
    {
      title: "Tillit",
      dataIndex: "confidence",
      key: "confidence",
      render: (value) => <Tag color={confidenceColor(String(value || ""))}>{String(value || "-")}</Tag>,
    },
  ];

  const observationColumns: ColumnsType<EnergySunbedObservation> = [
    { title: "Tid", dataIndex: "start", key: "start", render: (value) => timeText(String(value || "")) },
    { title: "Rom", dataIndex: "label", key: "label" },
    { title: "Varighet", dataIndex: "duration_minutes", key: "duration_minutes", align: "right", render: (value) => `${numberText(Number(value))} min` },
    { title: "Prøver", dataIndex: "samples_count", key: "samples_count", align: "right" },
    { title: "Estimert", dataIndex: "avg_w", key: "avg_w", align: "right", render: (value) => wattText(Number(value)) },
    { title: "Diff målt", dataIndex: "avg_observed_w", key: "avg_observed_w", align: "right", render: (value) => wattText(Number(value)) },
    { title: "Baseline", dataIndex: "avg_baseline_w", key: "avg_baseline_w", align: "right", render: (value) => wattText(Number(value)) },
    { title: "kWh", dataIndex: "estimated_kwh", key: "estimated_kwh", align: "right", render: (value) => kwhText(Number(value)) },
  ];

  return (
    <Space direction="vertical" size={14} className="page-stack energy-sunbeds-page">
      {data.cards.length ? (
        <div className="metric-grid primary-grid">
          {data.cards.map((card) => (
            <ModuleMetric card={card} key={card.title} module="energi" view="forbruk-per-seng" />
          ))}
        </div>
      ) : null}

      <Card className="work-card energy-sunbeds-method">
        <div>
          <Typography.Title level={4}>Metode</Typography.Title>
          <Typography.Paragraph>
            Beregningen bruker SUN2-timer mot HC3 differanseforbruk. Målinger brukes bare når nøyaktig én solseng er aktiv,
            etter {summary.warmup_minutes} min oppvarming og før siste {summary.stop_before_end_minutes} min av økten.
            Andre senger må ha vært stoppet i minst {summary.cooldown_minutes} min. Takvifte trekkes fra med{" "}
            {wattText(summary.roof_exhaust_adjustment_w)} når den er registrert på.
          </Typography.Paragraph>
        </div>
        <div className="sunbed-method-facts">
          <span>Periode {sunbeds.dateFrom} - {sunbeds.dateTo}</span>
          <span>{numberText(summary.energy_samples_total)} energisamples</span>
          <span>{numberText(summary.baseline_samples)} baseline-samples</span>
          <span>{numberText(summary.sample_interval_seconds)} sek sampleintervall</span>
        </div>
      </Card>

      {!sunbeds.rooms.length ? (
        <Alert
          type="warning"
          showIcon
          message="Ingen rene målepunkter i valgt periode"
          description={`Prøv en lengre periode. Maks ${sunbeds.maxDays} dager per beregning.`}
        />
      ) : (
        <Card className="chart-card energy-sunbeds-chart" title="Estimert effekt per solseng">
          <AppChart option={effectChartOption(sunbeds.rooms)} style={{ height: 300 }} />
        </Card>
      )}

      <Card className="table-card module-table-card energy-sunbeds-table" title="Estimert effekt per seng">
        <Table
          size="small"
          rowKey={(row) => row.room_id || row.label}
          columns={roomColumns}
          dataSource={sunbeds.rooms}
          pagination={false}
          scroll={{ x: "max-content" }}
        />
      </Card>

      <Card className="table-card module-table-card energy-sunbeds-table" title="Siste rene solinger">
        <Table
          size="small"
          rowKey={(row) => String(row.session_id)}
          columns={observationColumns}
          dataSource={sunbeds.observations}
          pagination={{ pageSize: 12, showSizeChanger: false }}
          scroll={{ x: "max-content" }}
        />
      </Card>
    </Space>
  );
}
