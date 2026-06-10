import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Card, Col, Row, Space, Typography } from "antd";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchStatusComparison,
  type StatusComparisonEvent,
  type StatusComparisonLane,
  type StatusComparisonSummary,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { nok } from "../format";
import { useAsyncData } from "../hooks";
import { appPath } from "../navigation";

function signedNok(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 kr";
  return `${value > 0 ? "+" : "-"}${nok(Math.abs(value))} kr`;
}

function signedCount(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 stk";
  return `${value > 0 ? "+" : "-"}${Math.abs(value)} stk`;
}

function timeText(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function eventPath(event: StatusComparisonEvent) {
  if (!event.href) return "#";
  return appPath(event.href) ?? event.href;
}

function TimelineEventBlock({ event, kind }: { event: StatusComparisonEvent; kind: StatusComparisonLane["kind"] }) {
  return (
    <Link
      className={`status-comparison-event kind-${kind} detail-${event.kind}`}
      style={{ left: `${event.left}%`, width: `${event.width}%` }}
      title={event.title}
      to={eventPath(event)}
    >
      <span>{event.label}</span>
    </Link>
  );
}

function TimelineLane({
  lane,
  ticks,
}: {
  lane: StatusComparisonLane;
  ticks: Array<{ label: string; left: number }>;
}) {
  return (
    <div className={`status-comparison-lane source-${lane.source} kind-${lane.kind}`}>
      <div className="status-comparison-lane-label">
        <strong>{lane.periodLabel}</strong>
        <span>{lane.label}</span>
        <em>
          {lane.count} stk / {nok(lane.paid)} kr
        </em>
      </div>
      <div className="status-comparison-track">
        {ticks.map((tick) => (
          <i className="status-comparison-track-tick" style={{ left: `${tick.left}%` }} key={`${lane.key}-${tick.label}-${tick.left}`} />
        ))}
        {lane.events.map((event) => (
          <TimelineEventBlock event={event} kind={lane.kind} key={event.id} />
        ))}
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  summary,
}: {
  title: string;
  summary: StatusComparisonSummary;
}) {
  return (
    <Card className="status-comparison-summary-card">
      <div className="status-comparison-summary-head">
        <span>{title}</span>
        <strong>{nok(summary.total)} kr</strong>
      </div>
      <div className="status-comparison-summary-meta">
        <span>Sol {summary.solAsOfLabel}</span>
        <span>Parkering {summary.parkingAsOfLabel}</span>
      </div>
      <div className="status-comparison-summary-split">
        <div>
          <span>Soling</span>
          <strong>{nok(summary.sol)} kr</strong>
          <em>{summary.solCount} stk</em>
        </div>
        <div>
          <span>Parkering</span>
          <strong>{nok(summary.parking)} kr</strong>
          <em>{summary.parkingCount} stk</em>
        </div>
      </div>
    </Card>
  );
}

export default function StatusComparisonPage() {
  const [searchParams] = useSearchParams();
  const period = searchParams.get("period") || "today";
  const compare = searchParams.get("compare") || "previous";
  const { data, loading, error } = useAsyncData(() => fetchStatusComparison(period, compare), [period, compare]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-comparison-page">
      <div className="status-comparison-top">
        <div>
          <Typography.Text className="eyebrow">Status sammenligning</Typography.Text>
          <div className="status-comparison-title">
            <strong>{data.title}</strong>
            <span>{data.comparisonLabel}</span>
          </div>
        </div>
        <Button icon={<ArrowLeftOutlined />}>
          <Link to="/status/oversikt">Oversikt</Link>
        </Button>
      </div>

      <Row gutter={[14, 14]}>
        <Col span={8}>
          <SummaryCard title={data.current.label} summary={data.current} />
        </Col>
        <Col span={8}>
          <SummaryCard title={data.comparison.label} summary={data.comparison} />
        </Col>
        <Col span={8}>
          <Card className="status-comparison-delta-card">
            <span>Differanse</span>
            <strong>{signedNok(data.delta.total)}</strong>
            <div>
              <em>Soling {signedNok(data.delta.sol)} / {signedCount(data.delta.solCount)}</em>
              <em>Parkering {signedNok(data.delta.parking)} / {signedCount(data.delta.parkingCount)}</em>
            </div>
          </Card>
        </Col>
      </Row>

      <Card
        className="status-comparison-timeline-card"
        title="Tidslinje"
        extra={
          <div className="status-comparison-legend">
            <span><i className="kind-sun" />Soling</span>
            <span><i className="kind-parking" />Parkering</span>
          </div>
        }
      >
        <div className="status-comparison-axis-meta">
          <span>{timeText(data.axis.start)}</span>
          <span>{timeText(data.axis.end)}</span>
        </div>
        <div className="status-comparison-scroll">
          <div className="status-comparison-grid">
            <div />
            <div className="status-comparison-axis">
              {data.axis.ticks.map((tick) => (
                <span key={`${tick.label}-${tick.left}`} style={{ left: `${tick.left}%` }}>
                  {tick.label}
                </span>
              ))}
            </div>
            {data.lanes.map((lane) => (
              <TimelineLane lane={lane} ticks={data.axis.ticks} key={lane.key} />
            ))}
          </div>
        </div>
      </Card>
    </Space>
  );
}
