import { ArrowLeftOutlined, DownloadOutlined, FileTextOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Space, Tag, Typography } from "antd";
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

function percentValue(value: unknown): string {
  const numeric = numberValue(value);
  if (numeric === null) return "-";
  return `${Math.round(numeric * 100)} %`;
}

function verdictFor(diffNumber: number | null) {
  if (diffNumber === null) {
    return {
      tone: "empty",
      label: "Kontroll mangler",
      detail: "Perioden eller skjematallene mangler, så Fibaro10 kan ikke kontrollere oppgjøret automatisk.",
    };
  }
  if (Math.abs(diffNumber) <= 1000) {
    return {
      tone: "ok",
      label: "Ser konsistent ut",
      detail: "Største kildeavvik mellom Fibaro10 og skjemaet er innenfor kontrollgrensen.",
    };
  }
  return {
    tone: "warn",
    label: "Krever manuell sjekk",
    detail: "Avviket er større enn kontrollgrensen. Kontroller perioden, kildefeltet og importerte parkeringer.",
  };
}

function confidenceTag(value?: number | null) {
  if (value === null || value === undefined) return null;
  const percent = Math.round(value * 100);
  const color = percent >= 90 ? "green" : percent >= 70 ? "gold" : "volcano";
  return <Tag color={color}>{percent} %</Tag>;
}

function sectionByTitle(sections: SettlementSection[], title: string) {
  return sections.find((section) => section.title === title);
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

function ReportMetric({ label, value, detail, tone }: { label: string; value: string; detail: string; tone?: string }) {
  return (
    <div className={`settlement-report-metric tone-${tone ?? "status"}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function VerdictPanel({
  label,
  detail,
  tone,
  diff,
  fibaro,
  schema,
}: {
  label: string;
  detail: string;
  tone: string;
  diff: unknown;
  fibaro: unknown;
  schema: unknown;
}) {
  return (
    <div className={`settlement-verdict settlement-verdict-${tone}`}>
      <div>
        <span>Kontrollresultat</span>
        <strong>{label}</strong>
        <p>{detail}</p>
      </div>
      <div className="settlement-verdict-values">
        <FocusPair label="Fibaro10" value={moneyValue(fibaro)} />
        <FocusPair label="Skjema" value={moneyValue(schema)} />
        <FocusPair label="Avvik" value={signedMoneyValue(diff)} />
      </div>
    </div>
  );
}

function FocusPair({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formStatusTag(row: SettlementField) {
  if (row.group === "amount" && row.expected === undefined) {
    return row.confidence === null || row.confidence === undefined ? null : confidenceTag(row.confidence);
  }
  if (row.status === "ok") return <Tag color="green">Stemmer</Tag>;
  if (row.status === "warn") return <Tag color="volcano">Avvik</Tag>;
  return <Tag>Ikke kontrollert</Tag>;
}

function SettlementFormRow({ row }: { row: SettlementField }) {
  const hasExpected = row.expected !== undefined;
  return (
    <div className={`settlement-form-row ${hasExpected ? "with-source-control" : ""} settlement-form-row-${row.status ?? "plain"}`}>
      <div className="settlement-form-label">
        <strong>{row.label}</strong>
        <span>{row.field}</span>
      </div>
      <div className="settlement-form-value">
        <span>Lest verdi</span>
        <strong>{moneyValue(row.value)}</strong>
      </div>
      {hasExpected ? (
        <>
          <div className="settlement-form-value">
            <span>{row.expectedLabel || "Beregnet"}</span>
            <strong>{moneyValue(row.expected)}</strong>
            {row.expectedDetail ? <small>{row.expectedDetail}</small> : null}
          </div>
          <div className="settlement-form-value">
            <span>Avvik</span>
            <strong>{signedMoneyValue(row.difference)}</strong>
            {row.expectedSource ? <small>{row.expectedSource}</small> : null}
          </div>
        </>
      ) : null}
      <div className="settlement-form-state">{formStatusTag(row)}</div>
    </div>
  );
}

function SettlementSimpleForm({ section }: { section?: SettlementSection }) {
  if (!section) return null;
  const amountRows = section.rows.filter((row) => row.group === "amount");
  const controlRows = section.rows.filter((row) => row.group === "control");
  return (
    <Card className="settlement-simple-form" title="Enkelt oppgjørsformular" extra={<Tag color="blue">4 aktuelle beløp</Tag>}>
      <div className="settlement-simple-form-grid">
        <div>
          <div className="settlement-simple-form-head">
            <Typography.Text className="eyebrow">Aktuelle beløp</Typography.Text>
            <Typography.Paragraph>Feltene under er de operative verdiene fra skjemaet.</Typography.Paragraph>
          </div>
          <div className="settlement-form-list amount">
            {amountRows.map((row) => (
              <SettlementFormRow key={row.field} row={row} />
            ))}
          </div>
        </div>
        <div>
          <div className="settlement-simple-form-head">
            <Typography.Text className="eyebrow">Kontrollsummer</Typography.Text>
            <Typography.Paragraph>Summer brukes kun for å sjekke at PDF-innlesingen traff riktig.</Typography.Paragraph>
          </div>
          <div className="settlement-form-list control">
            {controlRows.map((row) => (
              <SettlementFormRow key={row.field} row={row} />
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

function FieldList({ section, compact = false }: { section?: SettlementSection; compact?: boolean }) {
  if (!section) return null;
  return (
    <Card className={`settlement-field-card ${compact ? "compact" : ""}`} title={section.title}>
      <div className="settlement-field-list">
        {section.rows.map((row) => (
          <div className="settlement-field-row" key={`${section.title}-${row.field}`}>
            <div className="settlement-field-label">
              <strong>{row.label}</strong>
              <span>{row.field}</span>
            </div>
            <div className="settlement-field-data">
              <div className="settlement-field-value-line">
                <strong>{displayValue(row.value)}</strong>
                {confidenceTag(row.confidence)}
              </div>
              {row.note ? <p>{row.note}</p> : null}
              <small>{row.source}</small>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function SettlementDetailPage() {
  const { settlementId = "" } = useParams();
  const { data, loading, error } = useAsyncData(() => fetchSettlementDetail(settlementId), [settlementId]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const schemaSection = sectionByTitle(data.sections, "Nøkkeltall fra skjema");
  const formSection = sectionByTitle(data.sections, "Oppgjørsformular");
  const controlSection = sectionByTitle(data.sections, "Kontroll mot Fibaro10");
  const periodSection = sectionByTitle(data.sections, "Tolket periode");
  const emailSection = sectionByTitle(data.sections, "E-post og vedlegg");
  const parserSection = sectionByTitle(data.sections, "Parserkontroll");
  const flowbirdPaid = fieldByKey(controlSection, "flowbird_source_paid_ex_vat");
  const flowbirdCount = fieldByKey(controlSection, "flowbird_source_count");
  const grossCoinCard = fieldByKey(controlSection, "gross_coin_card_ex_vat");
  const flowbirdDiff = fieldByKey(controlSection, "flowbird_source_diff_ex_vat");
  const easyparkPaid = fieldByKey(controlSection, "easypark_source_paid_ex_vat");
  const easyparkCount = fieldByKey(controlSection, "easypark_source_count");
  const schemaEasypark = fieldByKey(controlSection, "easypark_ex_vat");
  const easyparkDiff = fieldByKey(controlSection, "easypark_source_diff_ex_vat");
  const payout = fieldByKey(schemaSection, "payout_inc_vat");
  const confidence = fieldByKey(parserSection, "confidence");
  const flowbirdDiffNumber = numberValue(flowbirdDiff?.value);
  const easyparkDiffNumber = numberValue(easyparkDiff?.value);
  const diffNumber =
    [flowbirdDiffNumber, easyparkDiffNumber]
      .filter((value): value is number => value !== null)
      .sort((a, b) => Math.abs(b) - Math.abs(a))[0] ?? null;
  const primaryDiff = Math.abs(flowbirdDiffNumber ?? 0) >= Math.abs(easyparkDiffNumber ?? 0) ? flowbirdDiff : easyparkDiff;
  const verdict = verdictFor(diffNumber);

  return (
    <Space direction="vertical" size={14} className="page-stack settlement-detail-page">
      <div className="settlement-report-head">
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

      <div className="settlement-report-strip">
        <ReportMetric label="Til utbetaling" value={moneyValue(payout?.value)} detail="Sluttsum fra Park Nordic" tone="revenue" />
        <ReportMetric label="Flowbird Fibaro10" value={moneyValue(flowbirdPaid?.value)} detail={`${displayValue(flowbirdCount?.value)} parkeringer`} tone="parking" />
        <ReportMetric label="Skjema mynt/kort" value={moneyValue(grossCoinCard?.value)} detail="Brutto eks. mva" tone="status" />
        <ReportMetric label="EasyPark Fibaro10" value={moneyValue(easyparkPaid?.value)} detail={`${displayValue(easyparkCount?.value)} parkeringer`} tone="parking" />
        <ReportMetric label="Skjema EasyPark" value={moneyValue(schemaEasypark?.value)} detail="Eks. mva" tone="status" />
        <ReportMetric
          label="Største avvik"
          value={signedMoneyValue(primaryDiff?.value)}
          detail="Skjema minus Fibaro10"
          tone={diffNumber !== null && Math.abs(diffNumber) > 1000 ? "revenue" : "energy"}
        />
        <ReportMetric label="Tolkesikkerhet" value={percentValue(confidence?.value)} detail="Parserkontroll" tone="status" />
      </div>

      <VerdictPanel
        label={verdict.label}
        detail={verdict.detail}
        tone={verdict.tone}
        diff={primaryDiff?.value}
        fibaro={easyparkPaid?.value}
        schema={schemaEasypark?.value}
      />

      <SettlementSimpleForm section={formSection} />

      <div className="settlement-report-layout">
        <div className="settlement-report-main">
          <FieldList section={controlSection} compact />
          <FieldList section={schemaSection} />
        </div>
        <Card
          className="settlement-document-card"
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

      <div className="settlement-secondary-grid">
        <FieldList section={periodSection} compact />
        <FieldList section={emailSection} compact />
        <FieldList section={parserSection} compact />
      </div>

      <Card className="work-card settlement-raw-card" title="Rå importmetadata">
        <pre>{JSON.stringify(data.raw, null, 2)}</pre>
      </Card>
    </Space>
  );
}
