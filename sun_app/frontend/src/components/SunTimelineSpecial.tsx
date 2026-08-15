import { AppLink, MosaicIcon, Panel, nok, resolveCorePath, useAppSearchParams } from "@lilletorget/microapp-ui";
import type { SunTimeline } from "../types";

function localPath(path: string | undefined) {
  return resolveCorePath(path, "sun");
}

function todayInOslo() {
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Europe/Oslo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function timelineItemClass(kind: string) {
  if (kind === "member") return "bg-yellow-500";
  if (kind === "no-member") return "bg-red-400";
  return "bg-sky-500";
}

export function SunTimelineSpecial({ timeline }: { timeline: SunTimeline }) {
  const [, setParams] = useAppSearchParams();
  const today = todayInOslo();
  const isToday = timeline.selectedDay >= today;
  const go = (day: string) => {
    const next = new URLSearchParams(window.location.search);
    day ? next.set("day", day) : next.delete("day");
    setParams(next);
  };

  return (
    <div className="space-y-5">
      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
          <div className="flex gap-2">
            <button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go(timeline.prevDay)} title="Forrige dag">
              <MosaicIcon name="arrow-left" />
            </button>
            <button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => go("")}>I dag</button>
            <button
              className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
              disabled={isToday}
              onClick={() => go(timeline.nextDay)}
              title="Neste dag"
            >
              <MosaicIcon name="arrow-right" />
            </button>
          </div>
          <strong className="text-sm text-gray-800 dark:text-gray-100">{timeline.selectedDayLabel}</strong>
          <input className="form-input" max={today} type="date" value={timeline.selectedDay} onChange={(event) => go(event.target.value)} />
        </div>
      </Panel>

      <Panel
        title="Rom gjennom døgnet"
        subtitle={`${timeline.totals.sessionsCount} solinger · ${nok(timeline.totals.paidAmountKr)} kr · ${nok(timeline.totals.durationMinutes)} min`}
      >
        <div className="overflow-x-auto p-5">
          <div className="min-w-[760px] space-y-2">
            <div className="grid grid-cols-[7rem_1fr_5rem] gap-3">
              <span />
              <div className="relative h-5">
                {timeline.ticks.map((tick) => (
                  <span className="absolute text-[10px] text-gray-400" style={{ left: `${tick.left}%` }} key={tick.label}>{tick.label}</span>
                ))}
              </div>
              <span />
            </div>

            {timeline.rooms.map((room) => (
              <div className="grid grid-cols-[7rem_1fr_5rem] items-center gap-3" key={room.roomId}>
                <strong className="text-xs text-gray-600 dark:text-gray-300">{room.label}</strong>
                <div className="relative h-8 overflow-hidden rounded-md border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/30">
                  {timeline.ticks.map((tick) => (
                    <span className="absolute inset-y-0 border-l border-gray-200 dark:border-gray-700" style={{ left: `${tick.left}%` }} key={tick.label} />
                  ))}
                  {room.sessions.map((item, index) => {
                    const href = localPath(item.href);
                    const block = (
                      <span
                        className={`absolute inset-y-1 min-w-px rounded ${timelineItemClass(item.kind)}`}
                        style={{ left: `${item.left}%`, width: `${item.width}%` }}
                        title={item.title}
                      />
                    );
                    return href
                      ? <AppLink to={href} key={`${item.left}-${index}`}>{block}</AppLink>
                      : <span key={`${item.left}-${index}`}>{block}</span>;
                  })}
                  {timeline.nowMarker != null ? (
                    <span className="absolute inset-y-0 border-l-2 border-red-500" style={{ left: `${timeline.nowMarker}%` }} />
                  ) : null}
                </div>
                <span className="text-right text-xs tabular-nums text-gray-500">{room.count} / {room.minutes}m</span>
              </div>
            ))}
          </div>
        </div>
      </Panel>
    </div>
  );
}
