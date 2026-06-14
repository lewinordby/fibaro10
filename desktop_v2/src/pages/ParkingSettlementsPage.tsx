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
import { fetchModule, runModuleAction, type ModuleAction, type ModuleCard, type ModuleResponse, type ModuleRow } from "../api";
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

function cardByTitle(data: ModuleResponse | null | undefined, title: string): ModuleCard | undefined {
  return data?.cards.find((card) => card.title === title);
}

function pathFor(row?: ModuleRow): string {
  return typeof row?.path === "string" ? row.path : "";
}

function settlementRows(data: ModuleResponse): SettlementRow[] {
  const table = data.tables.find((item) => item.title === "Parkeringsoppgjør");
  return (table?.rows ?? []).map((row, index) => ({
    ...row,
    __rowKey: String(row.id ?? row.attachment_sha256 ?? row.period_label ?? index),
  }));
}

function controlRows(data: ModuleResponse): SettlementRow[] {
  const table = data.tables.find((item) => item.title === "Kontroll mot interne parkeringstall");
  return (table?.rows ?? []).map((row, index) => ({
    ...row,
    __rowKey: String(row.period_label ?? row.attachment_filename ?? index),
  }));
}

function actionLabel(action: ModuleAction) {
  return action.label || "Kjør";
}

function SummaryTile({ label, value, detail, tone }: { label: string; value: string; detail: string; tone?: string }) {
  return (
    <div className={`settlement-summary-tile tone-${tone ?? "status"}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function FocusValue({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="settlement-focus-value">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
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
      <div className="settlement-ledger-money">
        <span>Skjema EasyPark</span>
        <strong>{money(row.easypark_ex_vat)}</strong>
        <small>Eks. mva</small>
      </div>
      <div className="settlement-ledger-money">
        <span>Til utbetaling</span>
        <strong>{money(row.payout_inc_vat)}</strong>
        <small>Sluttsum fra Park Nordic</small>
      </div>
      <div className={`settlement-ledger-diff ${diffTone(diff)}`}>
        <span>{diffText(diff)}</span>
        <strong>{signedMoney(diff)}</strong>
        <small>Største kildeavvik</small>
      </div>
      <ArrowRightOutlined className="settlement-ledger-arrow" />
    </Link>
  );
}

function ControlRow({ row, settlement }: { row: SettlementRow; settlement?: SettlementRow }) {
  const content = (
    <>
      <div className="settlement-control-period">
        <strong>{asText(row.period_label)}</strong>
        <span>
          {asText(row.period_start)} - {asText(row.period_end)}
        </span>
      </div>
      <div className="settlement-control-numbers">
        <FocusValue label="Flowbird Fibaro10" value={money(row.flowbird_source_paid_ex_vat)} detail={`${asText(row.flowbird_source_count)} parkeringer`} />
        <FocusValue label="Skjema mynt/kort" value={money(row.gross_coin_card_ex_vat)} detail="Eks. mva" />
        <FocusValue label="Avvik Flowbird" value={signedMoney(row.flowbird_source_diff_ex_vat)} detail={diffText(row.flowbird_source_diff_ex_vat)} />
        <FocusValue label="EasyPark Fibaro10" value={money(row.easypark_source_paid_ex_vat)} detail={`${asText(row.easypark_source_count)} parkeringer`} />
        <FocusValue label="Skjema EasyPark" value={money(row.easypark_ex_vat)} detail="Eks. mva" />
        <FocusValue label="Avvik EasyPark" value={signedMoney(row.easypark_source_diff_ex_vat)} detail={diffText(row.easypark_source_diff_ex_vat)} />
      </div>
    </>
  );
  const href = pathFor(settlement);
  if (!href) return <div className="settlement-control-row">{content}</div>;
  return (
    <Link className="settlement-control-row" to={href}>
      {content}
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
  const settlementsByPeriod = useMemo(() => new Map(rows.map((row) => [asText(row.period_label), row])), [rows]);
  const latest = rows[0];
  const parsedRows = rows.filter((row) => asText(row.status).toLowerCase().includes("tolket"));
  const reviewRows = rows.filter((row) => !asText(row.status).toLowerCase().includes("tolket"));
  const confidenceValues = rows.map((row) => confidencePercent(row.parser_confidence)).filter((value): value is number => value !== null);
  const averageConfidence = confidenceValues.length > 0 ? Math.round(confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length) : null;
  const lastControl = latest ? controlsByPeriod.get(asText(latest.period_label)) : undefined;
  const lastSourceDiff = largestSourceDiff(lastControl);
  const importAction = data?.actions?.[0] ?? null;
  const gmailCard = cardByTitle(data, "Gmail");
  const latestImportCard = cardByTitle(data, "Siste import");

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
    <Space direction="vertical" size={14} className="page-stack settlement-overview-page">
      <div className="settlement-page-head">
        <div>
          <Typography.Text className="eyebrow">Parkering</Typography.Text>
          <Typography.Title level={2}>Oppgjørskontroll</Typography.Title>
          <Typography.Text type="secondary">Park Nordic-oppgjør tolket fra Gmail og kontrollert mot interne Flowbird- og EasyPark-tall.</Typography.Text>
        </div>
        {importAction ? (
          <Button type="primary" icon={<SyncOutlined />} loading={runningAction === importAction.key} onClick={() => runAction(importAction)}>
            {actionLabel(importAction)}
          </Button>
        ) : null}
      </div>

      <div className="settlement-command-grid">
        <Card className="work-card settlement-focus-card">
          <div className="settlement-focus-head">
            <div>
              <Typography.Text className="eyebrow">Siste oppgjør</Typography.Text>
              <Typography.Title level={3}>
                {latest ? <Link to={pathFor(latest)}>{asText(latest.period_label)}</Link> : "Ingen oppgjør importert"}
              </Typography.Title>
              <Typography.Text type="secondary">{latest ? asText(latest.attachment_filename) : "Importer fra Gmail for å starte kontroll."}</Typography.Text>
            </div>
            {latest ? statusTag(latest.status) : null}
          </div>
          <div className="settlement-focus-values">
            <FocusValue label="Til utbetaling" value={money(latest?.payout_inc_vat)} detail="Sluttsum fra skjema" />
            <FocusValue label="Flowbird Fibaro10" value={money(lastControl?.flowbird_source_paid_ex_vat)} detail={`${asText(lastControl?.flowbird_source_count)} parkeringer`} />
            <FocusValue label="EasyPark Fibaro10" value={money(lastControl?.easypark_source_paid_ex_vat)} detail={`${asText(lastControl?.easypark_source_count)} parkeringer`} />
            <FocusValue label="Største avvik" value={signedMoney(lastSourceDiff)} detail={diffText(lastSourceDiff)} />
          </div>
        </Card>

        <Card className="work-card settlement-import-card">
          <div className="settlement-import-status">
            <div>
              <Typography.Text className="eyebrow">Import</Typography.Text>
              <Typography.Title level={3}>{asText(gmailCard?.value ?? "Ukjent")}</Typography.Title>
              <Typography.Text type="secondary">{asText(gmailCard?.detail ?? "Gmail-status er ikke rapportert.")}</Typography.Text>
            </div>
            {gmailCard?.value === "Klar" ? <CheckCircleOutlined className="settlement-import-icon ok" /> : <WarningOutlined className="settlement-import-icon warn" />}
          </div>
          <div className="settlement-import-meta">
            <span>Siste import</span>
            <strong>{asText(latestImportCard?.value)}</strong>
            <small>{asText(latestImportCard?.detail)}</small>
          </div>
        </Card>
      </div>

      <div className="settlement-summary-grid">
        <SummaryTile label="Importert" value={asText(data.cards[0]?.value ?? rows.length)} detail={`${parsedRows.length} tolket`} tone="parking" />
        <SummaryTile label="Krever kontroll" value={asText(reviewRows.length)} detail="Oppgjør uten full tolking" tone={reviewRows.length ? "revenue" : "energy"} />
        <SummaryTile label="Tolkesikkerhet" value={averageConfidence === null ? "-" : `${averageConfidence} %`} detail="Snitt av oppgjør med parserverdi" tone="status" />
        <SummaryTile label="Siste utbetaling" value={money(latest?.payout_inc_vat)} detail={asText(latest?.period_label)} tone="revenue" />
        <SummaryTile label="Siste avvik" value={money(lastSourceDiff)} detail="Største kildeavvik" tone="parking" />
      </div>

      <Card className="work-card settlement-register-card">
        <div className="settlement-card-head">
          <div>
            <Typography.Title level={4}>Oppgjør</Typography.Title>
            <Typography.Text type="secondary">{filteredRows.length} av {rows.length} oppgjør vises</Typography.Text>
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
        <div className="settlement-ledger-list">
          {filteredRows.map((row) => (
            <SettlementLedgerRow key={row.__rowKey} row={row} control={controlsByPeriod.get(asText(row.period_label))} />
          ))}
        </div>
      </Card>

      <Card className="work-card settlement-control-card">
        <div className="settlement-card-head">
          <div>
            <Typography.Title level={4}>Kontroll mot Fibaro10</Typography.Title>
            <Typography.Text type="secondary">Sammenligner skjemaets Flowbird/mynt-kort og EasyPark mot interne kildeverdier for samme periode.</Typography.Text>
          </div>
        </div>
        <div className="settlement-control-list">
          {controls.map((row) => (
            <ControlRow key={row.__rowKey} row={row} settlement={settlementsByPeriod.get(asText(row.period_label))} />
          ))}
        </div>
      </Card>
    </Space>
  );
}
