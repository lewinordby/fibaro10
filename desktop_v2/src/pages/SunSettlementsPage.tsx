import {
  ArrowRightOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  SearchOutlined,
  UploadOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { App as AntApp, Button, Card, Input, Space, Tooltip, Typography } from "antd";
import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { fetchModule, uploadSettlementFile, type ModuleResponse, type ModuleRow } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useAsyncData } from "../hooks";

type SettlementRow = ModuleRow & {
  __rowKey: string;
};

function asText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 2 }).format(value);
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

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value !== "string") return null;
  const normalized = value.replace(/\s/g, "").replace(",", ".");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function money(value: unknown): string {
  const numeric = asNumber(value);
  if (numeric === null) return "-";
  return `${new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 }).format(numeric)} kr`;
}

function confidencePercent(value: unknown): number | null {
  const numeric = asNumber(value);
  if (numeric === null) return null;
  return Math.round(numeric * 100);
}

function parseState(row: ModuleRow): { tone: "ok" | "warn" | "error"; label: string; detail: string } {
  const text = asText(row.status);
  const normalized = text.toLowerCase();
  const percent = confidencePercent(row.parser_confidence);
  const parsed = normalized.includes("tolket") || normalized.includes("ok");
  if (!parsed || (percent !== null && percent < 70)) {
    return {
      tone: "error",
      label: "Må kontrolleres",
      detail: percent === null ? text : `${text} - ${percent} % tolkningssikkerhet`,
    };
  }
  if (percent === null || percent < 90) {
    return {
      tone: "warn",
      label: "Usikker tolking",
      detail: percent === null ? text : `${text} - ${percent} % tolkningssikkerhet`,
    };
  }
  return {
    tone: "ok",
    label: "Tolket",
    detail: `${text} - ${percent} % tolkningssikkerhet`,
  };
}

function ParseStatus({ row }: { row: ModuleRow }) {
  const state = parseState(row);
  const icon =
    state.tone === "ok" ? <CheckCircleOutlined /> : state.tone === "warn" ? <WarningOutlined /> : <CloseCircleOutlined />;
  return (
    <Tooltip title={state.detail}>
      <span className={`settlement-parse-status ${state.tone}`} aria-label={state.label}>
        {icon}
      </span>
    </Tooltip>
  );
}

function settlementRows(data: ModuleResponse): SettlementRow[] {
  const table = data.tables.find((item) => item.title.toLowerCase().includes("solingsoppgj"));
  return (table?.rows ?? []).map((row, index) => ({
    ...row,
    __rowKey: String(row.id ?? row.attachment_sha256 ?? row.period_label ?? index),
  }));
}

function pathFor(row?: ModuleRow): string {
  return typeof row?.path === "string" ? row.path : "";
}

function filterSettlementRows(rows: SettlementRow[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return rows;
  return rows.filter((row) =>
    ["period_label", "attachment_filename", "email_subject", "sender", "status", "sum_check_status"].some((key) =>
      asText(row[key]).toLowerCase().includes(normalized),
    ),
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" | "empty" }) {
  return (
    <div className={`settlement-control-metric ${tone ? `tone-${tone}` : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function controlTone(status: string): "ok" | "warn" | "empty" {
  const normalized = status.toLowerCase();
  if (normalized === "ok") return "ok";
  if (normalized.includes("mangler")) return "empty";
  return "warn";
}

function SunSettlementRow({ row }: { row: SettlementRow }) {
  const percent = confidencePercent(row.parser_confidence);
  const href = pathFor(row);
  const sunStatus = asText(row.sun_revenue_control_status);
  const productStatus = asText(row.product_sales_control_status);
  const sunTone = controlTone(sunStatus);
  const productTone = controlTone(productStatus);
  return (
    <Link className="settlement-ledger-row sun" to={href || "#"}>
      <div className="settlement-ledger-identity">
        <div className="settlement-ledger-title">
          <FileTextOutlined />
          <strong>{asText(row.period_label)}</strong>
        </div>
        <span>{asText(row.attachment_filename)}</span>
        <small>{asText(row.imported_at)}</small>
      </div>
      <div className="settlement-ledger-state">
        <ParseStatus row={row} />
        <small>{percent === null ? "Ingen score" : `${percent} %`}</small>
      </div>
      <div className="settlement-source-check">
        <div className="settlement-source-check-head">
          <strong>Inntekter</strong>
          <span>{asText(row.sum_check_status)}</span>
        </div>
        <div className="settlement-source-check-grid two">
          <Metric label="Sol" value={money(row.sun_revenue_ex_vat)} />
          <Metric label="Produkt" value={money(row.product_sales_ex_vat)} />
        </div>
      </div>
      <div className={`settlement-source-check ${sunTone}`}>
        <div className="settlement-source-check-head">
          <strong>Solkontroll</strong>
          <span>{sunStatus}</span>
        </div>
        <div className="settlement-source-check-grid two">
          <Metric label="System" value={money(row.sun_revenue_source_ex_vat)} tone={sunTone} />
          <Metric label="Avvik" value={money(row.sun_revenue_diff_ex_vat)} tone={sunTone} />
        </div>
      </div>
      <div className={`settlement-source-check ${productTone}`}>
        <div className="settlement-source-check-head">
          <strong>Produktkontroll</strong>
          <span>{productStatus}</span>
        </div>
        <div className="settlement-source-check-grid two">
          <Metric label="Sun2" value={money(row.product_sales_source_ex_vat)} tone={productTone} />
          <Metric label="Avvik" value={money(row.product_sales_diff_ex_vat)} tone={productTone} />
        </div>
      </div>
      <div className="settlement-ledger-payout">
        <span>Beløp NOK</span>
        <strong>{money(row.payout_inc_vat)}</strong>
        <small>{asText(row.vat_25_percent)} mva</small>
      </div>
      <ArrowRightOutlined className="settlement-ledger-arrow" />
    </Link>
  );
}

export default function SunSettlementsPage() {
  const { message } = AntApp.useApp();
  const [query, setQuery] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { data, loading, error } = useAsyncData(() => fetchModule("soling", "oppgjor"), [refreshKey]);

  const rows = useMemo(() => (data ? settlementRows(data) : []), [data]);
  const filteredRows = useMemo(() => filterSettlementRows(rows, query), [rows, query]);
  const parsedRows = rows.filter((row) => asText(row.status).toLowerCase().includes("tolket"));
  const reviewRows = rows.filter((row) => !asText(row.status).toLowerCase().includes("tolket"));

  async function uploadFiles(files?: FileList | null) {
    if (!files?.length || !data?.uploadEndpoint || uploading) return;
    setUploading(true);
    let imported = 0;
    try {
      for (const file of Array.from(files)) {
        const result = await uploadSettlementFile(data.uploadEndpoint, file);
        imported += 1;
        if (files.length === 1) {
          message.success(String(result.message || "Solingsoppgjør importert."));
        }
      }
      if (files.length > 1) {
        message.success(`${imported} solingsoppgjør er behandlet.`);
      }
      setRefreshKey((value) => value + 1);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Import feilet");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={12} className="page-stack settlement-overview-page">
      <div className="settlement-page-head compact">
        <div>
          <Typography.Text className="eyebrow">Soling</Typography.Text>
          <Typography.Title level={2}>Oppgjørskontroll</Typography.Title>
          <Typography.Text type="secondary">Importer Altera-kreditnotaer og kontroller at skjemaets egne summer stemmer.</Typography.Text>
        </div>
        <Space>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.xlsx,.xls,.csv,.txt,application/pdf,image/jpeg,image/png"
            style={{ display: "none" }}
            onChange={(event) => uploadFiles(event.target.files)}
          />
          <Button type="primary" icon={<UploadOutlined />} loading={uploading} onClick={() => fileInputRef.current?.click()}>
            Last opp oppgjør
          </Button>
        </Space>
      </div>

      <Card className="work-card settlement-register-card">
        <div className="settlement-card-head">
          <div>
            <Typography.Title level={4}>Oppgjør</Typography.Title>
            <Typography.Text type="secondary">
              {filteredRows.length} av {rows.length} vises. {parsedRows.length} tolket, {reviewRows.length} krever kontroll.
            </Typography.Text>
          </div>
          <Input
            allowClear
            className="settlement-search"
            prefix={<SearchOutlined />}
            placeholder="Søk periode, fil eller status"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <div className="settlement-ledger-table-head sun">
          <span>Oppgjør</span>
          <span>Tolket</span>
          <span>Inntekter</span>
          <span>Solkontroll</span>
          <span>Produktkontroll</span>
          <span>Beløp</span>
          <span />
        </div>
        <div className="settlement-ledger-list">
          {filteredRows.map((row) => (
            <SunSettlementRow key={row.__rowKey} row={row} />
          ))}
          {!filteredRows.length ? (
            <div className="empty-state compact">
              <Typography.Text type="secondary">Ingen solingsoppgjør er importert ennå.</Typography.Text>
            </div>
          ) : null}
        </div>
      </Card>
    </Space>
  );
}
