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

type DoorView = "oversikt" | "solrom" | "andre" | "radata";

const DOOR_VIEWS: DoorView[] = ["oversikt", "solrom", "andre", "radata"];
const SECTION_ORDER = ["1etg", "2etg", "vip", "bygg"];

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
      title: "Koblet",
      value: summary.configured,
      detail: `${summary.planned} klargjort uten HC3-id`,
      tone: summary.planned ? "unknown" : "ok",
    },
    {
      title: "Siste endring",
      value: summary.latestAgeLabel,
      detail: summary.latestChangeText,
      tone: "status",
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

function DoorStatusCards({ doors, compact = false }: { doors: DoorStatusItem[]; compact?: boolean }) {
  return (
    <div className={`doors-status-grid ${compact ? "is-compact" : ""}`}>
      {doors.map((door) => (
        <Card className={`door-status-card is-${door.state} ${door.isConfigured ? "" : "is-planned"}`} key={door.deviceKey}>
          <div className="door-status-icon">{stateIcon(door.state)}</div>
          <div className="door-status-main">
            <div className="door-status-title">
              <strong>{door.title}</strong>
              {door.isConfigured ? stateTag(door) : <Tag>Klargjort</Tag>}
            </div>
            <span>{door.isConfigured ? door.hc3Name : "Venter på HC3 device-id"}</span>
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
              <dt>Normal</dt>
              <dd>{door.normalStateLabel}</dd>
            </div>
            <div>
              <dt>Sensor</dt>
              <dd>{door.deviceId ? `HC3 ${door.deviceId}` : "Ikke koblet"}</dd>
            </div>
          </dl>
          {door.isConfigured || door.recentPeriods.length ? (
            <DoorRecentPeriods periods={door.recentPeriods} />
          ) : (
            <div className="door-status-planned">Klar i Fibaro10. Legg inn HC3-id når sensoren er montert.</div>
          )}
        </Card>
      ))}
    </div>
  );
}

function sortDoors(doors: DoorStatusItem[]) {
  return [...doors].sort((a, b) => a.sortOrder - b.sortOrder || a.title.localeCompare(b.title, "nb"));
}

function groupStats(doors: DoorStatusItem[]) {
  const configured = doors.filter((door) => door.isConfigured).length;
  const open = doors.filter((door) => door.state === "open").length;
  const unknown = doors.filter((door) => door.state === "unknown").length;
  return { configured, open, unknown };
}

function groupBySection(doors: DoorStatusItem[]) {
  const groups = new Map<string, { key: string; title: string; doors: DoorStatusItem[] }>();
  sortDoors(doors).forEach((door) => {
    const key = door.sectionKey || door.groupKey || "andre";
    const current = groups.get(key) ?? { key, title: door.sectionTitle || door.groupTitle || "Dører", doors: [] };
    current.doors.push(door);
    groups.set(key, current);
  });
  return [...groups.values()].sort((a, b) => {
    const aIndex = SECTION_ORDER.indexOf(a.key);
    const bIndex = SECTION_ORDER.indexOf(b.key);
    const aSort = aIndex === -1 ? 99 : aIndex;
    const bSort = bIndex === -1 ? 99 : bIndex;
    return aSort - bSort || a.title.localeCompare(b.title, "nb");
  });
}

function DoorGroupSection({
  title,
  doors,
  splitBySection = false,
}: {
  title: string;
  doors: DoorStatusItem[];
  splitBySection?: boolean;
}) {
  const stats = groupStats(doors);
  const sections = splitBySection ? groupBySection(doors) : [{ key: "all", title, doors: sortDoors(doors) }];

  return (
    <Card className="work-card doors-group-card">
      <div className="doors-group-header">
        <div>
          <Typography.Title level={3}>{title}</Typography.Title>
          <span>
            {doors.length} dører · {stats.configured} koblet · {stats.open} åpne · {stats.unknown} ukjent/klargjort
          </span>
        </div>
      </div>
      <div className="doors-section-stack">
        {sections.map((section) => (
          <section className="doors-section" key={section.key}>
            {splitBySection ? (
              <div className="doors-section-title">
                <strong>{section.title}</strong>
                <span>{section.doors.length} rom</span>
              </div>
            ) : null}
            <DoorStatusCards doors={section.doors} compact={splitBySection} />
          </section>
        ))}
      </div>
    </Card>
  );
}

export default function DoorsPage() {
  const { view = "oversikt" } = useParams();
  const { data, loading, error, fetching, refetch } = useApiQuery(queryKeys.doorStatus(), fetchDoorStatus, {
    refetchInterval: 30_000,
  });

  if (!DOOR_VIEWS.includes(view as DoorView)) return <Navigate to="/dorer/oversikt" replace />;
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const activeView = view as DoorView;
  const isRawView = activeView === "radata";
  const solromDoors = data.doors.filter((door) => door.groupKey === "solrom");
  const otherDoors = data.doors.filter((door) => door.groupKey !== "solrom");
  const visibleDoors =
    activeView === "solrom" ? solromDoors : activeView === "andre" ? otherDoors : data.doors;
  const visibleDeviceIds = new Set(visibleDoors.map((door) => door.deviceId).filter((id): id is number => id !== null));
  const visiblePeriods =
    activeView === "oversikt" || isRawView
      ? data.periods
      : data.periods.filter((period) => period.deviceId !== null && period.deviceId !== undefined && visibleDeviceIds.has(period.deviceId));
  const title =
    activeView === "solrom"
      ? "Dører · solrom"
      : activeView === "andre"
        ? "Dører · andre dører"
        : isRawView
          ? "Dører · rådata"
          : "Dører";

  return (
    <Space direction="vertical" size={14} className="page-stack doors-page">
      <PageHeader
        eyebrow="Bygg og drift"
        title={title}
        description={
          isRawView
            ? "Alle mottatte HC3-rader for feilsøking og kontroll av dørscenene."
            : "Åpne- og lukkeperioder fra magnetfølerne, med klargjorte plasser for de nye sensorene."
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

      {!isRawView && activeView === "oversikt" ? (
        <>
          <DoorGroupSection title="Solrom" doors={solromDoors} splitBySection />
          <DoorGroupSection title="Andre dører" doors={otherDoors} />
        </>
      ) : null}

      {!isRawView && activeView === "solrom" ? <DoorGroupSection title="Solrom" doors={solromDoors} splitBySection /> : null}

      {!isRawView && activeView === "andre" ? <DoorGroupSection title="Andre dører" doors={otherDoors} /> : null}

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
              dataSource={visiblePeriods}
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
