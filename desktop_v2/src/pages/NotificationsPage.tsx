import {
  BellOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LinkOutlined,
  LockOutlined,
  MobileOutlined,
} from "@ant-design/icons";
import { Button, Space, Tag } from "antd";
import { fetchSystemNotifications, type NtfySubscription } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/system-pages.css";

function channelState(channel: NtfySubscription) {
  if (!channel.configured) {
    return { icon: <ExclamationCircleOutlined />, label: "Ikke konfigurert", color: "red" };
  }
  if (!channel.publishingEnabled) {
    return { icon: <ExclamationCircleOutlined />, label: "Utsending av", color: "gold" };
  }
  return { icon: <CheckCircleOutlined />, label: "Aktiv", color: "green" };
}

function NotificationChannel({ channel }: { channel: NtfySubscription }) {
  const state = channelState(channel);
  return (
    <article className={`notification-channel notification-channel-${channel.key}`}>
      <div className="notification-channel-heading">
        <div className="notification-channel-icon" aria-hidden="true">
          <BellOutlined />
        </div>
        <div>
          <span className="system-item-kicker">{channel.area}</span>
          <h2>{channel.title}</h2>
        </div>
        <Tag color={state.color} icon={state.icon}>
          {state.label}
        </Tag>
      </div>
      <p className="notification-channel-description">{channel.description}</p>
      <div className="notification-trigger-list" aria-label={`Varseltyper for ${channel.title}`}>
        {channel.triggers.map((trigger) => (
          <span key={trigger}>{trigger}</span>
        ))}
      </div>
      <div className="notification-channel-footer">
        <span>Prioritet: {channel.priority}</span>
        <Space size={8} wrap>
          <Button
            type="primary"
            icon={<BellOutlined />}
            href={channel.subscribeUrl || undefined}
            disabled={!channel.subscribeUrl}
          >
            Abonner
          </Button>
          <Button
            icon={<LinkOutlined />}
            href={channel.webUrl || undefined}
            target="_blank"
            rel="noreferrer"
            disabled={!channel.webUrl}
          >
            Åpne kanal
          </Button>
        </Space>
      </div>
    </article>
  );
}

export default function NotificationsPage() {
  const { data, loading, error } = useApiQuery(
    queryKeys.systemNotifications(),
    fetchSystemNotifications,
    { refetchInterval: 60_000 },
  );

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={14} className="page-stack system-hub-page notifications-page">
      <PageHeader
        eyebrow="System"
        title="Varslinger"
        description="Samlet oversikt over ntfy-kanalene i løsningen og hva som faktisk utløser et varsel."
        actions={
          <Button icon={<LinkOutlined />} href={data.providerUrl} target="_blank" rel="noreferrer">
            {data.provider}
          </Button>
        }
      />

      <section className="system-summary-strip" aria-label="Varslingsstatus">
        <div>
          <span>Kanaler</span>
          <strong>{data.summary.channels}</strong>
        </div>
        <div>
          <span>Konfigurert</span>
          <strong>{data.summary.configured}</strong>
        </div>
        <div>
          <span>Sender varsler</span>
          <strong>{data.summary.publishing}</strong>
        </div>
        <div className="system-summary-explanation">
          <MobileOutlined />
          <span>Abonnementet legges direkte til i ntfy-appen på enheten du bruker.</span>
        </div>
      </section>

      <section className="system-section-heading">
        <div>
          <span className="system-item-kicker">Abonnementer</span>
          <h2>Velg kanalene du trenger</h2>
        </div>
        <p>Hver kanal kan abonneres på uavhengig. Du kan derfor skille driftsvarsler fra tilgangsvarsler.</p>
      </section>

      <div className="notification-channel-grid">
        {data.subscriptions.map((channel) => (
          <NotificationChannel key={channel.key} channel={channel} />
        ))}
      </div>

      <section className="notification-setup-band">
        <div className="notification-setup-title">
          <MobileOutlined />
          <div>
            <span className="system-item-kicker">Første gangs oppsett</span>
            <h2>Slik kobler du til</h2>
          </div>
        </div>
        <ol>
          {data.setup.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </section>

      <div className="system-privacy-note">
        <LockOutlined />
        <span>{data.privacy}</span>
      </div>
    </Space>
  );
}
