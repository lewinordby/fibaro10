import { CheckCircleOutlined, ClockCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { Card, Col, List, Row, Space, Tag, Tooltip, Typography } from "antd";
import { Link } from "react-router-dom";
import { fetchOverview, type MetricCard as MetricCardData, type ServiceStatus, type StatusPeriod } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import MetricCard from "../components/MetricCard";
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

function datasourcePreview(services: ServiceStatus[]) {
  return services
    .map((service, index) => ({ service, index }))
    .sort((a, b) => serviceRank(a.service) - serviceRank(b.service) || a.index - b.index)
    .slice(0, 8)
    .map((row) => row.service);
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

function RevenuePeriodCard({ period }: { period: StatusPeriod }) {
  return (
    <Card className="status-period-card">
      <div className="status-period-head">
        <span>{period.title}</span>
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
      <div className="status-period-previous">
        <span>{period.previousLabel}</span>
        <strong>{nok(period.previousTotal)} kr</strong>
        <em>
          Soling {period.previousSolCount} / {nok(period.previousSol)} kr · Parkering{" "}
          {period.previousParkingCount} / {nok(period.previousParking)} kr
        </em>
      </div>
    </Card>
  );
}

export default function OverviewPage() {
  const { data, loading, error } = useAsyncData(fetchOverview, []);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const supportCards = data.cards.filter(isOverviewSupportCard);
  const overviewServices = datasourcePreview(data.services);

  function itemTitle(item: { href?: string; label: string }) {
    const internalPath = appPath(item.href);
    if (internalPath) return <Link to={internalPath}>{item.label}</Link>;
    if (item.href) return <a href={item.href}>{item.label}</a>;
    return item.label;
  }

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-overview-page">
      <div className="status-page-top">
        <div>
          <Typography.Text className="eyebrow">Status akkurat nå</Typography.Text>
          <div className="status-meta-line">
            <strong>{data.operatingWindow.label}</strong>
            <span>{data.operatingWindow.detail}</span>
          </div>
        </div>
        <Typography.Text type="secondary">
          Sist oppdatert {new Date(data.generatedAt).toLocaleString("nb-NO")}
        </Typography.Text>
      </div>

      <div className="status-strip-stack">
        <StatusStrip title="Lys" items={lightStripItems(data.lightItems)} />
        <StatusStrip title="Ventilasjon" items={data.fanItems} />
      </div>

      <div className="status-period-grid">
        {data.statusPeriods.map((period) => (
          <RevenuePeriodCard period={period} key={period.key} />
        ))}
      </div>

      <div className="metric-grid status-support-grid">
        {supportCards.map((card) => (
          <MetricCard card={card} key={`${card.group}-${card.title}`} />
        ))}
      </div>

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="Siste hendelser" className="work-card">
            <List
              dataSource={data.latestItems}
              locale={{ emptyText: "Ingen hendelser å vise" }}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta title={itemTitle(item)} description={item.detail || ""} />
                  <span className="list-value">{item.value}</span>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Status datakilder" className="work-card">
            <List
              dataSource={overviewServices}
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
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
