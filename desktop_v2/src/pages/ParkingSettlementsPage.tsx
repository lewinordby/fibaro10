import {
  ArrowRightOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  SearchOutlined,
  SyncOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { App as AntApp, Button, Card, Input, Space, Tooltip, Typography } from "antd";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchModule, runModuleAction, type ModuleAction, type ModuleResponse, type ModuleRow } from "../api";
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

function percentDiff(diff: unknown, reference: unknown): number | null {
  const diffNumber = asNumber(diff);
  const referenceNumber = asNumber(reference);
  if (diffNumber === null || referenceNumber === null || referenceNumber === 0) return null;
  return (diffNumber / Math.abs(referenceNumber)) * 100;
}

function signedPercentDiff(diff: unknown, reference: unknown): string {
  const percent = percentDiff(diff, reference);
  if (percent === null) return "-";
  const sign = percent > 0 ? "+" : "";
  return `${sign}${new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 1 }).format(percent)} %`;
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

function diffTone(value: unknown, reference?: unknown): "ok" | "warn" | "empty" {
  const numeric = asNumber(value);
  if (numeric === null) return "empty";
  const percent = percentDiff(value, reference);
  if (percent !== null) return Math.abs(percent) > 1 ? "warn" : "ok";
  return Math.abs(numeric) > 1000 ? "warn" : "ok";
}

function diffText(value: unknown, reference?: unknown): string {
  const numeric = asNumber(value);
  if (numeric === null) return "Mangler kontroll";
  const percent = percentDiff(value, reference);
  if (percent !== null) return Math.abs(percent) > 1 ? "Krever sjekk" : "Ser ok ut";
  return Math.abs(numeric) > 1000 ? "Krever sjekk" : "Ser ok ut";
}

function largestSourceDiff(row?: ModuleRow): { diff: unknown; reference: unknown } | null {
  if (!row) return null;
  const candidates = [
    { diff: row.flowbird_source_diff_ex_vat, reference: row.gross_coin_card_ex_vat },
    { diff: row.easypark_source_diff_ex_vat, reference: row.easypark_ex_vat },
  ];
  return candidates.reduce<{ diff: unknown; reference: unknown } | null>((selected, candidate) => {
    const candidateNumber = asNumber(candidate.diff);
    if (candidateNumber === null) return selected;
    if (!selected) return candidate;
    const selectedPercent = percentDiff(selected.diff, selected.reference);
    const candidatePercent = percentDiff(candidate.diff, candidate.reference);
    const selectedScore = selectedPercent === null ? Math.abs(asNumber(selected.diff) ?? 0) : Math.abs(selectedPercent);
    const candidateScore = candidatePercent === null ? Math.abs(candidateNumber) : Math.abs(candidatePercent);
    return candidateScore > selectedScore ? candidate : selected;
  }, null);
}

function pathFor(row?: ModuleRow): string {
  return typeof row?.path === "string" ? row.path : "";
}

function settlementRows(data: ModuleResponse): SettlementRow[] {
  const table = data.tables.find((item) => item.title.toLowerCase().includes("parkeringsoppgj"));
  return (table?.rows ?? []).map((row, index) => ({
    ...row,
    __rowKey: String(row.id ?? row.attachment_sha256 ?? row.period_label ?? index),
  }));
}

function controlRows(data: ModuleResponse): SettlementRow[] {
  const table = data.tables.find((item) => item.title.toLowerCase().includes("kontroll mot interne parkeringstall"));
  return (table?.rows ?? []).map((row, index) => ({
    ...row,
    __rowKey: String(row.period_label ?? row.attachment_filename ?? index),
  }));
}

function actionLabel(action: ModuleAction) {
  return action.label || "Kjør";
}

function ControlMetric({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" | "empty" }) {
  return (
    <div className={`settlement-control-metric ${tone ? `tone-${tone}` : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SourceCheck({
  title,
  schemaValue,
  fibaroValue,
  fibaroDetail,
  diff,
}: {
  title: string;
  schemaValue: unknown;
  fibaroValue: unknown;
  fibaroDetail: string;
  diff: unknown;
}) {
  const tone = diffTone(diff, schemaValue);
  return (
    <div className={`settlement-source-check ${tone}`}>
      <div className="settlement-source-check-head">
        <strong>{title}</strong>
        <span>{diffText(diff, schemaValue)}</span>
      </div>
      <div className="settlement-source-check-grid">
        <ControlMetric label="Skjema" value={money(schemaValue)} />
        <ControlMetric label={fibaroDetail} value={money(fibaroValue)} />
        <ControlMetric label="Avvik" value={signedPercentDiff(diff, schemaValue)} tone={tone} />
      </div>
    </div>
  );
}

function SettlementLedgerRow({ row, control }: { row: SettlementRow; control?: SettlementRow }) {
  const percent = confidencePercent(row.parser_confidence);
  const href = pathFor(row);
  const diff = largestSourceDiff(control);

  return (
    <Link className="settlement-ledger-row" to={href || "#"}>
      <div className="settlement-ledger-identity">
        <div className="settlement-ledger-title">
          <FileTextOutlined />
          <strong>{asText(row.period_label)}</strong>
        </div>
        <span>{asText(row.attachment_filename)}</span>
        <small>{asText(row.email_date)}</small>
      </div>
      <div className="settlement-ledger-state">
        <ParseStatus row={row} />
        <small>{percent === null ? "Ingen score" : `${percent} %`}</small>
      </div>
      <SourceCheck
        title="Flowbird / mynt-kort"
        schemaValue={control?.gross_coin_card_ex_vat}
        fibaroValue={control?.flowbird_source_paid_ex_vat}
        fibaroDetail={`${asText(control?.flowbird_source_count)} stk Fibaro10`}
        diff={control?.flowbird_source_diff_ex_vat}
      />
      <SourceCheck
        title="EasyPark"
        schemaValue={control?.easypark_ex_vat ?? row.easypark_ex_vat}
        fibaroValue={control?.easypark_source_paid_ex_vat}
        fibaroDetail={`${asText(control?.easypark_source_count)} stk Fibaro10`}
        diff={control?.easypark_source_diff_ex_vat}
      />
      <div className="settlement-ledger-payout">
        <span>Til utbetaling</span>
        <strong>{money(row.payout_inc_vat)}</strong>
        <small className={diffTone(diff?.diff, diff?.reference)}>Største avvik {signedPercentDiff(diff?.diff, diff?.reference)}</small>
      </div>
      <ArrowRightOutlined className="settlement-ledger-arrow" />
    </Link>
  );
}

function filterSettlementRows(rows: SettlementRow[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return rows;
  return rows.filter((row) =>
    ["period_label", "attachment_filename", "email_subject", "sender", "status"].some((key) => asText(row[key]).toLowerCase().includes(normalized)),
  );
}

export default function ParkingSettlementsPage() {
  const { message, modal } = AntApp.useApp();
  const [query, setQuery] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const { data, loading, error } = useAsyncData(() => fetchModule("parkering", "oppgjor"), [refreshKey]);

  const rows = useMemo(() => (data ? settlementRows(data) : []), [data]);
  const controls = useMemo(() => (data ? controlRows(data) : []), [data]);
  const filteredRows = useMemo(() => filterSettlementRows(rows, query), [rows, query]);
  const controlsByPeriod = useMemo(() => new Map(controls.map((row) => [asText(row.period_label), row])), [controls]);
  const parsedRows = rows.filter((row) => asText(row.status).toLowerCase().includes("tolket"));
  const reviewRows = rows.filter((row) => !asText(row.status).toLowerCase().includes("tolket"));
  const importAction = data?.actions?.[0] ?? null;

  async function runAction(action: ModuleAction) {
    const execute = async () => {
      setRunningAction(action.key);
      try {
        const result = await runModuleAction(action);
        message.success(String(result.message || "Handling utført"));
        setRefreshKey((value) => value + 1);
      } catch (err) {
        message.error(err instanceof Error ? err.message : "Kunne ikke kjøre handlingen");
      } finally {
        setRunningAction(null);
      }
    };
    if (action.confirm) {
      modal.confirm({
        title: action.label,
        content: action.confirm,
        okText: "Kjør",
        cancelText: "Avbryt",
        onOk: execute,
      });
      return;
    }
    await execute();
  }

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={12} className="page-stack settlement-overview-page">
      <div className="settlement-page-head compact">
        <div>
          <Typography.Text className="eyebrow">Parkering</Typography.Text>
          <Typography.Title level={2}>Oppgjørskontroll</Typography.Title>
          <Typography.Text type="secondary">Kontroll av Flowbird/mynt-kort og EasyPark mot interne kildetall.</Typography.Text>
        </div>
        {importAction ? (
          <Button type="primary" icon={<SyncOutlined />} loading={runningAction === importAction.key} onClick={() => runAction(importAction)}>
            {actionLabel(importAction)}
          </Button>
        ) : null}
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
            placeholder="Søk periode, fil, avsender eller status"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <div className="settlement-ledger-table-head">
          <span>Oppgjør</span>
          <span>Tolket</span>
          <span>Flowbird / mynt-kort</span>
          <span>EasyPark</span>
          <span>Utbetaling</span>
          <span />
        </div>
        <div className="settlement-ledger-list">
          {filteredRows.map((row) => (
            <SettlementLedgerRow key={row.__rowKey} row={row} control={controlsByPeriod.get(asText(row.period_label))} />
          ))}
        </div>
      </Card>
    </Space>
  );
}
