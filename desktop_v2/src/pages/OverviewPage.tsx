import { CheckCircleOutlined, ClockCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { Card, Col, List, Row, Space, Tag, Tooltip, Typography } from "antd";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  fetchOverview,
  type MetricCard as MetricCardData,
  type ServiceStatus,
  type StatusPeriod,
  type StatusPeriodComparison,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { nok } from "../format";
import { useAsyncData } from "../hooks";
import { appPath } from "../navigation";

type StripState = { label: string; state: boolean | null; tooltip?: string };
type StripItem = { label: string; state?: boolean | null; states?: StripState[]; tooltip?: string };

const SPOT_FRONT_LABELS = new Set(["Spot foran glassvegg", "Spot foran massasje"]);

const DATASOURCE_PRIORITY = [
  "hc3_energy_1min",
  "hc3_light_5min",
  "hc3_ventilation_5min",
  "sun2_sessions_import",
  "easypark_parking_import",
  "yr_weather_refresh",
  "roborock_sync",
  "parking_vehicle_svv_sync",
];

function stateTag(state: boolean | null) {
  if (state === true) return <Tag color="green">På</Tag>;
  if (state === false) return <Tag color="default">Av</Tag>;
  return <Tag>Ukjent</Tag>;
}

function stateTagWithTooltip(state: boolean | null, tooltip?: string) {
  const tag = stateTag(state);
  if (!tooltip) return tag;
  return (
    <Tooltip title={tooltip}>
      <span className="status-strip-tag-wrap" aria-label={tooltip}>
        {tag}
      </span>
    </Tooltip>
  );
}

function statusIcon(status: string) {
  if (status === "ok") return <CheckCircleOutlined className="status-ok" />;
  if (status === "bad") return <WarningOutlined className="status-bad" />;
  return <ClockCircleOutlined className="status-warn" />;
}

function isCombinedRevenueSource(card: MetricCardData) {
  return card.group === "Omsetning" || card.group === "Soling" || card.group === "Parkering";
}

function isOverviewSupportCard(card: MetricCardData) {
  if (isCombinedRevenueSource(card)) return false;
  return card.title !== "Åpning" && card.title !== "Datakilder";
}

function serviceRank(service: ServiceStatus) {
  const directRank = DATASOURCE_PRIORITY.indexOf(service.jobName || "");
  if (directRank >= 0) return directRank;
  if (service.label.toLowerCase().includes("easypark")) {
    return DATASOURCE_PRIORITY.indexOf("easypark_parking_import");
  }
  return DATASOURCE_PRIORITY.length + 1;
}

function sortedDatasources(services: ServiceStatus[]) {
  return services
    .map((service, index) => ({ service, index }))
    .sort((a, b) => serviceRank(a.service) - serviceRank(b.service) || a.index - b.index)
    .map((row) => row.service);
}

function signedNok(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 kr";
  return `${value > 0 ? "+" : "-"}${nok(Math.abs(value))} kr`;
}

function percentDelta(current: number, previous: number) {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) return "";
  const percent = ((current - previous) / previous) * 100;
  if (Math.abs(percent) < 0.5) return "0%";
  return `${percent > 0 ? "+" : "-"}${Math.abs(percent).toFixed(0)}%`;
}

function deltaClass(current: number, previous: number) {
  if (current > previous) return "positive";
  if (current < previous) return "negative";
  return "neutral";
}

function lightStripItems(items: Array<{ label: string; state: boolean | null }>): StripItem[] {
  const glassSpot = items.find((item) => item.label === "Spot foran glassvegg");
  const massageSpot = items.find((item) => item.label === "Spot foran massasje");
  let spotFrontInserted = false;
  const stripItems: StripItem[] = [];

  for (const item of items) {
    if (SPOT_FRONT_LABELS.has(item.label)) {
      if (spotFrontInserted) continue;
      spotFrontInserted = true;
      stripItems.push({
        label: "Spot foran",
        states: [
          { label: "glassvegg", state: glassSpot?.state ?? null, tooltip: "Spot foran glassvegg" },
          { label: "massasje", state: massageSpot?.state ?? null, tooltip: "Spot foran massasje" },
        ],
      });
      continue;
    }
    stripItems.push({ ...item, tooltip: item.label });
  }

  return stripItems;
}

function StatusStrip({
  title,
  items,
}: {
  title: string;
  items: StripItem[];
}) {
  return (
    <div className="status-strip">
      <div className="status-strip-title">{title}</div>
      <div className="status-strip-items">
        {items.map((item) => (
          <div className="status-strip-item" key={item.label}>
            <span>{item.label}</span>
            {item.states ? (
              <span className="status-strip-state-group">
                {item.states.map((state) => (
                  <span key={state.label}>{stateTagWithTooltip(state.state, state.tooltip)}</span>
                ))}
              </span>
            ) : (
              stateTagWithTooltip(item.state ?? null, item.tooltip)
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ComparisonRow({
  comparison,
  currentTotal,
}: {
  comparison: StatusPeriodComparison;
  currentTotal: number;
}) {
  const delta = currentTotal - comparison.total;
  const percent = percentDelta(currentTotal, comparison.total);

  return (
    <div className="status-period-comparison-row">
      <div className="status-period-comparison-main">
        <span>{comparison.label}</span>
        <strong>{nok(comparison.total)} kr</strong>
      </div>
      <div className={`status-period-delta ${deltaClass(currentTotal, comparison.total)}`}>
        <span>{signedNok(delta)}</span>
        {percent ? <em>{percent}</em> : null}
      </div>
      <div className="status-period-comparison-detail">
        <span>
          Soling {comparison.solCount} stk / {nok(comparison.sol)} kr · {comparison.solAsOfLabel}
        </span>
        <span>
          Parkering {comparison.parkingCount} stk / {nok(comparison.parking)} kr · {comparison.parkingAsOfLabel}
        </span>
      </div>
    </div>
  );
}

function RevenuePeriodCard({ period }: { period: StatusPeriod }) {
  const comparisons: StatusPeriodComparison[] = [
    {
      label: period.previousLabel,
      sol: period.previousSol,
      solCount: period.previousSolCount,
      parking: period.previousParking,
      parkingCount: period.previousParkingCount,
      total: period.previousTotal,
      solAsOfLabel: period.previousSolAsOfLabel,
      parkingAsOfLabel: period.previousParkingAsOfLabel,
    },
    ...(period.extraComparisons ?? []),
  ];

  return (
    <Card className="status-period-card">
      <div className="status-period-head">
        <div>
          <span>{period.title}</span>
          <em>Sol {period.solAsOfLabel} · parkering {period.parkingAsOfLabel}</em>
        </div>
        <strong>{nok(period.total)} kr</strong>
      </div>
      <div className="status-period-rows">
        <div>
          <span>Soling</span>
          <strong>{nok(period.sol)} kr</strong>
          <em>{period.solCount} stk</em>
        </div>
        <div>
          <span>Parkering</span>
          <strong>{nok(period.parking)} kr</strong>
          <em>{period.parkingCount} stk</em>
        </div>
      </div>
      <div className="status-period-comparisons">
        <div className="status-period-comparisons-title">Sammenligning</div>
        {comparisons.map((comparison) => (
          <ComparisonRow comparison={comparison} currentTotal={period.total} key={comparison.label} />
        ))}
      </div>
    </Card>
  );
}

function StatusSummary({
  label,
  detail,
  updatedAt,
}: {
  label: string;
  detail: string;
  updatedAt: string;
}) {
  return (
    <div className="status-summary">
      <div className="status-summary-state">
        <span>Status akkurat nå</span>
        <strong>{label}</strong>
        <em>{detail}</em>
      </div>
      <div className="status-summary-updated">
        <span>Sist oppdatert</span>
        <strong>{updatedAt}</strong>
      </div>
    </div>
  );
}

function OverviewInfoPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="status-info-card" title={title}>
      {children}
    </Card>
  );
}

function LatestEventList({
  items,
  itemTitle,
}: {
  items: Array<{ href?: string; label: string; detail?: string; value: string }>;
  itemTitle: (item: { href?: string; label: string }) => ReactNode;
}) {
  return (
    <List
      className="status-event-list"
      dataSource={items}
      locale={{ emptyText: "Ingen hendelser å vise" }}
      renderItem={(item) => (
        <List.Item>
          <List.Item.Meta title={itemTitle(item)} description={item.detail || ""} />
          <span className="list-value">{item.value}</span>
        </List.Item>
      )}
    />
  );
}

function DatasourceList({ services }: { services: ServiceStatus[] }) {
  return (
    <List
      className="status-source-list"
      dataSource={services}
      locale={{ emptyText: "Ingen datakilder å vise" }}
      renderItem={(item) => (
        <List.Item>
          <Space>
            {statusIcon(item.status)}
            <span>{item.label}</span>
          </Space>
          <Typography.Text type="secondary">{item.detail}</Typography.Text>
        </List.Item>
      )}
    />
  );
}

function SupportMetricStrip({ cards }: { cards: MetricCardData[] }) {
  return (
    <div className="status-support-strip">
      {cards.map((card) => {
        const content = (
          <div className={`status-support-item tone-${card.tone ?? "status"}`}>
            <div className="status-support-head">
              <span>{card.title}</span>
              <em>{card.group}</em>
            </div>
            <strong>
              {card.value}
              {card.unit ? <span>{card.unit}</span> : null}
            </strong>
            <small>{card.detail || "\u00a0"}</small>
          </div>
        );
        const internalPath = appPath(card.href);
        if (internalPath) {
          return (
            <Link className="status-support-link" to={internalPath} key={`${card.group}-${card.title}`}>
              {content}
            </Link>
          );
        }
        if (card.href) {
          return (
            <a className="status-support-link" href={card.href} key={`${card.group}-${card.title}`}>
              {content}
            </a>
          );
        }
        return (
          <div className="status-support-link" key={`${card.group}-${card.title}`}>
            {content}
          </div>
        );
      })}
    </div>
  );
}

export default function OverviewPage() {
  const { data, loading, error } = useAsyncData(fetchOverview, []);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const supportCards = data.cards.filter(isOverviewSupportCard);
  const overviewServices = sortedDatasources(data.services);

  function itemTitle(item: { href?: string; label: string }) {
    const internalPath = appPath(item.href);
    if (internalPath) return <Link to={internalPath}>{item.label}</Link>;
    if (item.href) return <a href={item.href}>{item.label}</a>;
    return item.label;
  }

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-overview-page">
      <StatusSummary
        label={data.operatingWindow.label}
        detail={data.operatingWindow.detail}
        updatedAt={new Date(data.generatedAt).toLocaleString("nb-NO")}
      />

      <div className="status-strip-stack">
        <StatusStrip title="Lys" items={lightStripItems(data.lightItems)} />
        <StatusStrip title="Ventilasjon" items={data.fanItems} />
      </div>

      <div className="status-period-grid">
        {data.statusPeriods.map((period) => (
          <RevenuePeriodCard period={period} key={period.key} />
        ))}
      </div>

      <SupportMetricStrip cards={supportCards} />

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <OverviewInfoPanel title="Siste hendelser">
            <LatestEventList items={data.latestItems} itemTitle={itemTitle} />
          </OverviewInfoPanel>
        </Col>
        <Col span={12}>
          <OverviewInfoPanel title="Status datakilder">
            <DatasourceList services={overviewServices} />
          </OverviewInfoPanel>
        </Col>
      </Row>
    </Space>
  );
}
