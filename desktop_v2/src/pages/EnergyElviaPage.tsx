import { ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import { Alert, App as AntApp, Button, Card, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useRef, useState } from "react";
import { uploadElviaFile, type EnergyElviaData, type EnergyElviaSummaryItem, type ModuleResponse } from "../api";
import "../styles/energy.css";

type EnergyElviaPageProps = {
  data: ModuleResponse;
  onReload: () => void;
};

const LABELS: Record<string, string> = {
  period: "Periode",
  period_label: "Periode",
  consumption_kwh: "kWh",
  production_kwh: "Produksjon",
  days_count: "Dager",
  hours_count: "Timer",
  estimated_hours_count: "Est.",
  timestamp: "Tid",
  source_file: "Fil",
  meter_id: "Måler",
  period_first: "Fra",
  period_last: "Til",
  inserted_count: "Nye",
  updated_count: "Oppdatert",
  skipped_count: "Uendret",
  total_kwh: "kWh",
  ok: "OK",
  message: "Melding",
  measured_at: "Målt",
  stat_date: "Dato",
  hour: "Time",
  status: "Status",
  is_estimated: "Estimert",
  source: "Kilde",
};

function label(column: string): string {
  return LABELS[column] ?? column.replaceAll("_", " ");
}

function numberText(value: unknown, digits = 0): string {
  const number = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(number)) return "-";
  return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: digits }).format(number);
}

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Ja" : "Nei";
  if (typeof value === "number") return numberText(value, 2);
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

function timeText(value: unknown): string {
  if (!value) return "-";
  return valueText(value);
}

function kwhText(value: unknown, digits = 0): string {
  const number = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${numberText(number, digits)} kWh`;
}

function statusTag(status?: string | null, fallback?: string | null) {
  const normalized = (status || "").toLowerCase();
  const color = normalized === "running" ? "processing" : normalized === "bad" || normalized === "error" ? "red" : "green";
  return <Tag color={color}>{fallback || status || "Ukjent"}</Tag>;
}

function SummaryTile({ title, value, unit, detail }: { title: string; value: string; unit?: string; detail: string }) {
  return (
    <Card className="work-card elvia-summary-tile">
      <span>{title}</span>
      <strong>
        {value}
        {unit ? <em>{unit}</em> : null}
      </strong>
      <small>{detail}</small>
    </Card>
  );
}

function summaryColumns(columns: string[]): ColumnsType<EnergyElviaSummaryItem> {
  return columns.map((column) => ({
    title: label(column),
    dataIndex: column,
    key: column,
    align: column.includes("kwh") || column.endsWith("_count") ? "right" : undefined,
    render: (value: unknown) => (column.includes("kwh") ? kwhText(value, column === "consumption_kwh" ? 1 : 2) : valueText(value)),
  }));
}

function recordColumns(columns: string[]): ColumnsType<Record<string, unknown>> {
  return columns.map((column) => ({
    title: label(column),
    dataIndex: column,
    key: column,
    ellipsis: true,
    align: /(_count|_kwh|hour)$/i.test(column) ? "right" : undefined,
    render: (value: unknown) => {
      if (typeof value === "boolean") return <Tag color={value ? "green" : "default"}>{value ? "Ja" : "Nei"}</Tag>;
      if (column.includes("kwh")) return kwhText(value, column === "consumption_kwh" ? 2 : 1);
      return valueText(value);
    },
  }));
}

function SummaryTable({
  title,
  rows,
  columns,
  rowKey,
}: {
  title: string;
  rows: EnergyElviaSummaryItem[];
  columns: string[];
  rowKey: keyof EnergyElviaSummaryItem;
}) {
  return (
    <Card className="work-card elvia-table-card" title={title}>
      <Table
        rowKey={(row, index) => String(row[rowKey] ?? index)}
        size="small"
        columns={summaryColumns(columns)}
        dataSource={rows}
        pagination={false}
      />
    </Card>
  );
}

function RecordTable({ title, rows, columns }: { title: string; rows: Record<string, unknown>[]; columns: string[] }) {
  return (
    <Card className="work-card elvia-table-card" title={title}>
      <Table
        rowKey={(row, index) => `${title}-${row.id ?? row.timestamp ?? row.measured_at ?? index}`}
        size="small"
        columns={recordColumns(columns)}
        dataSource={rows}
        pagination={{ pageSize: 25, showSizeChanger: true }}
        scroll={{ x: "max-content" }}
      />
    </Card>
  );
}

function UploadPanel({ elvia, onReload }: { elvia: EnergyElviaData; onReload: () => void }) {
  const { message } = AntApp.useApp();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  async function submit() {
    if (!file || uploading) {
      message.warning("Velg en JSON-fil fra Elvia først.");
      return;
    }
    setUploading(true);
    try {
      const result = await uploadElviaFile(elvia.uploadEndpoint, file);
      message.success(String(result.message || "Elvia-import startet."));
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      onReload();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Import feilet");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Card className="work-card elvia-upload-card" title="Importer Elvia-fil">
      <Typography.Paragraph type="secondary">
        Last opp JSON-eksporten fra Elvia. Samme fil kan importeres på nytt uten dobbelttelling.
      </Typography.Paragraph>
      <div className="elvia-upload-row">
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <Button type="primary" icon={<UploadOutlined />} loading={uploading} onClick={submit}>
          Importer
        </Button>
      </div>
      {file ? <Typography.Text type="secondary">Valgt fil: {file.name}</Typography.Text> : null}
    </Card>
  );
}

export default function EnergyElviaPage({ data, onReload }: EnergyElviaPageProps) {
  const elvia = data.energyElvia;
  const reloadRef = useRef(onReload);

  useEffect(() => {
    reloadRef.current = onReload;
  }, [onReload]);

  useEffect(() => {
    if (elvia?.status?.status !== "running") return;
    const timer = window.setInterval(() => reloadRef.current(), 5000);
    return () => window.clearInterval(timer);
  }, [elvia?.status?.status]);

  const latestImport = elvia?.latestImport;
  const importCards = useMemo(() => elvia?.imports.slice(0, 3) ?? [], [elvia?.imports]);

  if (!elvia) {
    return <Alert type="warning" message="Elvia-data mangler i API-responsen." />;
  }

  const total = elvia.summary.total;
  const latestPeriodLast = latestImport?.period_last;
  const status = elvia.status;

  return (
    <Space direction="vertical" size={16} className="page-stack elvia-page">
      {status ? (
        <Alert
          className="elvia-status-alert"
          type={status.status === "bad" ? "error" : status.status === "running" ? "warning" : "success"}
          showIcon
          message={
            <Space size={8} wrap>
              <span>Importstatus</span>
              {statusTag(status.status, status.statusText)}
              {status.message ? <Typography.Text>{status.message}</Typography.Text> : null}
              {status.durationSeconds ? <Typography.Text type="secondary">{numberText(status.durationSeconds, 1)} sek</Typography.Text> : null}
            </Space>
          }
        />
      ) : null}

      {latestPeriodLast ? (
        <Alert
          className="elvia-status-alert"
          type="info"
          message={`Faktisk siste time i Elvia-data er ${timeText(latestPeriodLast)}. Filnavnet kan vise en nyere sluttdato enn eksporten faktisk inneholder.`}
        />
      ) : null}

      <div className="elvia-top-row">
        <div className="elvia-summary-grid">
          <SummaryTile title="Totalt forbruk" value={numberText(total.consumption_kwh)} unit="kWh" detail={`${numberText(total.hours_count)} timer`} />
          <SummaryTile
            title="Periode"
            value={elvia.summary.firstAt && elvia.summary.lastAt ? `${timeText(elvia.summary.firstAt)} - ${timeText(elvia.summary.lastAt)}` : "-"}
            detail={`${numberText(total.days_count)} dager`}
          />
          <SummaryTile title="Estimerte timer" value={numberText(total.estimated_hours_count)} detail="Elvia-status ulik OK" />
          <SummaryTile
            title="Siste import"
            value={latestImport ? timeText(latestImport.timestamp) : "-"}
            detail={latestImport ? `Data til ${timeText(latestImport.period_last)}` : "Ingen import ennå"}
          />
        </div>
        <UploadPanel elvia={elvia} onReload={onReload} />
      </div>

      {importCards.length ? (
        <div className="elvia-import-grid">
          {importCards.map((run, index) => (
            <Card className={`work-card elvia-import-card ${run.ok === false ? "failed" : ""}`} key={`${run.timestamp ?? index}`}>
              <div className="elvia-import-head">
                <strong>{valueText(run.source_file || "Elvia-import")}</strong>
                {typeof run.ok === "boolean" ? <Tag color={run.ok ? "green" : "red"}>{run.ok ? "OK" : "Feil"}</Tag> : null}
              </div>
              <Typography.Text type="secondary">
                {timeText(run.timestamp)} · {numberText(run.hours_count)} timer
              </Typography.Text>
              <div className="elvia-import-metrics">
                <span>
                  Nye <strong>{numberText(run.inserted_count)}</strong>
                </span>
                <span>
                  Oppdatert <strong>{numberText(run.updated_count)}</strong>
                </span>
                <span>
                  Uendret <strong>{numberText(run.skipped_count)}</strong>
                </span>
              </div>
              {run.message ? <small>{valueText(run.message)}</small> : null}
            </Card>
          ))}
        </div>
      ) : null}

      <div className="elvia-main-grid">
        <SummaryTable title="Årssummer" rows={elvia.yearly} columns={["period", "consumption_kwh", "days_count", "hours_count", "estimated_hours_count"]} rowKey="period" />
        <SummaryTable title="10 høyeste forbruksdager" rows={elvia.topDays} columns={["period_label", "consumption_kwh", "hours_count", "estimated_hours_count"]} rowKey="period" />
        <SummaryTable title="10 høyeste forbruksmåneder" rows={elvia.topMonths} columns={["period", "consumption_kwh", "days_count", "estimated_hours_count"]} rowKey="period" />
      </div>

      <RecordTable
        title="Importer"
        rows={elvia.imports}
        columns={["timestamp", "source_file", "meter_id", "hours_count", "inserted_count", "updated_count", "skipped_count", "total_kwh", "ok", "message"]}
      />
      <RecordTable
        title="Siste Elvia-timer"
        rows={elvia.rows}
        columns={["measured_at", "stat_date", "hour", "consumption_kwh", "status", "is_estimated", "source"]}
      />

      <Button icon={<ReloadOutlined />} onClick={onReload} className="elvia-reload-button">
        Oppdater siden
      </Button>
    </Space>
  );
}
