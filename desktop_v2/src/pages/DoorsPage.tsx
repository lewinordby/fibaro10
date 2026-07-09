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
import { Link, Navigate, useParams } from "react-router-dom";

import {
  fetchDoorStatus,
  type DoorEventItem,
  type DoorPeriodItem,
  type DoorStatusItem,
  type DoorStatusResponse,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/doors.css";

type DoorStateRow = Pick<DoorStatusItem | DoorEventItem | DoorPeriodItem, "state" | "stateLabel">;

type SummaryCard = {
  title: string;
  value: string | number;
  detail: string;
  tone: "ok" | "warn" | "unknown" | "status";
};

function stateTag(row: DoorStateRow) {
  if (row.state === "closed") return <Tag color="green">{row.stateLabel || "Lukket"}</Tag>;
  if (row.state === "open") return <Tag color="gold">{row.stateLabel || "Åpen"}</Tag>;
  return <Tag>{row.stateLabel || "Ukjent"}</Tag>;
}

function stateIcon(state: DoorStatusItem["state"]) {
  if (state === "closed") return <LockOutlined />;
  if (state === "open") return <UnlockOutlined />;
  return <ExclamationCircleOutlined />;
}

function statusSummary(data: SummaryCard) {
  return (
    <Card className={`door-summary-card tone-${data.tone}`} key={data.title}>
      <span>{data.title}</span>
      <strong>{data.value}</strong>
      <small>{data.detail}</small>
    </Card>
  );
}

function buildSummaryCards(summary: DoorStatusResponse["summary"]): SummaryCard[] {
  return [
    {
      title: "Åpne nå",
      value: summary.open,
      detail: summary.open ? `${summary.activePeriods} aktiv åpning` : "Ingen åpne dører",
      tone: summary.open ? "warn" : "ok",
    },
    {
      title: "Lukket",
      value: summary.closed,
      detail: `${summary.known}/${summary.total} dører har kjent status`,
      tone: "ok",
    },
    {
      title: "Siste endring",
      value: summary.latestAgeLabel,
      detail: summary.latestChangeText,
      tone: "status",
    },
    {
      title: "Åpninger",
      value: summary.periods,
      detail: `${summary.changes} statusendringer, ${summary.events} råhendelser`,
      tone: summary.unknown ? "unknown" : "status",
    },
  ];
}

const periodColumns: ColumnsType<DoorPeriodItem> = [
  {
    title: "Dør",
    dataIndex: "title",
    render: (value, row) => (
      <div className="door-period-door">
        <strong>{value || row.deviceName || row.deviceKey || "-"}</strong>
        <span>{row.deviceId ? `HC3 ${row.deviceId}` : row.deviceKey || "-"}</span>
      </div>
    ),
  },
  {
    title: "Åpnet",
    dataIndex: "openedLabel",
    width: 150,
    render: (value, row) => (
      <div className="door-period-time">
        <strong>{value || "-"}</strong>
        <span>{row.openedAgeLabel}</span>
      </div>
    ),
  },
  {
    title: "Lukket",
    dataIndex: "closedLabel",
    width: 150,
    render: (value, row) => (
      <div className="door-period-time">
        <strong>{value || "-"}</strong>
        <span>{row.closedAgeLabel || (row.state === "open" ? "Pågår" : "")}</span>
      </div>
    ),
  },
  {
    title: "Var åpen",
    dataIndex: "durationLabel",
    width: 120,
    render: (value, row) => (
      <div className="door-period-duration">
        <strong>{value || "-"}</strong>
        {row.state === "open" ? <span>løpende</span> : null}
      </div>
    ),
  },
  {
    title: "Status",
    key: "status",
    width: 110,
    render: (_, row) => stateTag(row),
  },
];

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
    title: "Handling",
    dataIndex: "action",
    width: 105,
    render: (value) => value || "-",
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

function DoorRecentPeriods({ periods = [] }: { periods?: DoorPeriodItem[] }) {
  const visiblePeriods = periods.slice(0, 2);
  if (!visiblePeriods.length) {
    return (
      <div className="door-status-history">
        <div className="door-status-history-head">
          <span>Siste åpninger</span>
        </div>
        <div className="door-status-history-empty">Ingen åpne/lukkeperioder registrert</div>
      </div>
    );
  }

  return (
    <div className="door-status-history">
      <div className="door-status-history-head">
        <span>Siste åpninger</span>
        <small>{visiblePeriods.length} siste</small>
      </div>
      {visiblePeriods.map((period) => (
        <div className={`door-status-history-row is-${period.state}`} key={period.id}>
          <div className="door-status-history-times">
            <span>
              <UnlockOutlined />
              Åpnet {period.openedLabel}
            </span>
            <span>
              <LockOutlined />
              Lukket {period.closedLabel}
            </span>
          </div>
          <div className="door-status-history-duration">
            <strong>{period.durationLabel}</strong>
            <small>{period.state === "open" ? "pågår" : "åpen tid"}</small>
          </div>
        </div>
      ))}
    </div>
  );
}

function DoorStatusCards({ doors }: { doors: DoorStatusItem[] }) {
  return (
    <div className="doors-status-grid">
      {doors.map((door) => (
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
              <dt>Siste endring</dt>
              <dd>{door.lastChangedLabel}</dd>
            </div>
            <div>
              <dt>Siden</dt>
              <dd>{door.ageLabel}</dd>
            </div>
            <div>
              <dt>Batteri</dt>
              <dd>{door.batteryLabel}</dd>
            </div>
            <div>
              <dt>Sensor</dt>
              <dd>{door.deviceId ? `HC3 ${door.deviceId}` : door.deviceKey}</dd>
            </div>
          </dl>
          <DoorRecentPeriods periods={door.recentPeriods} />
        </Card>
      ))}
    </div>
  );
}

export default function DoorsPage() {
  const { view = "oversikt" } = useParams();
  const { data, loading, error, fetching, refetch } = useApiQuery(queryKeys.doorStatus(), fetchDoorStatus, {
    refetchInterval: 30_000,
  });

  if (view !== "oversikt" && view !== "radata") return <Navigate to="/dorer/oversikt" replace />;
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const isRawView = view === "radata";

  return (
    <Space direction="vertical" size={14} className="page-stack doors-page">
      <PageHeader
        eyebrow="Bygg og drift"
        title={isRawView ? "Dører · rådata" : "Dører"}
        description={
          isRawView
            ? "Alle mottatte HC3-rader for feilsøking og kontroll av dørscenene."
            : "Åpne- og lukkeperioder fra magnetfølerne, med varighet per åpning."
        }
        meta={
          <Space size={8}>
            <Typography.Text type="secondary">
              Sist endret {data.summary.latestAgeLabel} · {data.summary.latestChangeText}
            </Typography.Text>
            <Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={() => refetch()}>
              Oppdater
            </Button>
          </Space>
        }
      />

      <div className="doors-summary-grid">{buildSummaryCards(data.summary).map(statusSummary)}</div>

      <DoorStatusCards doors={data.doors} />

      {isRawView ? (
        <Card
          className="work-card doors-table-card"
          title="Råhendelser fra HC3"
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
      ) : (
        <>
          <Card
            className="work-card doors-table-card"
            title="Døråpninger"
            extra={
              <Link to="/dorer/radata">
                <Space size={6}>
                  <DatabaseOutlined />
                  Rådata
                </Space>
              </Link>
            }
          >
            <Table<DoorPeriodItem>
              rowKey="id"
              size="small"
              columns={periodColumns}
              dataSource={data.periods}
              pagination={{ pageSize: 20, showSizeChanger: true }}
              scroll={{ x: "max-content" }}
              locale={{ emptyText: "Ingen døråpninger logget ennå" }}
            />
          </Card>

          <Card className="doors-note-card">
            <Space>
              <CheckCircleOutlined className="status-ok" />
              <Typography.Text>
                Oversikten viser bare faktiske statusendringer. Gjentatte råmeldinger med samme status ligger under
                Rådata.
              </Typography.Text>
            </Space>
          </Card>
        </>
      )}
    </Space>
  );
}
