import { CheckCircleOutlined, ClockCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { Card, Col, List, Row, Space, Tag, Typography } from "antd";
import { fetchOverview } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import MetricCard from "../components/MetricCard";
import { useAsyncData } from "../hooks";

function stateTag(state: boolean | null) {
  if (state === true) return <Tag color="green">På</Tag>;
  if (state === false) return <Tag color="default">Av</Tag>;
  return <Tag>Ukjent</Tag>;
}

function statusIcon(status: string) {
  if (status === "ok") return <CheckCircleOutlined className="status-ok" />;
  if (status === "bad") return <WarningOutlined className="status-bad" />;
  return <ClockCircleOutlined className="status-warn" />;
}

export default function OverviewPage() {
  const { data, loading, error } = useAsyncData(fetchOverview, []);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const keyCards = data.cards.slice(0, 12);
  const secondaryCards = data.cards.slice(12);

  return (
    <Space direction="vertical" size={18} className="page-stack">
      <section className="hero-band">
        <div>
          <Typography.Text className="eyebrow">Status akkurat nå</Typography.Text>
          <Typography.Title level={1}>Oversikt</Typography.Title>
          <Typography.Paragraph>
            {data.operatingWindow.label} · {data.operatingWindow.detail}
          </Typography.Paragraph>
        </div>
        <div className="hero-meta">
          <span>Sist oppdatert</span>
          <strong>{new Date(data.generatedAt).toLocaleString("nb-NO")}</strong>
        </div>
      </section>

      <div className="metric-grid primary-grid">
        {keyCards.map((card) => (
          <MetricCard card={card} key={`${card.group}-${card.title}`} />
        ))}
      </div>

      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Card title="Siste hendelser" className="work-card">
            <List
              dataSource={data.latestItems}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={item.href ? <a href={item.href}>{item.label}</a> : item.label}
                    description={item.detail || ""}
                  />
                  <span className="list-value">{item.value}</span>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Datakilder" className="work-card">
            <List
              dataSource={data.services.slice(0, 7)}
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
        <Col span={4}>
          <Card title="Lys" className="work-card compact-list">
            {data.lightItems.map((item) => (
              <div className="state-row" key={item.label}>
                <span>{item.label}</span>
                {stateTag(item.state)}
              </div>
            ))}
          </Card>
        </Col>
        <Col span={4}>
          <Card title="Ventilasjon" className="work-card compact-list">
            {data.fanItems.map((item) => (
              <div className="state-row" key={item.label}>
                <span>{item.label}</span>
                {stateTag(item.state)}
              </div>
            ))}
          </Card>
        </Col>
      </Row>

      <div className="metric-grid secondary-grid">
        {secondaryCards.map((card) => (
          <MetricCard card={card} key={`${card.group}-${card.title}`} />
        ))}
      </div>
    </Space>
  );
}
