import { CheckCircleOutlined, WarningOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { Card, List, Space, Tag, Typography } from "antd";
import { fetchOverview, type ServiceStatus } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useAsyncData } from "../hooks";

function statusTag(row: ServiceStatus) {
  if (row.status === "ok") return <Tag color="green">OK</Tag>;
  if (row.status === "bad") return <Tag color="red">Feil</Tag>;
  if (row.status === "warn") return <Tag color="gold">Treg</Tag>;
  return <Tag>Ukjent</Tag>;
}

function statusIcon(row: ServiceStatus) {
  if (row.status === "ok") return <CheckCircleOutlined className="status-ok" />;
  if (row.status === "bad") return <WarningOutlined className="status-bad" />;
  return <ClockCircleOutlined className="status-warn" />;
}

export default function OperationsPage() {
  const { data, loading, error } = useAsyncData(fetchOverview, []);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={18} className="page-stack">
      <section className="section-head">
        <div>
          <Typography.Text className="eyebrow">Drift</Typography.Text>
          <Typography.Title level={1}>Datakilder og signaler</Typography.Title>
        </div>
      </section>

      <Card className="work-card" title="Datakilder">
        <List
          dataSource={data.services}
          renderItem={(item) => (
            <List.Item
              actions={[
                statusTag(item),
                <Typography.Text type="secondary" key="age">
                  {item.ageMinutes == null ? "" : `${Math.round(item.ageMinutes)} min`}
                </Typography.Text>,
              ]}
            >
              <List.Item.Meta
                avatar={statusIcon(item)}
                title={item.label}
                description={item.detail}
              />
            </List.Item>
          )}
        />
      </Card>
    </Space>
  );
}
