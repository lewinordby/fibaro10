import { CheckCircleOutlined, ClockCircleOutlined, WarningOutlined } from "@ant-design/icons";
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

  const warnings = data.services.filter((item) => item.status !== "ok").length;

  return (
    <Space direction="vertical" size={14} className="page-stack status-page status-operations-page">
      <div className="status-page-top">
        <div>
          <Typography.Text className="eyebrow">Drift</Typography.Text>
          <div className="status-meta-line">
            <strong>Datakilder og signaler</strong>
            <span>{data.services.length} datakilder</span>
          </div>
        </div>
        <Typography.Text type={warnings ? "warning" : "secondary"}>
          {warnings ? `${warnings} trenger sjekk` : "Alt OK"}
        </Typography.Text>
      </div>

      <Card className="work-card" title="Datakilder">
        <List
          dataSource={data.services}
          locale={{ emptyText: "Ingen datakilder å vise" }}
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
