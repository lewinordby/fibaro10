import { useEffect, useMemo, useState } from "react";
import { domainApi } from "../api";
import { useApi } from "../hooks";
import { AppLink, useAppSearchParams } from "../router";
import { MetricCard, Panel } from "./Mosaic";
import { ErrorState, Loading } from "./PageState";

type RecordValue = Record<string, any>;
type DoorStatus = {
  generatedAt: string;
  summary: RecordValue;
  doors: RecordValue[];
  changes: RecordValue[];
  periods: RecordValue[];
};
type Sunrooms = {
  generatedAt: string;
  ntfyDoorsSubscribeUrl?: string;
  ntfyDoorsWebUrl?: string;
  rules: RecordValue;
  summary: RecordValue;
  rooms: RecordValue[];
};
type RoomOverview = {
  generatedAt: string;
  dayDate?: string;
  dayStart?: string;
  dayEnd?: string;
  summary: RecordValue;
  rules: RecordValue;
  rooms: RecordValue[];
};

function localDay() {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Oslo" });
}
function shiftDay(day: string, amount: number) {
  const value = new Date(`${day}T12:00:00`);
  value.setDate(value.getDate() + amount);
  return value.toLocaleDateString("sv-SE");
}
function stamp(value?: string | null) {
  return value
    ? new Date(value).toLocaleString("nb-NO", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: "Europe/Oslo",
      })
    : "-";
}
function tone(value?: string) {
  return ["alert", "alarm"].includes(String(value))
    ? "red"
    : ["warning", "waiting"].includes(String(value))
      ? "yellow"
      : ["active", "closed"].includes(String(value))
        ? "sky"
        : "green";
}
function badge(value: string, color: string) {
  const classes: Record<string, string> = {
    red: "bg-red-500/10 text-red-700 dark:text-red-300",
    yellow: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-300",
    sky: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
    green: "bg-green-500/10 text-green-700 dark:text-green-300",
    gray: "bg-gray-500/10 text-gray-600 dark:text-gray-300",
  };
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${classes[color]}`}
    >
      {value}
    </span>
  );
}

export function DoorsSpecial({ view }: { view: string }) {
  if (["solrom", "solrom-ny", "solrom2-oversikt"].includes(view)) return <SunroomStatus compact={view === "solrom-ny"} />;
  if (["romkontroll-ny2", "soltimer", "romkontroll"].includes(view)) return <RoomControl />;
  if (["romkontroll-ny", "solrom-dagskontroll", "solrom2-dagskontroll"].includes(view)) return <RoomControl matrix />;
  if (view === "solrom2-avvik") return <RoomControl exceptions />;
  return <DoorOverview initialFilter={["andre", "dorer2-bygg"].includes(view) ? "andre" : "all"} />;
}

function DoorOverview({ initialFilter }: { initialFilter: "all" | "andre" }) {
  const result = useApi(
    () =>
      domainApi.get<DoorStatus>(
        "/api/hc3/doors/status?history_limit=150&period_limit=150",
      ),
    "door-status-special",
  );
  const [filter, setFilter] = useState<"all" | "solrom" | "andre">(initialFilter);
  if (result.loading) return <Loading />;
  if (result.error || !result.data)
    return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  const groups = [
    {
      key: "solrom",
      title: "Solrom",
      rows: data.doors.filter((row) => row.groupKey === "solrom"),
    },
    {
      key: "andre",
      title: "Andre dører",
      rows: data.doors.filter((row) => row.groupKey !== "solrom"),
    },
  ].filter((group) => filter === "all" || filter === group.key);
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          {([
            { key: "all", label: "Alle" },
            { key: "solrom", label: "Solrom" },
            { key: "andre", label: "Andre dører" },
          ] as const).map((item) => (
            <button
              className={`btn ${filter === item.key ? "bg-violet-500 text-white" : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"}`}
              onClick={() => setFilter(item.key)}
              key={item.key}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>Oppdatert {stamp(data.generatedAt)}</span>
          <button
            className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
            onClick={result.reload}
          >
            Oppdater
          </button>
        </div>
      </div>
      {groups.map((group) => (
        <section className="space-y-3" key={group.key}>
          <div className="flex items-end justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {group.title}
              </h2>
              <p className="text-xs text-gray-500">{group.rows.length} dører</p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-6">
            {group.rows.map((door) => (
              <DoorCard
                door={door}
                sunroom={group.key === "solrom"}
                key={door.deviceKey}
              />
            ))}
          </div>
        </section>
      ))}
      <Panel title="Siste statusendringer" subtitle="Nyeste først">
        <div className="divide-y divide-gray-100 dark:divide-gray-700/60">
          {data.changes.slice(0, 16).map((event) => (
            <div
              className="grid grid-cols-[6rem_1fr_auto] items-center gap-4 px-5 py-3 text-sm"
              key={event.id}
            >
              <strong className="tabular-nums">
                {event.timeLabel || stamp(event.timestamp)}
              </strong>
              <span>{event.deviceName}</span>
              {badge(
                event.stateLabel || event.action || "Endret",
                event.tone === "warn" ? "yellow" : "green",
              )}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function DoorCard({ door, sunroom }: { door: RecordValue; sunroom: boolean }) {
  const [open, setOpen] = useState(false);
  const isOpen = door.state === "open";
  const good = sunroom ? isOpen : !isOpen;
  const primary = sunroom ? (isOpen ? "Ledig" : "I bruk") : door.stateLabel;
  return (
    <article
      className={`overflow-hidden rounded-xl border bg-white shadow-sm dark:bg-gray-800 ${good ? "border-green-200 dark:border-green-900" : "border-red-200 dark:border-red-900"}`}
    >
      <button
        className="w-full p-4 text-left"
        onClick={() => setOpen((value) => !value)}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase text-gray-400">
              {door.sectionTitle || door.groupTitle}
            </p>
            <h3 className="mt-1 text-base font-bold text-gray-800 dark:text-gray-100">
              {door.title}
            </h3>
          </div>
          <span
            className={`flex h-9 w-9 items-center justify-center rounded-lg text-lg ${good ? "bg-green-500/10 text-green-600" : "bg-red-500/10 text-red-600"}`}
            aria-hidden="true"
          >
            {isOpen ? "↗" : "▮"}
          </span>
        </div>
        <div className="mt-4 flex items-end justify-between gap-3">
          <div>
            <strong
              className={
                good
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-600 dark:text-red-400"
              }
            >
              {primary}
            </strong>
            <p className="mt-1 text-xs text-gray-500">
              Siden {door.ageLabel || "ukjent"}
            </p>
          </div>
          <span className="text-xs text-gray-400">
            {door.lastChangedLabel || "-"}
          </span>
        </div>
      </button>
      {open ? (
        <div className="border-t border-gray-100 bg-gray-50 px-4 py-3 text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-900/30">
          <div className="grid grid-cols-2 gap-2">
            <span>Sensor</span>
            <strong className="text-right">HC3 {door.deviceId || "-"}</strong>
            <span>Batteri</span>
            <strong className="text-right">{door.batteryLabel || "-"}</strong>
            <span>Normalstilling</span>
            <strong className="text-right">
              {door.normalStateLabel || "-"}
            </strong>
          </div>
        </div>
      ) : null}
    </article>
  );
}

function SunroomStatus({ compact = false }: { compact?: boolean }) {
  const result = useApi(
    () => domainApi.get<Sunrooms>("/api/hc3/doors/sunroom-sessions"),
    "door-sunrooms-special",
  );
  if (result.loading) return <Loading />;
  if (result.error || !result.data)
    return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-5">
        <MetricCard
          label="Rom"
          value={data.summary.rooms || 0}
          unit="stk"
          detail="Med dørsensor"
          tone="violet"
        />
        <MetricCard
          label="Aktive"
          value={data.summary.active || 0}
          unit="stk"
          detail="Soltime pågår"
          tone="sky"
        />
        <MetricCard
          label="Venter"
          value={data.summary.waiting || 0}
          unit="stk"
          detail="Avventer soltime"
          tone="yellow"
        />
        <MetricCard
          label="Varsel"
          value={(data.summary.warning || 0) + (data.summary.alert || 0)}
          unit="stk"
          detail="Krever kontroll"
          tone="red"
        />
        <MetricCard
          label="Uten soltime"
          value={data.summary.missingSession || 0}
          unit="stk"
          detail={`${data.rules.noSessionAlarmMinutes || 8} min alarmgrense`}
          tone="yellow"
        />
      </div>
      <div className="flex justify-end gap-2">
        {data.ntfyDoorsSubscribeUrl ? (
          <a
            className="btn bg-violet-500 text-white"
            href={data.ntfyDoorsSubscribeUrl}
          >
            Abonner på dørvarsler
          </a>
        ) : null}
        <button
          className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
          onClick={result.reload}
        >
          Oppdater
        </button>
      </div>
      <div className={`grid gap-4 ${compact ? "sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-6" : "md:grid-cols-2 xl:grid-cols-3"}`}>
        {data.rooms.map((room) => (
          <SunroomCard room={room} compact={compact} key={room.deviceKey} />
        ))}
      </div>
    </div>
  );
}

function SunroomCard({ room, compact = false }: { room: RecordValue; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const session = room.session || {};
  const roomNumber = String(
    room.displayRoomNumber || room.roomNumber || room.roomLabel || "",
  ).replace(/\D/g, "");
  return (
    <article
      className={`overflow-hidden rounded-xl border bg-white shadow-sm dark:bg-gray-800 ${room.severity === "alert" ? "border-red-400" : room.severity === "warning" || room.missingSession ? "border-yellow-400" : "border-gray-200 dark:border-gray-700"}`}
    >
      <button
        className="w-full p-5 text-left"
        onClick={() => setOpen((value) => !value)}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase text-gray-400">
              {room.sectionTitle}
            </p>
            <h3 className="mt-1 text-xl font-bold text-gray-800 dark:text-gray-100">
              {room.title}
            </h3>
          </div>
          {badge(room.status || room.doorStateLabel, tone(room.severity))}
        </div>
        <div className={`mt-5 grid gap-3 text-sm ${compact ? "grid-cols-2" : "grid-cols-3"}`}>
          <div className={compact ? "col-span-2" : ""}>
            <small className="block text-gray-400">Dør</small>
            <strong>{room.doorStateLabel}</strong>
            <p className="text-xs text-gray-400">{room.doorAgeLabel}</p>
          </div>
          <div>
            <small className="block text-gray-400">Soltime</small>
            <strong>{session.startedLabel || "-"}</strong>
            <p className="text-xs text-gray-400">
              {session.durationMinutes
                ? `${session.durationMinutes} min`
                : "Ingen aktiv"}
            </p>
          </div>
          <div>
            <small className="block text-gray-400">Forventet ut</small>
            <strong>{room.expectedExitLabel || "-"}</strong>
            <p className="text-xs text-gray-400">
              {room.remainingLabel || room.overstayLabel || ""}
            </p>
          </div>
        </div>
      </button>
      {open ? (
        <div className="border-t border-gray-100 bg-gray-50 p-4 text-sm dark:border-gray-700 dark:bg-gray-900/30">
          <div className="grid grid-cols-2 gap-y-2">
            <span>Sun2-ID</span>
            <strong className="text-right">{session.sun2UserId || "-"}</strong>
            <span>Seng</span>
            <strong className="text-right">
              {session.sun2BedId || room.roomLabel || "-"}
            </strong>
            <span>Betalt</span>
            <strong className="text-right">
              {session.paidAmountKr == null
                ? "-"
                : `${session.paidAmountKr} kr`}
            </strong>
            <span>Detalj</span>
            <strong className="text-right">{room.detail || "-"}</strong>
          </div>
          {roomNumber ? (
            <AppLink
              className="btn mt-4 w-full justify-center bg-violet-500 text-white"
              to={`/dorer/romkontroll?room=${encodeURIComponent(roomNumber)}&day=${encodeURIComponent(localDay())}`}
            >
              Vis dagens hendelser
            </AppLink>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function RoomControl({ matrix = false, exceptions = false }: { matrix?: boolean; exceptions?: boolean }) {
  const [params, setParams] = useAppSearchParams();
  const day = params.get("day") || localDay();
  const roomParam = params.get("room") || "";
  const result = useApi(
    () =>
      domainApi.get<RoomOverview>(
        `/api/hc3/doors/sunroom-overview?days=2&day=${encodeURIComponent(day)}`,
      ),
    `room-control-${day}`,
  );
  const [selectedRoom, setSelectedRoom] = useState(roomParam);
  useEffect(() => {
    if (
      result.data?.rooms.length &&
      !result.data.rooms.some(
        (room) => String(room.displayRoomNumber) === selectedRoom,
      )
    )
      setSelectedRoom(String(result.data.rooms[0].displayRoomNumber));
  }, [result.data, selectedRoom]);
  const updateSelection = (nextDay: string, nextRoom = selectedRoom) => {
    const next = new URLSearchParams(params);
    next.set("day", nextDay);
    if (nextRoom) next.set("room", nextRoom);
    setParams(next);
  };
  const setDay = (value: string) => updateSelection(value);
  const selectRoom = (value: string) => {
    setSelectedRoom(value);
    updateSelection(day, value);
  };
  if (result.loading) return <Loading />;
  if (result.error || !result.data)
    return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  const room =
    data.rooms.find(
      (item) => String(item.displayRoomNumber) === selectedRoom,
    ) || data.rooms[0];
  return (
    <div className="space-y-5">
      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div>
            <p className="text-xs font-semibold uppercase text-gray-400">
              Romkontroll
            </p>
            <strong>{data.dayDate || day}</strong>
            <p className="text-xs text-gray-500">
              {data.summary.daySessions || data.summary.sessions || 0} soltimer
              · {data.summary.dayEvents || 0} hendelser ·{" "}
              {data.summary.energyConfirmed || 0} effektbekreftet
            </p>
          </div>
          <div className="flex gap-2">
            <button
              className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
              onClick={() => setDay(shiftDay(day, -1))}
            >
              Forrige dag
            </button>
            <input
              className="form-input"
              type="date"
              max={localDay()}
              value={day}
              onChange={(event) => setDay(event.target.value)}
            />
            <button
              className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
              disabled={day >= localDay()}
              onClick={() => setDay(shiftDay(day, 1))}
            >
              Neste dag
            </button>
            <button
              className="btn bg-violet-500 text-white"
              onClick={() => setDay(localDay())}
            >
              I dag
            </button>
          </div>
        </div>
      </Panel>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {data.rooms.map((item) => {
          const active =
            Number(item.summary?.periods || 0) +
              Number(item.summary?.sessions || 0) >
            0;
          return (
            <button
              className={`min-w-20 rounded-lg border px-3 py-2 text-sm font-semibold ${String(item.displayRoomNumber) === selectedRoom ? "border-violet-500 bg-violet-500 text-white" : active ? "border-yellow-300 bg-yellow-50 text-gray-800 dark:border-yellow-800 dark:bg-yellow-950/30 dark:text-gray-100" : "border-gray-200 bg-white text-gray-500 dark:border-gray-700 dark:bg-gray-800"}`}
              onClick={() => selectRoom(String(item.displayRoomNumber))}
              key={item.displayRoomNumber}
            >
              Rom {item.displayRoomNumber}
              <small className="mt-0.5 block font-normal">
                {active
                  ? `${item.summary.sessions || 0} timer`
                  : "Ingen aktivitet"}
              </small>
            </button>
          );
        })}
      </div>
      {matrix || exceptions ? <RoomMatrix rooms={data.rooms} day={day} exceptions={exceptions} /> : room ? <RoomDay room={room} day={day} /> : null}
    </div>
  );
}

function RoomMatrix({
  rooms,
  day,
  exceptions,
}: {
  rooms: RecordValue[];
  day: string;
  exceptions: boolean;
}) {
  const visible = exceptions
    ? rooms.filter(
        (room) =>
          Number(room.summary?.warnings || 0) > 0 ||
          Number(room.summary?.alerts || 0) > 0 ||
          Number(room.summary?.matched || 0) < Number(room.summary?.sessions || 0),
      )
    : rooms;
  return (
    <Panel
      title={exceptions ? "Avvik og usikre koblinger" : `Dagsmatrise ${day}`}
      subtitle={
        exceptions
          ? `${visible.length} rom krever kontroll`
          : "Alle solrom samlet for valgt dag"
      }
    >
      <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
        {visible.map((room) => {
          const summary = room.summary || {};
          const alert = Number(summary.alerts || 0) > 0;
          const warning =
            Number(summary.warnings || 0) > 0 ||
            Number(summary.matched || 0) < Number(summary.sessions || 0);
          return (
            <AppLink
              className={`rounded-lg border p-4 text-left transition hover:-translate-y-0.5 ${
                alert
                  ? "border-red-300 bg-red-50/60 dark:border-red-900 dark:bg-red-950/20"
                  : warning
                    ? "border-yellow-300 bg-yellow-50/60 dark:border-yellow-900 dark:bg-yellow-950/20"
                    : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
              }`}
              to={`/dorer/romkontroll?room=${encodeURIComponent(String(room.displayRoomNumber))}&day=${encodeURIComponent(day)}`}
              key={room.deviceKey || room.displayRoomNumber}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="text-xs font-semibold uppercase text-gray-400">
                    {room.sectionTitle}
                  </span>
                  <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100">
                    Rom {room.displayRoomNumber}
                  </h3>
                </div>
                {badge(
                  alert ? "Alarm" : warning ? "Kontroller" : "OK",
                  alert ? "red" : warning ? "yellow" : "green",
                )}
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-gray-500">Soltimer</dt>
                <dd className="text-right font-semibold">{summary.sessions || 0}</dd>
                <dt className="text-gray-500">Matchet</dt>
                <dd className="text-right font-semibold">{summary.matched || 0}</dd>
                <dt className="text-gray-500">Effekt</dt>
                <dd className="text-right font-semibold">{summary.energyConfirmed || 0}</dd>
                <dt className="text-gray-500">Varsler</dt>
                <dd className="text-right font-semibold">
                  {Number(summary.warnings || 0) + Number(summary.alerts || 0)}
                </dd>
              </dl>
            </AppLink>
          );
        })}
        {!visible.length ? (
          <div className="p-8 text-sm text-gray-500">Ingen avvik i valgt dag.</div>
        ) : null}
      </div>
    </Panel>
  );
}

function RoomDay({ room, day }: { room: RecordValue; day: string }) {
  const events = [...(room.dayEvents || [])].sort((left, right) =>
    String(right.time || "").localeCompare(String(left.time || "")),
  );
  const timelineEvents = [...events].sort((left, right) =>
    String(left.time || "").localeCompare(String(right.time || "")),
  );
  const left = (value?: string) => {
    if (!value) return 0;
    const date = new Date(value);
    const minutes = date.getHours() * 60 + date.getMinutes();
    return Math.max(0, Math.min(100, ((minutes - 360) / 1080) * 100));
  };
  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-4">
        <MetricCard
          label="Dør nå"
          value={room.status?.doorStateLabel || "Ukjent"}
          detail={room.status?.doorAgeLabel || ""}
          tone={room.status?.doorState === "closed" ? "red" : "green"}
        />
        <MetricCard
          label="Siste lukket"
          value={room.latestPeriod?.closedLabel || "-"}
          detail={room.latestPeriod?.durationLabel || ""}
          tone="gray"
        />
        <MetricCard
          label="Siste åpnet"
          value={room.latestPeriod?.openedLabel || "-"}
          detail={room.latestPeriod?.status || ""}
          tone="gray"
        />
        <MetricCard
          label="Dagens kontroll"
          value={`${room.summary?.matched || 0} / ${room.summary?.sessions || 0}`}
          detail={`${room.summary?.warnings || 0} varsler · ${room.summary?.alerts || 0} alarmer`}
          tone={room.summary?.alerts ? "red" : "green"}
        />
      </div>
      <Panel
        title={`${room.title} · ${day}`}
        subtitle={`${room.sectionTitle} · åpningstid 06:00-24:00`}
      >
        <div className="p-5">
          <div className="relative mt-7 h-20 rounded-lg border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/30">
            <div className="absolute inset-x-0 top-1/2 border-t border-gray-300 dark:border-gray-600" />
            {Array.from({ length: 10 }, (_, index) => (
              <span
                className="absolute bottom-1 text-[10px] text-gray-400"
                style={{ left: `${index * 11.11}%` }}
                key={index}
              >
                {String(6 + index * 2).padStart(2, "0")}
              </span>
            ))}
            {timelineEvents.map((event, index) => (
              <span
                className={`absolute top-3 h-8 w-0.5 ${String(event.tone).includes("warn") ? "bg-red-500" : String(event.kind).includes("session") ? "bg-yellow-500" : "bg-violet-500"}`}
                style={{ left: `${left(event.time)}%` }}
                title={`${event.timeLabel} ${event.label} ${event.detail || ""}`}
                key={`${event.id}-${index}`}
              >
                <i className="absolute -left-1 -top-1 h-2.5 w-2.5 rounded-full bg-current" />
              </span>
            ))}
          </div>
        </div>
      </Panel>
      <Panel title="Hendelser" subtitle="Nyeste først">
        <div className="divide-y divide-gray-100 dark:divide-gray-700/60">
          {events.map((event) => (
            <div
              className="grid grid-cols-[5rem_9rem_1fr_auto] gap-3 px-5 py-3 text-sm"
              key={event.id}
            >
              <strong className="tabular-nums">
                {event.timeLabel || stamp(event.time)}
              </strong>
              <span>{event.label}</span>
              <span className="text-gray-500">{event.detail || ""}</span>
              {badge(
                event.source || event.kind || "Hendelse",
                String(event.tone).includes("warn") ? "yellow" : "gray",
              )}
            </div>
          ))}
          {!events.length ? (
            <div className="p-8 text-center text-sm text-gray-500">
              Ingen hendelser for dette rommet denne dagen.
            </div>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}
