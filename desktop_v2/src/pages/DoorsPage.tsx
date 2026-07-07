import {
  CheckCircleOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  LockOutlined,
  ReloadOutlined,
  UnlockOutlined,
} from "@ant-design/icons";
import { Button, Card, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link } from "react-router-dom";

import { fetchDoorStatus, type DoorEventItem, type DoorStatusItem } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";

function stateTag(row: Pick<DoorStatusItem | DoorEventItem, "state" | "stateLabel">) {
  if (row.state === "closed") return <Tag color="green">Lukket</Tag>;
  if (row.state === "open") return <Tag color="gold">Åpen</Tag>;
  return <Tag>Ukjent</Tag>;
}

function stateIcon(state: DoorStatusItem["state"]) {
  if (state === "closed") return <LockOutlined />;
  if (state === "open") return <UnlockOutlined />;
  return <ExclamationCircleOutlined />;
}

function statusSummary(data: ReturnType<typeof buildSummaryCards>[number]) {
  return (
    <Card className={`door-summary-card tone-${data.tone}`} key={data.title}>
      <span>{data.title}</span>
      <strong>{data.value}</strong>
      <small>{data.detail}</small>
    </Card>
  );
}

function buildSummaryCards(summary: {
  total: number;
  known: number;
  open: number;
  closed: number;
  unknown: number;
  latestAgeLabel: string;
  events: number;
}) {
  return [
    { title: "Lukket", value: summary.closed, detail: `${summary.known}/${summary.total} med status`, tone: "ok" },
    { title: "Åpen", value: summary.open, detail: summary.open ? "Sjekk aktiv åpning" : "Ingen åpne nå", tone: summary.open ? "warn" : "ok" },
    { title: "Ukjent", value: summary.unknown, detail: summary.unknown ? "Mangler første hendelse" : "Alle kjent", tone: summary.unknown ? "unknown" : "ok" },
    { title: "Sist endret", value: summary.latestAgeLabel, detail: `${summary.events} hendelser lagret`, tone: "status" },
  ];
}

const eventColumns: ColumnsType<DoorEventItem> = [
  {
    title: "Tid",
    dataIndex: "timeLabel",
    width: 150,
    render: (value, row) => (
      <div className="door-event-time">
        <strong>{value || "-"}</strong>
        <span>{row.ageLabel}</span>
      </div>
    ),
  },
  {
    title: "Status",
    key: "status",
    width: 100,
    render: (_, row) => stateTag(row),
  },
  {
    title: "Dør",
    dataIndex: "deviceName",
    render: (value, row) => (
      <div className="door-event-name">
        <strong>{value || row.deviceKey || "-"}</strong>
        <span>{row.deviceId ? `HC3 ${row.deviceId}` : "-"}</span>
      </div>
    ),
  },
  {
    title: "Råverdi",
    dataIndex: "rawValue",
    width: 100,
    render: (value) => <Typography.Text code>{value ?? "-"}</Typography.Text>,
  },
  {
    title: "Batteri",
    dataIndex: "batteryLevel",
    width: 95,
    align: "right",
    render: (value) => (value === null || value === undefined ? "-" : `${Math.round(Number(value))}%`),
  },
];

export default function DoorsPage() {
  const { data, loading, error, fetching, refetch } = useApiQuery(queryKeys.doorStatus(), fetchDoorStatus, {
    refetchInterval: 30_000,
  });

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={14} className="page-stack doors-page">
      <PageHeader
        eyebrow="Bygg og drift"
        title="Dører"
        description="Magnetfølere fra HC3, oppdatert når dørene åpnes eller lukkes."
        meta={
          <Space size={8}>
            <Typography.Text type="secondary">Sist endret {data.summary.latestAgeLabel}</Typography.Text>
            <Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={() => refetch()}>
              Oppdater
            </Button>
          </Space>
        }
      />

      <div className="doors-summary-grid">
        {buildSummaryCards(data.summary).map(statusSummary)}
      </div>

      <div className="doors-status-grid">
        {data.doors.map((door) => (
          <Card className={`door-status-card is-${door.state}`} key={door.deviceKey}>
            <div className="door-status-icon">{stateIcon(door.state)}</div>
            <div className="door-status-main">
              <div className="door-status-title">
                <strong>{door.title}</strong>
                {stateTag(door)}
              </div>
              <span>{door.hc3Name}</span>
            </div>
            <dl>
              <div>
                <dt>Sist endret</dt>
                <dd>{door.lastChangedLabel}</dd>
              </div>
              <div>
                <dt>Alder</dt>
                <dd>{door.ageLabel}</dd>
              </div>
              <div>
                <dt>Batteri</dt>
                <dd>{door.batteryLabel}</dd>
              </div>
              <div>
                <dt>Råverdi</dt>
                <dd>{door.rawValue ?? "-"}</dd>
              </div>
            </dl>
          </Card>
        ))}
      </div>

      <Card
        className="work-card doors-table-card"
        title="Siste dørhendelser"
        extra={
          <Link to={data.datakildePath}>
            <Space size={6}>
              <DatabaseOutlined />
              Datakilde
            </Space>
          </Link>
        }
      >
        <Table<DoorEventItem>
          rowKey="id"
          size="small"
          columns={eventColumns}
          dataSource={data.events}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          scroll={{ x: "max-content" }}
          locale={{ emptyText: "Ingen dørhendelser logget ennå" }}
        />
      </Card>

      <Card className="doors-note-card">
        <Space>
          <CheckCircleOutlined className="status-ok" />
          <Typography.Text>
            HC3-scenen logger kun ved verdiendring. Lang tid siden siste hendelse betyr normalt bare at døren ikke har
            endret status.
          </Typography.Text>
        </Space>
      </Card>
    </Space>
  );
}
