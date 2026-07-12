import { ArrowLeftOutlined, CheckCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, DatePicker, Space, Tag, Typography } from "antd";
import dayjs from "dayjs";
import "dayjs/locale/nb";
import { useMemo } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import {
  fetchDoorSunroomOverview,
  fetchDoorSunroomRoomDetail,
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
import "../styles/solroom2.css";

dayjs.locale("nb");

type Solroom2View = "oversikt" | "dagskontroll" | "avvik" | "rom";

const SOLROOM2_VIEWS: Solroom2View[] = ["oversikt", "dagskontroll", "avvik", "rom"];
const SECTION_ORDER = ["1etg", "2etg", "vip"];
const SEVERITY_ORDER: Record<string, number> = { alert: 0, warning: 1, waiting: 2, active: 3, free: 4, ok: 5, unknown: 6 };

function normalizedDay(value: string | null): string {
  const parsed = value ? dayjs(value) : dayjs();
  return parsed.isValid() ? parsed.format("YYYY-MM-DD") : dayjs().format("YYYY-MM-DD");
}

function dayText(value?: string | null): string {
  const parsed = value ? dayjs(value) : dayjs();
  return parsed.isValid() ? parsed.format("dddd D. MMMM YYYY") : "Valgt dato";
}

function compactTime(value?: string | null): string {
  const parsed = value ? dayjs(value) : null;
  return parsed?.isValid() ? parsed.format("HH:mm:ss") : "-";
}

function compactDateTime(value?: string | null): string {
  const parsed = value ? dayjs(value) : null;
  return parsed?.isValid() ? parsed.format("DD.MM HH:mm:ss") : "-";
}

function clamp(value: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, value));
}

function roomKey(room: DoorSunroomOverviewRoom): string {
  return room.roomId || room.deviceKey;
}

function sectionSort(left: DoorSunroomOverviewRoom, right: DoorSunroomOverviewRoom): number {
  const leftIndex = SECTION_ORDER.indexOf(left.sectionKey);
  const rightIndex = SECTION_ORDER.indexOf(right.sectionKey);
  return (leftIndex === -1 ? 99 : leftIndex) - (rightIndex === -1 ? 99 : rightIndex) || left.displayRoomNumber - right.displayRoomNumber;
}

function roomTone(room: DoorSunroomOverviewRoom): string {
  const severity = room.status.severity || room.latestPeriod?.severity || "unknown";
  if (severity === "alert") return "alert";
  if (severity === "warning") return "warning";
  if (room.summary.withoutDoor > 0 || room.status.missingSession) return "waiting";
  if (severity === "active") return "active";
  if (severity === "free" || severity === "ok") return "free";
  return "unknown";
}

function roomStatusLabel(room: DoorSunroomOverviewRoom): string {
  const tone = roomTone(room);
  if (tone === "alert") return "Kritisk";
  if (tone === "warning") return "Varsel";
  if (tone === "waiting") return "Mangler kontroll";
  if (tone === "active") return "I bruk";
  if (tone === "free") return "Ledig";
  return "Ukjent";
}

function roomSortByAttention(left: DoorSunroomOverviewRoom, right: DoorSunroomOverviewRoom): number {
  return (SEVERITY_ORDER[roomTone(left)] ?? 9) - (SEVERITY_ORDER[roomTone(right)] ?? 9) || sectionSort(left, right);
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
  const total = end.diff(start);
  if (!parsed.isValid() || total <= 0) return 0;
  return clamp((parsed.diff(start) / total) * 100);
}

function segmentStyle(leftTime: string | null | undefined, rightTime: string | null | undefined, start: dayjs.Dayjs, end: dayjs.Dayjs) {
  const left = percentForTime(leftTime, start, end);
  const right = percentForTime(rightTime, start, end);
  return { left: `${left}%`, width: `${clamp(Math.max(1.3, right - left))}%` };
}

function eventClass(event: DoorSunroomDayEvent): string {
  const text = `${event.kind} ${event.label} ${event.source || ""}`.toLocaleLowerCase("nb-NO");
  if (text.includes("power") || text.includes("effekt")) return "power";
  if (text.includes("sun") || text.includes("sol")) return "sun";
  if (text.includes("door") || text.includes("dør") || text.includes("open") || text.includes("closed")) return "door";
  if (text.includes("inngang")) return "entrance";
  return "event";
}

function Timeline({
  data,
  room,
  compact = false,
}: {
  data: DoorSunroomOverviewResponse;
  room: DoorSunroomOverviewRoom;
  compact?: boolean;
}) {
  const { start, end } = openingRange(data, data.dayDate || dayjs().format("YYYY-MM-DD"));
  const periods = room.periods.slice(0, compact ? 5 : 80);
  const events = (room.dayEvents || []).slice(0, compact ? 10 : 120);
  return (
    <div className={`solroom2-timeline ${compact ? "is-compact" : ""}`}>
      <div className="solroom2-timeline-rail">
        {periods.map((period) => {
          const doorStyle = segmentStyle(period.closedAt || period.openedAt, period.openedAt || period.expectedExitAt, start, end);
          const session = period.session;
          const sunStyle = session ? segmentStyle(session.sunStartAt || session.startedAt, session.endedAt || session.expectedExitAt || period.expectedExitAt, start, end) : null;
          return (
            <span key={period.id}>
              <span className={`solroom2-door-span tone-${period.severity || "ok"}`} style={doorStyle} />
              {sunStyle ? <span className="solroom2-sun-span" style={sunStyle} /> : null}
            </span>
          );
        })}
        {events.map((event) => (
          <span
            className={`solroom2-marker kind-${eventClass(event)}`}
            style={{ left: `${percentForTime(event.time, start, end)}%` }}
            title={`${event.timeLabel}: ${event.label}${event.detail ? ` - ${event.detail}` : ""}`}
            key={event.id}
          />
        ))}
      </div>
      {!compact ? (
        <div className="solroom2-timeline-scale">
          <span>{start.format("HH:mm")}</span>
          <span>{start.add(end.diff(start) / 2).format("HH:mm")}</span>
          <span>{end.format("HH:mm")}</span>
        </div>
      ) : null}
    </div>
  );
}

function DayPicker({
  selectedDay,
  onDayChange,
  fetching,
  onRefresh,
}: {
  selectedDay: string;
  onDayChange: (day: string) => void;
  fetching: boolean;
  onRefresh: () => void;
}) {
  const value = dayjs(selectedDay);
  return (
    <div className="solroom2-daybar">
      <div>
        <span>Dato</span>
        <strong>{dayText(selectedDay)}</strong>
      </div>
      <PeriodNavigator
        previousLabel="Forrige dag"
        nextLabel="Neste dag"
        canNext={value.isBefore(dayjs(), "day")}
        onPrevious={() => onDayChange(value.subtract(1, "day").format("YYYY-MM-DD"))}
        onNext={() => onDayChange(value.add(1, "day").format("YYYY-MM-DD"))}
        middle={
          <DatePicker
            allowClear={false}
            format="DD.MM.YYYY"
            size="small"
            value={value}
            onChange={(next) => {
              if (next) onDayChange(next.format("YYYY-MM-DD"));
            }}
          />
        }
        extra={
          <Space size={8} wrap>
            <Button size="small" onClick={() => onDayChange(dayjs().format("YYYY-MM-DD"))}>
              I dag
            </Button>
            <Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={onRefresh}>
              Oppdater
            </Button>
          </Space>
        }
      />
    </div>
  );
}

function Metric({ label, value, detail, tone = "neutral" }: { label: string; value: string | number; detail?: string; tone?: string }) {
  return (
    <div className={`solroom2-metric tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function groupedRooms(rooms: DoorSunroomOverviewRoom[]) {
  const groups = new Map<string, { title: string; rooms: DoorSunroomOverviewRoom[] }>();
  [...rooms].sort(sectionSort).forEach((room) => {
    const key = room.sectionKey || "solrom";
    const current = groups.get(key) ?? { title: room.sectionTitle || key, rooms: [] };
    current.rooms.push(room);
    groups.set(key, current);
  });
  return [...groups.entries()].sort(([left], [right]) => {
    const leftIndex = SECTION_ORDER.indexOf(left);
    const rightIndex = SECTION_ORDER.indexOf(right);
    return (leftIndex === -1 ? 99 : leftIndex) - (rightIndex === -1 ? 99 : rightIndex);
  });
}

function RoomTile({ data, room, selectedDay }: { data: DoorSunroomOverviewResponse; room: DoorSunroomOverviewRoom; selectedDay: string }) {
  const tone = roomTone(room);
  const period = room.latestPeriod;
  const session = period?.session || room.status.session;
  return (
    <Link className={`solroom2-room-tile tone-${tone}`} to={`/solrom-2/rom?room=${encodeURIComponent(roomKey(room))}&day=${encodeURIComponent(selectedDay)}`}>
      <div className="solroom2-room-top">
        <div>
          <strong>Rom {room.displayRoomNumber}</strong>
          <span>{room.sectionTitle}</span>
        </div>
        <Tag className="solroom2-status-tag">{roomStatusLabel(room)}</Tag>
      </div>
      <div className="solroom2-room-core">
        <div>
          <span>Dør</span>
          <strong>{room.status.doorStateLabel}</strong>
          <small>{room.status.doorAgeLabel || room.status.doorChangedLabel}</small>
        </div>
        <div>
          <span>Soltime</span>
          <strong>{session?.sun2UserId || (room.status.isOccupied ? "Venter" : "-")}</strong>
          <small>{session ? `${session.startedLabel} · ${session.durationMinutes || 0} min` : room.status.detail}</small>
        </div>
        <div>
          <span>Forventet ut</span>
          <strong>{period?.expectedExitLabel || room.status.expectedExitLabel || "-"}</strong>
          <small>{period?.overstayLabel || period?.remainingLabel || room.status.remainingLabel}</small>
        </div>
      </div>
      <Timeline data={data} room={room} compact />
      <div className="solroom2-room-foot">
        <span>{room.summary.sessions} soltimer</span>
        <span>{room.summary.energyConfirmed ? `${room.summary.energyConfirmed} strøm OK` : `${room.summary.withoutDoor} uten dør`}</span>
      </div>
    </Link>
  );
}

function Overview({
  data,
  selectedDay,
  onDayChange,
  fetching,
  refetch,
}: {
  data: DoorSunroomOverviewResponse;
  selectedDay: string;
  onDayChange: (day: string) => void;
  fetching: boolean;
  refetch: () => void;
}) {
  const attention = [...data.rooms].filter((room) => ["alert", "warning", "waiting"].includes(roomTone(room))).sort(roomSortByAttention);
  const groups = useMemo(() => groupedRooms(data.rooms), [data.rooms]);
  const activeRooms = data.rooms.filter((room) => room.status.isOccupied).length;
  const freeRooms = data.rooms.filter((room) => room.status.doorState === "open").length;

  return (
    <Space direction="vertical" size={14} className="page-stack solroom2-page">
      <PageHeader
        eyebrow="Bygg og drift"
        title="Solrom-2"
        description="Operativ romflate: hva skjer nå, hva må sjekkes, og hvordan henger dør, soltime og strøm sammen."
        meta={<Typography.Text type="secondary">Oppdatert {compactDateTime(data.generatedAt)}</Typography.Text>}
      />
      <DayPicker selectedDay={selectedDay} onDayChange={onDayChange} fetching={fetching} onRefresh={refetch} />

      <div className="solroom2-metric-grid">
        <Metric label="I bruk nå" value={activeRooms} detail={`${data.summary.rooms} rom totalt`} tone="active" />
        <Metric label="Ledige" value={freeRooms} detail="Åpen dør tolkes som ledig" tone="free" />
        <Metric label="Varsel" value={data.summary.warnings + data.summary.alerts} detail={`${data.summary.alerts} kritiske`} tone={data.summary.alerts ? "alert" : data.summary.warnings ? "warning" : "ok"} />
        <Metric label="Kontroll" value={data.summary.doorMatches} detail={`${data.summary.sessionsWithoutDoor} uten dørmatch`} tone={data.summary.sessionsWithoutDoor ? "waiting" : "ok"} />
      </div>

      <div className="solroom2-overview-layout">
        <section className="solroom2-panel solroom2-attention">
          <div className="solroom2-panel-title">
            <strong>Dette må vurderes først</strong>
            <span>{attention.length ? `${attention.length} rom` : "Ingen avvik"}</span>
          </div>
          {attention.length ? (
            <div className="solroom2-attention-list">
              {attention.map((room) => (
                <Link className={`solroom2-attention-item tone-${roomTone(room)}`} to={`/solrom-2/rom?room=${encodeURIComponent(roomKey(room))}&day=${encodeURIComponent(selectedDay)}`} key={room.deviceKey}>
                  <strong>Rom {room.displayRoomNumber}</strong>
                  <span>{roomStatusLabel(room)}</span>
                  <small>{room.latestPeriod?.detail || room.status.detail}</small>
                </Link>
              ))}
            </div>
          ) : (
            <div className="solroom2-empty">
              <CheckCircleOutlined />
              <span>Ingen rom krever oppmerksomhet nå.</span>
            </div>
          )}
          <div className="solroom2-rule-card">
            <strong>Regelgrunnlag</strong>
            <span>Sol starter ca. +{data.rules.paymentDelayMinutes} min etter betaling. Normal utgang er solslutt +{data.rules.exitGraceMinutes} min. Vifte går +{data.rules.fanAfterRunMinutes} min.</span>
          </div>
        </section>

        <section className="solroom2-panel">
          <div className="solroom2-panel-title">
            <strong>Romstatus</strong>
            <span>Lukket = i bruk · åpen = ledig</span>
          </div>
          <div className="solroom2-section-stack">
            {groups.map(([key, group]) => (
              <section className="solroom2-room-section" key={key}>
                <div className="solroom2-section-head">
                  <strong>{group.title}</strong>
                  <span>{group.rooms.filter((room) => room.status.isOccupied).length}/{group.rooms.length} i bruk</span>
                </div>
                <div className="solroom2-room-grid">
                  {group.rooms.map((room) => (
                    <RoomTile data={data} room={room} selectedDay={selectedDay} key={room.deviceKey} />
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

function DayControl({
  data,
  selectedDay,
  onDayChange,
  fetching,
  refetch,
}: {
  data: DoorSunroomOverviewResponse;
  selectedDay: string;
  onDayChange: (day: string) => void;
  fetching: boolean;
  refetch: () => void;
}) {
  const rooms = [...data.rooms].sort(sectionSort);
  const activeRooms = rooms.filter((room) => room.summary.periods || room.summary.sessions || room.dayEvents?.length);
  return (
    <Space direction="vertical" size={14} className="page-stack solroom2-page">
      <PageHeader
        eyebrow="Solrom-2"
        title="Dagskontroll"
        description="Hele åpningsdagen per rom. Brukes for å se sammenheng mellom dør, betaling, forventet ut og effekt."
        meta={<Typography.Text type="secondary">{activeRooms.length} rom med aktivitet</Typography.Text>}
      />
      <DayPicker selectedDay={selectedDay} onDayChange={onDayChange} fetching={fetching} onRefresh={refetch} />
      <section className="solroom2-panel">
        <div className="solroom2-panel-title">
          <strong>Dagsmatrise</strong>
          <span>{dayText(data.dayDate || selectedDay)}</span>
        </div>
        <div className="solroom2-day-matrix">
          {rooms.map((room) => (
            <Link className={`solroom2-day-row tone-${roomTone(room)}`} to={`/solrom-2/rom?room=${encodeURIComponent(roomKey(room))}&day=${encodeURIComponent(selectedDay)}`} key={room.deviceKey}>
              <div className="solroom2-day-room">
                <strong>Rom {room.displayRoomNumber}</strong>
                <span>{roomStatusLabel(room)}</span>
              </div>
              <Timeline data={data} room={room} />
              <div className="solroom2-day-facts">
                <span>{room.summary.periods} dørperioder</span>
                <span>{room.summary.sessions} soltimer</span>
                <span>{room.summary.energyConfirmed} strøm OK</span>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </Space>
  );
}

function IssueGroup({ title, rooms, selectedDay, empty }: { title: string; rooms: DoorSunroomOverviewRoom[]; selectedDay: string; empty: string }) {
  return (
    <section className="solroom2-panel">
      <div className="solroom2-panel-title">
        <strong>{title}</strong>
        <span>{rooms.length}</span>
      </div>
      <div className="solroom2-issue-list">
        {rooms.length ? (
          rooms.map((room) => (
            <Link className={`solroom2-issue-row tone-${roomTone(room)}`} to={`/solrom-2/rom?room=${encodeURIComponent(roomKey(room))}&day=${encodeURIComponent(selectedDay)}`} key={room.deviceKey}>
              <strong>Rom {room.displayRoomNumber}</strong>
              <span>{room.latestPeriod?.status || room.status.status || roomStatusLabel(room)}</span>
              <small>{room.latestPeriod?.detail || room.status.detail || `${room.summary.sessions} soltimer`}</small>
            </Link>
          ))
        ) : (
          <div className="solroom2-empty compact">{empty}</div>
        )}
      </div>
    </section>
  );
}

function Deviations({
  data,
  selectedDay,
  onDayChange,
  fetching,
  refetch,
}: {
  data: DoorSunroomOverviewResponse;
  selectedDay: string;
  onDayChange: (day: string) => void;
  fetching: boolean;
  refetch: () => void;
}) {
  const alertRooms = data.rooms.filter((room) => roomTone(room) === "alert");
  const warningRooms = data.rooms.filter((room) => roomTone(room) === "warning");
  const missingRooms = data.rooms.filter((room) => room.summary.withoutDoor > 0 || room.status.missingSession);
  const energyRooms = data.rooms.filter((room) =>
    [...room.periods, ...room.recentSessions].some((item) => item.energy && !["confirmed", "power_seen"].includes(item.energy.status)),
  );
  return (
    <Space direction="vertical" size={14} className="page-stack solroom2-page">
      <PageHeader
        eyebrow="Solrom-2"
        title="Avvik og kontroll"
        description="Samler rom som bør undersøkes: overtid, manglende Sun2/dørmatch og usikker effekt."
        meta={<Typography.Text type="secondary">Oppdatert {compactDateTime(data.generatedAt)}</Typography.Text>}
      />
      <DayPicker selectedDay={selectedDay} onDayChange={onDayChange} fetching={fetching} onRefresh={refetch} />
      <div className="solroom2-metric-grid">
        <Metric label="Kritiske" value={alertRooms.length} detail="Rød vurdering" tone={alertRooms.length ? "alert" : "ok"} />
        <Metric label="Varsel" value={warningRooms.length} detail="Oransje vurdering" tone={warningRooms.length ? "warning" : "ok"} />
        <Metric label="Uten match" value={missingRooms.length} detail={`${data.summary.sessionsWithoutDoor} soltimer`} tone={missingRooms.length ? "waiting" : "ok"} />
        <Metric label="Effekt usikker" value={energyRooms.length} detail={`${data.summary.energyConfirmed} bekreftet`} tone={energyRooms.length ? "warning" : "energy"} />
      </div>
      <div className="solroom2-issue-grid">
        <IssueGroup title="Kritisk" rooms={alertRooms} selectedDay={selectedDay} empty="Ingen kritiske rom." />
        <IssueGroup title="Varsel" rooms={warningRooms} selectedDay={selectedDay} empty="Ingen oransje varsler." />
        <IssueGroup title="Mangler match" rooms={missingRooms} selectedDay={selectedDay} empty="Ingen manglende dør/Sun2-match." />
        <IssueGroup title="Effekt må kontrolleres" rooms={energyRooms} selectedDay={selectedDay} empty="Ingen tydelige effektavvik." />
      </div>
    </Space>
  );
}

function EventList({ events }: { events: DoorSunroomDayEvent[] }) {
  const ordered = [...events].sort((left, right) => dayjs(right.time || 0).valueOf() - dayjs(left.time || 0).valueOf());
  return (
    <div className="solroom2-event-list">
      {ordered.length ? (
        ordered.map((event) => (
          <div className={`solroom2-event kind-${eventClass(event)}`} key={event.id}>
            <time>{event.timeLabel || compactTime(event.time)}</time>
            <div>
              <strong>{event.label}</strong>
              {event.detail ? <span>{event.detail}</span> : null}
            </div>
          </div>
        ))
      ) : (
        <div className="solroom2-empty compact">Ingen hendelser for valgt rom.</div>
      )}
    </div>
  );
}

function PeriodTable({ periods }: { periods: DoorSunroomOverviewPeriod[] }) {
  const ordered = [...periods].sort((left, right) => dayjs(right.closedAt || right.openedAt || 0).valueOf() - dayjs(left.closedAt || left.openedAt || 0).valueOf());
  return (
    <div className="solroom2-table-wrap">
      <table className="solroom2-table">
        <thead>
          <tr>
            <th>Dør lukket</th>
            <th>Dør åpnet</th>
            <th>Varighet</th>
            <th>Soltime</th>
            <th>Forventet ut</th>
            <th>Kontroll</th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((period) => (
            <tr key={period.id}>
              <td>{compactTime(period.closedAt)}</td>
              <td>{period.isActive ? "Pågår" : compactTime(period.openedAt)}</td>
              <td>{period.durationLabel || "-"}</td>
              <td>{period.session ? `${period.session.startedLabel} · ${period.session.durationMinutes || 0} min` : period.missingSession ? "Mangler" : "-"}</td>
              <td>{period.expectedExitLabel || "-"}</td>
              <td>{period.energy?.statusLabel || period.status || "-"}</td>
            </tr>
          ))}
          {!ordered.length ? (
            <tr>
              <td colSpan={6}>Ingen dørperioder for valgt rom.</td>
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
  onDayChange: (day: string) => void;
  fetching: boolean;
  refetch: () => void;
}) {
  const rooms = [...data.rooms].sort(sectionSort);
  const selectedRoom = rooms.find((room) => roomKey(room) === selectedRoomId) || rooms[0];
  if (!selectedRoom) return <Navigate to="/solrom-2/oversikt" replace />;
  const period = selectedRoom.latestPeriod || detail?.currentPeriod || null;
  const session = period?.session || selectedRoom.status.session || null;
  const energy = selectedRoom.latestPeriod?.energy || null;

  return (
    <Space direction="vertical" size={14} className="page-stack solroom2-page">
      <PageHeader
        eyebrow="Solrom-2"
        title={`Rom ${selectedRoom.displayRoomNumber}`}
        description={`${selectedRoom.sectionTitle} · ${roomStatusLabel(selectedRoom)} · ${dayText(selectedDay)}`}
        actions={
          <Space wrap>
            <Link to="/solrom-2/oversikt">
              <Button size="small" icon={<ArrowLeftOutlined />}>
                Til oversikt
              </Button>
            </Link>
            <Button size="small" icon={<ReloadOutlined spin={fetching} />} onClick={refetch}>
              Oppdater
            </Button>
          </Space>
        }
      />
      <DayPicker selectedDay={selectedDay} onDayChange={onDayChange} fetching={fetching} onRefresh={refetch} />
      <div className="solroom2-detail-layout">
        <aside className="solroom2-room-rail">
          {rooms.map((room) => (
            <Link className={`solroom2-rail-item tone-${roomTone(room)} ${roomKey(room) === roomKey(selectedRoom) ? "is-active" : ""}`} to={`/solrom-2/rom?room=${encodeURIComponent(roomKey(room))}&day=${encodeURIComponent(selectedDay)}`} key={room.deviceKey}>
              <strong>Rom {room.displayRoomNumber}</strong>
              <span>{roomStatusLabel(room)}</span>
              <small>{room.status.doorAgeLabel || room.status.doorChangedLabel}</small>
            </Link>
          ))}
        </aside>
        <section className="solroom2-detail-main">
          <div className={`solroom2-room-hero tone-${roomTone(selectedRoom)}`}>
            <div>
              <span>Situasjon</span>
              <strong>{selectedRoom.status.status || roomStatusLabel(selectedRoom)}</strong>
              <small>{selectedRoom.status.detail}</small>
            </div>
            <div className="solroom2-hero-grid">
              <Metric label="Dør" value={selectedRoom.status.doorStateLabel} detail={selectedRoom.status.doorAgeLabel} tone={roomTone(selectedRoom)} />
              <Metric label="Sun2" value={session?.sun2UserId || session?.roomLabel || "-"} detail={session ? `${session.startedLabel} · ${session.durationMinutes || 0} min` : "Ingen koblet"} tone="sun" />
              <Metric label="Forventet ut" value={period?.expectedExitLabel || selectedRoom.status.expectedExitLabel || "-"} detail={period?.overstayLabel || period?.remainingLabel || ""} tone={roomTone(selectedRoom)} />
              <Metric label="Effekt" value={energy?.statusLabel || "-"} detail={energy?.detail || `${selectedRoom.summary.energyConfirmed} bekreftet`} tone="energy" />
            </div>
          </div>
          <section className="solroom2-panel">
            <div className="solroom2-panel-title">
              <strong>Tidslinje</strong>
              <span>Dør, soltid, inngang og effekt</span>
            </div>
            <Timeline data={data} room={selectedRoom} />
          </section>
          <div className="solroom2-detail-grid">
            <section className="solroom2-panel">
              <div className="solroom2-panel-title">
                <strong>Hendelser</strong>
                <span>Nyest først</span>
              </div>
              <EventList events={selectedRoom.dayEvents || []} />
            </section>
            <section className="solroom2-panel">
              <div className="solroom2-panel-title">
                <strong>Perioder</strong>
                <span>{selectedRoom.periods.length}</span>
              </div>
              <PeriodTable periods={selectedRoom.periods} />
            </section>
          </div>
        </section>
      </div>
    </Space>
  );
}

export default function Solroom2Page() {
  const { view = "oversikt" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeView = SOLROOM2_VIEWS.includes(view as Solroom2View) ? (view as Solroom2View) : null;
  const selectedDay = normalizedDay(searchParams.get("day"));
  const selectedRoomParam = searchParams.get("room") || "";
  const overviewQuery = useApiQuery(
    queryKeys.doorSunroomOverview(2, selectedDay),
    () => fetchDoorSunroomOverview(2, selectedDay),
    { enabled: Boolean(activeView), refetchInterval: 30_000 },
  );
  const selectedRoomId =
    selectedRoomParam ||
    overviewQuery.data?.rooms.find((room) => ["alert", "warning", "waiting"].includes(roomTone(room)))?.roomId ||
    overviewQuery.data?.rooms[0]?.roomId ||
    "";
  const detailQuery = useApiQuery(
    queryKeys.doorSunroomRoom(selectedRoomId),
    () => fetchDoorSunroomRoomDetail(selectedRoomId),
    { enabled: activeView === "rom" && Boolean(selectedRoomId), refetchInterval: 30_000 },
  );

  function setSelectedDay(day: string) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      next.set("day", day);
      return next;
    });
  }

  function refetchAll() {
    overviewQuery.refetch();
    detailQuery.refetch();
  }

  if (!activeView) return <Navigate to="/solrom-2/oversikt" replace />;
  if (overviewQuery.loading) return <LoadingBlock />;
  if (overviewQuery.error || !overviewQuery.data) return <ErrorBlock error={overviewQuery.error} />;

  if (activeView === "dagskontroll") {
    return <DayControl data={overviewQuery.data} selectedDay={selectedDay} onDayChange={setSelectedDay} fetching={overviewQuery.fetching} refetch={() => overviewQuery.refetch()} />;
  }
  if (activeView === "avvik") {
    return <Deviations data={overviewQuery.data} selectedDay={selectedDay} onDayChange={setSelectedDay} fetching={overviewQuery.fetching} refetch={() => overviewQuery.refetch()} />;
  }
  if (activeView === "rom") {
    if (!selectedRoomId) return <Navigate to="/solrom-2/oversikt" replace />;
    return (
      <RoomDetail
        data={overviewQuery.data}
        detail={detailQuery.data}
        selectedDay={selectedDay}
        selectedRoomId={selectedRoomId}
        onDayChange={setSelectedDay}
        fetching={overviewQuery.fetching || detailQuery.fetching}
        refetch={refetchAll}
      />
    );
  }
  return <Overview data={overviewQuery.data} selectedDay={selectedDay} onDayChange={setSelectedDay} fetching={overviewQuery.fetching} refetch={() => overviewQuery.refetch()} />;
}
