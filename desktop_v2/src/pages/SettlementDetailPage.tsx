import { ArrowLeftOutlined, DownloadOutlined, FileTextOutlined } from "@ant-design/icons";
import { Alert, Button, Space, Tag, Typography } from "antd";
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

function SettlementValueRow({ row, showControl = false }: { row: SettlementField; showControl?: boolean }) {
  const status = valueStatus(row, showControl);
  const hasControl = showControl && row.expected !== undefined && row.expected !== null;
  return (
    <div className={`settlement-value-row ${status}${hasControl ? " has-control" : ""}`}>
      <div className="settlement-value-main">
        <div className="settlement-value-title">
          {showControl ? <span className="settlement-value-status" aria-hidden="true" /> : null}
          <span>{row.label}</span>
          {confidenceTag(row.confidence)}
        </div>
        {hasControl ? (
          <div className="settlement-value-control">
            <span>{row.expectedLabel || "Beregnet"} {moneyValue(row.expected)}</span>
            <b>Avvik {signedMoneyValue(row.difference)}</b>
          </div>
        ) : null}
      </div>
      <strong>{moneyValue(row.value)}</strong>
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
  const parser = fieldByKey(parserSection, "parser");
  const parserMethod = fieldByKey(parserSection, "method");
  const pages = fieldByKey(parserSection, "pages_count");

  return (
    <Space direction="vertical" size={12} className="page-stack settlement-detail-page">
      <div className="settlement-report-head compact">
        <div>
          <Typography.Text className="eyebrow">{domain === "soling" ? "Solingsoppgjør" : "Parkeringsoppgjør"}</Typography.Text>
          <Typography.Title level={2}>{data.title}</Typography.Title>
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
          <section className="settlement-read-card" aria-label="Leste verdier fra oppgjørsskjema">
            <div className="settlement-read-head">
              <div>
                <span>Lest fra skjema</span>
                <strong>{data.original.sizeLabel}</strong>
              </div>
              {confidenceTag(numberValue(confidence?.value))}
            </div>
            <div className="settlement-read-section">
              <div className="settlement-read-section-title">Beløp</div>
              <div className="settlement-value-list">
                {amountRows.map((row) => (
                  <SettlementValueRow key={row.field} row={row} showControl={row.expected !== undefined} />
                ))}
              </div>
            </div>

            <div className="settlement-read-section">
              <div className="settlement-read-section-title">Sumkontroll</div>
              <div className="settlement-value-list">
                {controlRows.map((row) => (
                  <SettlementValueRow key={row.field} row={row} showControl />
                ))}
              </div>
            </div>

            <dl className="settlement-file-facts">
              <div>
                <dt>Fil</dt>
                <dd title={data.original.filename}>{data.original.filename}</dd>
              </div>
              <div>
                <dt>Parser</dt>
                <dd>{displayValue(parser?.value)}</dd>
              </div>
              <div>
                <dt>Metode</dt>
                <dd>{displayValue(parserMethod?.value)}</dd>
              </div>
              <div>
                <dt>Sider</dt>
                <dd>{displayValue(pages?.value)}</dd>
              </div>
            </dl>
          </section>
        </aside>

        <section className="settlement-document-card focus" aria-label="Originalskjema">
          <div className="settlement-document-toolbar">
            <strong>Originalskjema</strong>
          </div>
          <OriginalPreview previewKind={data.original.previewKind} previewUrl={data.original.previewUrl} filename={data.original.filename} />
        </section>
      </div>
    </Space>
  );
}
