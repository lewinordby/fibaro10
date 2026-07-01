import { CheckCircleOutlined, ClockCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { Card, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link } from "react-router-dom";
import { fetchHealth, type HealthResponse, type HealthSource } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";

type SourceRow = HealthSource & {
  key: string;
};

function statusTag(row: HealthSource) {
  if (row.status === "ok") return <Tag color="green">OK</Tag>;
  if (row.status === "bad") return <Tag color="red">Feil</Tag>;
  if (row.status === "warn") return <Tag color="gold">Treg</Tag>;
  return <Tag>Ukjent</Tag>;
}

function statusIcon(row: HealthSource) {
  if (row.status === "ok") return <CheckCircleOutlined className="status-ok" />;
  if (row.status === "bad") return <WarningOutlined className="status-bad" />;
  return <ClockCircleOutlined className="status-warn" />;
}

function sourceTitle(row: HealthSource) {
  return row.title || row.label || row.jobName || "-";
}

function sourcePath(row: HealthSource) {
  return row.jobName ? `/admin/datakilder/${encodeURIComponent(row.jobName)}` : "";
}

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(value?: number | null) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  if (value < 1) return "<1 s";
  if (value < 90) return `${Math.round(value)} s`;
  return `${Math.round(value / 60)} min`;
}

function recordText(row: HealthSource) {
  const imported = row.recordsImported;
  const total = row.recordsTotal;
  if (imported !== null && imported !== undefined && total !== null && total !== undefined) return `${imported}/${total}`;
  if (total !== null && total !== undefined) return String(total);
  if (imported !== null && imported !== undefined) return String(imported);
  return "-";
}

function summaryCards(data: HealthResponse) {
  const sources = data.summary.sources;
  return [
    { title: "Datakilder", value: sources.total, detail: `${sources.ok} OK`, tone: "status" },
    { title: "Treg", value: sources.warn, detail: "Bør sjekkes", tone: sources.warn ? "warning" : "status" },
    { title: "Feil", value: sources.bad, detail: "Krever tiltak", tone: sources.bad ? "danger" : "status" },
    { title: "Lagring", value: data.storage.length, detail: "Tabeller i health", tone: "status" },
  ];
}

const columns: ColumnsType<SourceRow> = [
  {
    title: "Nr",
    dataIndex: "sourceNo",
    width: 70,
    sorter: (left, right) => Number(left.sourceNo || 999) - Number(right.sourceNo || 999),
    render: (value) => (value ? `#${value}` : "-"),
  },
  {
    title: "Status",
    dataIndex: "status",
    width: 105,
    filters: [
      { text: "OK", value: "ok" },
      { text: "Treg", value: "warn" },
      { text: "Feil", value: "bad" },
      { text: "Ukjent", value: "unknown" },
    ],
    onFilter: (value, row) => row.status === value,
    render: (_, row) => (
      <Space size={6}>
        {statusIcon(row)}
        {statusTag(row)}
      </Space>
    ),
  },
  {
    title: "Datakilde",
    dataIndex: "title",
    sorter: (left, right) => sourceTitle(left).localeCompare(sourceTitle(right), "nb"),
    render: (_, row) => (
      <div className="operations-source-title">
        <strong>{sourcePath(row) ? <Link to={sourcePath(row)}>{sourceTitle(row)}</Link> : sourceTitle(row)}</strong>
        <span>{row.jobName}</span>
      </div>
    ),
  },
  {
    title: "Kategori",
    dataIndex: "category",
    width: 120,
    sorter: (left, right) => String(left.category || "").localeCompare(String(right.category || ""), "nb"),
    render: (value) => value || "-",
  },
  {
    title: "Kilde",
    dataIndex: "source",
    width: 150,
    render: (value) => value || "-",
  },
  {
    title: "Sist OK",
    dataIndex: "lastSuccessAt",
    width: 145,
    sorter: (left, right) =>
      new Date(left.lastSuccessAt || 0).getTime() - new Date(right.lastSuccessAt || 0).getTime(),
    render: formatDateTime,
  },
  {
    title: "Neste",
    dataIndex: "nextExpectedAt",
    width: 145,
    render: formatDateTime,
  },
  {
    title: "Rader",
    key: "records",
    width: 90,
    align: "right",
    render: (_, row) => recordText(row),
  },
  {
    title: "Tid",
    dataIndex: "durationSeconds",
    width: 90,
    align: "right",
    render: formatDuration,
  },
  {
    title: "Melding",
    dataIndex: "message",
    ellipsis: true,
    render: (value, row) => value || row.detail || row.statusText || "-",
  },
];

export default function OperationsPage() {
  const { data, loading, error } = useApiQuery(queryKeys.health(true), () => fetchHealth(true), {
    refetchInterval: 60_000,
  });

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const sources = [...data.sources]
    .map((item, index) => ({
      ...item,
      key: item.jobName || `${item.title || item.label || "source"}-${index}`,
    }))
    .sort((left, right) => Number(left.sourceNo || 999) - Number(right.sourceNo || 999));
  const warnings = data.summary.sources.warn + data.summary.sources.bad + data.summary.sources.unknown;

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-operations-page">
      <PageHeader
        eyebrow="Drift"
        title="Datakilder og jobber"
        description={`${data.summary.sources.total} datakilder fra health-details`}
        meta={
          <Typography.Text type={warnings ? "warning" : "secondary"}>
            {warnings ? `${warnings} trenger sjekk` : "Alt OK"}
          </Typography.Text>
        }
      />

      <div className="metric-grid operations-summary-grid">
        {summaryCards(data).map((card) => (
          <Card className={`summary-card tone-${card.tone}`} title={card.title} key={card.title}>
            <strong>{card.value}</strong>
            <span>{card.detail}</span>
          </Card>
        ))}
      </div>

      <Card className="work-card operations-table-card" title="Datakilder">
        <Table<SourceRow>
          rowKey="key"
          size="small"
          columns={columns}
          dataSource={sources}
          pagination={{ pageSize: 25, showSizeChanger: true }}
          scroll={{ x: "max-content" }}
          locale={{ emptyText: "Ingen datakilder aa vise" }}
        />
      </Card>
    </Space>
  );
}
