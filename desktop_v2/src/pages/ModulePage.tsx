import { Card, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useParams } from "react-router-dom";
import { fetchModule, type ModuleCard, type ModuleTable } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useAsyncData } from "../hooks";

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Ja" : "Nei";
  if (typeof value === "number") {
    return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 2 }).format(value);
  }
  if (typeof value === "object") return JSON.stringify(value);
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}T/.test(text)) {
    const date = new Date(text);
    if (!Number.isNaN(date.getTime())) return date.toLocaleString("nb-NO");
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    const date = new Date(`${text}T00:00:00`);
    if (!Number.isNaN(date.getTime())) return date.toLocaleDateString("nb-NO");
  }
  return text;
}

function labelize(column: string): string {
  const labels: Record<string, string> = {
    bucket_start: "Tid",
    timestamp: "Tid",
    start_time: "Start",
    started_at: "Start",
    end_time: "Slutt",
    car_license_number: "Reg.nr",
    fee_inc_vat: "Beløp",
    paid_amount_kr: "Beløp",
    parking_time_min: "Min",
    duration_minutes: "Min",
    circuit_no: "Kurs",
    expected_power_w: "Forventet W",
    inntak_w: "Inntak W",
    differanse_beregnet_w: "Diff W",
    temp_avg_inne: "Inne",
    temp_ute: "Ute",
    humidity_kjeller: "Fukt kjeller",
    weather_text: "Vær",
  };
  return labels[column] ?? column.replaceAll("_", " ");
}

function moduleColumns(table: ModuleTable): ColumnsType<Record<string, unknown>> {
  return table.columns.map((column) => ({
    title: labelize(column),
    dataIndex: column,
    key: column,
    ellipsis: true,
    render: (value: unknown) => {
      if (typeof value === "boolean") {
        return <Tag color={value ? "green" : "default"}>{displayValue(value)}</Tag>;
      }
      if (column === "status" && typeof value === "string") {
        const normalized = value.toLowerCase();
        const color = normalized.includes("ongoing") || normalized.includes("ok") ? "green" : "default";
        return <Tag color={color}>{displayValue(value)}</Tag>;
      }
      return displayValue(value);
    },
  }));
}

function ModuleMetric({ card }: { card: ModuleCard }) {
  return (
    <Card className={`metric-card module-metric tone-${card.tone ?? "status"}`}>
      <Typography.Text className="metric-title">{card.title}</Typography.Text>
      <div className="metric-value-row">
        <span className="metric-value">{card.value}</span>
        {card.unit ? <span className="metric-unit">{card.unit}</span> : null}
      </div>
      <div className="metric-detail">{card.detail || "\u00a0"}</div>
    </Card>
  );
}

export default function ModulePage({ module, view: explicitView }: { module: string; view?: string }) {
  const params = useParams();
  const view = explicitView ?? params.view;
  const { data, loading, error } = useAsyncData(() => fetchModule(module, view), [module, view]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={18} className="page-stack">
      <section className="section-head">
        <div>
          <Typography.Text className="eyebrow">Desktop v2</Typography.Text>
          <Typography.Title level={1}>{data.title}</Typography.Title>
          <Typography.Paragraph>{data.subtitle}</Typography.Paragraph>
        </div>
      </section>

      <div className="metric-grid primary-grid">
        {data.cards.map((card) => (
          <ModuleMetric card={card} key={card.title} />
        ))}
      </div>

      <Card className="table-card module-table-card">
        <Tabs
          items={data.tables.map((table) => ({
            key: table.title,
            label: table.title,
            children: (
              <Table
                rowKey={(_, index) => `${table.title}-${index}`}
                size="small"
                columns={moduleColumns(table)}
                dataSource={table.rows}
                pagination={{ pageSize: 25, showSizeChanger: true }}
                scroll={{ x: "max-content" }}
              />
            ),
          }))}
        />
      </Card>
    </Space>
  );
}
