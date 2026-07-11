import {
  CheckCircleOutlined,
  DatabaseOutlined,
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

type DoorSemanticIconVariant = "solrom-free" | "solrom-busy" | "other-ok" | "other-alert" | "unknown";
type DoorSemanticBadge = "check" | "lock" | "alert" | "unknown";

function doorSemanticIconVariant(door: DoorStatusItem): DoorSemanticIconVariant {
  if (!door.isConfigured || door.state === "unknown") return "unknown";
  if (door.groupKey === "solrom") return door.state === "closed" ? "solrom-busy" : "solrom-free";
  return door.state === door.normalState ? "other-ok" : "other-alert";
}

function DoorSemanticIcon({ door, compact = false }: { door: DoorStatusItem; compact?: boolean }) {
  const variant = doorSemanticIconVariant(door);
  const badge: DoorSemanticBadge =
    variant === "solrom-free" || variant === "other-ok"
      ? "check"
      : variant === "solrom-busy"
        ? "lock"
        : variant === "other-alert"
          ? "alert"
          : "unknown";
  const isOpen = door.state === "open";

  return (
    <span className={`door-semantic-icon variant-${variant} ${compact ? "is-compact" : ""}`} aria-hidden="true">
      <svg viewBox="0 0 72 72" focusable="false">
        <path className="door-shadow" d="M17 61h34" />
        {isOpen ? (
          <g className="door-open-shape">
            <path className="door-frame" d="M18 58V14h30v44" />
            <path className="door-panel" d="M22 56V16l27 7v39z" />
            <path className="door-edge" d="M49 23v39" />
            <circle className="door-knob" cx="39" cy="38" r="2.2" />
          </g>
        ) : (
          <g className="door-closed-shape">
            <path className="door-panel" d="M18 58V14h32v44z" />
            <path className="door-frame" d="M18 14h32v44H18z" />
            <path className="door-edge" d="M26 14v44" />
            <circle className="door-knob" cx="41" cy="36" r="2.2" />
          </g>
        )}
        <g className={`door-badge door-badge-${badge}`}>
          <circle className="badge-bg" cx="55" cy="18" r="12" />
          {badge === "check" ? <path className="badge-mark" d="m49.5 18.5 4.3 4.3 8.8-9.2" /> : null}
          {badge === "lock" ? (
            <>
              <path className="badge-lock-body" d="M48.6 18.7h12.8v8.4H48.6z" />
              <path className="badge-mark" d="M51.2 18.7v-3.4a3.8 3.8 0 0 1 7.6 0v3.4" />
            </>
          ) : null}
          {badge === "alert" ? (
            <>
              <path className="badge-mark" d="M55 10.8v9.5" />
              <circle className="badge-dot" cx="55" cy="24.6" r="1.7" />
            </>
          ) : null}
          {badge === "unknown" ? <path className="badge-mark" d="M50 18h10" /> : null}
        </g>
      </svg>
    </span>
  );
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

function DoorStatusFacts({ door }: { door: DoorStatusItem }) {
  if (!door.isConfigured) {
    return (
      <div className="door-status-setup">
        <div>
          <span>Klargjort</span>
          <strong>Venter på HC3-id</strong>
        </div>
        <div className="door-status-chips">
          <span>{door.normalStateLabel}</span>
          <span>Sensor ikke koblet</span>
        </div>
      </div>
    );
  }

  return (
    <div className="door-status-facts">
      <div className="door-status-last-change">
        <span>Sist endret</span>
        <strong>{door.lastChangedLabel}</strong>
        <small>{door.ageLabel}</small>
      </div>
      <div className="door-status-chips">
        <span>{door.batteryLabel === "-" ? "Batteri ukjent" : `Batteri ${door.batteryLabel}`}</span>
        <span>{door.normalStateLabel}</span>
        <span>{door.deviceId ? `HC3 ${door.deviceId}` : "Ikke koblet"}</span>
      </div>
    </div>
  );
}

function DoorStatusCards({ doors, compact = false }: { doors: DoorStatusItem[]; compact?: boolean }) {
  return (
    <div className={`doors-status-grid ${compact ? "is-compact" : ""}`}>
      {doors.map((door) => (
        <Card className={`door-status-card is-${door.state} ${door.isConfigured ? "" : "is-planned"}`} key={door.deviceKey}>
          <DoorSemanticIcon door={door} />
          <div className="door-status-main">
            <div className="door-status-title">
              <strong>{door.title}</strong>
              {door.isConfigured ? stateTag(door) : <Tag>Klargjort</Tag>}
            </div>
            <span>{door.isConfigured ? door.hc3Name : "Venter på HC3 device-id"}</span>
          </div>
          <DoorStatusFacts door={door} />
          {door.isConfigured || door.recentPeriods.length ? (
            <DoorRecentPeriods periods={door.recentPeriods} />
          ) : (
            <div className="door-status-planned">Legg inn HC3 device-id når sensoren er montert.</div>
          )}
        </Card>
      ))}
    </div>
  );
}

type CompactDoorTone = "free" | "busy" | "normal" | "alert" | "unknown";

type CompactDoorDisplay = {
  tone: CompactDoorTone;
  status: string;
  detail: string;
  since: string;
  changedAt: string;
  meta: string[];
};

function compactDoorDisplay(door: DoorStatusItem): CompactDoorDisplay {
  const changedAt = door.lastChangedLabel && door.lastChangedLabel !== "-" ? door.lastChangedLabel : "-";
  const since = door.ageLabel && door.ageLabel !== "-" ? door.ageLabel : "Ikke registrert";
  const meta = [
    door.deviceId ? `HC3 ${door.deviceId}` : "Mangler HC3-id",
    door.batteryLabel && door.batteryLabel !== "-" ? `Batteri ${door.batteryLabel}` : "Batteri ukjent",
  ];

  if (!door.isConfigured) {
    return {
      tone: "unknown",
      status: "Klargjort",
      detail: "Venter på sensor",
      since: "Ikke i drift",
      changedAt: "-",
      meta,
    };
  }

  if (door.state === "unknown") {
    return {
      tone: "unknown",
      status: "Ukjent",
      detail: "Ingen sikker status",
      since,
      changedAt,
      meta,
    };
  }

  if (door.groupKey === "solrom") {
    const inUse = door.state === "closed";
    return {
      tone: inUse ? "busy" : "free",
      status: inUse ? "I bruk" : "Ledig",
      detail: inUse ? "Dør lukket" : "Dør åpen",
      since,
      changedAt,
      meta,
    };
  }

  const isNormal = door.state === door.normalState;
  return {
    tone: isNormal ? "normal" : "alert",
    status: door.stateLabel || (door.state === "closed" ? "Lukket" : "Åpen"),
    detail: isNormal ? "Som forventet" : `Forventet ${door.normalStateLabel.toLowerCase()}`,
    since,
    changedAt,
    meta,
  };
}

function compactStats(doors: DoorStatusItem[], mode: "solrom" | "other") {
  if (mode === "solrom") {
    const busy = doors.filter((door) => door.isConfigured && door.state === "closed").length;
    const free = doors.filter((door) => door.isConfigured && door.state === "open").length;
    const unknown = doors.length - busy - free;
    return `${busy} i bruk · ${free} ledige${unknown ? ` · ${unknown} ukjent/klargjort` : ""}`;
  }

  const normal = doors.filter((door) => door.isConfigured && door.state !== "unknown" && door.state === door.normalState).length;
  const alert = doors.filter((door) => door.isConfigured && door.state !== "unknown" && door.state !== door.normalState).length;
  const unknown = doors.length - normal - alert;
  return `${normal} normal · ${alert} avvik${unknown ? ` · ${unknown} ukjent/klargjort` : ""}`;
}

function CompactDoorCard({ door }: { door: DoorStatusItem }) {
  const display = compactDoorDisplay(door);
  return (
    <div className={`door-compact-card tone-${display.tone}`} title={`${door.title}: ${display.status}`}>
      <div className="door-compact-main">
        <DoorSemanticIcon door={door} compact />
        <div className="door-compact-name">
          <strong>{door.title}</strong>
          <span>{display.detail}</span>
        </div>
        <strong className="door-compact-status">{display.status}</strong>
      </div>
      <div className="door-compact-timegrid">
        <div>
          <span>Stått slik</span>
          <strong>{display.since}</strong>
        </div>
        <div>
          <span>Endret</span>
          <strong>{display.changedAt}</strong>
        </div>
      </div>
      <div className="door-compact-meta">
        {display.meta.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
    </div>
  );
}

function DoorCompactSection({
  title,
  doors,
  mode,
}: {
  title: string;
  doors: DoorStatusItem[];
  mode: "solrom" | "other";
}) {
  const sections = mode === "solrom" ? groupBySection(doors) : [{ key: "other", title: "Andre dører", doors: sortDoors(doors) }];

  return (
    <section className={`doors-compact-panel is-${mode}`}>
      <div className="doors-compact-header">
        <div>
          <Typography.Title level={3}>{title}</Typography.Title>
          <span>{compactStats(doors, mode)}</span>
        </div>
        {mode === "solrom" ? <small>Lukket = i bruk · Åpen = ledig</small> : <small>Grønn = normal · Rød = avvik</small>}
      </div>
      <div className="doors-compact-sections">
        {sections.map((section) => (
          <div className="doors-compact-section" key={section.key}>
            {mode === "solrom" ? (
              <div className="doors-compact-section-title">
                <strong>{section.title}</strong>
                <span>{compactStats(section.doors, mode)}</span>
              </div>
            ) : null}
            <div className="doors-compact-grid">
              {section.doors.map((door) => (
                <CompactDoorCard door={door} key={door.deviceKey} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function DoorOverviewBoard({ solromDoors, otherDoors }: { solromDoors: DoorStatusItem[]; otherDoors: DoorStatusItem[] }) {
  return (
    <div className="doors-compact-board">
      <DoorCompactSection title="Solrom" doors={solromDoors} mode="solrom" />
      <DoorCompactSection title="Andre dører" doors={otherDoors} mode="other" />
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
    <Card className="work-card doors-group-card doors-panel-card">
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

      {activeView === "oversikt" ? null : (
        <div className="doors-summary-grid">{buildSummaryCards(data.summary).map(statusSummary)}</div>
      )}

      {!isRawView && activeView === "oversikt" ? (
        <DoorOverviewBoard solromDoors={solromDoors} otherDoors={otherDoors} />
      ) : null}

      {!isRawView && activeView === "solrom" ? <DoorGroupSection title="Solrom" doors={solromDoors} splitBySection /> : null}

      {!isRawView && activeView === "andre" ? <DoorGroupSection title="Andre dører" doors={otherDoors} /> : null}

      {isRawView ? (
        <Card
          className="work-card doors-table-card doors-panel-card"
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
      ) : activeView !== "oversikt" ? (
        <>
          <Card
            className="work-card doors-table-card doors-panel-card"
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
      ) : null}
    </Space>
  );
}
