import {
  ArrowRightOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  UploadOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { App as AntApp, Button, Card, Select, Space, Tooltip, Typography } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
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

function periodSortValue(row: ModuleRow): number {
  const raw = asText(row.period_start || row.period_label);
  const parsed = new Date(`${raw}T00:00:00`).getTime();
  return Number.isFinite(parsed) ? parsed : 0;
}

function yearKey(row: ModuleRow): string {
  const raw = asText(row.period_start || row.period_label);
  const parsed = new Date(`${raw}T00:00:00`);
  if (!Number.isNaN(parsed.getTime())) return String(parsed.getFullYear());
  const match = raw.match(/\b(19\d{2}|20\d{2})\b/);
  return match?.[1] ?? "-";
}

function settlementYearOptions(rows: SettlementRow[]) {
  const map = new Map<string, { key: string; label: string; sortValue: number; count: number }>();
  for (const row of rows) {
    const key = yearKey(row);
    if (!key || key === "-") continue;
    const existing = map.get(key);
    if (existing) {
      existing.count += 1;
      existing.sortValue = Math.max(existing.sortValue, periodSortValue(row));
    } else {
      map.set(key, {
        key,
        label: key,
        sortValue: periodSortValue(row),
        count: 1,
      });
    }
  }
  return Array.from(map.values()).sort((left, right) => right.sortValue - left.sortValue || right.label.localeCompare(left.label, "nb"));
}

function sortSettlementsNewestFirst(rows: SettlementRow[]) {
  return [...rows].sort(
    (left, right) =>
      periodSortValue(right) - periodSortValue(left) ||
      asText(right.imported_at).localeCompare(asText(left.imported_at), "nb") ||
      asText(right.period_label).localeCompare(asText(left.period_label), "nb"),
  );
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

function VoucherLine({
  label,
  value,
  kind = "neutral",
}: {
  label: string;
  value: unknown;
  kind?: "income" | "cost" | "sum" | "payout" | "neutral";
}) {
  return (
    <div className={`settlement-voucher-line ${kind}`}>
      <span>{label}</span>
      <strong>{money(value)}</strong>
    </div>
  );
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
      <div className="sun-settlement-ledger-controls">
        <div className="sun-settlement-ledger-context">
          <div className="settlement-ledger-title">
            <FileTextOutlined />
            <strong>{asText(row.period_label)}</strong>
          </div>
          <div className="sun-settlement-context-meta">
            <ParseStatus row={row} />
            <span>{percent === null ? "Ingen score" : `${percent} % tolket`}</span>
          </div>
          <span>{asText(row.attachment_filename)}</span>
          <small>Importert {asText(row.imported_at)}</small>
        </div>
        <div className={`settlement-source-check ${sunTone}`}>
          <div className="settlement-source-check-head">
            <strong>Sol</strong>
            <span>{sunStatus}</span>
          </div>
          <div className="settlement-source-check-grid">
            <Metric label="Skjema" value={money(row.sun_revenue_ex_vat)} />
            <Metric label="System" value={money(row.sun_revenue_source_ex_vat)} tone={sunTone} />
            <Metric label="Avvik" value={money(row.sun_revenue_diff_ex_vat)} tone={sunTone} />
          </div>
        </div>
        <div className={`settlement-source-check ${productTone}`}>
          <div className="settlement-source-check-head">
            <strong>Produkt</strong>
            <span>{productStatus}</span>
          </div>
          <div className="settlement-source-check-grid">
            <Metric label="Skjema" value={money(row.product_sales_ex_vat)} />
            <Metric label="System" value={money(row.product_sales_source_ex_vat)} tone={productTone} />
            <Metric label="Avvik" value={money(row.product_sales_diff_ex_vat)} tone={productTone} />
          </div>
        </div>
        <div className="settlement-ledger-payout sun-settlement-payout">
          <span>Utbetalt</span>
          <strong>{money(row.payout_inc_vat)}</strong>
          <small>{money(row.vat_25_percent)} mva</small>
        </div>
      </div>
      <div className="sun-settlement-ledger-main">
        <div className="settlement-voucher" aria-label="Forenklet oppgjørsskjema">
          <div className="settlement-voucher-head">
            <span>Oppgjørsskjema</span>
            <span>Beløp</span>
          </div>
          <div className="settlement-voucher-grid">
            <VoucherLine label="Solomsetning" value={row.sun_revenue_ex_vat} kind="income" />
            <VoucherLine label="Produktsalg" value={row.product_sales_ex_vat} kind="income" />
            <VoucherLine label="Transaksjonskostnad" value={row.transaction_fee_ex_vat} kind="cost" />
            <VoucherLine label="Serviceavtale" value={row.service_fee_ex_vat} kind="cost" />
            <VoucherLine label="Markedsføring SMS" value={row.marketing_sms_fee_ex_vat} kind="cost" />
            <VoucherLine label="Markedsføring e-post" value={row.marketing_email_fee_ex_vat} kind="cost" />
          </div>
          <div className="settlement-voucher-totals">
            <VoucherLine label="Sum eks. mva" value={row.sum_ex_vat} kind="sum" />
            <VoucherLine label="25 % mva" value={row.vat_25_percent} />
            <VoucherLine label="Til utbetaling" value={row.payout_inc_vat} kind="payout" />
          </div>
        </div>
      </div>
      <ArrowRightOutlined className="settlement-ledger-arrow" />
    </Link>
  );
}

export default function SunSettlementsPage() {
  const { message } = AntApp.useApp();
  const [selectedYearKey, setSelectedYearKey] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { data, loading, error } = useAsyncData(() => fetchModule("soling", "oppgjor"), [refreshKey]);

  const rows = useMemo(() => (data ? settlementRows(data) : []), [data]);
  const years = useMemo(() => settlementYearOptions(rows), [rows]);
  const activeYear = years.find((year) => year.key === selectedYearKey) ?? years[0];
  const visibleRows = useMemo(
    () => (activeYear ? sortSettlementsNewestFirst(rows.filter((row) => yearKey(row) === activeYear.key)) : []),
    [activeYear, rows],
  );
  const parsedRows = rows.filter((row) => asText(row.status).toLowerCase().includes("tolket"));
  const reviewRows = rows.filter((row) => !asText(row.status).toLowerCase().includes("tolket"));

  useEffect(() => {
    if (!years.length) {
      setSelectedYearKey(null);
      return;
    }
    if (!selectedYearKey || !years.some((year) => year.key === selectedYearKey)) {
      setSelectedYearKey(years[0].key);
    }
  }, [years, selectedYearKey]);

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
              {activeYear ? `${visibleRows.length} bilag i ${activeYear.label}.` : "Ingen år valgt."} {parsedRows.length} tolket, {reviewRows.length} krever kontroll.
            </Typography.Text>
          </div>
          <div className="settlement-year-tools">
            <Select
              className="settlement-year-select"
              value={activeYear?.key}
              placeholder="Velg år"
              onChange={setSelectedYearKey}
              options={years.map((year) => ({
                value: year.key,
                label: `${year.label} (${year.count})`,
              }))}
            />
          </div>
        </div>
        <div className="settlement-ledger-table-head sun">
          <span>Kontroll</span>
          <span>Bilag</span>
          <span />
        </div>
        <div className="settlement-ledger-list">
          {visibleRows.map((row) => (
            <SunSettlementRow key={row.__rowKey} row={row} />
          ))}
          {!visibleRows.length ? (
            <div className="empty-state compact">
              <Typography.Text type="secondary">Ingen solingsoppgjør er importert for valgt år.</Typography.Text>
            </div>
          ) : null}
        </div>
      </Card>
    </Space>
  );
}
