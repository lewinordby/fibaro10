import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Card, Descriptions, List, Space, Tag, Typography } from "antd";
import { Link, useParams } from "react-router-dom";
import { fetchBuildLogEntry } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/build.css";

export default function BuildDetailPage() {
  const params = useParams();
  const build = params.build ?? "";
  const { data, loading, error } = useApiQuery(queryKeys.buildLogEntry(build), () => fetchBuildLogEntry(build), {
    enabled: Boolean(build),
    staleTime: 5 * 60_000,
  });

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={16} className="page-stack build-detail-page">
      <div className="build-detail-topline">
        <Link to="/admin/build">
          <Button icon={<ArrowLeftOutlined />}>Buildoversikt</Button>
        </Link>
        {data.isCurrent ? <Tag color="blue">Aktiv build</Tag> : null}
      </div>

      <Card className="work-card build-detail-hero">
        <Typography.Text className="eyebrow">Build {data.build}</Typography.Text>
        <Typography.Title level={2}>{data.headline}</Typography.Title>
        {data.title && data.title !== data.headline ? <Typography.Text strong>{data.title}</Typography.Text> : null}
        <Typography.Paragraph>{data.description}</Typography.Paragraph>
        <Descriptions size="small" column={4} className="build-detail-meta">
          <Descriptions.Item label="Dato">{data.date}</Descriptions.Item>
          <Descriptions.Item label="Versjon">v{data.version}</Descriptions.Item>
          <Descriptions.Item label="Tidsbruk">{data.workDuration || "-"}</Descriptions.Item>
          <Descriptions.Item label="Kreditter">{data.creditsUsed || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>

      <div className="build-detail-grid">
        <Card className="work-card" title="Endringer">
          <List
            size="small"
            dataSource={data.changes}
            locale={{ emptyText: "Ingen endringer registrert" }}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        </Card>

        <Card className="work-card" title="Berørte applikasjoner">
          <List
            size="small"
            dataSource={data.applications}
            locale={{ emptyText: "Ingen applikasjoner registrert" }}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        </Card>
      </div>

      <Card className="work-card" title="Bestilling / prompt">
        <pre className="build-request-block">{data.request || "Ikke registrert"}</pre>
      </Card>
    </Space>
  );
}
