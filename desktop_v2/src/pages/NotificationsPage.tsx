import {
  BellOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  LinkOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { App as AntApp, Button, Collapse, Empty, Input, Modal, Segmented, Space, Tag } from "antd";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  fetchSystemNotifications,
  reviewOperationalIncident,
  type NtfySubscription,
  type OperationalIncident,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/notifications.css";

type IncidentFilter = "open" | "critical" | "acknowledged" | "all";

const dateTimeFormatter = new Intl.DateTimeFormat("nb-NO", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

function formatDateTime(value?: string | null) {
  if (!value) return "Ukjent tidspunkt";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : dateTimeFormatter.format(parsed);
}

function channelState(channel: NtfySubscription) {
  if (!channel.configured) return { label: "Ikke konfigurert", color: "red" };
  if (!channel.publishingEnabled) return { label: "Utsending av", color: "gold" };
  return { label: "Aktiv", color: "green" };
}

function NotificationChannel({ channel }: { channel: NtfySubscription }) {
  const state = channelState(channel);
  return (
    <article className="incident-channel">
      <div>
        <span>{channel.area}</span>
        <strong>{channel.title}</strong>
        <p>{channel.description}</p>
      </div>
      <Tag color={state.color}>{state.label}</Tag>
      <Space size={6}>
        <Button size="small" type="primary" icon={<BellOutlined />} href={channel.subscribeUrl || undefined} disabled={!channel.subscribeUrl}>
          Abonner
        </Button>
        <Button size="small" icon={<LinkOutlined />} href={channel.webUrl || undefined} target="_blank" rel="noreferrer" disabled={!channel.webUrl}>
          Kanal
        </Button>
      </Space>
    </article>
  );
}

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const { message } = AntApp.useApp();
  const [filter, setFilter] = useState<IncidentFilter>("open");
  const [selected, setSelected] = useState<OperationalIncident | null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const queryKey = queryKeys.systemNotifications();
  const { data, loading, error } = useApiQuery(queryKey, fetchSystemNotifications, {
    refetchInterval: 30_000,
    staleTime: 10_000,
  });

  const visibleIncidents = useMemo(() => {
    const rows = data?.incidents ?? [];
    if (filter === "critical") return rows.filter((row) => row.severity === "critical");
    if (filter === "acknowledged") return rows.filter((row) => row.reviewState === "acknowledged");
    if (filter === "open") return rows.filter((row) => row.reviewState !== "acknowledged");
    return rows;
  }, [data?.incidents, filter]);

  function openIncident(row: OperationalIncident) {
    setSelected(row);
    setNote(row.reviewNote || "");
  }

  async function saveReview(state: "acknowledged" | "open") {
    if (!selected || saving) return;
    setSaving(true);
    try {
      const result = await reviewOperationalIncident(selected.key, state, note);
      message.success(String(result.message || "Lagret"));
      setSelected(null);
      await queryClient.invalidateQueries({ queryKey });
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Lagring feilet");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const summary = data.incidentSummary;
  return (
    <div className="incident-page">
      <header className="incident-heading">
        <div>
          <span className="incident-kicker">Operativ kontroll</span>
          <h1>Hendelser og varslinger</h1>
          <p>Aktive driftsavvik samlet fra datakilder, dører, pullerter, backup og varselkø.</p>
        </div>
        <Button icon={<LinkOutlined />} href={data.providerUrl} target="_blank" rel="noreferrer">
          {data.provider}
        </Button>
      </header>

      <section className="incident-summary" aria-label="Hendelsesstatus">
        <div className="tone-attention"><span>Ubehandlet</span><strong>{summary.unreviewed}</strong></div>
        <div className="tone-critical"><span>Kritisk</span><strong>{summary.critical}</strong></div>
        <div className="tone-warning"><span>Til kontroll</span><strong>{summary.warning}</strong></div>
        <div className="tone-ok"><span>Bekreftet lest</span><strong>{summary.acknowledged}</strong></div>
      </section>

      <section className="incident-controls" aria-label="Driftsvern">
        {data.controls.map((control) => (
          <Link to={control.path} className={`incident-control status-${control.status}`} key={control.key}>
            <span className="incident-control-icon" aria-hidden="true">
              {control.status === "ok" ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
            </span>
            <span>
              <strong>{control.title}</strong>
              <small>{control.detail}</small>
            </span>
            <Tag>{control.statusLabel}</Tag>
          </Link>
        ))}
      </section>

      <section className="incident-workspace">
        <div className="incident-list-heading">
          <div>
            <span className="incident-kicker">Aktive forhold</span>
            <h2>Dette må vurderes</h2>
          </div>
          <Segmented<IncidentFilter>
            value={filter}
            onChange={setFilter}
            options={[
              { label: `Ubehandlet ${summary.unreviewed}`, value: "open" },
              { label: `Kritisk ${summary.critical}`, value: "critical" },
              { label: `Bekreftet ${summary.acknowledged}`, value: "acknowledged" },
              { label: `Alle ${summary.active}`, value: "all" },
            ]}
          />
        </div>

        <div className="incident-table" role="table" aria-label="Aktive hendelser">
          <div className="incident-table-head" role="row">
            <span>Status</span><span>Område og hendelse</span><span>Observert</span><span>Anbefalt handling</span><span />
          </div>
          {visibleIncidents.length ? visibleIncidents.map((row) => (
            <article className={`incident-row severity-${row.severity} ${row.reviewState === "acknowledged" ? "is-acknowledged" : ""}`} role="row" key={row.key}>
              <div className="incident-severity">
                <ExclamationCircleOutlined />
                <strong>{row.severityLabel}</strong>
                {row.reviewState === "acknowledged" ? <small>Bekreftet lest</small> : <small>Ubehandlet</small>}
              </div>
              <div className="incident-main">
                <span>{row.domain} · {row.source}</span>
                <strong>{row.title}</strong>
                <p>{row.detail}</p>
              </div>
              <div className="incident-time">
                <ClockCircleOutlined />
                <span>{formatDateTime(row.startedAt)}</span>
              </div>
              <p className="incident-action-copy">{row.recommendedAction}</p>
              <Button size="small" onClick={() => openIncident(row)}>Behandle</Button>
            </article>
          )) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Ingen hendelser i dette utvalget" />
          )}
        </div>
      </section>

      <Collapse
        className="incident-secondary"
        items={[
          {
            key: "channels",
            label: <span><BellOutlined /> Varselkanaler ({data.summary.publishing}/{data.summary.channels} sender)</span>,
            children: <div className="incident-channel-grid">{data.subscriptions.map((channel) => <NotificationChannel channel={channel} key={channel.key} />)}</div>,
          },
          {
            key: "setup",
            label: <span><SafetyCertificateOutlined /> Oppsett og personvern</span>,
            children: <div className="incident-setup"><ol>{data.setup.map((step) => <li key={step}>{step}</li>)}</ol><p>{data.privacy}</p></div>,
          },
        ]}
      />

      <Modal
        open={Boolean(selected)}
        title={selected?.title}
        onCancel={() => setSelected(null)}
        footer={
          <Space>
            {selected?.reviewState === "acknowledged" ? (
              <Button loading={saving} onClick={() => saveReview("open")}>Åpne igjen</Button>
            ) : (
              <Button type="primary" loading={saving} icon={<CheckCircleOutlined />} onClick={() => saveReview("acknowledged")}>Bekreft lest</Button>
            )}
          </Space>
        }
        width={680}
      >
        {selected ? (
          <div className="incident-dialog">
            <div className="incident-dialog-meta">
              <Tag color={selected.severity === "critical" ? "red" : "gold"}>{selected.severityLabel}</Tag>
              <span>{selected.domain}</span><span>{selected.source}</span><span>{formatDateTime(selected.startedAt)}</span>
            </div>
            <p>{selected.detail}</p>
            <div className="incident-recommendation">
              <strong>Anbefalt handling</strong>
              <span>{selected.recommendedAction}</span>
              {selected.path ? <Link to={selected.path} onClick={() => setSelected(null)}>Åpne detaljside <LinkOutlined /></Link> : null}
            </div>
            <label className="incident-note-label" htmlFor="incident-note">Kommentar</label>
            <Input.TextArea id="incident-note" rows={4} maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Hva er kontrollert, og hva skal følges opp?" />
            {selected.reviewedAt ? <small>Sist kvittert {formatDateTime(selected.reviewedAt)} av {selected.reviewedBy || "ukjent"}.</small> : null}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
