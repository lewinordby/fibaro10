import { ArrowLeftOutlined, DownloadOutlined, FileTextOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link, useParams } from "react-router-dom";
import { fetchSettlementDetail, type SettlementField, type SettlementSection } from "../api";
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

function confidenceTag(value?: number | null) {
  if (value === null || value === undefined) return <Typography.Text type="secondary">-</Typography.Text>;
  const percent = Math.round(value * 100);
  const color = percent >= 90 ? "green" : percent >= 70 ? "gold" : "volcano";
  return <Tag color={color}>{percent} %</Tag>;
}

const fieldColumns: ColumnsType<SettlementField> = [
  {
    title: "Felt",
    dataIndex: "label",
    width: 220,
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
    width: 180,
    render: (value) => <Typography.Text className="settlement-field-value">{displayValue(value)}</Typography.Text>,
  },
  {
    title: "Sikkerhet",
    dataIndex: "confidence",
    width: 100,
    render: (value) => confidenceTag(value),
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

function FieldSection({ section }: { section: SettlementSection }) {
  return (
    <Card className="table-card settlement-field-card" title={section.title}>
      <Table
        rowKey={(row, index) => `${section.title}-${row.field}-${index}`}
        size="small"
        columns={fieldColumns}
        dataSource={section.rows}
        pagination={false}
        scroll={{ x: "max-content" }}
      />
    </Card>
  );
}

export default function SettlementDetailPage() {
  const { settlementId = "" } = useParams();
  const { data, loading, error } = useAsyncData(() => fetchSettlementDetail(settlementId), [settlementId]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const primarySections = data.sections.filter((section) => ["Nøkkeltall fra skjema", "Kontroll mot Fibaro10"].includes(section.title));
  const secondarySections = data.sections.filter((section) => !["Nøkkeltall fra skjema", "Kontroll mot Fibaro10"].includes(section.title));

  return (
    <Space direction="vertical" size={14} className="page-stack settlement-detail-page">
      <div className="settlement-detail-top">
        <div>
          <Typography.Text className="eyebrow">Parkeringsoppgjør</Typography.Text>
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

      <div className="settlement-detail-grid">
        <Space direction="vertical" size={12} className="settlement-detail-main">
          {primarySections.map((section) => (
            <FieldSection section={section} key={section.title} />
          ))}
        </Space>

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
      </div>

      {secondarySections.map((section) => (
        <FieldSection section={section} key={section.title} />
      ))}

      <Card className="work-card settlement-raw-card" title="Rå importmetadata">
        <pre>{JSON.stringify(data.raw, null, 2)}</pre>
      </Card>
    </Space>
  );
}
