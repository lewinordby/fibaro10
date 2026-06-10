import { Button, Card, Input, Space, Typography } from "antd";
import { Fragment } from "react";
import { Link } from "react-router-dom";
import type { SunTimeline, SunTimelineItem } from "../../api";

function sunNumber(value: number, maximumFractionDigits = 0): string {
  return new Intl.NumberFormat("nb-NO", { maximumFractionDigits }).format(value || 0);
}

function TimelineBlock({ item, aggregate = false }: { item: SunTimelineItem; aggregate?: boolean }) {
  return (
    <Link
      className={`${aggregate ? "sun-aggregate-block" : "sun-session-block"} kind-${item.kind}`}
      title={item.title}
      to={item.href}
      style={{ left: `${item.left}%`, width: `${item.width}%` }}
    >
      {aggregate ? null : <span>{item.label}</span>}
    </Link>
  );
}

function NowMarker({ value }: { value: number | null }) {
  if (value === null || value === undefined) return null;
  return <div className="sun-now-marker" style={{ left: `${value}%` }} />;
}

export function SunTimelinePanel({ timeline, onDayChange }: { timeline: SunTimeline; onDayChange: (day: string) => void }) {
  const peak = timeline.energySummary.peakHour;
  return (
    <Space direction="vertical" size={12} className="sun-timeline-stack">
      <Card className="work-card sun-timeline-toolbar">
        <Space size={8}>
          <Button size="small" onClick={() => onDayChange(timeline.prevDay)}>
            Forrige dag
          </Button>
          <Button size="small" onClick={() => onDayChange("")}>
            I dag
          </Button>
          <Button size="small" onClick={() => onDayChange(timeline.nextDay)}>
            Neste dag
          </Button>
        </Space>
        <Space size={8}>
          <Typography.Text type="secondary">Dato</Typography.Text>
          <Input
            className="sun-timeline-date"
            type="date"
            value={timeline.selectedDay}
            onChange={(event) => onDayChange(event.target.value)}
          />
        </Space>
      </Card>

      <Card
        className="chart-card sun-timeline-card"
        title="Rom gjennom døgnet"
        extra={
          <div className="sun-timeline-legend">
            <span>
              <i className="kind-standard" />
              Standard
            </span>
            <span>
              <i className="kind-member" />
              Medlem
            </span>
            <span>
              <i className="kind-no-member" />
              Ikke medlem
            </span>
          </div>
        }
      >
        <div className="sun-timeline-note">
          <span>{timeline.selectedDayLabel}</span>
          <span>
            {timeline.energySummary.hoursCount
              ? `${sunNumber(timeline.energySummary.totalKwh, 1)} kWh Elvia${peak ? `, topp ${String(peak.hour).padStart(2, "0")}:00` : ""}`
              : "Ingen Elvia-data for dagen"}
          </span>
        </div>
        <div className="sun-timeline-scroll">
          <div className="sun-timeline-grid">
            <div />
            <div className="sun-time-axis" aria-hidden="true">
              {timeline.ticks.map((tick) => (
                <span key={`${tick.label}-${tick.left}`} style={{ left: `${tick.left}%` }}>
                  {tick.label}
                </span>
              ))}
            </div>
            <div />

            <div className="sun-room-label">
              Strøm
              <small>Elvia</small>
            </div>
            <div className="sun-energy-line">
              <NowMarker value={timeline.nowMarker} />
              {timeline.energyHours.map((item) => (
                <div
                  className={`sun-energy-bar ${item.consumptionKwh ? "" : "empty"}`}
                  key={item.hour}
                  title={item.title}
                  style={{
                    left: `${item.left}%`,
                    width: `calc(${item.width}% - 2px)`,
                    height: `${item.consumptionKwh ? Math.max(6, item.height) : 2}%`,
                  }}
                />
              ))}
            </div>
            <div className="sun-energy-total">
              {timeline.energySummary.hoursCount ? `${sunNumber(timeline.energySummary.totalKwh, 1)} kWh` : "-"}
            </div>

            <div className="sun-room-label">
              Alle rom
              <small>sum</small>
            </div>
            <div className="sun-aggregate-line">
              <NowMarker value={timeline.nowMarker} />
              {timeline.aggregateSessions.map((item, index) => (
                <TimelineBlock aggregate item={item} key={`${item.href}-${item.left}-${index}`} />
              ))}
            </div>
            <div className="sun-aggregate-total">{timeline.totals.sessionsCount} stk</div>

            {timeline.rooms.map((room) => (
              <Fragment key={room.roomId}>
                <div className="sun-room-label">
                  {room.label}
                  <small>{room.roomId}</small>
                </div>
                <div className="sun-room-line">
                  <NowMarker value={timeline.nowMarker} />
                  {room.sessions.map((item, index) => (
                    <TimelineBlock item={item} key={`${room.roomId}-${item.left}-${index}`} />
                  ))}
                </div>
                <div className="sun-room-total">
                  {room.count} stk / {sunNumber(room.minutes)} min
                </div>
              </Fragment>
            ))}
          </div>
        </div>
        {!timeline.totals.sessionsCount ? <div className="sun-timeline-empty">Ingen enkelttimer er registrert for denne dagen.</div> : null}
      </Card>
    </Space>
  );
}
