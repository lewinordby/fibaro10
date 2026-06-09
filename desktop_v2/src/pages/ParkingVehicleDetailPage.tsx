import { ArrowLeftOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link, useParams } from "react-router-dom";
import { fetchParkingVehicleDetail } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useAsyncData } from "../hooks";
import { modulePath } from "../moduleViews";

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") {
    return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 2 }).format(value);
  }
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

const parkingColumns: ColumnsType<Record<string, unknown>> = [
  { title: "Start", dataIndex: "start_time", sorter: (a, b) => String(a.start_time ?? "").localeCompare(String(b.start_time ?? "")), render: displayValue },
  { title: "Slutt", dataIndex: "end_time", render: displayValue },
  { title: "Beløp", dataIndex: "fee_inc_vat", align: "right", sorter: (a, b) => Number(a.fee_inc_vat ?? 0) - Number(b.fee_inc_vat ?? 0), render: (value) => `${displayValue(value)} kr` },
  { title: "Min", dataIndex: "parking_time_min", align: "right", sorter: (a, b) => Number(a.parking_time_min ?? 0) - Number(b.parking_time_min ?? 0), render: displayValue },
  { title: "Område", dataIndex: "parking_area", render: displayValue },
  { title: "Kilde", dataIndex: "source_system", render: displayValue },
  {
    title: "Status",
    dataIndex: "status",
    render: (value) => {
      const text = displayValue(value);
      const color = text.toLowerCase().includes("ongoing") ? "green" : "default";
      return <Tag color={color}>{text}</Tag>;
    },
  },
  {
    title: "Eier-sjekk",
    dataIndex: "owner_warning",
    render: (value) => (value ? <Tag color="gold">{displayValue(value)}</Tag> : "-"),
  },
];

export default function ParkingVehicleDetailPage() {
  const { plate = "" } = useParams();
  const { data, loading, error } = useAsyncData(() => fetchParkingVehicleDetail(plate), [plate]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={14} className="page-stack vehicle-detail-page">
      <div className="vehicle-detail-top">
        <div>
          <Typography.Text className="eyebrow">Kjøretøy</Typography.Text>
          <Typography.Title level={2}>
            {data.plate} · {data.title}
          </Typography.Title>
          <Typography.Text type="secondary">{data.subtitle}</Typography.Text>
        </div>
        <Link to={modulePath("parkering", "kjoretoy")}>
          <Button icon={<ArrowLeftOutlined />}>Til kjøretøy</Button>
        </Link>
      </div>

      {data.warnings.map((warning) => (
        <Alert key={warning} type="warning" showIcon message={warning} />
      ))}

      <div className="vehicle-detail-card-grid">
        {data.cards.map((card) => (
          <Card className={`vehicle-detail-card tone-${card.tone ?? "status"}`} key={card.title}>
            <span>{card.title}</span>
            <strong>
              {card.value}
              {card.unit ? <em>{card.unit}</em> : null}
            </strong>
            <small>{card.detail}</small>
          </Card>
        ))}
      </div>

      <Card className="work-card" title="Bil og eier">
        <div className="vehicle-field-grid">
          {data.fields.map((field) => (
            <div className="vehicle-field" key={field.label}>
              <span>{field.label}</span>
              <strong>{displayValue(field.value)}</strong>
              {field.detail ? <small>{field.detail}</small> : null}
            </div>
          ))}
        </div>
      </Card>

      <Card className="table-card" title="Alle parkeringer">
        <Table
          rowKey={(row, index) => String(row.id ?? index)}
          size="small"
          columns={parkingColumns}
          dataSource={data.sessions}
          pagination={{ pageSize: 50, showSizeChanger: true }}
          scroll={{ x: "max-content" }}
        />
      </Card>
    </Space>
  );
}
