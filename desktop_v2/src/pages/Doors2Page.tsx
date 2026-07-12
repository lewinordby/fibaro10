import { ArrowLeftOutlined, CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, DatePicker, Space, Tag, Typography } from "antd";
import dayjs from "dayjs";
import "dayjs/locale/nb";
import { useMemo, type ReactNode } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import {
  fetchDoorStatus,
  fetchDoorSunroomOverview,
  fetchDoorSunroomRoomDetail,
  type DoorEventItem,
  type DoorPeriodItem,
  type DoorStatusItem,
  type DoorSunroomDayEvent,
  type DoorSunroomOverviewPeriod,
  type DoorSunroomOverviewResponse,
  type DoorSunroomOverviewRoom,
  type DoorSunroomRoomDetailResponse,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { PeriodNavigator } from "../components/PeriodNavigator";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/doors2.css";

dayjs.locale("nb");

type Doors2View = "oversikt" | "rom" | "bygg";

const DOORS2_VIEWS: Doors2View[] = ["oversikt", "rom", "bygg"];
const SECTION_ORDER = ["1etg", "2etg", "vip", "bygg"];
const SEVERITY_WEIGHT: Record<string, number> = {
  alert: 0,
  warning: 1,
  waiting: 2,
  active: 3,
  free: 4,
  ok: 5,
  unknown: 6,
};

function normalizedDay(value: string | null): string {
  const parsed = value ? dayjs(value) : dayjs();
  return parsed.isValid() ? parsed.format("YYYY-MM-DD") : dayjs().format("YYYY-MM-DD");
}

function dayLabel(value?: string | null): string {
  const parsed = value ? dayjs(value) : dayjs();
  return parsed.isValid() ? parsed.format("dddd D. MMMM YYYY") : "Valgt dato";
}

function shortDateTime(value?: string | null): string {
  const parsed = value ? dayjs(value) : null;
  return parsed?.isValid() ? parsed.format("DD.MM HH:mm:ss") : "-";
}

function timeOnly(value?: string | null): string {
  const parsed = value ? dayjs(value) : null;
  return parsed?.isValid() ? parsed.format("HH:mm:ss") : "-";
}

function clamp(value: number, min = 0, max = 100): number {
  return Math.min(max, Math.max(min, value));
}

function sectionSort(left: DoorSunroomOverviewRoom, right: DoorSunroomOverviewRoom): number {
  const leftIndex = SECTION_ORDER.indexOf(left.sectionKey);
  const rightIndex = SECTION_ORDER.indexOf(right.sectionKey);
  return (leftIndex === -1 ? 99 : leftIndex) - (rightIndex === -1 ? 99 : rightIndex) || left.displayRoomNumber - right.displayRoomNumber;
}

function severityRank(room: DoorSunroomOverviewRoom): number {
  const severity = room.status?.severity || room.latestPeriod?.severity || "unknown";
  const hasMissing = room.summary.withoutDoor > 0 || room.status?.missingSession;
  if (hasMissing && severity !== "alert" && severity !== "warning") return SEVERITY_WEIGHT.waiting;
  return SEVERITY_WEIGHT[severity] ?? SEVERITY_WEIGHT.unknown;
}

function severityLabel(room: DoorSunroomOverviewRoom): string {
  const severity = room.status?.severity || room.latestPeriod?.severity || "unknown";
  if (severity === "alert") return "Kritisk";
  if (severity === "warning") return "Varsel";
  if (room.summary.withoutDoor > 0 || room.status?.missingSession) return "Mangler match";
  if (severity === "waiting") return "Venter";
  if (severity === "active") return "I bruk";
  if (severity === "free" || severity === "ok") return "Ledig";
  return "Ukjent";
}

function roomTone(room: DoorSunroomOverviewRoom): string {
  const severity = room.status?.severity || room.latestPeriod?.severity || "unknown";
  if (severity === "alert") return "alert";
  if (severity === "warning") return "warning";
  if (room.summary.withoutDoor > 0 || room.status?.missingSession) return "waiting";
  if (severity === "active") return "active";
  if (severity === "free" || severity === "ok") return "free";
  return "unknown";
}

function openingRange(data: DoorSunroomOverviewResponse, selectedDay: string) {
  const fallbackStart = dayjs(selectedDay).hour(6).minute(0).second(0).millisecond(0);
  const fallbackEnd = dayjs(selectedDay).add(1, "day").hour(0).minute(0).second(0).millisecond(0);
  const start = data.dayStart && dayjs(data.dayStart).isValid() ? dayjs(data.dayStart) : fallbackStart;
  const end = data.dayEnd && dayjs(data.dayEnd).isValid() ? dayjs(data.dayEnd) : fallbackEnd;
  return end.isAfter(start) ? { start, end } : { start: fallbackStart, end: fallbackEnd };
}

function percentForTime(time: string | null | undefined, start: dayjs.Dayjs, end: dayjs.Dayjs): number {
  if (!time) return 0;
  const parsed = dayjs(time);
  if (!parsed.isValid()) return 0;
  const total = end.diff(start);
  if (total <= 0) return 0;
  return clamp((parsed.diff(start) / total) * 100);
}

function periodSegment(period: DoorSunroomOverviewPeriod, start: dayjs.Dayjs, end: dayjs.Dayjs) {
  const left = percentForTime(period.closedAt || period.openedAt, start, end);
  const right = percentForTime(period.openedAt || period.expectedExitAt || null, start, end);
  return { left, width: clamp(Math.max(1.2, right - left)) };
}

function sessionSegment(period: DoorSunroomOverviewPeriod, start: dayjs.Dayjs, end: dayjs.Dayjs) {
  const session = period.session;
  if (!session) return null;
  const left = percentForTime(session.sunStartAt || session.startedAt, start, end);
  const right = percentForTime(session.endedAt || session.expectedExitAt || period.expectedExitAt, start, end);
  return { left, width: clamp(Math.max(1.2, right - left)) };
}

function eventKindClass(kind?: string | null): string {
  const normalized = String(kind || "").toLocaleLowerCase("nb-NO");
  if (normalized.includes("power") || normalized.includes("effekt")) return "power";
  if (normalized.includes("session") || normalized.includes("sun")) return "sun";
  if (normalized.includes("open") || normalized.includes("closed") || normalized.includes("door")) return "door";
  return "event";
}

function RoomTimeline({
  data,
  room,
  compact = false,
}: {
  data: DoorSunroomOverviewResponse;
  room: DoorSunroomOverviewRoom;
  compact?: boolean;
}) {
  const { start, end } = openingRange(data, data.dayDate || dayjs().format("YYYY-MM-DD"));
  const visiblePeriods = room.periods.slice(0, compact ? 4 : 24);
  const markers = (room.dayEvents || []).slice(0, compact ? 8 : 80);

  return (
    <div className={`doors2-timeline ${compact ? "is-compact" : ""}`}>
      <div className="doors2-timeline-rail">
        {visiblePeriods.map((period) => {
          const segment = periodSegment(period, start, end);
          const sun = sessionSegment(period, start, end);
          return (
            <span key={period.id}>
              <span className={`doors2-door-segment tone-${period.severity || "ok"}`} style={{ left: `${segment.left}%`, width: `${segment.width}%` }} />
              {sun ? <span className="doors2-sun-segment" style={{ left: `${sun.left}%`, width: `${sun.width}%` }} /> : null}
            </span>
          );
        })}
        {markers.map((event) => (
          <span
            className={`doors2-marker kind-${eventKindClass(event.kind)}`}
            style={{ left: `${percentForTime(event.time, start, end)}%` }}
            title={`${event.timeLabel}: ${event.label}${event.detail ? ` - ${event.detail}` : ""}`}
            key={event.id}
          />
        ))}
      </div>
      {!compact ? (
        <div className="doors2-timeline-scale">
          <span>{start.format("HH:mm")}</span>
          <span>{start.add(end.diff(start) / 2).format("HH:mm")}</span>
          <span>{end.format("HH:mm")}</span>
        </div>
      ) : null}
    </div>
  );
}

function Metric({ label, value, detail, tone = "neutral" }: { label: string; value: string | number; detail?: string; tone?: string }) {
  return (
    <div className={`doors2-metric tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function DoorDayPicker({
  selectedDay,
  onDayChange,
  extra,
}: {
  selectedDay: string;
  onDayChange: (value: string) => void;
  extra?: ReactNode;
}) {
  const selectedDayValue = dayjs(selectedDay);
  return (
    <div className="doors2-daybar">
      <div>
        <span>Dato</span>
        <strong>{dayLabel(selectedDay)}</strong>
      </div>
      <PeriodNavigator
        previousLabel="Forrige dag"
        nextLabel="Neste dag"
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
          <Space size={8} wrap>
            <Button size="small" onClick={() => onDayChange(dayjs().format("YYYY-MM-DD"))}>
              I dag
            </Button>
            {extra}
          </Space>
        }
      />
    </div>
  );
}

function RoomCard({ data, room, selectedDay }: { data: DoorSunroomOverviewResponse; room: DoorSunroomOverviewRoom; selectedDay: string }) {
  const tone = roomTone(room);
  const active = room.latestPeriod?.isActive || room.status?.isOccupied;
  const href = `/dorer2/rom?room=${encodeURIComponent(room.roomId || room.deviceKey)}&day=${encodeURIComponent(selectedDay)}`;

  return (
    <Link className={`doors2-room-card tone-${tone}`} to={href}>
      <div className="doors2-room-head">
        <div>
          <strong>Rom {room.displayRoomNumber}</strong>
          <span>{room.sectionTitle}</span>
        </div>
        <Tag className="doors2-room-tag">{severityLabel(room)}</Tag>
      </div>
      <div className="doors2-room-main">
        <div>
          <span>Dør</span>
          <strong>{room.status.doorStateLabel || "-"}</strong>
          <small>{room.status.doorAgeLabel || room.status.doorChangedLabel}</small>
        </div>
        <div>
          <span>Soltime</span>
          <strong>{room.latestPeriod?.session ? room.latestPeriod.session.sun2UserId || room.latestPeriod.session.roomLabel : active ? "Venter" : "-"}</strong>
          <small>{room.latestPeriod?.session ? `${room.latestPeriod.session.startedLabel} - ${room.latestPeriod.session.durationMinutes || 0} min` : room.status.detail}</small>
        </div>
      </div>
      <RoomTimeline data={data} room={room} compact />
      <div className="doors2-room-foot">
        <span>Ut: {room.latestPeriod?.expectedExitLabel || room.status.expectedExitLabel || "-"}</span>
        <span>{room.summary.energyConfirmed ? `${room.summary.energyConfirmed} strøm OK` : `${room.summary.sessions} soltimer`}</span>
      </div>
    </Link>
  );
}

function SituationOverview({
  data,
  selectedDay,
  onDayChange,
  fetching,
  refetch,
}: {
  data: DoorSunroomOverviewResponse;
  selectedDay: string;
  onDayChange: (value: string) => void;
  fetching: boolean;
  refetch: () => void;
}) {
  const sortedRooms = [...data.rooms].sort((left, right) => severityRank(left) - severityRank(right) || sectionSort(left, right));
  const attentionRooms = sortedRooms.filter((room) => severityRank(room) <= SEVERITY_WEIGHT.waiting);
  const groupedRooms = useMemo(() => {
    const groups = new Map<string, { title: string; rooms: DoorSunroomOverviewRoom[] }>();
    [...data.rooms].sort(sectionSort).forEach((room) => {
      const key = room.sectionKey || "solrom";
      const current = groups.get(key) ?? { title: room.sectionTitle || key, rooms: [] };
      current.rooms.push(room);
      groups.set(key, current);
    });
    return [...groups.entries()].sort(([leftKey], [rightKey]) => {
      const leftIndex = SECTION_ORDER.indexOf(leftKey);
      const rightIndex = SECTION_ORDER.indexOf(rightKey);
      return (leftIndex === -1 ? 99 : leftIndex) - (rightIndex === -1 ? 99 : rightIndex);
    });
  }, [data.rooms]);

  return (
    <Space direction="vertical" size={14} className="page-stack doors2-page">
      <PageHeader
        eyebrow="Bygg og drift"
        title="Dører2 · situasjon"
        description="Operativ oversikt sortert etter avvik, med dør, Sun2 og effekt i samme bilde."
        meta={<Typography.Text type="secondary">Oppdatert {shortDateTime(data.generatedAt)}</Typography.Text>}
        actions={<Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={() => refetch()}>Oppdater</Button>}
      />
      <DoorDayPicker selectedDay={selectedDay} onDayChange={onDayChange} />

      <div className="doors2-metrics">
        <Metric label="I bruk nå" value={data.summary.active} detail={`${data.summary.rooms} rom totalt`} tone="active" />
        <Metric label="Varsel" value={data.summary.warnings + data.summary.alerts} detail={`${data.summary.alerts} røde`} tone={data.summary.alerts ? "alert" : data.summary.warnings ? "warning" : "ok"} />
        <Metric label="Dør/Sun2" value={data.summary.doorMatches} detail={`${data.summary.sessionsWithoutDoor} uten dørmatch`} tone={data.summary.sessionsWithoutDoor ? "waiting" : "ok"} />
        <Metric label="Effekt bekreftet" value={data.summary.energyConfirmed} detail={`${data.summary.energySamples} samples`} tone="energy" />
      </div>

      <div className="doors2-situation-grid">
        <section className="doors2-attention-panel">
          <div className="doors2-section-title">
            <strong>Oppmerksomhet</strong>
            <span>{attentionRooms.length ? `${attentionRooms.length} rom` : "Ingen avvik"}</span>
          </div>
          {attentionRooms.length ? (
            <div className="doors2-attention-list">
              {attentionRooms.map((room) => (
                <Link className={`doors2-attention-row tone-${roomTone(room)}`} to={`/dorer2/rom?room=${encodeURIComponent(room.roomId || room.deviceKey)}&day=${encodeURIComponent(selectedDay)}`} key={room.deviceKey}>
                  <strong>Rom {room.displayRoomNumber}</strong>
                  <span>{severityLabel(room)}</span>
                  <small>{room.latestPeriod?.detail || room.status.detail || room.status.doorAgeLabel}</small>
                </Link>
              ))}
            </div>
          ) : (
            <div className="doors2-empty">
              <CheckCircleOutlined />
              <span>Ingen rom krever oppmerksomhet på valgt dato.</span>
            </div>
          )}
        </section>

        <section className="doors2-map-panel">
          <div className="doors2-section-title">
            <strong>Romkart</strong>
            <span>Lukket = i bruk · åpen = ledig</span>
          </div>
          <div className="doors2-room-sections">
            {groupedRooms.map(([key, group]) => (
              <section className="doors2-room-section" key={key}>
                <div className="doors2-room-section-head">
                  <strong>{group.title}</strong>
                  <span>{group.rooms.filter((room) => room.status.isOccupied).length}/{group.rooms.length} i bruk</span>
                </div>
                <div className="doors2-room-grid">
                  {group.rooms.map((room) => (
                    <RoomCard data={data} room={room} selectedDay={selectedDay} key={room.deviceKey} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        </section>
      </div>
    </Space>
  );
}

function EventList({ events }: { events: DoorSunroomDayEvent[] }) {
  const ordered = [...events].sort((left, right) => dayjs(right.time || 0).valueOf() - dayjs(left.time || 0).valueOf());
  return (
    <div className="doors2-events">
      {ordered.length ? (
        ordered.map((event) => (
          <div className={`doors2-event kind-${eventKindClass(event.kind)}`} key={event.id}>
            <time>{event.timeLabel || timeOnly(event.time)}</time>
            <div>
              <strong>{event.label}</strong>
              {event.detail ? <span>{event.detail}</span> : null}
            </div>
          </div>
        ))
      ) : (
        <div className="doors2-empty compact">Ingen hendelser på valgt dato.</div>
      )}
    </div>
  );
}

function RoomPeriodRows({ periods }: { periods: DoorSunroomOverviewPeriod[] }) {
  const ordered = [...periods].sort((left, right) => dayjs(right.closedAt || right.openedAt || 0).valueOf() - dayjs(left.closedAt || left.openedAt || 0).valueOf());
  return (
    <div className="doors2-table-wrap">
      <table className="doors2-table">
        <thead>
          <tr>
            <th>Dør lukket</th>
            <th>Dør åpnet</th>
            <th>Varighet</th>
            <th>Soltime</th>
            <th>Forventet ut</th>
            <th>Effekt</th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((period) => (
            <tr key={period.id}>
              <td>{timeOnly(period.closedAt)}</td>
              <td>{period.isActive ? "Pågår" : timeOnly(period.openedAt)}</td>
              <td>{period.durationLabel || "-"}</td>
              <td>{period.session ? `${period.session.startedLabel} · ${period.session.durationMinutes || 0} min` : period.missingSession ? "Mangler" : "-"}</td>
              <td>{period.expectedExitLabel || "-"}</td>
              <td>{period.energy?.statusLabel || period.energy?.qualityLabel || "-"}</td>
            </tr>
          ))}
          {!ordered.length ? (
            <tr>
              <td colSpan={6}>Ingen dørperioder på valgt dato.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function RoomDetail({
  data,
  detail,
  selectedDay,
  selectedRoomId,
  onDayChange,
  fetching,
  refetch,
}: {
  data: DoorSunroomOverviewResponse;
  detail: DoorSunroomRoomDetailResponse | null;
  selectedDay: string;
  selectedRoomId: string;
  onDayChange: (value: string) => void;
  fetching: boolean;
  refetch: () => void;
}) {
  const rooms = [...data.rooms].sort(sectionSort);
  const selectedRoom = rooms.find((room) => (room.roomId || room.deviceKey) === selectedRoomId) || rooms[0];
  if (!selectedRoom) return <Navigate to="/dorer2/oversikt" replace />;
  const current = selectedRoom.latestPeriod || detail?.currentPeriod || null;
  const currentSession = current?.session || selectedRoom.status.session || null;
  const currentEnergy = selectedRoom.latestPeriod?.energy || null;

  return (
    <Space direction="vertical" size={14} className="page-stack doors2-page">
      <PageHeader
        eyebrow="Dører2"
        title={`Rom ${selectedRoom.displayRoomNumber}`}
        description={`${selectedRoom.sectionTitle} · ${severityLabel(selectedRoom)} · oppdatert ${shortDateTime(data.generatedAt)}`}
        actions={
          <Space wrap>
            <Link to="/dorer2/oversikt">
              <Button size="small" icon={<ArrowLeftOutlined />}>Til situasjon</Button>
            </Link>
            <Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={() => refetch()}>Oppdater</Button>
          </Space>
        }
      />
      <DoorDayPicker selectedDay={selectedDay} onDayChange={onDayChange} />

      <div className="doors2-detail-layout">
        <aside className="doors2-room-rail">
          {rooms.map((room) => (
            <Link
              className={`doors2-rail-row tone-${roomTone(room)} ${(room.roomId || room.deviceKey) === (selectedRoom.roomId || selectedRoom.deviceKey) ? "is-active" : ""}`}
              to={`/dorer2/rom?room=${encodeURIComponent(room.roomId || room.deviceKey)}&day=${encodeURIComponent(selectedDay)}`}
              key={room.deviceKey}
            >
              <strong>Rom {room.displayRoomNumber}</strong>
              <span>{severityLabel(room)}</span>
              <small>{room.status.doorAgeLabel || room.status.doorChangedLabel}</small>
            </Link>
          ))}
        </aside>

        <section className="doors2-room-detail">
          <div className={`doors2-room-hero tone-${roomTone(selectedRoom)}`}>
            <div>
              <span>Aktuell situasjon</span>
              <strong>{selectedRoom.status.status || severityLabel(selectedRoom)}</strong>
              <small>{selectedRoom.status.detail}</small>
            </div>
            <div className="doors2-hero-grid">
              <Metric label="Dør" value={selectedRoom.status.doorStateLabel} detail={selectedRoom.status.doorAgeLabel} tone={roomTone(selectedRoom)} />
              <Metric label="Soltime" value={currentSession?.sun2UserId || currentSession?.roomLabel || "-"} detail={currentSession ? `${currentSession.startedLabel} · ${currentSession.durationMinutes || 0} min` : "Ingen koblet"} tone="sun" />
              <Metric label="Forventet ut" value={current?.expectedExitLabel || selectedRoom.status.expectedExitLabel || "-"} detail={current?.overstayLabel || current?.remainingLabel || ""} tone={roomTone(selectedRoom)} />
              <Metric label="Effekt" value={currentEnergy?.statusLabel || "-"} detail={currentEnergy?.detail || `${selectedRoom.summary.energyConfirmed} bekreftet i dag`} tone="energy" />
            </div>
          </div>

          <section className="doors2-detail-card">
            <div className="doors2-section-title">
              <strong>Tidslinje for dagen</strong>
              <span>Dørsegment, solsegment og markører samlet</span>
            </div>
            <RoomTimeline data={data} room={selectedRoom} />
          </section>

          <div className="doors2-detail-columns">
            <section className="doors2-detail-card">
              <div className="doors2-section-title">
                <strong>Hendelser</strong>
                <span>Nyest først</span>
              </div>
              <EventList events={selectedRoom.dayEvents || []} />
            </section>
            <section className="doors2-detail-card">
              <div className="doors2-section-title">
                <strong>Perioder</strong>
                <span>{selectedRoom.periods.length} på valgt dato</span>
              </div>
              <RoomPeriodRows periods={selectedRoom.periods} />
            </section>
          </div>
        </section>
      </div>
    </Space>
  );
}

function buildingDoorTone(door: DoorStatusItem): string {
  if (!door.isConfigured || door.state === "unknown") return "unknown";
  return door.state === door.normalState ? "ok" : "alert";
}

function BuildingDoorCard({ door }: { door: DoorStatusItem }) {
  const tone = buildingDoorTone(door);
  return (
    <div className={`doors2-building-card tone-${tone}`}>
      <div>
        <strong>{door.title}</strong>
        <span>{door.sectionTitle || door.groupTitle || "Bygg"}</span>
      </div>
      <div className="doors2-building-state">
        <strong>{door.stateLabel || "-"}</strong>
        <span>Siden {door.ageLabel || door.lastChangedLabel || "-"}</span>
      </div>
      <small>Normal: {door.normalStateLabel || "-"} · Sensor {door.deviceId || "-"}</small>
    </div>
  );
}

function DoorChangeRows({ changes, periods }: { changes: DoorEventItem[]; periods: DoorPeriodItem[] }) {
  const rows = [...changes].slice(0, 20);
  return (
    <div className="doors2-detail-card">
      <div className="doors2-section-title">
        <strong>Siste endringer</strong>
        <span>{periods.filter((period) => !period.closedAt).length} aktive perioder</span>
      </div>
      <div className="doors2-events">
        {rows.map((event) => (
          <div className={`doors2-event kind-door`} key={event.id}>
            <time>{event.timeLabel || timeOnly(event.timestamp)}</time>
            <div>
              <strong>{event.deviceName || event.deviceKey || "Dør"}</strong>
              <span>{event.stateLabel} · {event.ageLabel}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BuildingDoors({
  statusData,
  fetching,
  refetch,
}: {
  statusData: Awaited<ReturnType<typeof fetchDoorStatus>>;
  fetching: boolean;
  refetch: () => void;
}) {
  const buildingDoors = statusData.doors.filter((door) => door.groupKey !== "solrom").sort((left, right) => {
    const toneDiff = (buildingDoorTone(left) === "alert" ? 0 : 1) - (buildingDoorTone(right) === "alert" ? 0 : 1);
    return toneDiff || left.sortOrder - right.sortOrder || left.title.localeCompare(right.title, "nb");
  });
  const alerts = buildingDoors.filter((door) => buildingDoorTone(door) === "alert").length;

  return (
    <Space direction="vertical" size={14} className="page-stack doors2-page">
      <PageHeader
        eyebrow="Dører2"
        title="Byggdører"
        description="Byggdører vurderes mot normalposisjon. Avvik vises først."
        meta={<Typography.Text type="secondary">Oppdatert {shortDateTime(statusData.generatedAt)}</Typography.Text>}
        actions={<Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={() => refetch()}>Oppdater</Button>}
      />
      <div className="doors2-metrics">
        <Metric label="Byggdører" value={buildingDoors.length} detail={`${statusData.summary.configured} koblet totalt`} />
        <Metric label="Avvik" value={alerts} detail={alerts ? "Sjekk først" : "Ingen"} tone={alerts ? "alert" : "ok"} />
        <Metric label="Åpne" value={buildingDoors.filter((door) => door.state === "open").length} detail="Akkurat nå" />
        <Metric label="Ukjent" value={buildingDoors.filter((door) => door.state === "unknown").length} detail="Mangler status" tone="unknown" />
      </div>
      <div className="doors2-building-grid">
        {buildingDoors.map((door) => (
          <BuildingDoorCard door={door} key={door.deviceKey || door.deviceId || door.title} />
        ))}
      </div>
      <DoorChangeRows changes={statusData.changes} periods={statusData.periods} />
    </Space>
  );
}

export default function Doors2Page() {
  const { view = "oversikt" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeView = DOORS2_VIEWS.includes(view as Doors2View) ? (view as Doors2View) : null;
  const selectedDay = normalizedDay(searchParams.get("day"));
  const selectedRoomParam = searchParams.get("room") || "";

  const overviewQuery = useApiQuery(
    queryKeys.doorSunroomOverview(2, selectedDay),
    () => fetchDoorSunroomOverview(2, selectedDay),
    { enabled: activeView === "oversikt" || activeView === "rom", refetchInterval: 30_000 },
  );
  const selectedRoomId =
    selectedRoomParam ||
    overviewQuery.data?.rooms.find((room) => severityRank(room) <= SEVERITY_WEIGHT.waiting)?.roomId ||
    overviewQuery.data?.rooms[0]?.roomId ||
    "";
  const detailQuery = useApiQuery(
    queryKeys.doorSunroomRoom(selectedRoomId),
    () => fetchDoorSunroomRoomDetail(selectedRoomId),
    { enabled: activeView === "rom" && Boolean(selectedRoomId), refetchInterval: 30_000 },
  );
  const statusQuery = useApiQuery(queryKeys.doorStatus(), fetchDoorStatus, {
    enabled: activeView === "bygg",
    refetchInterval: 30_000,
  });

  function setSelectedDay(day: string) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      next.set("day", day);
      return next;
    });
  }

  if (!activeView) return <Navigate to="/dorer2/oversikt" replace />;

  if (activeView === "bygg") {
    if (statusQuery.loading) return <LoadingBlock />;
    if (statusQuery.error || !statusQuery.data) return <ErrorBlock error={statusQuery.error} />;
    return <BuildingDoors statusData={statusQuery.data} fetching={statusQuery.fetching} refetch={() => statusQuery.refetch()} />;
  }

  if (overviewQuery.loading) return <LoadingBlock />;
  if (overviewQuery.error || !overviewQuery.data) return <ErrorBlock error={overviewQuery.error} />;

  if (activeView === "rom") {
    if (!selectedRoomId) return <Navigate to="/dorer2/oversikt" replace />;
    return (
      <RoomDetail
        data={overviewQuery.data}
        detail={detailQuery.data}
        selectedDay={selectedDay}
        selectedRoomId={selectedRoomId}
        onDayChange={setSelectedDay}
        fetching={overviewQuery.fetching || detailQuery.fetching}
        refetch={() => {
          overviewQuery.refetch();
          detailQuery.refetch();
        }}
      />
    );
  }

  return (
    <SituationOverview
      data={overviewQuery.data}
      selectedDay={selectedDay}
      onDayChange={setSelectedDay}
      fetching={overviewQuery.fetching}
      refetch={() => overviewQuery.refetch()}
    />
  );
}
