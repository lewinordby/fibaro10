import { CalendarOutlined } from "@ant-design/icons";
import { Button, Card, Input, Space } from "antd";
import { Fragment } from "react";
import { Link } from "react-router-dom";
import type { ParkingTimeline, ParkingTimelineItem } from "../../api";
import { PeriodNavigator } from "../../components/PeriodNavigator";

function parkingNumber(value: number, maximumFractionDigits = 0): string {
  return new Intl.NumberFormat("nb-NO", { maximumFractionDigits }).format(value || 0);
}

function ParkingNowMarker({ value }: { value: number | null }) {
  if (value === null || value === undefined) return null;
  return <div className="parking-now-marker" style={{ left: `${value}%` }} />;
}

function ParkingBlock({ item }: { item: ParkingTimelineItem }) {
  return (
    <Link
      aria-label={item.title}
      className={`parking-session-block kind-${item.kind}`}
      title={item.title}
      to={item.href}
      style={{ left: `${item.left}%`, width: `${item.width}%` }}
    />
  );
}

function occupancySegments(count: number, scaleMax: number) {
  const capped = Math.min(Math.max(count, 0), scaleMax);
  return {
    normal: Math.min(capped, 20),
    warn: Math.max(0, Math.min(capped, 23) - 20),
    over: Math.max(0, capped - 23),
  };
}

export function ParkingTimelinePanel({
  timeline,
  onDayChange,
}: {
  timeline: ParkingTimeline;
  onDayChange: (day: string) => void;
}) {
  const layoutLabel = timeline.layout.map((row) => `${row.label} ${row.count} spor`).join(" + ");
  const occupancyScaleMax = timeline.occupancyScaleMax || 25;
  return (
    <Space direction="vertical" size={12} className="parking-timeline-stack">
      <Card className="work-card parking-timeline-toolbar">
        <PeriodNavigator
          previousLabel="Forrige dag"
          nextLabel="Neste dag"
          onPrevious={() => onDayChange(timeline.prevDay)}
          onNext={() => onDayChange(timeline.nextDay)}
          middle={
            <Button size="small" onClick={() => onDayChange("")}>
              I dag
            </Button>
          }
          extra={
            <Input
              className="parking-timeline-date"
              prefix={<CalendarOutlined />}
              type="date"
              value={timeline.selectedDay}
              onChange={(event) => onDayChange(event.target.value)}
            />
          }
        />
      </Card>

      <Card
        className="chart-card parking-timeline-card"
        title="Parkeringsdøgn kapasitet"
        extra={
          <div className="parking-timeline-legend">
            <span>
              <i className="kind-paid" />
              Betalt
            </span>
            <span>
              <i className="kind-ongoing" />
              Pågående
            </span>
            <span>
              <i className="kind-unpaid" />
              Uten beløp
            </span>
          </div>
        }
      >
        <div className="parking-timeline-note">
          <span>{timeline.selectedDayLabel}</span>
          <span>
            {layoutLabel} · topp {timeline.summary.peakCount}/{timeline.capacity}
            {timeline.summary.peakTimeLabel ? ` kl ${timeline.summary.peakTimeLabel}` : ""}
          </span>
        </div>

        <div className="parking-timeline-summary">
          <div>
            <span>Parkeringer</span>
            <strong>{parkingNumber(timeline.summary.sessionsCount)}</strong>
          </div>
          <div>
            <span>Omsetning</span>
            <strong>{parkingNumber(timeline.summary.paidAmountKr)} kr</strong>
          </div>
          <div>
            <span>Beleggstid</span>
            <strong>{parkingNumber(timeline.summary.durationHours, 1)} t</strong>
          </div>
          <div>
            <span>Utnyttelse</span>
            <strong>{parkingNumber(timeline.summary.utilizationPercent, 1)}%</strong>
          </div>
        </div>

        <div className="parking-timeline-scroll">
          <div className="parking-timeline-grid">
            <div />
            <div className="parking-time-axis" aria-hidden="true">
              {timeline.ticks.map((tick) => (
                <span key={`${tick.label}-${tick.left}`} style={{ left: `${tick.left}%` }}>
                  {tick.label}
                </span>
              ))}
            </div>
            <div />

            <div className="parking-space-label">
              Belegg
              <small>15 min</small>
            </div>
            <div className="parking-occupancy-line">
              <ParkingNowMarker value={timeline.nowMarker} />
              {timeline.occupancy.map((item, index) => {
                const segments = occupancySegments(item.count, occupancyScaleMax);
                return (
                  <div
                    className="parking-occupancy-stack"
                    key={`${item.left}-${index}`}
                    title={item.title}
                    style={{
                      left: `${item.left}%`,
                      width: `calc(${item.width}% - 1px)`,
                      opacity: item.count ? 1 : 0.16,
                    }}
                  >
                    {segments.normal ? (
                      <div
                        className="parking-occupancy-segment normal"
                        style={{ height: `${(segments.normal / occupancyScaleMax) * 100}%` }}
                      />
                    ) : null}
                    {segments.warn ? (
                      <div
                        className="parking-occupancy-segment warn"
                        style={{ height: `${(segments.warn / occupancyScaleMax) * 100}%` }}
                      />
                    ) : null}
                    {segments.over ? (
                      <div
                        className="parking-occupancy-segment over"
                        style={{ height: `${(segments.over / occupancyScaleMax) * 100}%` }}
                      />
                    ) : null}
                  </div>
                );
              })}
            </div>
            <div className="parking-space-total">{timeline.summary.peakCount}/{timeline.capacity}</div>

            {timeline.spaceRows.map((row) => (
              <Fragment key={row.key}>
                <div className="parking-row-heading">
                  <span>{row.label}</span>
                  <em>{row.count} spor fordelt etter samtidighet</em>
                </div>
                {row.spaces.map((space) => (
                  <Fragment key={space.spaceId}>
                    <div className="parking-space-label">
                      {space.label}
                      {space.count ? <small>{space.count} stk</small> : null}
                    </div>
                    <div className="parking-space-line">
                      <ParkingNowMarker value={timeline.nowMarker} />
                      {space.sessions.map((item) => (
                        <ParkingBlock item={item} key={item.id} />
                      ))}
                    </div>
                    <div className="parking-space-total">
                      {space.count ? `${parkingNumber(space.minutes)} min` : "-"}
                    </div>
                  </Fragment>
                ))}
              </Fragment>
            ))}

            {timeline.overflowSessions.length ? (
              <>
                <div className="parking-space-label">
                  Over
                  <small>kapasitet</small>
                </div>
                <div className="parking-space-line overflow">
                  {timeline.overflowSessions.map((item) => (
                    <ParkingBlock item={item} key={item.id} />
                  ))}
                </div>
                <div className="parking-space-total">{timeline.overflowSessions.length} stk</div>
              </>
            ) : null}
          </div>
        </div>

        {!timeline.summary.sessionsCount ? (
          <div className="parking-timeline-empty">Ingen parkeringer er registrert for denne dagen.</div>
        ) : null}
      </Card>
    </Space>
  );
}
