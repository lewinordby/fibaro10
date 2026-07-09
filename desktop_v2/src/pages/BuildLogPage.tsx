import { Card, Space, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link, useNavigate } from "react-router-dom";
import { fetchBuildLog, type BuildLogListEntry } from "../api";
import { DataTableCard } from "../components/DataTableCard";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";

export default function BuildLogPage() {
  const navigate = useNavigate();
  const { data, loading, error } = useApiQuery(queryKeys.buildLog(), fetchBuildLog, {
    staleTime: 5 * 60_000,
  });

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const columns: ColumnsType<BuildLogListEntry> = [
    {
      title: "Dato",
      dataIndex: "date",
      key: "date",
      width: 130,
      sorter: (left, right) => left.date.localeCompare(right.date, "nb-NO", { numeric: true }),
    },
    {
      title: "Build",
      dataIndex: "build",
      key: "build",
      width: 120,
      sorter: (left, right) => Number(left.build) - Number(right.build),
      render: (value: string, row) => (
        <Space size={6}>
          <Link to={row.path}>{value}</Link>
          {row.isCurrent ? <Tag color="blue">Aktiv</Tag> : null}
        </Space>
      ),
    },
    {
      title: "Leveranseoverskrift",
      dataIndex: "headline",
      key: "headline",
      sorter: (left, right) => left.headline.localeCompare(right.headline, "nb-NO"),
      render: (value: string, row) => <Link to={row.path}>{value}</Link>,
    },
  ];

  return (
    <Space direction="vertical" size={16} className="page-stack build-log-page">
      <Card className="work-card build-log-intro">
        <Typography.Text className="eyebrow">Buildlogg</Typography.Text>
        <div className="build-log-intro-row">
          <div>
            <Typography.Title level={2}>Leveransehistorikk</Typography.Title>
            <Typography.Paragraph>
              Kort oversikt over hver deploy. Åpne en build for komplett bestilling, endringer, berørte applikasjoner og måledata.
            </Typography.Paragraph>
          </div>
          <div className="build-log-current">
            <span>Aktiv build</span>
            <strong>{data.currentBuild}</strong>
          </div>
        </div>
      </Card>

      <DataTableCard<BuildLogListEntry>
        cardTitle="Buildoversikt"
        className="module-table-card"
        rowKey="build"
        size="small"
        columns={columns}
        dataSource={data.rows}
        pagination={{ pageSize: 25, showSizeChanger: true }}
        onRow={(row) => ({
          onClick: () => navigate(row.path),
        })}
        rowClassName="clickable-table-row"
      />
    </Space>
  );
}
