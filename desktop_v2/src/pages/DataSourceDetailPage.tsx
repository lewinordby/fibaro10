import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Card, Descriptions, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link, useParams } from "react-router-dom";

import { fetchImportStatusDetail, type ImportStatusRun, type ImportStatusSource } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
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

function formatMinutes(value?: number | null) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  if (value < 60) return `${value} min`;
  if (value % (24 * 60) === 0) {
    const days = value / (24 * 60);
    return days === 1 ? "1 dag" : `${days} dager`;
  }
  if (value % 60 === 0) {
    const hours = value / 60;
    return hours === 1 ? "1 time" : `${hours} timer`;
  }
  return `${Math.floor(value / 60)} t ${value % 60} min`;
}

function recordText(imported?: number | null, total?: number | null) {
  if (imported !== null && imported !== undefined && total !== null && total !== undefined) return `${imported}/${total}`;
  if (total !== null && total !== undefined) return String(total);
  if (imported !== null && imported !== undefined) return String(imported);
  return "-";
}

function statusTag(status?: string | null) {
  const normalized = String(status || "unknown").toLowerCase();
  if (normalized === "ok") return <Tag color="green">OK</Tag>;
  if (normalized === "bad" || normalized === "error" || normalized === "failed") return <Tag color="red">Feil</Tag>;
  if (normalized === "warn") return <Tag color="gold">Treg</Tag>;
  if (normalized === "running") return <Tag color="blue">Kjører</Tag>;
  return <Tag>Ukjent</Tag>;
}

function runStatusTag(row: ImportStatusRun) {
  if (row.ok === true) return <Tag color="green">OK</Tag>;
  if (row.ok === false) return <Tag color="red">Feil</Tag>;
  return statusTag(row.status);
}

function sourceTitle(source: ImportStatusSource) {
  return source.title || source.job_name || "Datakilde";
}

const runColumns: ColumnsType<ImportStatusRun> = [
  {
    title: "Status",
    key: "status",
    width: 95,
    render: (_, row) => runStatusTag(row),
  },
  {
    title: "Ferdig",
    dataIndex: "finished_at",
    width: 170,
    sorter: (left, right) => new Date(left.finished_at || 0).getTime() - new Date(right.finished_at || 0).getTime(),
    render: formatDateTime,
  },
  {
    title: "Start",
    dataIndex: "started_at",
    width: 170,
    render: formatDateTime,
  },
  {
    title: "Rader",
    key: "records",
    width: 95,
    align: "right",
    render: (_, row) => recordText(row.records_imported, row.records_total),
  },
  {
    title: "Tid",
    dataIndex: "duration_seconds",
    width: 95,
    align: "right",
    render: formatDuration,
  },
  {
    title: "Melding",
    dataIndex: "message",
    ellipsis: true,
    render: (value) => value || "-",
  },
];

export default function DataSourceDetailPage() {
  const { jobName = "" } = useParams();
  const { data, loading, error } = useApiQuery(
    queryKeys.importStatusDetail(jobName),
    () => fetchImportStatusDetail(jobName),
    { refetchInterval: 60_000 },
  );

  if (!jobName) return <ErrorBlock error={new Error("Mangler datakilde")} />;
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const source = data.source;
  const title = sourceTitle(source);
  const latestMessage = source.message || source.status_text || source.age || "-";
  const dependencies = (source.dependencies || []).filter(Boolean);

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-datasource-detail-page">
      <PageHeader
        eyebrow={source.source_no ? `Datakilde #${source.source_no}` : "Datakilde"}
        title={title}
        description={source.description || source.job_name}
        meta={
          <Button icon={<ArrowLeftOutlined />} size="small">
            <Link to="/admin/datakilder">Datakilder</Link>
          </Button>
        }
      />

      <div className="metric-grid operations-summary-grid">
        <Card className="summary-card tone-status" title="Status">
          <strong>{source.status_text || source.status || "-"}</strong>
          <span>{statusTag(source.status)}</span>
        </Card>
        <Card className="summary-card tone-status" title="Sist OK">
          <strong>{formatDateTime(source.last_success_at)}</strong>
          <span>{source.age || "-"}</span>
        </Card>
        <Card className="summary-card tone-status" title="Neste forventet">
          <strong>{formatDateTime(source.next_expected_at)}</strong>
          <span>{source.source || source.category || "-"}</span>
        </Card>
        <Card className="summary-card tone-status" title="Siste kjøringer">
          <strong>{data.summary.ok}/{data.summary.runs}</strong>
          <span>{data.summary.failed ? `${data.summary.failed} feil` : "Ingen feil i listen"}</span>
        </Card>
      </div>

      <Card className="work-card datasource-explanation-card" title="Hvordan hentes datagrunnlaget">
        <div className="datasource-explanation-grid">
          <section>
            <Typography.Text type="secondary">Datagrunnlag</Typography.Text>
            <Typography.Paragraph>{source.data_flow || source.description || "-"}</Typography.Paragraph>
          </section>
          <section>
            <Typography.Text type="secondary">Kjøreplan</Typography.Text>
            <Typography.Paragraph>{source.schedule_text || "-"}</Typography.Paragraph>
          </section>
          <section>
            <Typography.Text type="secondary">Avhengige komponenter</Typography.Text>
            <div className="datasource-dependencies">
              {dependencies.length ? dependencies.map((item) => <Tag key={item}>{item}</Tag>) : <span>-</span>}
            </div>
          </section>
        </div>
      </Card>

      <Card className="work-card" title="Datakildeinfo">
        <Descriptions bordered column={{ xs: 1, sm: 2, xl: 3 }} size="small">
          <Descriptions.Item label="Jobbnavn">
            <Typography.Text code>{source.job_name}</Typography.Text>
          </Descriptions.Item>
          <Descriptions.Item label="Kategori">{source.category || "-"}</Descriptions.Item>
          <Descriptions.Item label="Kilde">{source.source || "-"}</Descriptions.Item>
          <Descriptions.Item label="Status">{statusTag(source.status)}</Descriptions.Item>
          <Descriptions.Item label="Sist kjørt">{formatDateTime(source.last_run_at)}</Descriptions.Item>
          <Descriptions.Item label="Siste feil">{formatDateTime(source.last_failed_at)}</Descriptions.Item>
          <Descriptions.Item label="Rader">{recordText(source.records_imported, source.records_total)}</Descriptions.Item>
          <Descriptions.Item label="Varighet">{formatDuration(source.duration_seconds)}</Descriptions.Item>
          <Descriptions.Item label="Forventet intervall">{formatMinutes(source.expected_interval_minutes)}</Descriptions.Item>
          <Descriptions.Item label="Varsel etter">{formatMinutes(source.warning_after_minutes)}</Descriptions.Item>
          <Descriptions.Item label="Alder">{source.age || "-"}</Descriptions.Item>
          <Descriptions.Item label="Melding" span={3}>
            {latestMessage}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card className="work-card operations-table-card" title="Siste kjøringer">
        <Table<ImportStatusRun>
          rowKey="id"
          size="small"
          columns={runColumns}
          dataSource={data.runs}
          pagination={{ pageSize: 25, showSizeChanger: true }}
          scroll={{ x: "max-content" }}
          locale={{ emptyText: "Ingen kjøringer lagret for denne datakilden" }}
        />
      </Card>
    </Space>
  );
}
