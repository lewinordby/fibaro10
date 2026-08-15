import {
  BellOutlined,
  CameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  ExperimentOutlined,
  LinkOutlined,
  ReloadOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Alert, App as AntApp, Button, Card, Empty, Tag, Typography } from "antd";
import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  fetchBollardOverview,
  sendBollardTestNotification,
  type BollardCameraMonitor,
  type BollardIncident,
  type BollardNotificationResponse,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/bollards.css";

type ImageMode = "sideBySide" | "compare" | "overlay";

const EMPTY_MONITORS: BollardCameraMonitor[] = [];

const IMAGE_MODE_LABELS: Record<ImageMode, string> = {
  sideBySide: "Referanse og siste bilde",
  compare: "Transparent overlegg",
  overlay: "Forskjellsbilde",
};

const IMAGE_MODE_BUTTON_LABELS: Record<ImageMode, string> = {
  sideBySide: "Side om side",
  compare: "Gjennomsiktig",
  overlay: "Markerte forskjeller",
};

function formatStamp(value?: string | null): string {
  if (!value) return "–";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(parsed);
}

function formatImageStamp(value?: string | null): string {
  if (!value) return "Ikke tilgjengelig";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(parsed);
}

function imageUrl(url?: string | null, stamp?: string | null): string {
  if (!url) return "";
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}captured=${encodeURIComponent(stamp || "current")}`;
}

function cameraStatus(status?: string | null): { label: string; color: string; detail: string; attention: boolean } {
  const normalized = String(status || "").toLowerCase();
  const statuses: Record<string, { label: string; color: string; detail: string; attention: boolean }> = {
    normal: { label: "Normal", color: "green", detail: "Ingen varig endring er oppdaget.", attention: false },
    changed: { label: "Endring", color: "gold", detail: "En endring vurderes og må vedvare før alarm.", attention: true },
    obscured: { label: "Tildekket", color: "orange", detail: "Kameraområdet kan være tildekket.", attention: true },
    suspected: { label: "Kontroller", color: "red", detail: "Endringen har vedvart og bør kontrolleres.", attention: true },
    camera_error: { label: "Kamerafeil", color: "red", detail: "Siste automatiske kontroll feilet.", attention: true },
    error: { label: "Feil", color: "red", detail: "Siste automatiske kontroll feilet.", attention: true },
    waiting: { label: "Venter", color: "default", detail: "Venter på første komplette kontroll.", attention: false },
    uncalibrated: { label: "Mangler referanse", color: "default", detail: "Referansebildet er ikke klart.", attention: true },
  };
  return statuses[normalized] || { label: "Ukjent", color: "default", detail: "Status er ikke rapportert.", attention: true };
}

function combinedCameraStatus(monitor: BollardCameraMonitor): ReturnType<typeof cameraStatus> {
  if (monitor.hybrid_status === "corroborated") {
    return { label: "Kontroller", color: "red", detail: "Både lokal AI og klassisk analyse finner et avvik.", attention: true };
  }
  if (monitor.hybrid_status === "ai_review") {
    return { label: "AI-kontroll", color: "gold", detail: "Bare lokal AI finner et avvik. Resultatet vises for kontroll.", attention: true };
  }
  if (monitor.hybrid_status === "classical_review" && monitor.ai_status === "normal") {
    return { label: "Normal", color: "green", detail: "AI-kontrollen avviser et rent piksel- eller lysutslag.", attention: false };
  }
  return cameraStatus(monitor.status);
}

function frameStyle(crop?: BollardCameraMonitor["display_crop"]): CSSProperties {
  const width = Math.max(1, Number(crop?.width || 16));
  const height = Math.max(1, Number(crop?.height || 9));
  return {
    "--bollard-crop-aspect": `${width} / ${height}`,
    "--bollard-crop-native-width": `${width}px`,
    "--bollard-crop-native-height": `${height}px`,
  } as CSSProperties;
}

function changeScoreLabel(monitor: BollardCameraMonitor): string {
  return monitor.change_score == null ? "Ikke beregnet" : `${Math.round(monitor.change_score * 100)} %`;
}

function aiStatus(monitor: BollardCameraMonitor): { label: string; color: string; detail: string } {
  const status = String(monitor.ai_status || "not_ready").toLowerCase();
  if (status === "normal") return { label: "AI normal", color: "green", detail: "Lokal AI finner ikke et visuelt avvik." };
  if (status === "anomaly") return { label: "AI avvik", color: "red", detail: "Lokal AI finner et mønster som avviker fra normalbildene." };
  if (status === "training") return { label: "AI trener", color: "blue", detail: "Modellen bygges lokalt fra historiske normalbilder." };
  if (status === "error") return { label: "AI-feil", color: "orange", detail: "AI-kontrollen feilet, men vanlig bildeanalyse kjører videre." };
  if (status === "disabled") return { label: "AI av", color: "default", detail: "AI-tjenesten er ikke konfigurert." };
  return { label: "AI ikke klar", color: "default", detail: "Venter på en ferdig lokal modell." };
}

function ratioLabel(monitor: BollardCameraMonitor): string {
  return monitor.ai_score_ratio == null ? "–" : `${monitor.ai_score_ratio.toFixed(2)} × terskel`;
}

function aiConclusion(monitor: BollardCameraMonitor): string {
  const status = String(monitor.ai_status || "not_ready").toLowerCase();
  if (status === "normal") return "Støtter normal vurdering";
  if (status === "anomaly") return "Bør kontrolleres visuelt";
  if (status === "training") return "Modellen er ikke ferdig";
  if (status === "error") return "Visuell kontroll gjelder";
  return "Ingen ferdig AI-vurdering";
}

function monitorKey(monitor: BollardCameraMonitor): string {
  return monitor.monitor_id || (monitor.asset_key ? `asset:${monitor.asset_key}` : `camera:${monitor.camera_id}`);
}

function monitorName(monitor: BollardCameraMonitor): string {
  return monitor.display_name || monitor.camera_name;
}

function isStairMonitor(monitor: BollardCameraMonitor): boolean {
  return monitor.item_type === "stairs" || monitor.asset_type === "stairs" || Boolean(monitor.asset_key);
}

function CameraNavigator({
  monitors,
  selectedMonitorId,
  onSelect,
}: {
  monitors: BollardCameraMonitor[];
  selectedMonitorId: string;
  onSelect: (monitorId: string) => void;
}) {
  const groups = [
    { key: "bollards", label: "Pullerter", items: monitors.filter((monitor) => !isStairMonitor(monitor)) },
    { key: "stairs", label: "Trapp", items: monitors.filter(isStairMonitor) },
  ].filter((group) => group.items.length);
  let itemNumber = 0;

  return (
    <Card className="bollard-camera-navigator" title={<><CameraOutlined /> Kontrollområder</>} extra={`${monitors.length} områder`}>
      <div className="bollard-camera-list">
        {groups.map((group) => (
          <section className={`bollard-camera-group is-${group.key}`} key={group.key} aria-label={group.label}>
            <span className="bollard-camera-group-label">{group.label}</span>
            <div className="bollard-camera-group-items">
              {group.items.map((monitor) => {
                const status = combinedCameraStatus(monitor);
                const key = monitorKey(monitor);
                const selected = key === selectedMonitorId;
                const ai = aiStatus(monitor);
                itemNumber += 1;
                return (
                  <button
                    type="button"
                    className={selected ? "bollard-camera-choice is-selected" : "bollard-camera-choice"}
                    key={key}
                    onClick={() => onSelect(key)}
                    aria-pressed={selected}
                  >
                    <span className="bollard-camera-number">{String(itemNumber).padStart(2, "0")}</span>
                    <span className="bollard-camera-choice-copy">
                      <strong>{monitorName(monitor)}</strong>
                      <small>Kontrollert {formatStamp(monitor.last_checked_at)}</small>
                    </span>
                    <Tag color={status.color}>{status.label}</Tag>
                    <span className="bollard-camera-score"><small>Visuell {changeScoreLabel(monitor)}</small><strong>{ai.label}</strong></span>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
      <Typography.Text className="bollard-navigator-hint" type="secondary">
        Velg pullertområde eller trapp for stor inspeksjonsvisning.
      </Typography.Text>
    </Card>
  );
}

function CameraInspector({ monitor }: { monitor: BollardCameraMonitor }) {
  const [selectedMode, setSelectedMode] = useState<ImageMode>("compare");
  const [opacity, setOpacity] = useState(50);
  const [nativePixels, setNativePixels] = useState(false);
  const [showAiDetails, setShowAiDetails] = useState(false);
  const status = combinedCameraStatus(monitor);
  const baseline = imageUrl(monitor.baseline_crop_url || monitor.baseline_url, monitor.baseline_captured_at);
  const latest = imageUrl(monitor.latest_crop_url || monitor.latest_url, monitor.latest_captured_at);
  const overlay = imageUrl(monitor.overlay_crop_url || monitor.overlay_url, monitor.latest_captured_at);
  const aiHeatmap = imageUrl(monitor.ai_heatmap_url, monitor.ai_last_checked_at);
  const ai = aiStatus(monitor);
  const availableModes = useMemo(() => {
    const modes: ImageMode[] = [];
    if (baseline && latest) modes.push("sideBySide");
    if (baseline && latest) modes.push("compare");
    if (overlay) modes.push("overlay");
    return modes;
  }, [baseline, latest, overlay]);
  const mode = availableModes.includes(selectedMode) ? selectedMode : availableModes[0];
  const baseUrl = mode === "compare" ? baseline : overlay;
  const showsReference = mode === "compare";
  const name = monitorName(monitor);

  useEffect(() => {
    if (mode !== "compare") return undefined;

    const handleOpacityShortcut = (event: KeyboardEvent) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName;
      if (target?.isContentEditable || tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT") return;

      event.preventDefault();
      const direction = event.key === "ArrowRight" ? 5 : -5;
      setOpacity((current) => Math.max(0, Math.min(100, current + direction)));
    };

    window.addEventListener("keydown", handleOpacityShortcut);
    return () => window.removeEventListener("keydown", handleOpacityShortcut);
  }, [mode]);

  return (
    <Card className="bollard-workbench-card">
      <div className="bollard-workbench-heading">
        <div>
          <Typography.Text className="eyebrow">Valgt kontrollområde</Typography.Text>
          <Typography.Title level={2}>{name}</Typography.Title>
          <Typography.Text type="secondary">Fast pikselutsnitt fra originalbildet · kontrollert {formatStamp(monitor.last_checked_at)}</Typography.Text>
        </div>
        <Tag color={status.color} icon={status.attention ? <WarningOutlined /> : <CheckCircleOutlined />}>{status.label}</Tag>
      </div>

      {availableModes.length ? (
        <>
          <div className="bollard-workbench-toolbar">
            <div className="bollard-image-switch" role="group" aria-label={`Velg bilde for ${name}`}>
              {availableModes.map((value) => (
                <button
                  key={value}
                  type="button"
                  className={value === mode ? "is-active" : ""}
                  onClick={() => setSelectedMode(value)}
                >
                  {IMAGE_MODE_BUTTON_LABELS[value]}
                </button>
              ))}
            </div>
            <div className="bollard-image-switch" role="group" aria-label="Velg bildestørrelse">
              <button type="button" className={nativePixels ? "" : "is-active"} onClick={() => setNativePixels(false)}>Tilpasset</button>
              <button type="button" className={nativePixels ? "is-active" : ""} onClick={() => setNativePixels(true)}>1:1 piksler</button>
            </div>
            {mode === "compare" ? (
              <label className="bollard-opacity-inline">
                <span className="bollard-opacity-endpoint is-reference">
                  <b>Referanse</b>
                  <small>{formatImageStamp(monitor.baseline_captured_at)}</small>
                </span>
                <span className="bollard-opacity-endpoint is-latest">
                  <b>Siste bilde <em>{opacity} %</em></b>
                  <small>{formatImageStamp(monitor.latest_captured_at)}</small>
                </span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={opacity}
                  aria-label={`Gjennomsiktighet for siste bilde fra ${name}`}
                  onInput={(event) => setOpacity(Number(event.currentTarget.value))}
                />
              </label>
            ) : null}
          </div>

          {mode === "sideBySide" ? (
            <div className="bollard-visual-pair" aria-label={`Visuell sammenligning av ${name}`}>
              <figure className="bollard-visual-panel is-reference">
                <figcaption><strong>Referanse</strong><span>{formatImageStamp(monitor.baseline_captured_at)}</span></figcaption>
                <div className={nativePixels ? "bollard-pixel-viewport is-native" : "bollard-pixel-viewport"}>
                  <div className={nativePixels ? "bollard-workbench-frame is-native" : "bollard-workbench-frame"} style={frameStyle(monitor.display_crop)}>
                    <img src={baseline} alt={`Referansebilde fra ${name}`} decoding="async" />
                  </div>
                </div>
              </figure>
              <figure className="bollard-visual-panel is-latest">
                <figcaption><strong>Siste bilde</strong><span>{formatImageStamp(monitor.latest_captured_at)}</span></figcaption>
                <div className={nativePixels ? "bollard-pixel-viewport is-native" : "bollard-pixel-viewport"}>
                  <div className={nativePixels ? "bollard-workbench-frame is-native" : "bollard-workbench-frame"} style={frameStyle(monitor.display_crop)}>
                    <img src={latest} alt={`Siste bilde fra ${name}`} decoding="async" />
                  </div>
                </div>
              </figure>
            </div>
          ) : (
            <figure className="bollard-workbench-figure">
              <div className="bollard-workbench-image-labels">
                <span>{IMAGE_MODE_LABELS[mode]}</span>
                {showsReference ? <span className="bollard-reference-key"><i /> Dra bryteren for å se endringer</span> : null}
              </div>
              <div className={nativePixels ? "bollard-pixel-viewport is-native" : "bollard-pixel-viewport"}>
                <div className={`bollard-workbench-frame is-${mode}${nativePixels ? " is-native" : ""}`} style={frameStyle(monitor.display_crop)}>
                  <img
                    className={showsReference ? "bollard-reference-layer" : undefined}
                    src={baseUrl}
                    alt={`${IMAGE_MODE_LABELS[mode]} fra ${name}`}
                    decoding="async"
                  />
                  {mode === "compare" ? (
                    <div className="bollard-overlay-layer" style={{ opacity: opacity / 100 }}>
                      <img className="bollard-latest-layer" src={latest} alt={`Siste bilde fra ${name}`} decoding="async" />
                    </div>
                  ) : null}
                  <div className="bollard-frame-legend" aria-hidden="true">
                    {showsReference ? <span className="is-reference">Referanse</span> : null}
                    {mode === "compare" ? <span className="is-latest">Siste bilde · {opacity} %</span> : null}
                    {mode === "overlay" ? <span className="is-difference">Pikselforskjeller markert</span> : null}
                  </div>
                </div>
              </div>
            </figure>
          )}
        </>
      ) : (
        <Alert type="warning" showIcon message="Kamerabildet er ikke klart ennå" />
      )}

      <div className="bollard-visual-result">
        <EyeOutlined />
        <span><small>Vanlig bildekontroll</small><strong>{status.detail}</strong></span>
        <span><small>Endringsscore</small><strong>{changeScoreLabel(monitor)}</strong></span>
      </div>
      <div className={`bollard-ai-summary is-${String(monitor.ai_status || "not-ready").replace("_", "-")}`}>
        <span className="bollard-ai-summary-icon"><ExperimentOutlined /></span>
        <span className="bollard-ai-summary-copy">
          <small>AI-kontroll · tillegg til den visuelle kontrollen</small>
          <strong>{ai.label} · {aiConclusion(monitor)}</strong>
          <em>{ai.detail} Du kan åpne områdene AI reagerer på, men de er ikke en ferdig konklusjon om skade.</em>
        </span>
        {aiHeatmap ? (
          <Button type="default" icon={<EyeOutlined />} onClick={() => setShowAiDetails((value) => !value)}>
            {showAiDetails ? "Skjul AI-forklaring" : "Se hva AI reagerer på"}
          </Button>
        ) : null}
      </div>
      {showAiDetails && aiHeatmap ? (
        <div className="bollard-ai-details">
          <Alert
            type="info"
            showIcon
            message="Slik skal AI-resultatet tolkes"
            description="Lyse og varme områder er de delene av bildet som skiller seg mest fra modellens normalbilder. Markeringen kan skyldes skade eller flytting, men også lys, skygge, regn eller objekter foran kameraet. Kontroller derfor alltid mot referanse og siste bilde over."
          />
          <figure>
            <figcaption><strong>Områder AI reagerer på</strong><span>{formatImageStamp(monitor.ai_last_checked_at)}</span></figcaption>
            <div className="bollard-ai-image-frame">
              <img src={aiHeatmap} alt={`Områder AI reagerer på for ${name}`} decoding="async" />
            </div>
            <small>AI-score {ratioLabel(monitor)} · trent med {monitor.ai_training_samples ?? "ukjent antall"} normalbilder</small>
          </figure>
        </div>
      ) : null}
      {monitor.last_error ? <Alert type="error" showIcon message={monitor.last_error} /> : null}
      {monitor.ai_last_error && monitor.ai_status === "error" ? <Alert type="warning" showIcon message="AI-laget er midlertidig utilgjengelig" description="Vanlig kontroll og varsling fortsetter uavhengig." /> : null}
    </Card>
  );
}

function IncidentPanel({ incidents }: { incidents: BollardIncident[] }) {
  const activeCount = incidents.filter((incident) => ["active", "acknowledged"].includes(String(incident.status).toLowerCase())).length;
  return (
    <Card
      className="bollard-incidents-card"
      title={<><WarningOutlined /> Avvik og historikk</>}
      extra={<Tag color={activeCount ? "red" : "green"}>{activeCount ? `${activeCount} aktive` : "Ingen aktive"}</Tag>}
    >
      {incidents.length ? (
        <div className="bollard-incident-list">
          {incidents.slice(0, 12).map((incident) => {
            const active = ["active", "acknowledged"].includes(String(incident.status).toLowerCase());
            return (
              <div className={active ? "bollard-incident-row is-active" : "bollard-incident-row"} key={incident.incident_id}>
                <span className="bollard-incident-state"><i />{active ? "Aktiv" : "Løst"}</span>
                <strong>{incident.display_name}</strong>
                <span>Oppdaget {formatStamp(incident.detected_at)}</span>
                <span>Sist sett {formatStamp(incident.last_observed_at || incident.resolved_at)}</span>
              </div>
            );
          })}
        </div>
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Ingen registrerte kontrollavvik" />
      )}
    </Card>
  );
}

function NotificationPanel({ notifications }: { notifications: BollardNotificationResponse }) {
  const { message } = AntApp.useApp();
  const [sending, setSending] = useState(false);
  const active = notifications.configured && notifications.enabled && notifications.monitoringReady;
  const badge = !notifications.configured ? "Ikke klar" : !notifications.enabled ? "Av" : active ? "Aktiv" : "Venter";
  const summary = !notifications.configured
    ? "Varselkanalen er ikke konfigurert ennå."
    : !notifications.enabled
      ? "Kanalen er klar, men varsling er slått av i Protect Ledger."
      : active
        ? "Automatisk kontroll og mobilvarsling er aktiv."
        : "Varsling er klar, men overvåkingen venter på komplett kamerastatus.";

  async function sendTest() {
    if (sending) return;
    setSending(true);
    try {
      await sendBollardTestNotification();
      message.success("Testvarselet er sendt til varselkanalen.");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Kunne ikke sende testvarsel.");
    } finally {
      setSending(false);
    }
  }

  return (
    <Card
      className="bollard-notification-card"
      title={<><BellOutlined /> Mobilvarsling</>}
      extra={<Tag color={active ? "green" : notifications.configured ? "gold" : "red"}>{badge}</Tag>}
    >
      <Typography.Paragraph>{summary}</Typography.Paragraph>
      <div className="bollard-notification-actions">
        <Button type="primary" icon={<BellOutlined />} href={notifications.subscribeUrl || undefined} disabled={!notifications.subscribeUrl}>
          Abonner
        </Button>
        <Button icon={<CheckCircleOutlined />} loading={sending} disabled={!notifications.configured} onClick={() => void sendTest()}>
          Send test
        </Button>
        {notifications.webUrl ? <Button icon={<LinkOutlined />} href={notifications.webUrl} target="_blank">Varselkanal</Button> : null}
      </div>
      <Typography.Text className="bollard-privacy-note" type="secondary">
        {notifications.privacy || "Kun alarmtekst sendes. Bilder og analysedata forblir lokale."}
      </Typography.Text>
    </Card>
  );
}

export default function BollardsPage() {
  const { data, loading, fetching, error, refetch } = useApiQuery(
    queryKeys.bollardOverview(),
    fetchBollardOverview,
    { staleTime: 30_000, refetchInterval: 60_000, refetchOnWindowFocus: true },
  );
  const monitors = data?.status.camera_monitors || EMPTY_MONITORS;
  const assetMonitors = data?.status.asset_monitors || EMPTY_MONITORS;
  const inspectionItems = useMemo(() => [...monitors, ...assetMonitors], [monitors, assetMonitors]);
  const [selectedMonitorId, setSelectedMonitorId] = useState("");

  useEffect(() => {
    if (inspectionItems.length && !inspectionItems.some((monitor) => monitorKey(monitor) === selectedMonitorId)) {
      setSelectedMonitorId(monitorKey(inspectionItems[0]));
    }
  }, [inspectionItems, selectedMonitorId]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const { status, notifications } = data;
  const summary = status.summary || {};
  const runtime = status.runtime || {};
  const settings = status.settings || {};
  const intervalMinutes = Math.max(1, Math.round(Number(settings.analysis_interval_seconds || 300) / 60));
  const ready = Boolean(summary.monitoring_ready);
  const selectedMonitor = inspectionItems.find((monitor) => monitorKey(monitor) === selectedMonitorId) || inspectionItems[0];
  const incidents = status.incidents || [];

  return (
    <div className="page-stack bollards-page">
      <PageHeader
        eyebrow="UniFi Protect · lokal behandling"
        title="Pullert- og trappekontroll"
        description={`Protect Ledger sammenligner pullerter og trapp mot hvert sitt faste referanseutsnitt hvert ${intervalMinutes}. minutt.`}
        actions={<Button icon={<ReloadOutlined />} loading={fetching} onClick={() => void refetch()}>Oppdater data</Button>}
        meta={<Tag color={ready ? "green" : "gold"} icon={ready ? <CheckCircleOutlined /> : <WarningOutlined />}>{ready ? "Overvåking klar" : "Kontroller oppsett"}</Tag>}
      />

      <Card className={ready ? "bollard-command-strip is-ready" : "bollard-command-strip is-warning"}>
        <div className="bollard-command-state">
          <span className="bollard-command-icon">{ready ? <CheckCircleOutlined /> : <WarningOutlined />}</span>
          <div><small>Automatisk overvåking</small><strong>{ready ? "Systemet er klart" : settings.monitoring_enabled ? "Venter på komplett status" : "Overvåking er slått av"}</strong></div>
        </div>
        <div className="bollard-command-facts">
          <span><CameraOutlined /><small>Kontrollområder</small><strong>{(summary.baseline_cameras || 0) + (summary.calibrated_assets || 0)} / {summary.inspection_objects || 4}</strong></span>
          <span><WarningOutlined /><small>Aktive avvik</small><strong>{summary.active_incidents || 0}</strong></span>
          <span><ClockCircleOutlined /><small>Siste kontroll</small><strong>{formatStamp(runtime.last_success_at)}</strong></span>
          <span><ExperimentOutlined /><small>AI som tillegg</small><strong>{summary.ai_profiles_ready || 0} / {summary.ai_profiles_total || summary.inspection_objects || 4} klare</strong></span>
        </div>
      </Card>

      {runtime.last_error ? <Alert type="error" showIcon message="Automatisk kontroll rapporterer feil" description={runtime.last_error} /> : null}

      <section className="bollard-desktop-workspace" aria-label="Kamerainspeksjon">
        <CameraNavigator monitors={inspectionItems} selectedMonitorId={selectedMonitor ? monitorKey(selectedMonitor) : ""} onSelect={setSelectedMonitorId} />
        {selectedMonitor ? <CameraInspector key={monitorKey(selectedMonitor)} monitor={selectedMonitor} /> : <Alert type="warning" showIcon message="Ingen kontrollområder er tilgjengelige" />}
      </section>

      <section className="bollard-support-grid">
        <IncidentPanel incidents={incidents} />
        <NotificationPanel notifications={notifications} />
      </section>
    </div>
  );
}
