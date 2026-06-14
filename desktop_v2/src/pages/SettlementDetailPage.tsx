import { ArrowLeftOutlined, DownloadOutlined, FileTextOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link, useParams } from "react-router-dom";
import { fetchSettlementDetail, type SettlementField } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useAsyncData } from "../hooks";
import { modulePath } from "../moduleViews";

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
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

const fieldColumns: ColumnsType<SettlementField> = [
  {
    title: "Felt",
    dataIndex: "label",
    width: 210,
    render: (value, row) => (
      <Space direction="vertical" size={0}>
        <Typography.Text strong>{displayValue(value)}</Typography.Text>
        <Typography.Text type="secondary" className="settlement-field-key">
          {row.field}
        </Typography.Text>
      </Space>
    ),
  },
  {
    title: "Verdi",
    dataIndex: "value",
    render: (value) => <Typography.Text>{displayValue(value)}</Typography.Text>,
  },
  {
    title: "Kilde / regel",
    dataIndex: "source",
    render: (value, row) => (
      <Space direction="vertical" size={0}>
        <Typography.Text>{displayValue(value)}</Typography.Text>
        {row.note ? <Typography.Text type="secondary">{row.note}</Typography.Text> : null}
      </Space>
    ),
  },
];

function OriginalPreview({
  previewKind,
  previewUrl,
  filename,
}: {
  previewKind: string;
  previewUrl: string;
  filename: string;
}) {
  if (previewKind === "image") {
    return <img className="settlement-original-image" src={previewUrl} alt={filename} />;
  }
  if (previewKind === "pdf" || previewKind === "text") {
    return <iframe className="settlement-original-frame" src={previewUrl} title={filename} />;
  }
  return (
    <Alert
      type="info"
      showIcon
      message="Forhåndsvisning er ikke tilgjengelig for denne filtypen"
      description="Bruk Åpne original eller Last ned for å kontrollere skjemaet."
    />
  );
}

export default function SettlementDetailPage() {
  const { settlementId = "" } = useParams();
  const { data, loading, error } = useAsyncData(() => fetchSettlementDetail(settlementId), [settlementId]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={14} className="page-stack settlement-detail-page">
      <div className="settlement-detail-top">
        <div>
          <Typography.Text className="eyebrow">Oppgjør</Typography.Text>
          <Typography.Title level={2}>{data.title}</Typography.Title>
          <Typography.Text type="secondary">{data.subtitle}</Typography.Text>
        </div>
        <Space wrap>
          <Button href={data.original.previewUrl} target="_blank" rel="noreferrer" icon={<FileTextOutlined />}>
            Åpne original
          </Button>
          <Button href={data.original.downloadUrl} icon={<DownloadOutlined />}>
            Last ned
          </Button>
          <Link to={modulePath("parkering", "oppgjor")}>
            <Button icon={<ArrowLeftOutlined />}>Til oppgjør</Button>
          </Link>
        </Space>
      </div>

      <div className="vehicle-detail-card-grid settlement-card-grid">
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

      <Card
        className="work-card settlement-original-card"
        title="Originalskjema"
        extra={
          <Space size={8} wrap>
            <Tag>{data.original.contentType}</Tag>
            <Tag>{data.original.sizeLabel}</Tag>
          </Space>
        }
      >
        <OriginalPreview previewKind={data.original.previewKind} previewUrl={data.original.previewUrl} filename={data.original.filename} />
      </Card>

      {data.sections.map((section) => (
        <Card className="table-card settlement-field-card" title={section.title} key={section.title}>
          <Table
            rowKey={(row, index) => `${section.title}-${row.field}-${index}`}
            size="small"
            columns={fieldColumns}
            dataSource={section.rows}
            pagination={false}
            scroll={{ x: "max-content" }}
          />
        </Card>
      ))}

      <Card className="work-card settlement-raw-card" title="Rå importmetadata">
        <pre>{JSON.stringify(data.raw, null, 2)}</pre>
      </Card>
    </Space>
  );
}
