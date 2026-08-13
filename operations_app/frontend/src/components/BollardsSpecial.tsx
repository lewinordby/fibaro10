import { useEffect, useMemo, useState } from "react";
import { ErrorState, Loading, MetricCard, Panel, Segmented, useApi } from "@lilletorget/microapp-ui";
import { domainApi } from "@lilletorget/microapp-ui/api";

type Monitor = {
  monitor_id?: string; item_type?: string; asset_key?: string; asset_type?: string; display_name?: string;
  camera_id: string; camera_name: string; status: string; baseline_captured_at?: string | null; latest_captured_at?: string | null;
  last_checked_at?: string | null; change_score?: number | null; baseline_url?: string | null; latest_url?: string | null;
  overlay_url?: string | null; baseline_crop_url?: string | null; latest_crop_url?: string | null; overlay_crop_url?: string | null;
  ai_heatmap_url?: string | null; ai_status?: string; ai_score?: number | null; ai_threshold?: number | null; ai_training_samples?: number | null;
  ai_last_checked_at?: string | null; ai_last_error?: string | null; last_error?: string | null;
};
type Incident = { incident_id: number; display_name: string; status: string; severity?: string | null; detected_at: string; last_observed_at?: string | null; resolved_at?: string | null };
type Status = { settings: { analysis_interval_seconds?: number; monitoring_enabled?: boolean }; camera_monitors: Monitor[]; asset_monitors?: Monitor[]; incidents?: Incident[]; summary: Record<string, number | boolean | undefined>; runtime: { last_success_at?: string | null; last_error?: string | null } };
type Notifications = { configured: boolean; enabled: boolean; monitoringReady: boolean; subscribeUrl?: string | null; webUrl?: string | null; privacy?: string | null };

function stamp(value?: string | null) { return value ? new Date(value).toLocaleString("nb-NO", { timeZone: "Europe/Oslo" }) : "-"; }
function key(monitor: Monitor) { return monitor.monitor_id || monitor.asset_key || monitor.camera_id; }
function name(monitor: Monitor) { return monitor.display_name || monitor.camera_name; }
function statusLabel(value?: string) {
  const labels: Record<string, string> = { normal: "Normal", changed: "Endring", obscured: "Tildekket", suspected: "Kontroller", error: "Feil", training: "Trener", active: "Aktiv", resolved: "Løst", acknowledged: "Bekreftet" };
  return labels[String(value || "").toLowerCase()] || value || "Ukjent";
}

export function BollardsSpecial() {
  const status = useApi(() => domainApi.get<Status>("/api/unifi-protect/bollards"), "bollards-live");
  const notifications = useApi(() => domainApi.get<Notifications>("/api/unifi-protect/bollards/mobile-notifications"), "bollards-notifications");
  const monitors = useMemo(() => [...(status.data?.camera_monitors || []), ...(status.data?.asset_monitors || [])], [status.data]);
  const [selected, setSelected] = useState("");
  useEffect(() => { if (monitors.length && !monitors.some((item) => key(item) === selected)) setSelected(key(monitors[0])); }, [monitors, selected]);
  if ((status.loading || notifications.loading) && !status.data) return <Loading />;
  if (status.error || !status.data) return <ErrorState error={status.error} onRetry={status.reload} />;
  const data = status.data;
  const current = monitors.find((item) => key(item) === selected) || monitors[0];
  const summary = data.summary;
  return <div className="space-y-5">
    <div className="grid grid-cols-2 gap-4 xl:grid-cols-4"><MetricCard label="Kontrollområder" value={Number(summary.inspection_objects || monitors.length)} unit="stk" detail={`${Number(summary.connected_cameras || 0)} kameraer tilkoblet`} tone="violet" /><MetricCard label="Aktive avvik" value={Number(summary.active_incidents || 0)} unit="stk" detail="Krever visuell kontroll" tone={Number(summary.active_incidents || 0) ? "red" : "green"} /><MetricCard label="AI-profiler" value={`${Number(summary.ai_profiles_ready || 0)} / ${Number(summary.ai_profiles_total || monitors.length)}`} detail="Klare for analyse" tone="violet" /><MetricCard label="Siste kontroll" value={stamp(data.runtime.last_success_at)} detail={`${Math.max(1, Math.round(Number(data.settings.analysis_interval_seconds || 300) / 60))} min intervall`} tone="gray" /></div>
    {data.runtime.last_error ? <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">{data.runtime.last_error}</div> : null}
    <div className="grid gap-5 xl:grid-cols-[20rem_minmax(0,1fr)]"><Panel title="Kontrollområder" subtitle={`${monitors.length} faste utsnitt`}><div className="divide-y divide-gray-100 dark:divide-gray-700/60">{monitors.map((monitor, index) => <button className={`grid w-full grid-cols-[2rem_1fr_auto] items-center gap-3 p-4 text-left ${key(monitor) === selected ? "bg-violet-500/10" : "hover:bg-gray-50 dark:hover:bg-gray-900/30"}`} onClick={() => setSelected(key(monitor))} key={key(monitor)}><span className="text-xs font-bold text-gray-400">{String(index + 1).padStart(2, "0")}</span><span><strong className="block text-sm text-gray-800 dark:text-gray-100">{name(monitor)}</strong><small className="text-gray-400">{stamp(monitor.last_checked_at)}</small></span><span className={`rounded-full px-2 py-1 text-xs font-semibold ${monitor.status === "normal" ? "bg-green-500/10 text-green-700 dark:text-green-300" : "bg-yellow-500/10 text-yellow-700 dark:text-yellow-300"}`}>{statusLabel(monitor.status)}</span></button>)}</div></Panel>{current ? <Inspector monitor={current} /> : <Panel><div className="p-8 text-sm text-gray-500">Ingen kontrollområder er tilgjengelige.</div></Panel>}</div>
    <div className="grid gap-5 xl:grid-cols-2"><Incidents incidents={data.incidents || []} /><Notification data={notifications.data} reload={notifications.reload} /></div>
  </div>;
}

function Inspector({ monitor }: { monitor: Monitor }) {
  const [mode, setMode] = useState("compare");
  const [opacity, setOpacity] = useState(50);
  const [heatmap, setHeatmap] = useState(false);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (mode !== "compare" || !["ArrowLeft", "ArrowRight"].includes(event.key) || ["INPUT", "TEXTAREA", "SELECT"].includes((event.target as HTMLElement)?.tagName)) return;
      event.preventDefault(); setOpacity((value) => Math.max(0, Math.min(100, value + (event.key === "ArrowRight" ? 5 : -5))));
    };
    window.addEventListener("keydown", handler); return () => window.removeEventListener("keydown", handler);
  }, [mode]);
  const reference = monitor.baseline_crop_url || monitor.baseline_url || "";
  const latest = monitor.latest_crop_url || monitor.latest_url || "";
  const difference = monitor.overlay_crop_url || monitor.overlay_url || "";
  return <Panel title={name(monitor)} subtitle={`Fast utsnitt · kontrollert ${stamp(monitor.last_checked_at)}`} actions={<span className={`rounded-full px-3 py-1 text-xs font-semibold ${monitor.status === "normal" ? "bg-green-500/10 text-green-700 dark:text-green-300" : "bg-yellow-500/10 text-yellow-700 dark:text-yellow-300"}`}>{statusLabel(monitor.status)}</span>}>
    <div className="space-y-4 p-5"><div className="flex flex-wrap items-center justify-between gap-4"><Segmented value={mode} onChange={setMode} options={[{ value: "compare", label: "Gjennomsiktig" }, { value: "side", label: "Side om side" }, { value: "difference", label: "Markerte forskjeller" }]} />{mode === "compare" ? <label className="flex min-w-72 items-center gap-3 text-xs font-semibold text-gray-500"><span>Referanse</span><input className="w-full accent-violet-500" type="range" min="0" max="100" step="5" value={opacity} onChange={(event) => setOpacity(Number(event.target.value))} /><span>Siste {opacity}%</span></label> : null}</div>
      {mode === "side" ? <div className="grid gap-3 lg:grid-cols-2"><ImageFigure label="Referanse" stampValue={monitor.baseline_captured_at} src={reference} /><ImageFigure label="Siste bilde" stampValue={monitor.latest_captured_at} src={latest} /></div> : mode === "difference" ? <ImageFigure label="Endrede piksler" stampValue={monitor.latest_captured_at} src={difference} /> : <figure><figcaption className="mb-2 flex justify-between text-xs text-gray-500"><span>Referanse: {stamp(monitor.baseline_captured_at)}</span><span>Siste: {stamp(monitor.latest_captured_at)}</span></figcaption><div className="relative mx-auto aspect-video max-h-[62dvh] overflow-hidden rounded-lg bg-gray-950"><img className="absolute inset-0 h-full w-full object-contain" src={reference} alt={`Referanse ${name(monitor)}`} /><img className="absolute inset-0 h-full w-full object-contain" style={{ opacity: opacity / 100 }} src={latest} alt={`Siste bilde ${name(monitor)}`} /></div></figure>}
      <div className="grid gap-3 rounded-lg bg-gray-50 p-4 text-sm dark:bg-gray-900/30 sm:grid-cols-3"><div><small className="block text-gray-400">Visuell status</small><strong>{statusLabel(monitor.status)}</strong></div><div><small className="block text-gray-400">Endringsscore</small><strong>{monitor.change_score == null ? "-" : `${Math.round(monitor.change_score * 100)} %`}</strong></div><div><small className="block text-gray-400">AI-kontroll</small><strong>{statusLabel(monitor.ai_status)}{monitor.ai_score == null ? "" : ` · ${monitor.ai_score.toFixed(2)}`}</strong></div></div>
      {monitor.ai_heatmap_url ? <div><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => setHeatmap((value) => !value)}>{heatmap ? "Skjul AI-varmekart" : "Vis AI-varmekart"}</button>{heatmap ? <div className="mt-3"><ImageFigure label="Områder AI reagerer på" stampValue={monitor.ai_last_checked_at} src={monitor.ai_heatmap_url} /><p className="mt-2 text-xs text-gray-500">Varmekartet er forklaringsstøtte. Kontroller alltid mot referanse og siste bilde.</p></div> : null}</div> : null}
      {monitor.last_error || monitor.ai_last_error ? <div className="rounded-lg bg-yellow-500/10 p-3 text-sm text-yellow-700 dark:text-yellow-300">{monitor.last_error || monitor.ai_last_error}</div> : null}
    </div>
  </Panel>;
}

function ImageFigure({ label, stampValue, src }: { label: string; stampValue?: string | null; src: string }) {
  return <figure><figcaption className="mb-2 flex justify-between text-xs text-gray-500"><strong>{label}</strong><span>{stamp(stampValue)}</span></figcaption><div className="aspect-video overflow-hidden rounded-lg bg-gray-950">{src ? <img className="h-full w-full object-contain" src={src} alt={label} /> : <div className="flex h-full items-center justify-center text-gray-400">Bilde mangler</div>}</div></figure>;
}

function Incidents({ incidents }: { incidents: Incident[] }) {
  return <Panel title="Avvik og historikk" subtitle={`${incidents.filter((item) => ["active", "acknowledged"].includes(item.status)).length} aktive`}><div className="divide-y divide-gray-100 dark:divide-gray-700/60">{incidents.slice(0, 12).map((item) => <div className="grid grid-cols-[auto_1fr_auto] gap-3 p-4 text-sm" key={item.incident_id}><span className={`mt-1 h-2.5 w-2.5 rounded-full ${["active", "acknowledged"].includes(item.status) ? "bg-red-500" : "bg-green-500"}`} /><span><strong className="block">{item.display_name}</strong><small className="text-gray-400">Oppdaget {stamp(item.detected_at)}</small></span><span className="text-gray-500">{statusLabel(item.status)}</span></div>)}{!incidents.length ? <div className="p-6 text-sm text-gray-500">Ingen registrerte avvik.</div> : null}</div></Panel>;
}

function Notification({ data, reload }: { data?: Notifications | null; reload: () => void }) {
  const [message, setMessage] = useState("");
  const test = async () => { try { await domainApi.mutate("/api/unifi-protect/bollards/mobile-notifications/test", "POST"); setMessage("Testvarsel sendt"); reload(); } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); } };
  return <Panel title="Mobilvarsling" subtitle={data?.configured && data.enabled ? "Automatisk varsling er aktiv" : "Kontroller kanaloppsettet"}><div className="space-y-4 p-5"><p className="text-sm text-gray-500">{data?.privacy || "Bilder og analysedata forblir lokale."}</p><div className="flex flex-wrap gap-2">{data?.subscribeUrl ? <a className="btn bg-violet-500 text-white hover:bg-violet-600" href={data.subscribeUrl}>Abonner</a> : null}<button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={!data?.configured} onClick={test}>Send test</button>{data?.webUrl ? <a className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" href={data.webUrl} target="_blank" rel="noreferrer">Varselkanal</a> : null}</div>{message ? <p className="text-sm text-gray-500">{message}</p> : null}</div></Panel>;
}
