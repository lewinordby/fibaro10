import {
  ArrowRightOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  SearchOutlined,
  SyncOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { App as AntApp, Button, Card, Input, Progress, Space, Tag, Typography } from "antd";
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

function signedMoney(value: unknown): string {
  const numeric = asNumber(value);
  if (numeric === null) return "-";
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${money(numeric)}`;
}

function confidencePercent(value: unknown): number | null {
  const numeric = asNumber(value);
  if (numeric === null) return null;
  return Math.round(numeric * 100);
}

function statusTag(value: unknown) {
  const text = asText(value);
  const normalized = text.toLowerCase();
  const ok = normalized.includes("tolket") || normalized.includes("ok");
  const review = normalized.includes("kontroll") || normalized.includes("mangler");
  return (
    <Tag icon={ok ? <CheckCircleOutlined /> : review ? <WarningOutlined /> : undefined} color={ok ? "green" : review ? "gold" : "default"}>
      {text}
    </Tag>
  );
}

function diffTone(value: unknown): "ok" | "warn" | "empty" {
  const numeric = asNumber(value);
  if (numeric === null) return "empty";
  return Math.abs(numeric) > 1000 ? "warn" : "ok";
}

function diffText(value: unknown): string {
  const numeric = asNumber(value);
  if (numeric === null) return "Mangler kontroll";
  return Math.abs(numeric) > 1000 ? "Krever sjekk" : "Ser ok ut";
}

function largestSourceDiff(row?: ModuleRow): unknown {
  if (!row) return undefined;
  const candidates = [row.flowbird_source_diff_ex_vat, row.easypark_source_diff_ex_vat];
  return candidates.reduce<unknown>((selected, candidate) => {
    const selectedNumber = asNumber(selected);
    const candidateNumber = asNumber(candidate);
    if (candidateNumber === null) return selected;
    if (selectedNumber === null || Math.abs(candidateNumber) > Math.abs(selectedNumber)) return candidate;
    return selected;
  }, undefined);
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
  const tone = diffTone(diff);
  return (
    <div className={`settlement-source-check ${tone}`}>
      <div className="settlement-source-check-head">
        <strong>{title}</strong>
        <span>{diffText(diff)}</span>
      </div>
      <div className="settlement-source-check-grid">
        <ControlMetric label="Skjema" value={money(schemaValue)} />
        <ControlMetric label={fibaroDetail} value={money(fibaroValue)} />
        <ControlMetric label="Avvik" value={signedMoney(diff)} tone={tone} />
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
        {statusTag(row.status)}
        {percent === null ? (
          <Typography.Text type="secondary">Ingen parserverdi</Typography.Text>
        ) : (
          <Progress percent={percent} size="small" strokeColor={percent >= 90 ? "#15803d" : percent >= 70 ? "#f59e0b" : "#dc2626"} />
        )}
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
        <small className={diffTone(diff)}>Største avvik {signedMoney(diff)}</small>
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
          <span>Status</span>
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
