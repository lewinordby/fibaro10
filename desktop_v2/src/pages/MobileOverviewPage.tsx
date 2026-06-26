import { MobileOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Space, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { fetchMobilePreviewScreens } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";

function frameUrl(baseUrl: string, refreshToken: number): string {
  const separator = baseUrl.includes("?") ? "&" : "?";
  return `${baseUrl}${separator}r=${refreshToken}`;
}

export default function MobileOverviewPage() {
  const { data, loading, error } = useApiQuery(queryKeys.mobileScreens(), fetchMobilePreviewScreens, {
    staleTime: 60_000,
  });
  const [refreshToken, setRefreshToken] = useState(() => Date.now());
  const refreshMs = Math.max(15, data?.refreshSeconds ?? 60) * 1000;

  useEffect(() => {
    const timer = window.setInterval(() => setRefreshToken(Date.now()), refreshMs);
    return () => window.clearInterval(timer);
  }, [refreshMs]);

  const screens = useMemo(() => data?.screens ?? [], [data]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={14} className="page-stack mobile-preview-page">
      <PageHeader
        eyebrow="Mobil"
        title="Mobilskjermer"
        description={`Live visning fra mobilappen. Rammene lastes på nytt hvert ${data.refreshSeconds}. sekund.`}
        actions={
          <Button icon={<ReloadOutlined />} onClick={() => setRefreshToken(Date.now())}>
            Oppdater
          </Button>
        }
      />

      <div className="mobile-preview-grid">
        {screens.map((screen) => (
          <Card
            key={screen.key}
            className="mobile-preview-card"
            title={
              <Space size={7}>
                <MobileOutlined />
                <span>{screen.title}</span>
              </Space>
            }
            extra={
              <a href={frameUrl(screen.frameUrl, refreshToken)} target="_blank" rel="noreferrer">
                Åpne
              </a>
            }
          >
            <Typography.Text className="mobile-preview-subtitle">{screen.subtitle}</Typography.Text>
            <div className="mobile-preview-shell">
              <iframe
                title={screen.title}
                className="mobile-preview-frame"
                src={frameUrl(screen.frameUrl, refreshToken)}
                loading="lazy"
              />
            </div>
          </Card>
        ))}
      </div>
    </Space>
  );
}
