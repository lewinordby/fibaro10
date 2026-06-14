import { ArrowLeftOutlined, DownloadOutlined, FileTextOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Space, Tag, Typography } from "antd";
import { Link, useParams } from "react-router-dom";
import { fetchSettlementDetail, fetchSunSettlementDetail, type SettlementField, type SettlementSection } from "../api";
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

function numberValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value !== "string") return null;
  const parsed = Number(value.replace(/\s/g, "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function moneyValue(value: unknown): string {
  const numeric = numberValue(value);
  if (numeric === null) return displayValue(value);
  return `${new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 }).format(numeric)} kr`;
}

function signedMoneyValue(value: unknown): string {
  const numeric = numberValue(value);
  if (numeric === null) return "-";
  return `${numeric > 0 ? "+" : ""}${moneyValue(numeric)}`;
}

function confidenceTag(value?: number | null) {
  if (value === null || value === undefined) return null;
  const percent = Math.round(value * 100);
  const color = percent >= 90 ? "green" : percent >= 70 ? "gold" : "volcano";
  return <Tag color={color}>{percent} %</Tag>;
}

function sectionByTitle(sections: SettlementSection[], title: string) {
  const wanted = title.toLowerCase();
  const exact = sections.find((section) => section.title.toLowerCase() === wanted);
  if (exact) return exact;
  const partial = sections.find((section) => section.title.toLowerCase().includes(wanted));
  if (partial) return partial;
  if (wanted.includes("oppgj")) return sections.find((section) => section.title.toLowerCase().includes("oppgj"));
  if (wanted.includes("kontroll")) return sections.find((section) => section.title.toLowerCase().includes("kontroll"));
  if (wanted.includes("parser")) return sections.find((section) => section.title.toLowerCase().includes("parser"));
  return undefined;
}

function fieldByKey(section: SettlementSection | undefined, key: string) {
  return section?.rows.find((row) => row.field === key);
}

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

function valueStatus(row: SettlementField, showControl: boolean): "ok" | "warn" | "missing" | "plain" {
  if (!showControl) return row.value === null || row.value === undefined || row.value === "" ? "missing" : "plain";
  if (row.status === "ok") return "ok";
  if (row.status === "warn") return "warn";
  if (row.status === "missing") return "missing";
  return "plain";
}

function SettlementValueTile({ row, showControl = false }: { row: SettlementField; showControl?: boolean }) {
  const status = valueStatus(row, showControl);
  const hasControl = showControl && row.expected !== undefined;
  return (
    <div className={`settlement-value-tile ${status}`}>
      <div className="settlement-value-title">
        <span>{row.label}</span>
        {confidenceTag(row.confidence)}
      </div>
      <strong>{moneyValue(row.value)}</strong>
      {hasControl ? (
        <div className="settlement-value-control">
          <span>{row.expectedLabel || "Beregnet"} {moneyValue(row.expected)}</span>
          <b>Avvik {signedMoneyValue(row.difference)}</b>
        </div>
      ) : null}
    </div>
  );
}

type SettlementDomain = "parkering" | "soling";

export default function SettlementDetailPage({ domain = "parkering" }: { domain?: SettlementDomain }) {
  const { settlementId = "" } = useParams();
  const fetcher = domain === "soling" ? fetchSunSettlementDetail : fetchSettlementDetail;
  const { data, loading, error } = useAsyncData(() => fetcher(settlementId), [fetcher, settlementId]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const formSection = sectionByTitle(data.sections, "Oppgjørsformular");
  const parserSection = sectionByTitle(data.sections, "Parserkontroll");
  const amountRows = formSection?.rows.filter((row) => row.group === "amount") ?? [];
  const controlRows = formSection?.rows.filter((row) => row.group === "control") ?? [];
  const confidence = fieldByKey(parserSection, "confidence");

  return (
    <Space direction="vertical" size={12} className="page-stack settlement-detail-page">
      <div className="settlement-report-head compact">
        <div>
          <Typography.Text className="eyebrow">{domain === "soling" ? "Solingsoppgjør" : "Parkeringsoppgjør"}</Typography.Text>
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
          <Link to={modulePath(domain, "oppgjor")}>
            <Button icon={<ArrowLeftOutlined />}>Til oppgjør</Button>
          </Link>
        </Space>
      </div>

      <div className="settlement-document-layout">
        <aside className="settlement-read-panel">
          <Card
            className="settlement-read-card"
            title="Lest fra skjema"
            extra={
              <Space size={6}>
                <Tag>{data.original.sizeLabel}</Tag>
                {confidenceTag(numberValue(confidence?.value))}
              </Space>
            }
          >
            <div className="settlement-read-section">
              <Typography.Text className="eyebrow">Aktuelle beløp</Typography.Text>
              <div className="settlement-value-list">
                {amountRows.map((row) => (
                  <SettlementValueTile key={row.field} row={row} />
                ))}
              </div>
            </div>

            <div className="settlement-read-section">
              <Typography.Text className="eyebrow">Sumkontroll</Typography.Text>
              <div className="settlement-value-list">
                {controlRows.map((row) => (
                  <SettlementValueTile key={row.field} row={row} showControl />
                ))}
              </div>
            </div>
          </Card>
        </aside>

        <Card
          className="settlement-document-card focus"
          title="Originalskjema"
          extra={
            <Space size={8} wrap>
              <Tag>{data.original.contentType}</Tag>
              <Tag>{data.original.filename}</Tag>
            </Space>
          }
        >
          <OriginalPreview previewKind={data.original.previewKind} previewUrl={data.original.previewUrl} filename={data.original.filename} />
        </Card>
      </div>
    </Space>
  );
}
