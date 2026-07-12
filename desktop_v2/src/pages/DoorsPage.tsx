import {
  ArrowLeftOutlined,
  BellOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  LockOutlined,
  ReloadOutlined,
  UnlockOutlined,
} from "@ant-design/icons";
import { Button, Card, DatePicker, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { ReactNode } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import dayjs from "dayjs";
import "dayjs/locale/nb";

import {
  fetchDoorSunroomOverview,
  fetchDoorSunroomRoomDetail,
  fetchDoorSunroomSessions,
  fetchDoorStatus,
  type DoorEventItem,
  type DoorPeriodItem,
  type DoorSunroomEnergyEvidence,
  type DoorSunroomDayEvent,
  type DoorSunroomOverviewPeriod,
  type DoorSunroomOverviewResponse,
  type DoorSunroomOverviewRoom,
  type DoorSunroomOverviewSession,
  type DoorSunroomRoomDetailResponse,
  type DoorSunroomRoomPeriod,
  type DoorSunroomSessionItem,
  type DoorSunroomSessionsResponse,
  type DoorStatusItem,
  type DoorStatusResponse,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { PeriodNavigator } from "../components/PeriodNavigator";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/doors.css";

dayjs.locale("nb");

type DoorStateRow = Pick<DoorStatusItem | DoorEventItem | DoorPeriodItem, "state" | "stateLabel">;

type SummaryCard = {
  title: string;
  value: string | number;
  detail: string;
  tone: "ok" | "warn" | "unknown" | "status";
};

type DoorView =
  | "oversikt"
  | "oversikt-ny"
  | "romkontroll"
  | "romkontroll-ny"
  | "romkontroll-ny2"
  | "soltimer"
  | "solrom"
  | "solrom-ny"
  | "andre"
  | "radata";

const DOOR_VIEWS: DoorView[] = [
  "oversikt",
  "oversikt-ny",
  "romkontroll",
  "romkontroll-ny",
  "romkontroll-ny2",
  "soltimer",
  "solrom",
  "solrom-ny",
  "andre",
  "radata",
];
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

function newOverviewSummary(doors: DoorStatusItem[], solromDoors: DoorStatusItem[], otherDoors: DoorStatusItem[]) {
  const connected = doors.filter((door) => door.isConfigured).length;
  const solromBusy = solromDoors.filter((door) => door.isConfigured && door.state === "closed").length;
  const solromFree = solromDoors.filter((door) => door.isConfigured && door.state === "open").length;
  const otherAlerts = otherDoors.filter(
    (door) => door.isConfigured && door.state !== "unknown" && door.state !== door.normalState,
  ).length;
  const unknown = doors.filter((door) => !door.isConfigured || door.state === "unknown").length;
  return [
    { label: "Solrom i bruk", value: solromBusy, tone: solromBusy ? "busy" : "neutral" },
    { label: "Solrom ledige", value: solromFree, tone: "free" },
    { label: "Avvik andre dører", value: otherAlerts, tone: otherAlerts ? "alert" : "normal" },
    { label: "Koblet", value: `${connected}/${doors.length}`, tone: unknown ? "unknown" : "normal" },
  ];
}

function doorBoardStatusText(door: DoorStatusItem, display: CompactDoorDisplay) {
  if (!door.isConfigured) return "Klargjort";
  if (door.state === "unknown") return "Ukjent";
  if (door.groupKey === "solrom") return display.status;
  return door.state === door.normalState ? "Normal" : "Avvik";
}

function DoorBoardCell({ door }: { door: DoorStatusItem }) {
  const display = compactDoorDisplay(door);
  const boardStatus = doorBoardStatusText(door, display);
  const stateLabel =
    door.groupKey === "solrom"
      ? display.detail
      : door.state === "unknown"
        ? "Ingen sikker status"
        : `${door.stateLabel} · ${display.detail}`;
  return (
    <div className={`door-board-cell tone-${display.tone}`} title={`${door.title}: ${boardStatus} · ${display.changedAt}`}>
      <div className="door-board-cell-head">
        <strong>{door.title}</strong>
        <span>{boardStatus}</span>
      </div>
      <div className="door-board-cell-state">{stateLabel}</div>
      <div className="door-board-cell-times">
        <span>
          <small>Stått slik</small>
          <strong>{display.since}</strong>
        </span>
        <span>
          <small>Endret</small>
          <strong>{display.changedAt}</strong>
        </span>
      </div>
    </div>
  );
}

function DoorBoardSection({
  title,
  doors,
  mode,
}: {
  title: string;
  doors: DoorStatusItem[];
  mode: "solrom" | "other";
}) {
  const stats = mode === "solrom" ? compactStats(doors, mode) : compactStats(doors, "other");
  return (
    <section className={`door-board-section is-${mode}`}>
      <div className="door-board-section-head">
        <strong>{title}</strong>
        <span>{stats}</span>
      </div>
      <div className="door-board-grid">
        {sortDoors(doors).map((door) => (
          <DoorBoardCell door={door} key={door.deviceKey} />
        ))}
      </div>
    </section>
  );
}

function DoorChangeFeed({ changes, doors }: { changes: DoorEventItem[]; doors: DoorStatusItem[] }) {
  const visibleChanges = changes.slice(0, 10);
  const titleByDeviceId = new Map(doors.filter((door) => door.deviceId !== null).map((door) => [door.deviceId, door.title]));
  const titleByDeviceKey = new Map(doors.map((door) => [door.deviceKey, door.title]));
  return (
    <aside className="door-change-feed">
      <div className="door-change-feed-head">
        <strong>Siste endringer</strong>
        <span>{visibleChanges.length} siste</span>
      </div>
      {visibleChanges.length ? (
        <div className="door-change-list">
          {visibleChanges.map((change) => (
            <div className={`door-change-item is-${change.state}`} key={change.id}>
              <div>
                <strong>
                  {(change.deviceId !== null && change.deviceId !== undefined ? titleByDeviceId.get(change.deviceId) : null) ||
                    (change.deviceKey ? titleByDeviceKey.get(change.deviceKey) : null) ||
                    change.deviceName ||
                    change.deviceKey ||
                    "Ukjent dør"}
                </strong>
                <span>{change.stateLabel || change.action || "-"}</span>
              </div>
              <time>{change.timeLabel || "-"}</time>
            </div>
          ))}
        </div>
      ) : (
        <div className="door-change-empty">Ingen statusendringer registrert ennå.</div>
      )}
    </aside>
  );
}

function DoorNewOverviewBoard({
  doors,
  solromDoors,
  otherDoors,
  changes,
}: {
  doors: DoorStatusItem[];
  solromDoors: DoorStatusItem[];
  otherDoors: DoorStatusItem[];
  changes: DoorEventItem[];
}) {
  const solromSections = groupBySection(solromDoors);
  const summary = newOverviewSummary(doors, solromDoors, otherDoors);
  return (
    <div className="doors-new-overview">
      <section className="door-board-command">
        <div>
          <Typography.Title level={3}>Dørstatus</Typography.Title>
          <span>Lukket solrom betyr i bruk. Andre dører varsler når de avviker fra normalposisjon.</span>
        </div>
        <div className="door-board-summary">
          {summary.map((item) => (
            <div className={`door-board-summary-item tone-${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <div className="door-board-layout">
        <div className="door-board-main">
          {solromSections.map((section) => (
            <DoorBoardSection title={section.title} doors={section.doors} mode="solrom" key={section.key} />
          ))}
          <DoorBoardSection title="Andre dører" doors={otherDoors} mode="other" />
        </div>
        <DoorChangeFeed changes={changes} doors={doors} />
      </div>
    </div>
  );
}

function sunroomSeverityLabel(severity: string) {
  if (severity === "alert") return "Rød";
  if (severity === "warning") return "Oransje";
  if (severity === "waiting") return "Venter";
  if (severity === "active") return "I bruk";
  if (severity === "free") return "Ledig";
  return "Ukjent";
}

function sunroomSeverityTag(item: DoorSunroomSessionItem) {
  if (item.severity === "alert") return <Tag color="red">Rød</Tag>;
  if (item.severity === "warning") return <Tag color="orange">Oransje</Tag>;
  if (item.severity === "waiting") return <Tag color="blue">Venter</Tag>;
  if (item.severity === "active") return <Tag color="gold">I bruk</Tag>;
  if (item.severity === "free") return <Tag color="green">Ledig</Tag>;
  return <Tag>Ukjent</Tag>;
}

function SunroomSessionFacts({ item }: { item: DoorSunroomSessionItem }) {
  const session = item.session;
  if (!session) {
    const title = !item.isOccupied ? "Ingen aktiv soltime" : item.missingSession ? "Ingen soltime funnet" : "Avventer Sun2";
    return (
      <div className="door-sunroom-empty-session">
        <strong>{title}</strong>
        <span>{item.detail}</span>
      </div>
    );
  }

  return (
    <div className="door-sunroom-session-facts">
      <div>
        <span>Betaling/start</span>
        <strong>{session.startedLabel}</strong>
      </div>
      <div>
        <span>Solen starter</span>
        <strong>{session.sunStartLabel}</strong>
      </div>
      <div>
        <span>Slutt</span>
        <strong>{session.endedLabel}</strong>
      </div>
      <div>
        <span>Forventet ut</span>
        <strong>{item.expectedExitLabel}</strong>
      </div>
    </div>
  );
}

function SunroomCard({ item }: { item: DoorSunroomSessionItem }) {
  const detailHref = `/dorer/soltimer?room=${encodeURIComponent(item.roomId || item.deviceKey)}`;
  return (
    <Link className={`door-sunroom-card severity-${item.severity}`} to={detailHref} aria-label={`Åpne detaljer for ${item.title}`}>
      <div className="door-sunroom-card-head">
        <div>
          <strong>{item.title}</strong>
          <span>{item.sectionTitle}</span>
        </div>
        {sunroomSeverityTag(item)}
      </div>

      <div className="door-sunroom-state-row">
        <div>
          <span>Dør</span>
          <strong>{item.doorState === "closed" ? "Lukket" : item.doorState === "open" ? "Åpen" : "Ukjent"}</strong>
          <small>{item.doorAgeLabel}</small>
        </div>
        <div>
          <span>Romstatus</span>
          <strong>{item.status}</strong>
          <small>{item.isOccupied ? `I bruk ${item.occupiedDurationLabel}` : "Ledig"}</small>
        </div>
      </div>

      <SunroomSessionFacts item={item} />

      <div className="door-sunroom-card-foot">
        <div>
          <ClockCircleOutlined />
          <span>
            {item.severity === "alert" || item.severity === "warning"
              ? `Overtid ${item.overstayLabel || "-"}`
              : item.session
                ? item.remainingLabel
                : item.doorChangedLabel}
          </span>
        </div>
        <span>Detaljer</span>
      </div>
    </Link>
  );
}

function sunroomMoney(value: number | null | undefined) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric) || numeric <= 0) return "-";
  return `${new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 }).format(numeric)} kr`;
}

function PeriodStatus({ severity, status }: { severity: string; status: string }) {
  const color =
    severity === "alert"
      ? "red"
      : severity === "warning"
        ? "orange"
        : severity === "active"
          ? "gold"
          : severity === "waiting"
            ? "blue"
            : "green";
  return <Tag color={color}>{status}</Tag>;
}

const sunroomPeriodColumns: ColumnsType<DoorSunroomRoomPeriod> = [
  {
    title: "Dør lukket",
    dataIndex: "closedLabel",
    width: 170,
    render: (value, row) => (
      <div className="door-room-time-cell">
        <strong>{value || "-"}</strong>
        <span>{row.closedAgeLabel}</span>
      </div>
    ),
  },
  {
    title: "Dør åpnet",
    dataIndex: "openedLabel",
    width: 170,
    render: (value, row) => (
      <div className="door-room-time-cell">
        <strong>{value || "-"}</strong>
        <span>{row.isActive ? "Pågår" : row.openedAgeLabel}</span>
      </div>
    ),
  },
  {
    title: "Varighet",
    dataIndex: "durationLabel",
    width: 110,
    render: (value) => <strong>{value || "-"}</strong>,
  },
  {
    title: "Soltime",
    key: "session",
    render: (_, row) =>
      row.session ? (
        <div className="door-room-session-cell">
          <Link to={row.session.href}>Betalt {row.session.startedLabel}</Link>
          <span>
            Solstart {row.session.sunStartLabel} · slutt {row.session.endedLabel}
          </span>
          <span>
            {row.session.durationMinutes ? `${row.session.durationMinutes} min` : "-"} · {sunroomMoney(row.session.paidAmountKr)}
          </span>
        </div>
      ) : (
        <span className="door-room-muted">Ingen koblet soltime</span>
      ),
  },
  {
    title: "Forventet ut",
    dataIndex: "expectedExitLabel",
    width: 170,
    render: (value, row) => (
      <div className="door-room-time-cell">
        <strong>{value || "-"}</strong>
        <span>{row.overstayLabel ? `Overtid ${row.overstayLabel}` : row.remainingLabel}</span>
      </div>
    ),
  },
  {
    title: "Status",
    key: "status",
    width: 130,
    render: (_, row) => <PeriodStatus severity={row.severity} status={row.status} />,
  },
];

function DoorSunroomRoomDetail({
  data,
  loading,
  error,
  fetching,
  refetch,
  onBack,
}: {
  data?: DoorSunroomRoomDetailResponse | null;
  loading: boolean;
  error: unknown;
  fetching: boolean;
  refetch: () => void;
  onBack: () => void;
}) {
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const current = data.currentPeriod;
  const history = data.periods.filter((period) => !period.isActive);

  return (
    <div className="door-room-detail">
      <section className={`door-room-hero severity-${data.room.severity}`}>
        <Button size="small" icon={<ArrowLeftOutlined />} onClick={onBack}>
          Til oversikt
        </Button>
        <div className="door-room-hero-main">
          <div>
            <Typography.Title level={3}>{data.room.title}</Typography.Title>
            <span>
              {data.room.sectionTitle} · {data.room.roomLabel} · dør {data.room.doorStateLabel.toLowerCase()}
            </span>
          </div>
          <div className="door-room-hero-status">
            {sunroomSeverityTag(data.room)}
            <strong>{data.room.status}</strong>
            <span>{data.room.detail}</span>
          </div>
        </div>
        <Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={() => refetch()}>
          Oppdater
        </Button>
      </section>

      <div className="door-room-summary-grid">
        <div>
          <span>Perioder</span>
          <strong>{data.summary.periods}</strong>
        </div>
        <div>
          <span>Soltimer</span>
          <strong>{data.summary.sessions}</strong>
        </div>
        <div>
          <span>Varsler</span>
          <strong>{data.summary.warnings + data.summary.alerts}</strong>
        </div>
        <div>
          <span>Uten dørmatch</span>
          <strong>{data.summary.sessionsWithoutDoor}</strong>
        </div>
      </div>

      <Card className="work-card door-room-current-card" title="Pågående">
        {current ? (
          <div className="door-room-current">
            <div>
              <span>Dør lukket</span>
              <strong>{current.closedLabel}</strong>
              <small>{current.durationLabel}</small>
            </div>
            <div>
              <span>Soltime</span>
              <strong>{current.session?.startedLabel || "Ikke funnet"}</strong>
              <small>
                {current.session
                  ? `Solstart ${current.session.sunStartLabel} · slutt ${current.session.endedLabel} · ${current.session.durationMinutes || "-"} min`
                  : current.detail}
              </small>
            </div>
            <div>
              <span>Forventet ut</span>
              <strong>{current.expectedExitLabel}</strong>
              <small>{current.overstayLabel ? `Overtid ${current.overstayLabel}` : current.remainingLabel}</small>
            </div>
            <div>
              <span>Status</span>
              <strong>{current.status}</strong>
              <small>{current.detail}</small>
            </div>
          </div>
        ) : (
          <div className="door-room-empty-current">Ingen pågående lukket-periode for dette rommet.</div>
        )}
      </Card>

      <Card className="work-card door-room-history-card" title={`Historikk siste ${data.days} dager`}>
        <Table<DoorSunroomRoomPeriod>
          rowKey="id"
          size="small"
          columns={sunroomPeriodColumns}
          dataSource={history}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          scroll={{ x: "max-content" }}
          locale={{ emptyText: "Ingen historiske dørperioder for valgt periode" }}
        />
      </Card>

      {data.sessionsWithoutDoor.length ? (
        <Card className="work-card door-room-unmatched-card" title="Soltimer uten matchende dørperiode">
          <div className="door-room-unmatched-list">
            {data.sessionsWithoutDoor.map((session) => (
              <Link to={session.href} key={session.id}>
                <strong>{session.startedLabel}</strong>
                <span>
                  Solstart {session.sunStartLabel} · slutt {session.endedLabel} · {session.durationMinutes || "-"} min · forventet ut{" "}
                  {session.expectedExitLabel}
                </span>
              </Link>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}

function energyEvidenceTag(energy?: DoorSunroomEnergyEvidence | null) {
  if (!energy) return <Tag>Ingen måling</Tag>;
  if (energy.status === "confirmed") return <Tag color="green">{energy.statusLabel}</Tag>;
  if (energy.status === "deviation") return <Tag color="orange">{energy.statusLabel}</Tag>;
  if (energy.quality === "overlap") return <Tag color="blue">{energy.qualityLabel}</Tag>;
  if (energy.status === "power_seen") return <Tag color="gold">{energy.statusLabel}</Tag>;
  return <Tag>{energy.statusLabel || energy.qualityLabel || "Ikke vurdert"}</Tag>;
}

function roomControlTone(room: DoorSunroomOverviewRoom) {
  const status = room.status;
  if (status.severity === "alert") return "alert";
  if (status.severity === "warning") return "warning";
  if (status.isOccupied) return "active";
  if (status.doorState === "open") return "free";
  return "unknown";
}

function roomControlStatusText(room: DoorSunroomOverviewRoom) {
  const status = room.status;
  if (status.severity === "alert") return "Kritisk";
  if (status.severity === "warning") return "Varsel";
  if (status.isOccupied) return "I bruk";
  if (status.doorState === "open") return "Ledig";
  return "Ukjent";
}

function roomControlPriority(room: DoorSunroomOverviewRoom) {
  const status = room.status;
  if (status.severity === "alert") return 0;
  if (status.severity === "warning") return 1;
  if (status.isOccupied && !room.latestPeriod?.session) return 2;
  if (room.sessionsWithoutDoor.length) return 3;
  if (status.isOccupied) return 4;
  return 5;
}

function roomControlGeneratedLabel(value?: string | null) {
  if (!value) return "ukjent tidspunkt";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function SunroomControlMetric({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value?: ReactNode;
  detail?: ReactNode;
  tone?: "ok" | "warn" | "alert" | "muted";
}) {
  return (
    <div className={`door-room-control-metric ${tone ? `tone-${tone}` : ""}`}>
      <span>{label}</span>
      <strong>{value || "-"}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function SunroomControlKeyLine({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value?: ReactNode;
  detail?: ReactNode;
  tone?: "ok" | "warn" | "alert" | "muted";
}) {
  return (
    <div className={`door-room-control-keyline ${tone ? `tone-${tone}` : ""}`}>
      <span>{label}</span>
      <strong>{value || "-"}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function SunroomControlTimeline({
  latest,
  status,
}: {
  latest?: DoorSunroomOverviewPeriod | null;
  status: DoorSunroomSessionItem;
}) {
  const exitTone =
    latest?.severity === "alert" || status.severity === "alert"
      ? "alert"
      : latest?.severity === "warning" || status.severity === "warning"
        ? "warn"
        : undefined;
  return (
    <div className="door-room-control-timeline" aria-label="Tidslinje for dør og soltime">
      <SunroomControlMetric label="Dør igjen" value={latest?.closedLabel || "-"} detail={latest?.durationLabel || status.doorAgeLabel} />
      <SunroomControlMetric label="Betalt" value={latest?.session?.startedLabel || "-"} detail={latest?.session ? "Sun2 registrert" : "Ingen match"} />
      <SunroomControlMetric label="Solstart" value={latest?.session?.sunStartLabel || "-"} detail={latest?.session ? "+3 min etter betaling" : "-"} />
      <SunroomControlMetric label="Sol slutt" value={latest?.session?.endedLabel || "-"} detail={latest?.session?.durationMinutes ? `${latest.session.durationMinutes} min soltid` : "-"} />
      <SunroomControlMetric
        label="Forventet ut"
        value={latest?.expectedExitLabel || status.expectedExitLabel || "-"}
        detail={latest?.overstayLabel ? `Overtid ${latest.overstayLabel}` : latest?.remainingLabel || status.remainingLabel || "-"}
        tone={exitTone}
      />
      <SunroomControlMetric label="Dør opp" value={latest?.openedLabel || "-"} detail={latest?.openedLabel ? "Avsluttet" : latest?.isActive ? "Pågår" : "-"} />
    </div>
  );
}

function SunroomControlSession({ session, expectedExitLabel }: { session: DoorSunroomOverviewSession; expectedExitLabel?: string | null }) {
  const energy = session.energy;
  return (
    <div className={`door-room-control-session energy-${energy?.status || energy?.quality || "missing"}`}>
      <div className="door-room-control-session-head">
        <div>
          <span>Sun2</span>
          <Link to={session.href}>
            {session.startedLabel} · {session.durationMinutes ? `${session.durationMinutes} min` : "-"} · {sunroomMoney(session.paidAmountKr)}
          </Link>
        </div>
        {session.hasDoorMatch ? <Tag color="green">Dørmatch</Tag> : <Tag color="orange">Uten dørmatch</Tag>}
      </div>
      <div className="door-room-control-facts">
        <SunroomControlMetric label="Solstart" value={session.sunStartLabel} />
        <SunroomControlMetric label="Sol slutt" value={session.endedLabel} />
        <SunroomControlMetric label="Forventet ut" value={expectedExitLabel || session.expectedExitLabel || "-"} />
      </div>
      <div className="door-room-control-energy">
        {energyEvidenceTag(energy)}
        <div>
          <strong>
            {energy ? `Start ${energy.startDelayLabel || "-"} · netto ${energy.estimatedNetLabel || "-"}` : "Ingen energivurdering"}
          </strong>
          <span>
            {energy
              ? `${energy.detail || energy.qualityLabel || ""}${energy.samplesCount ? ` · ${energy.samplesCount} samples` : ""}`
              : "Strøm kan bare vurderes når det finnes HC3-samples rundt solstart."}
          </span>
        </div>
      </div>
      {session.userName || session.sun2UserId ? (
        <small>
          {session.userName || "Ukjent medlem"}
          {session.sun2UserId ? ` · ${session.sun2UserId}` : ""}
          {session.sun2BedId ? ` · seng ${session.sun2BedId}` : ""}
        </small>
      ) : null}
    </div>
  );
}

function RoomControlAttention({ rooms }: { rooms: DoorSunroomOverviewRoom[] }) {
  const items = [...rooms]
    .filter((room) => roomControlPriority(room) < 4)
    .sort((a, b) => roomControlPriority(a) - roomControlPriority(b) || a.displayRoomNumber - b.displayRoomNumber)
    .slice(0, 6);

  return (
    <section className="door-room-control-attention">
      <div className="door-room-control-attention-head">
        <strong>Trenger oppfølging</strong>
        <span>{items.length ? `${items.length} rom` : "Ingen aktive avvik"}</span>
      </div>
      {items.length ? (
        <div className="door-room-control-attention-list">
          {items.map((room) => {
            const status = room.status;
            const latest = room.latestPeriod;
            const detailHref = room.roomId ? `/dorer/soltimer?room=${encodeURIComponent(room.roomId)}` : "/dorer/soltimer";
            const detail =
              status.severity === "alert" || status.severity === "warning"
                ? status.detail || latest?.detail || status.remainingLabel
                : !latest?.session && status.isOccupied
                  ? "Dør lukket, men ingen Sun2-time er koblet ennå"
                  : room.sessionsWithoutDoor.length
                    ? `${room.sessionsWithoutDoor.length} soltime(r) uten dørmatch`
                    : status.detail;
            return (
              <Link className={`door-room-control-attention-item tone-${roomControlTone(room)}`} to={detailHref} key={room.deviceKey}>
                <strong>Rom {room.displayRoomNumber}</strong>
                <span>{roomControlStatusText(room)}</span>
                <small>{detail || status.doorAgeLabel || "-"}</small>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="door-room-control-attention-ok">Ingen rom er over forventet tid, og ingen nye soltimer mangler dørmatch.</div>
      )}
    </section>
  );
}

function SunroomControlRoomCard({ room }: { room: DoorSunroomOverviewRoom }) {
  const status = room.status;
  const latest = room.latestPeriod;
  const session = latest?.session as DoorSunroomOverviewSession | null | undefined;
  const energy = latest?.energy;
  const detailHref = room.roomId ? `/dorer/soltimer?room=${encodeURIComponent(room.roomId)}` : "/dorer/soltimer";
  const recentHistory = room.periods.filter((period) => period.id !== latest?.id).slice(0, 1);
  const tone = roomControlTone(room);
  const exitTone =
    latest?.severity === "alert" || status.severity === "alert"
      ? "alert"
      : latest?.severity === "warning" || status.severity === "warning"
        ? "warn"
        : undefined;

  return (
    <article className={`door-room-control-card tone-${tone}`}>
      <div className="door-room-control-head">
        <div>
          <span>{room.sectionTitle}</span>
          <strong>Rom {room.displayRoomNumber}</strong>
        </div>
        <div className="door-room-control-head-status">
          <span className={`door-room-control-state-pill tone-${tone}`}>{roomControlStatusText(room)}</span>
          <Link to={detailHref}>Detaljer</Link>
        </div>
      </div>

      <div className="door-room-control-now">
        <SunroomControlKeyLine
          label="Dør"
          value={status.doorStateLabel}
          detail={status.doorAgeLabel}
          tone={status.doorState === "closed" ? "warn" : "ok"}
        />
        <SunroomControlKeyLine
          label={status.isOccupied ? "Pågår" : "Status"}
          value={status.isOccupied ? status.occupiedDurationLabel || status.status : status.status}
          detail={status.detail || (status.isOccupied ? "Rommet er i bruk" : "Ledig")}
          tone={status.severity === "alert" ? "alert" : status.severity === "warning" ? "warn" : status.isOccupied ? "warn" : "ok"}
        />
        <SunroomControlKeyLine
          label="Forventet ut"
          value={latest?.expectedExitLabel || status.expectedExitLabel || "-"}
          detail={latest?.overstayLabel ? `Overtid ${latest.overstayLabel}` : latest?.remainingLabel || status.remainingLabel || "-"}
          tone={exitTone}
        />
      </div>

      <SunroomControlTimeline latest={latest} status={status} />

      {session ? (
        <SunroomControlSession session={{ ...session, energy: energy || undefined, hasDoorMatch: true }} expectedExitLabel={latest?.expectedExitLabel} />
      ) : latest ? (
        <div className="door-room-control-empty">
          <strong>{latest.status}</strong>
          <span>{latest.detail}</span>
        </div>
      ) : room.recentSessions[0] ? (
        <SunroomControlSession session={room.recentSessions[0]} />
      ) : (
        <div className="door-room-control-empty">
          <strong>Ingen nylig aktivitet</strong>
          <span>Ingen dørperiode eller soltime i valgt periode.</span>
        </div>
      )}

      <div className="door-room-control-history">
        <div className="door-room-control-history-head">
          <span>{room.summary.sessions} soltimer i perioden</span>
          <strong>{room.summary.matched} dørmatch</strong>
          <small>{room.summary.energyConfirmed} strøm OK</small>
        </div>
        {recentHistory.length ? (
          recentHistory.map((period) => (
            <div className="door-room-control-history-row" key={period.id}>
              <span>
                {period.closedLabel} - {period.openedLabel || "pågår"}
              </span>
              <strong>{period.session?.startedLabel || period.status}</strong>
              <small>{period.session ? `${period.session.durationMinutes || "-"} min · ${sunroomMoney(period.session.paidAmountKr)}` : period.detail}</small>
            </div>
          ))
        ) : (
          <div className="door-room-control-history-empty">Ingen tidligere dørperioder i valgt periode.</div>
        )}
      </div>
    </article>
  );
}

function DoorSunroomRoomControlBoard({
  data,
  loading,
  error,
  fetching,
  refetch,
  days,
  onDaysChange,
}: {
  data?: DoorSunroomOverviewResponse | null;
  loading: boolean;
  error: unknown;
  fetching: boolean;
  refetch: () => void;
  days: number;
  onDaysChange: (days: number) => void;
}) {
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const freeRooms = data.rooms.filter((room) => room.status.doorState === "open").length;
  const warningRooms = data.summary.warnings + data.summary.alerts;

  return (
    <div className="door-room-control-board">
      <section className="door-room-control-command">
        <div>
          <Typography.Title level={3}>Romkontroll</Typography.Title>
          <span>Oppdatert {roomControlGeneratedLabel(data.generatedAt)}</span>
        </div>
        <div className="door-room-control-actions">
          <Space.Compact>
            {[1, 2, 7, 14].map((value) => (
              <Button key={value} size="small" type={value === days ? "primary" : "default"} onClick={() => onDaysChange(value)}>
                {value === 1 ? "24 t" : `${value} d`}
              </Button>
            ))}
          </Space.Compact>
          <Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={() => refetch()}>
            Oppdater
          </Button>
        </div>
      </section>

      <div className="door-room-control-summary">
        <div className="tone-free">
          <span>Ledige</span>
          <strong>{freeRooms}</strong>
        </div>
        <div className="tone-active">
          <span>I bruk</span>
          <strong>{data.summary.active}</strong>
        </div>
        <div className={warningRooms ? "tone-alert" : "tone-ok"}>
          <span>Varsler</span>
          <strong>{warningRooms}</strong>
        </div>
        <div className="tone-ok">
          <span>Dørmatch</span>
          <strong>{data.summary.doorMatches}/{data.summary.sessions}</strong>
        </div>
        <div className="tone-ok">
          <span>Strøm OK</span>
          <strong>{data.summary.energyConfirmed}</strong>
        </div>
        <div className={data.summary.sessionsWithoutDoor ? "tone-warn" : "tone-ok"}>
          <span>Uten dør</span>
          <strong>{data.summary.sessionsWithoutDoor}</strong>
        </div>
      </div>

      <RoomControlAttention rooms={data.rooms} />

      <div className="door-room-control-grid">
        {[...data.rooms].sort((a, b) => a.displayRoomNumber - b.displayRoomNumber).map((room) => (
          <SunroomControlRoomCard room={room} key={room.deviceKey} />
        ))}
      </div>
    </div>
  );
}

function RoomVisualTimeline({ room }: { room: DoorSunroomOverviewRoom }) {
  const latest = room.latestPeriod;
  const session = latest?.session || room.recentSessions[0] || null;
  const expected = latest?.expectedExitAt || session?.expectedExitAt || room.status.expectedExitAt;
  const segments: Array<[string, number, number]> = [];
  if (latest?.closedAt) segments.push(["door", 0, 100]);
  if (session?.sunStartAt && session.endedAt) segments.push(["sun", 32, 42]);
  if (session?.endedAt && expected) segments.push(["exit", 74, 14]);
  if (expected && room.status.isOccupied && (latest?.overstaySeconds || room.status.overstaySeconds || 0) > 0) {
    segments.push(["overdue", 88, 12]);
  }
  if (!segments.length) {
    return <div className="door-room-visual-timeline" />;
  }

  return (
    <div className="door-room-visual-timeline">
      <div className="door-room-visual-track">
        {segments.map(([kind, left, width]) => (
          <div className={`door-room-visual-segment kind-${kind}`} key={kind} style={{ left: `${left}%`, width: `${width}%` }} />
        ))}
      </div>
    </div>
  );
}

function RoomVisualCard({ room }: { room: DoorSunroomOverviewRoom }) {
  const status = room.status;
  const latest = room.latestPeriod;
  const session = latest?.session || room.recentSessions[0] || null;
  const tone = roomControlTone(room);

  return (
    <article className={`door-room-visual-card tone-${tone}`}>
      <div className="door-room-visual-head">
        <div className="door-room-visual-number">
          Rom {room.displayRoomNumber}
        </div>
        <div className="door-room-visual-title">
          <strong>{room.sectionTitle}</strong>
          <span>{session ? `${session.durationMinutes || "-"} min · ${sunroomMoney(session.paidAmountKr)}` : status.detail || room.roomLabel}</span>
        </div>
        <span className={`door-room-visual-status tone-${tone}`}>
          {roomControlStatusText(room)}
        </span>
      </div>

      <RoomVisualTimeline room={room} />
    </article>
  );
}

function DoorSunroomVisualControlBoard({
  data,
  loading,
  error,
}: {
  data?: DoorSunroomOverviewResponse | null;
  loading: boolean;
  error: unknown;
}) {
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const rooms = data.rooms;

  return (
    <div className="door-room-visual-grid">
      {rooms.map((room) => (
        <RoomVisualCard room={room} key={room.deviceKey} />
      ))}
    </div>
  );
}

const SUNROOM_OPEN_HOUR = 7;
const SUNROOM_CLOSE_HOUR = 23;

type PrecisionMarker = {
  key: string;
  kind: string;
  label: string;
  time: string | null;
  detail?: string | null;
};

type PrecisionSegment = {
  key: string;
  kind: string;
  start: string | null;
  end: string | null;
};

function parseTimelineMs(value?: string | null) {
  if (!value) return null;
  const ms = Date.parse(value);
  return Number.isFinite(ms) ? ms : null;
}

function timelineClockLabel(value?: string | null) {
  const ms = parseTimelineMs(value);
  if (ms === null) return "-";
  return new Date(ms).toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function percentBetween(value: number, start: number, end: number) {
  if (end <= start) return 0;
  return Math.max(0, Math.min(100, ((value - start) / (end - start)) * 100));
}

function openingTimelineWindow(dayValue?: string | null) {
  const parsed = dayValue ? dayjs(dayValue) : dayjs();
  const day = parsed.isValid() ? parsed : dayjs();
  const start = day.hour(SUNROOM_OPEN_HOUR).minute(0).second(0).millisecond(0);
  const end = day.hour(SUNROOM_CLOSE_HOUR).minute(0).second(0).millisecond(0);
  return {
    startMs: start.valueOf(),
    endMs: end.valueOf(),
    startIso: start.toISOString(),
    endIso: end.toISOString(),
  };
}

function precisionMarkersForPeriod(period?: DoorSunroomOverviewPeriod | null, session?: DoorSunroomOverviewSession | null) {
  const markers: PrecisionMarker[] = [];
  if (period?.closedAt) markers.push({ key: "door-closed", kind: "door-closed", label: "Dør stengt", time: period.closedAt });
  if (period?.openedAt) markers.push({ key: "door-open", kind: "door-open", label: "Dør åpen", time: period.openedAt });
  if (session?.sunStartAt) markers.push({ key: "sun-start", kind: "sun-start", label: "Sol start", time: session.sunStartAt });
  if (session?.endedAt) markers.push({ key: "sun-end", kind: "sun-end", label: "Sol slutt", time: session.endedAt });
  const entranceMarkers = period?.entranceMarkers?.length ? period.entranceMarkers : session?.entranceMarkers || [];
  const powerMarkers = period?.powerMarkers?.length ? period.powerMarkers : session?.powerMarkers || [];
  for (const marker of [...entranceMarkers, ...powerMarkers]) {
    markers.push({
      key: `${marker.kind}-${marker.eventId || marker.time}`,
      kind: marker.kind,
      label: marker.label,
      time: marker.time,
      detail: marker.deltaLabel || marker.valueLabel || marker.detail,
    });
  }
  return markers.sort((a, b) => (parseTimelineMs(a.time) || 0) - (parseTimelineMs(b.time) || 0));
}

function roomControlDateLabel(value?: string | null) {
  if (!value) return "Dagens hendelser";
  const date = new Date(value.includes("T") ? value : `${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("nb-NO", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" });
}

function normalizedDayParam(value?: string | null) {
  const parsed = value ? dayjs(value) : dayjs();
  return parsed.isValid() ? parsed.format("YYYY-MM-DD") : dayjs().format("YYYY-MM-DD");
}

function roomControlEventTone(kind?: string | null, fallback?: string | null) {
  if (fallback) return fallback;
  if (!kind) return "neutral";
  if (kind.startsWith("door_")) return "door";
  if (kind.startsWith("sun_")) return "sun";
  if (kind.startsWith("entrance_")) return "entrance";
  if (kind.startsWith("power_")) return "power";
  return "neutral";
}

function roomDailyEventsFallback(room: DoorSunroomOverviewRoom) {
  const latest = room.latestPeriod;
  const session = latest?.session || room.recentSessions[0] || null;
  const markers = precisionMarkersForPeriod(latest, session as DoorSunroomOverviewSession | null);
  return markers.map((marker, index): DoorSunroomDayEvent => ({
    id: `${marker.key}-${index}`,
    kind: marker.kind,
    label: marker.label,
    time: marker.time,
    timeLabel: marker.time ? timelineClockLabel(marker.time) : "-",
    detail: marker.detail || null,
    source: null,
    tone: roomControlEventTone(marker.kind),
  }));
}

function roomDailyEvents(room: DoorSunroomOverviewRoom, order: "asc" | "desc" = "asc") {
  const events = room.dayEvents?.length ? room.dayEvents : roomDailyEventsFallback(room);
  return [...events].sort((a, b) => {
    const diff = (parseTimelineMs(a.time) || 0) - (parseTimelineMs(b.time) || 0);
    return order === "asc" ? diff : -diff;
  });
}

function DoorRoomDailyFact({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "ok" | "warn" | "alert" | "muted";
}) {
  return (
    <div className={`door-room-daily-fact ${tone ? `tone-${tone}` : ""}`}>
      <span>{label}</span>
      <strong>{value || "-"}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function DoorRoomDailyTimeline({
  room,
  generatedAt,
  dayStart,
}: {
  room: DoorSunroomOverviewRoom;
  generatedAt?: string | null;
  dayStart?: string | null;
}) {
  const latest = room.latestPeriod;
  const session = latest?.session || room.recentSessions[0] || null;
  const timelineDay = dayStart || session?.sunStartAt || latest?.closedAt || generatedAt;
  const { startMs: axisStart, endMs: axisEnd, startIso, endIso } = openingTimelineWindow(timelineDay);
  const generatedMs = parseTimelineMs(generatedAt) || Date.now();
  const markers = roomDailyEvents(room, "asc").filter((event) => {
    const ms = parseTimelineMs(event.time);
    return ms !== null && ms >= axisStart && ms <= axisEnd;
  });
  const segments: PrecisionSegment[] = [];
  for (const period of room.periods || []) {
    if (!period.closedAt) continue;
    const activeEnd = generatedMs >= axisStart && generatedMs <= axisEnd ? generatedAt || null : endIso;
    segments.push({
      key: `door-${period.id}`,
      kind: "door",
      start: period.closedAt,
      end: period.openedAt || activeEnd,
    });
  }
  const sessions = new Map<string, DoorSunroomOverviewSession>();
  if (session?.id) sessions.set(String(session.id), session as DoorSunroomOverviewSession);
  for (const period of room.periods || []) {
    if (period.session?.id) sessions.set(String(period.session.id), period.session);
  }
  for (const row of room.recentSessions || []) {
    if (row.id) sessions.set(String(row.id), row);
  }
  for (const row of sessions.values()) {
    if (row.sunStartAt && row.endedAt) {
      segments.push({ key: `sun-${row.id}`, kind: "sun", start: row.sunStartAt, end: row.endedAt });
    }
  }

  return (
    <div className="door-room-daily-timeline">
      <div className="door-room-daily-timeline-head">
        <span>Åpningstid</span>
        <strong>{SUNROOM_OPEN_HOUR.toString().padStart(2, "0")}:00-{SUNROOM_CLOSE_HOUR}:00</strong>
      </div>
      <div className="door-room-daily-track">
        {segments.map((segment) => {
          const start = parseTimelineMs(segment.start);
          const end = parseTimelineMs(segment.end);
          if (start === null || end === null) return null;
          const left = percentBetween(Math.max(start, axisStart), axisStart, axisEnd);
          const right = percentBetween(Math.min(end, axisEnd), axisStart, axisEnd);
          if (right <= left) return null;
          return <span className={`daily-segment kind-${segment.kind}`} key={segment.key} style={{ left: `${left}%`, width: `${right - left}%` }} />;
        })}
        {markers.map((marker, index) => {
          const ms = parseTimelineMs(marker.time);
          if (ms === null) return null;
          return (
            <span
              className={`daily-marker kind-${marker.kind || "neutral"}`}
              key={`${marker.id || marker.kind || "marker"}-${marker.time || index}`}
              style={{ left: `${percentBetween(ms, axisStart, axisEnd)}%` }}
              title={`${marker.label} ${timelineClockLabel(marker.time)}${marker.detail ? ` - ${marker.detail}` : ""}`}
            />
          );
        })}
      </div>
      <div className="door-room-daily-scale">
        <span>{timelineClockLabel(startIso)}</span>
        <span>{timelineClockLabel(endIso)}</span>
      </div>
    </div>
  );
}

function DoorRoomDailyEventsTable({ room }: { room: DoorSunroomOverviewRoom }) {
  const events = roomDailyEvents(room, "desc");
  if (!events.length) {
    return <div className="door-room-daily-empty-line">Ingen hendelser registrert for denne datoen.</div>;
  }

  return (
    <table className="door-room-daily-events">
      <thead>
        <tr>
          <th>Tid</th>
          <th>Hendelse</th>
          <th>Kilde</th>
          <th>Detalj</th>
        </tr>
      </thead>
      <tbody>
        {events.map((event) => {
          const tone = roomControlEventTone(event.kind, event.tone);
          return (
            <tr className={`tone-${tone}`} key={event.id}>
              <td>{timelineClockLabel(event.time)}</td>
              <td>
                <span className={`door-room-daily-dot tone-${tone}`} />
                {event.label}
              </td>
              <td>{event.source || "-"}</td>
              <td>{event.detail || "-"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function DoorRoomDailyCard({
  room,
  generatedAt,
  dayStart,
}: {
  room: DoorSunroomOverviewRoom;
  generatedAt?: string | null;
  dayStart?: string | null;
}) {
  const latest = room.latestPeriod;
  const session = latest?.session || room.recentSessions[0] || null;
  const tone = roomControlTone(room);
  const isActive = latest?.isActive || room.status.isOccupied;
  const progressLabel = isActive
    ? room.status.occupiedDurationLabel || latest?.durationLabel || "-"
    : latest?.durationLabel || room.status.doorAgeLabel || "-";
  const progressDetail = isActive ? "Pågår" : latest?.openedLabel ? "Avsluttet" : room.status.status;
  const expectedTone =
    latest?.severity === "alert" || room.status.severity === "alert"
      ? "alert"
      : latest?.severity === "warning" || room.status.severity === "warning"
        ? "warn"
        : undefined;

  return (
    <article className={`door-room-daily-card tone-${tone}`}>
      <div className="door-room-daily-head">
        <div>
          <span>{room.sectionTitle}</span>
          <strong>Rom {room.displayRoomNumber}</strong>
        </div>
        <span className={`door-room-control-state-pill tone-${tone}`}>{roomControlStatusText(room)}</span>
      </div>

      <div className="door-room-daily-facts">
        <DoorRoomDailyFact label="Dør lukket" value={timelineClockLabel(latest?.closedAt)} detail={latest?.closedAgeLabel || "-"} tone={latest?.closedAt ? "warn" : "muted"} />
        <DoorRoomDailyFact label="Pågår" value={progressLabel} detail={progressDetail} tone={isActive ? "warn" : "ok"} />
        <DoorRoomDailyFact
          label="Forventet ut"
          value={timelineClockLabel(latest?.expectedExitAt || session?.expectedExitAt || room.status.expectedExitAt)}
          detail={latest?.overstayLabel ? `Overtid ${latest.overstayLabel}` : latest?.remainingLabel || room.status.remainingLabel || "-"}
          tone={expectedTone}
        />
      </div>

      <DoorRoomDailyTimeline room={room} generatedAt={generatedAt} dayStart={dayStart} />
      <DoorRoomDailyEventsTable room={room} />
    </article>
  );
}

function DoorSunroomDailyControlBoard({
  data,
  loading,
  error,
  selectedDay,
  selectedRoomId,
  onDayChange,
  onRoomChange,
}: {
  data?: DoorSunroomOverviewResponse | null;
  loading: boolean;
  error: unknown;
  selectedDay: string;
  selectedRoomId: string;
  onDayChange: (day: string) => void;
  onRoomChange: (roomId: string) => void;
}) {
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;
  const rooms = [...data.rooms].sort((a, b) => a.displayRoomNumber - b.displayRoomNumber);
  const selectedDayValue = dayjs(selectedDay);
  const today = dayjs().startOf("day");
  const activeRoom =
    rooms.find((room) => (room.roomId || room.deviceKey) === selectedRoomId) ||
    rooms.find((room) => (room.dayEvents || []).length > 0) ||
    rooms[0];
  const activeKey = activeRoom?.roomId || activeRoom?.deviceKey || "";
  const dayStats = {
    roomsWithActivity: data.summary.dayActivityRooms ?? rooms.filter((room) => (room.dayEvents || []).length > 0).length,
    events: data.summary.dayEvents ?? rooms.reduce((sum, room) => sum + (room.dayEvents || []).length, 0),
    sessions: data.summary.daySessions ?? rooms.reduce((sum, room) => sum + (room.dayEvents || []).filter((event) => event.kind === "sun_start").length, 0),
    powerEvents:
      data.summary.dayPowerEvents ??
      rooms.reduce((sum, room) => sum + (room.dayEvents || []).filter((event) => event.kind.startsWith("power_")).length, 0),
  };

  const tabItems = rooms.map((room) => {
    const roomKey = room.roomId || room.deviceKey;
    const activityCount = room.dayEvents?.length || 0;
    return {
      key: roomKey,
      label: (
        <span className={`door-room-day-tab-label ${activityCount ? "has-activity" : ""}`}>
          Rom {room.displayRoomNumber}
          {activityCount ? <small>{activityCount}</small> : null}
        </span>
      ),
      children: <DoorRoomDailyCard room={room} generatedAt={data.generatedAt} dayStart={data.dayStart || data.dayDate || selectedDay} />,
    };
  });

  const changeDay = (nextDay: dayjs.Dayjs) => {
    onDayChange(nextDay.format("YYYY-MM-DD"));
  };

  return (
    <div className="door-room-daily-board">
      <section className="door-room-daily-date">
        <div>
          <span>Dato</span>
          <strong>{roomControlDateLabel(data.dayDate || selectedDay)}</strong>
        </div>
        <PeriodNavigator
          previousLabel="Forrige dag"
          nextLabel="Neste dag"
          canNext={selectedDayValue.startOf("day").isBefore(today)}
          onPrevious={() => changeDay(selectedDayValue.subtract(1, "day"))}
          onNext={() => changeDay(selectedDayValue.add(1, "day"))}
          middle={
            <DatePicker
              allowClear={false}
              format="DD.MM.YYYY"
              size="small"
              value={selectedDayValue}
              onChange={(value) => {
                if (value) changeDay(value);
              }}
            />
          }
          extra={
            <Button size="small" onClick={() => changeDay(dayjs())}>
              I dag
            </Button>
          }
        />
      </section>

      <div className="door-room-daily-summary">
        <div>
          <span>Rom med aktivitet</span>
          <strong>{dayStats.roomsWithActivity}/{rooms.length}</strong>
        </div>
        <div>
          <span>Soltimer</span>
          <strong>{dayStats.sessions}</strong>
        </div>
        <div>
          <span>Hendelser</span>
          <strong>{dayStats.events}</strong>
        </div>
        <div>
          <span>Effektmarkører</span>
          <strong>{dayStats.powerEvents}</strong>
        </div>
      </div>

      <Tabs
        className="door-room-day-tabs"
        activeKey={activeKey}
        items={tabItems}
        onChange={onRoomChange}
      />
    </div>
  );
}

function DoorSunroomPrecisionControlBoard({
  data,
  loading,
  error,
  selectedDay,
  selectedRoomId,
  onDayChange,
  onRoomChange,
}: {
  data?: DoorSunroomOverviewResponse | null;
  loading: boolean;
  error: unknown;
  selectedDay: string;
  selectedRoomId: string;
  onDayChange: (day: string) => void;
  onRoomChange: (roomId: string) => void;
}) {
  return (
    <DoorSunroomDailyControlBoard
      data={data}
      loading={loading}
      error={error}
      selectedDay={selectedDay}
      selectedRoomId={selectedRoomId}
      onDayChange={onDayChange}
      onRoomChange={onRoomChange}
    />
  );
}

function DoorSolroomNewBoard({
  data,
  loading,
  error,
  selectedDay,
  onDayChange,
}: {
  data?: DoorSunroomOverviewResponse | null;
  loading: boolean;
  error: unknown;
  selectedDay: string;
  onDayChange: (day: string) => void;
}) {
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const selectedDayValue = dayjs(selectedDay);
  const rooms = data.rooms;
  const sections = new Map<string, DoorSunroomOverviewRoom[]>();
  rooms.forEach((room) => {
    const key = room.sectionKey || "solrom";
    sections.set(key, [...(sections.get(key) ?? []), room]);
  });
  const orderedSections = [...sections.entries()];

  return (
    <div className="door-room-daily-board">
      <section className="door-room-daily-date">
        <div>
          <span>Dato</span>
          <strong>{roomControlDateLabel(data.dayDate || selectedDay)}</strong>
        </div>
        <PeriodNavigator
          canNext={selectedDayValue.isBefore(dayjs(), "day")}
          onPrevious={() => onDayChange(selectedDayValue.subtract(1, "day").format("YYYY-MM-DD"))}
          onNext={() => onDayChange(selectedDayValue.add(1, "day").format("YYYY-MM-DD"))}
          middle={
            <DatePicker
              allowClear={false}
              format="DD.MM.YYYY"
              size="small"
              value={selectedDayValue}
              onChange={(value) => {
                if (value) onDayChange(value.format("YYYY-MM-DD"));
              }}
            />
          }
          extra={
            <Button size="small" onClick={() => onDayChange(dayjs().format("YYYY-MM-DD"))}>
              I dag
            </Button>
          }
        />
      </section>

      <div className="door-board-main">
        {orderedSections.map(([key, sectionRooms]) => (
          <section className="door-board-section is-solrom" key={key}>
            <div className="door-board-section-head">
              <strong>{sectionRooms[0]?.sectionTitle || key}</strong>
              <span>{sectionRooms.length} rom</span>
            </div>
            <div className="doors-compact-grid">
              {sectionRooms.map((room) => (
                <DoorRoomDailyCard room={room} generatedAt={data.generatedAt} dayStart={data.dayStart || data.dayDate || selectedDay} key={room.deviceKey} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function SunroomSection({ title, rooms }: { title: string; rooms: DoorSunroomSessionItem[] }) {
  return (
    <section className="door-sunroom-section">
      <div className="door-sunroom-section-head">
        <strong>{title}</strong>
        <span>
          {rooms.filter((room) => room.isOccupied).length} i bruk · {rooms.filter((room) => room.severity === "alert").length} røde
        </span>
      </div>
      <div className="door-sunroom-grid">
        {rooms.map((room) => (
          <SunroomCard item={room} key={room.deviceKey} />
        ))}
      </div>
    </section>
  );
}

function DoorSunroomSessionsBoard({
  data,
  loading,
  error,
  fetching,
  refetch,
}: {
  data?: DoorSunroomSessionsResponse | null;
  loading: boolean;
  error: unknown;
  fetching: boolean;
  refetch: () => void;
}) {
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const sections = new Map<string, DoorSunroomSessionItem[]>();
  data.rooms.forEach((room) => {
    const key = room.sectionKey || "solrom";
    const current = sections.get(key) ?? [];
    current.push(room);
    sections.set(key, current);
  });
  const orderedSections = [...sections.entries()].sort((a, b) => {
    const aIndex = SECTION_ORDER.indexOf(a[0]);
    const bIndex = SECTION_ORDER.indexOf(b[0]);
    return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
  });

  return (
    <div className="door-sunroom-board">
      <section className="door-sunroom-command">
        <div>
          <Typography.Title level={3}>Dør og soltime</Typography.Title>
          <span>
            Lukket solrom kobles mot siste Sun2-time i samme rom. Forventet ut er betaling + oppstart + soltid
            + normal utgangstid. Oransje etter {data.rules.warnAfterEndMinutes} min, rødt etter{" "}
            {data.rules.alertAfterEndMinutes} min fra solslutt.
          </span>
        </div>
        <div className="door-sunroom-actions">
          <a className="door-sunroom-ntfy-link" href={data.ntfyDoorsSubscribeUrl}>
            <BellOutlined />
            Abonner på dørvarsler
          </a>
          <Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={() => refetch()}>
            Oppdater
          </Button>
        </div>
      </section>

      <div className="door-sunroom-summary">
        <div className="tone-active">
          <span>I bruk</span>
          <strong>{data.summary.active}</strong>
        </div>
        <div className="tone-waiting">
          <span>Venter</span>
          <strong>{data.summary.waiting}</strong>
        </div>
        <div className="tone-warning">
          <span>Oransje</span>
          <strong>{data.summary.warning}</strong>
        </div>
        <div className="tone-alert">
          <span>Rød</span>
          <strong>{data.summary.alert}</strong>
        </div>
        <div className="tone-missing">
          <span>Mangler soltime</span>
          <strong>{data.summary.missingSession}</strong>
        </div>
      </div>

      <div className="door-sunroom-rules">
        <span>Solstart +{data.rules.paymentDelayMinutes} min</span>
        <span>Forventet ut +{data.rules.exitGraceMinutes} min</span>
        <span>Vifte +{data.rules.fanAfterRunMinutes} min</span>
        <span>Sun2-frist {data.rules.sessionGraceMinutes} min</span>
        <span>Monitor hvert {Math.round(data.rules.monitorIntervalSeconds / 60)} min</span>
      </div>

      <div className="door-sunroom-sections">
        {orderedSections.map(([key, rooms]) => (
          <SunroomSection title={rooms[0]?.sectionTitle || key} rooms={rooms} key={key} />
        ))}
      </div>

      {data.summary.alert ? (
        <Card className="door-sunroom-alert-note">
          <Space>
            <ExclamationCircleOutlined />
            <Typography.Text>
              Røde rom publiseres på samlet ntfy-tema for dørvarsler. Varsling har innebygd nedkjøling for å unngå spam.
            </Typography.Text>
          </Space>
        </Card>
      ) : null}
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
  const [searchParams, setSearchParams] = useSearchParams();
  const { data, loading, error, fetching, refetch } = useApiQuery(queryKeys.doorStatus(), fetchDoorStatus, {
    refetchInterval: 30_000,
  });
  const selectedSunroomRoomId = view === "soltimer" ? searchParams.get("room") || "" : "";
  const sunroomQuery = useApiQuery(queryKeys.doorSunroomSessions(), fetchDoorSunroomSessions, {
    enabled: view === "soltimer" && !selectedSunroomRoomId,
    refetchInterval: 30_000,
  });
  const requestedControlDays = Number(searchParams.get("days") || "2");
  const controlDays = [1, 2, 7, 14].includes(requestedControlDays) ? requestedControlDays : 2;
  const selectedControlDay = normalizedDayParam(searchParams.get("day"));
  const selectedControlRoomId = view === "romkontroll-ny2" ? searchParams.get("room") || "" : "";
  const overviewDay = view === "romkontroll-ny2" || view === "solrom-ny" ? selectedControlDay : "";
  const sunroomOverviewQuery = useApiQuery(
    queryKeys.doorSunroomOverview(controlDays, overviewDay),
    () => fetchDoorSunroomOverview(controlDays, overviewDay || undefined),
    {
      enabled: view === "romkontroll" || view === "romkontroll-ny" || view === "romkontroll-ny2" || view === "solrom-ny",
      refetchInterval: 30_000,
    },
  );
  const sunroomDetailQuery = useApiQuery(
    queryKeys.doorSunroomRoom(selectedSunroomRoomId),
    () => fetchDoorSunroomRoomDetail(selectedSunroomRoomId),
    {
      enabled: view === "soltimer" && Boolean(selectedSunroomRoomId),
      refetchInterval: 30_000,
    },
  );

  if (!DOOR_VIEWS.includes(view as DoorView)) return <Navigate to="/dorer/oversikt" replace />;
  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const activeView = view as DoorView;
  const isRawView = activeView === "radata";
  const solromDoors = data.doors.filter((door) => door.groupKey === "solrom");
  const otherDoors = data.doors.filter((door) => door.groupKey !== "solrom");
  const visibleDoors =
    activeView === "solrom" || activeView === "solrom-ny" ? solromDoors : activeView === "andre" ? otherDoors : data.doors;
  const visibleDeviceIds = new Set(visibleDoors.map((door) => door.deviceId).filter((id): id is number => id !== null));
  const visiblePeriods =
    activeView === "oversikt" || activeView === "oversikt-ny" || isRawView
      ? data.periods
      : data.periods.filter((period) => period.deviceId !== null && period.deviceId !== undefined && visibleDeviceIds.has(period.deviceId));
  const title =
    activeView === "solrom"
      ? "Dører · solrom"
      : activeView === "romkontroll"
        ? "Dører · romkontroll"
      : activeView === "romkontroll-ny"
        ? "Dører · romkontroll - ny"
      : activeView === "romkontroll-ny2"
        ? "Dører · romkontroll - ny2"
      : activeView === "soltimer"
        ? "Dører · dør og soltime"
      : activeView === "andre"
        ? "Dører · andre dører"
        : isRawView
          ? "Dører · rådata"
          : activeView === "oversikt-ny"
            ? "Dører · oversikt - ny"
          : "Dører";

  return (
    <Space direction="vertical" size={14} className="page-stack doors-page">
      <PageHeader
        eyebrow="Bygg og drift"
        title={title}
        description={
          isRawView
            ? "Alle mottatte HC3-rader for feilsøking og kontroll av dørscenene."
            : activeView === "romkontroll"
              ? "Samlet kontrollflate for rom 1-12 med dør, Sun2-time, forventet ut-tid og strømindikasjon."
            : activeView === "romkontroll-ny"
              ? "Alternativ grafisk kontrollflate med tidslinje per rom og tydelige markører for dør, soltid og forventet ut."
            : activeView === "romkontroll-ny2"
              ? "Daglig romkontroll med siste status øverst og hendelsestabell for dør, soltime, inngang og effekt gjennom dagen."
            : activeView === "soltimer"
              ? "Kobler solromdør mot Sun2-enkelttime og varsler når kunden er vesentlig over forventet ut-tid."
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

      {activeView === "oversikt" ||
      activeView === "oversikt-ny" ||
      activeView === "soltimer" ||
      activeView === "romkontroll" ||
      activeView === "romkontroll-ny" ||
      activeView === "romkontroll-ny2" ||
      activeView === "solrom-ny" ? null : (
        <div className="doors-summary-grid">{buildSummaryCards(data.summary).map(statusSummary)}</div>
      )}

      {!isRawView && activeView === "oversikt" ? (
        <DoorOverviewBoard solromDoors={solromDoors} otherDoors={otherDoors} />
      ) : null}

      {!isRawView && activeView === "oversikt-ny" ? (
        <DoorNewOverviewBoard doors={data.doors} solromDoors={solromDoors} otherDoors={otherDoors} changes={data.changes} />
      ) : null}

      {!isRawView && activeView === "romkontroll" ? (
        <DoorSunroomRoomControlBoard
          data={sunroomOverviewQuery.data}
          loading={sunroomOverviewQuery.loading}
          error={sunroomOverviewQuery.error}
          fetching={sunroomOverviewQuery.fetching}
          refetch={sunroomOverviewQuery.refetch}
          days={controlDays}
          onDaysChange={(nextDays) => {
            const next = new URLSearchParams(searchParams);
            next.set("days", String(nextDays));
            setSearchParams(next, { replace: true });
          }}
        />
      ) : null}

      {!isRawView && activeView === "romkontroll-ny" ? (
        <DoorSunroomVisualControlBoard
          data={sunroomOverviewQuery.data}
          loading={sunroomOverviewQuery.loading}
          error={sunroomOverviewQuery.error}
        />
      ) : null}

      {!isRawView && activeView === "romkontroll-ny2" ? (
        <DoorSunroomPrecisionControlBoard
          data={sunroomOverviewQuery.data}
          loading={sunroomOverviewQuery.loading}
          error={sunroomOverviewQuery.error}
          selectedDay={selectedControlDay}
          selectedRoomId={selectedControlRoomId}
          onDayChange={(nextDay: string) => {
            const next = new URLSearchParams(searchParams);
            next.set("day", nextDay);
            setSearchParams(next, { replace: true });
          }}
          onRoomChange={(roomId: string) => {
            const next = new URLSearchParams(searchParams);
            next.set("room", roomId);
            setSearchParams(next, { replace: true });
          }}
        />
      ) : null}

      {!isRawView && activeView === "solrom-ny" ? (
        <DoorSolroomNewBoard
          data={sunroomOverviewQuery.data}
          loading={sunroomOverviewQuery.loading}
          error={sunroomOverviewQuery.error}
          selectedDay={selectedControlDay}
          onDayChange={(nextDay: string) => {
            const next = new URLSearchParams(searchParams);
            next.set("day", nextDay);
            setSearchParams(next, { replace: true });
          }}
        />
      ) : null}

      {!isRawView && activeView === "soltimer" ? (
        selectedSunroomRoomId ? (
          <DoorSunroomRoomDetail
            data={sunroomDetailQuery.data}
            loading={sunroomDetailQuery.loading}
            error={sunroomDetailQuery.error}
            fetching={sunroomDetailQuery.fetching}
            refetch={sunroomDetailQuery.refetch}
            onBack={() => {
              const next = new URLSearchParams(searchParams);
              next.delete("room");
              setSearchParams(next, { replace: true });
            }}
          />
        ) : (
          <DoorSunroomSessionsBoard
            data={sunroomQuery.data}
            loading={sunroomQuery.loading}
            error={sunroomQuery.error}
            fetching={sunroomQuery.fetching}
            refetch={sunroomQuery.refetch}
          />
        )
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
      ) : activeView !== "oversikt" &&
        activeView !== "oversikt-ny" &&
        activeView !== "soltimer" &&
        activeView !== "romkontroll" &&
        activeView !== "romkontroll-ny" &&
        activeView !== "romkontroll-ny2" &&
        activeView !== "solrom-ny" ? (
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
