import { useEffect, useState } from "react";
import { domainApi } from "../api";
import { displayCell } from "../format";
import { useApi } from "../hooks";
import { AppLink } from "../router";
import type { DomainUiConfig, JsonRecord, ModuleCard, ModuleEditConfig, ModuleTable } from "../types";
import { DataTable } from "./ModuleContent";
import { MetricCard, Panel } from "./Mosaic";
import { ErrorState, Loading } from "./PageState";

type Field = { label: string; value: unknown; detail?: string };
type DetailOriginal = { filename: string; contentType: string; sizeLabel: string; previewKind: string; previewUrl: string; downloadUrl: string };
type SettlementDetail = { id: number; title: string; subtitle: string; cards: ModuleCard[]; original: DetailOriginal; sections: Array<{ title: string; rows: Field[] }>; raw: JsonRecord };
type VisitDetail = { title: string; subtitle: string; visit: JsonRecord; cards: ModuleCard[]; fields: Field[]; taskTable: ModuleTable; taskEdit: ModuleEditConfig; visitEdit: ModuleEditConfig };
type ImportStatusDetail = { source: JsonRecord; runs: JsonRecord[]; summary: { runs: number; ok: number; failed: number; unknown: number } };
type BuildDetail = { build: string; version?: string; date: string; headline: string; title?: string; description: string; applications: string[]; changes: string[]; request: string; workDuration: string; creditsUsed: string; isCurrent?: boolean };

function Back({ to, label }: { to: string; label: string }) {
  return <AppLink className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-800 dark:hover:text-gray-100" to={to}>← {label}</AppLink>;
}

function Cards({ cards, tone = "gray" }: { cards: ModuleCard[]; tone?: "gray" | "green" | "yellow" | "violet" }) {
  return <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">{cards.map((card) => <MetricCard key={card.title} label={card.title} value={card.value} unit={card.unit} detail={card.detail} tone={tone} />)}</div>;
}

function Fields({ fields }: { fields: Field[] }) {
  return <dl className="grid gap-x-8 gap-y-4 p-5 sm:grid-cols-2 xl:grid-cols-3">{fields.map((field) => <div key={field.label}><dt className="text-xs font-semibold uppercase text-gray-400">{field.label}</dt><dd className="mt-1 break-words text-sm font-medium text-gray-800 dark:text-gray-100">{displayCell(field.label, field.value)}</dd>{field.detail ? <small className="text-gray-400">{field.detail}</small> : null}</div>)}</dl>;
}

export function SettlementDetailPage({ domain, id }: { domain: "parking" | "sun"; id: string }) {
  const endpoint = domain === "sun" ? `/api/soling/settlements/${id}` : `/api/settlements/${id}`;
  const result = useApi(() => domainApi.get<SettlementDetail>(endpoint), `settlement-${domain}-${id}`);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  return <div className="space-y-5"><Back to="/oppgjor" label="Til oppgjør" /><Cards cards={data.cards} tone={domain === "sun" ? "yellow" : "gray"} /><div className="grid min-h-[70dvh] gap-5 xl:grid-cols-[20rem_1fr]"> <div className="space-y-5">{data.sections.map((section) => <Panel title={section.title} key={section.title}><Fields fields={section.rows} /></Panel>)}</div><Panel title={data.original.filename} subtitle={`${data.original.contentType} · ${data.original.sizeLabel}`} actions={<a className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" href={data.original.downloadUrl}>Last ned</a>}><div className="min-h-[70dvh] bg-gray-100 dark:bg-gray-900/40">{data.original.previewKind === "pdf" ? <iframe className="h-[76dvh] w-full" title={data.original.filename} src={data.original.previewUrl} /> : data.original.previewKind === "image" ? <img className="mx-auto max-h-[76dvh] object-contain" src={data.original.previewUrl} alt={data.original.filename} /> : <div className="p-8 text-sm text-gray-500">Forhåndsvisning er ikke tilgjengelig. Bruk Last ned.</div>}</div></Panel></div></div>;
}

export function MaintenanceVisitDetailPage({ id, config, coreUrl }: { id: string; config: DomainUiConfig; coreUrl: string }) {
  const result = useApi(() => domainApi.get<VisitDetail>(`/api/maintenance/site-visits/${id}`), `maintenance-visit-${id}`);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => setNote(String(result.data?.visit.notes || "")), [result.data]);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  const saveNote = async () => { setSaving(true); setMessage(""); try { await domainApi.mutate(`/api/maintenance/site-visits/${id}`, "PATCH", { notes: note }); setMessage("Notatet er lagret"); result.reload(); } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); } finally { setSaving(false); } };
  return <div className="space-y-5"><Back to="/besok" label="Til besøk" /><Cards cards={data.cards} tone="green" /><div className="grid gap-5 xl:grid-cols-[22rem_1fr]"><div className="space-y-5"><Panel title="Besøksdetaljer"><Fields fields={data.fields} /></Panel><Panel title="Notat"><div className="p-5"><textarea className="form-textarea min-h-36 w-full" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Notat om besøket" /><div className="mt-3 flex items-center gap-3"><button className="btn bg-green-600 text-white hover:bg-green-700" disabled={saving} onClick={saveNote}>{saving ? "Lagrer ..." : "Lagre notat"}</button>{message ? <span className="text-sm text-gray-500">{message}</span> : null}</div></div></Panel></div><DataTable table={data.taskTable} config={config} coreUrl={coreUrl} reload={result.reload} /></div></div>;
}

export function DataSourceDetailPage({ jobName, config, coreUrl }: { jobName: string; config: DomainUiConfig; coreUrl: string }) {
  const result = useApi(() => domainApi.get<ImportStatusDetail>(`/api/import-status/${encodeURIComponent(jobName)}`), `data-source-${jobName}`);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const { source, runs, summary } = result.data;
  const cards: ModuleCard[] = [{ title: "Kjøringer", value: summary.runs, unit: "stk", detail: "I vist historikk" }, { title: "Vellykket", value: summary.ok, unit: "stk", detail: "Fullført uten feil" }, { title: "Feilet", value: summary.failed, unit: "stk", detail: "Krever kontroll" }, { title: "Status", value: String(source.status_text || source.status || "-"), detail: String(source.age || "") }];
  const sourceFields: Field[] = [{ label: "Datakilde nr.", value: source.source_no }, { label: "Navn", value: source.title }, { label: "Kategori", value: source.category }, { label: "Kilde", value: source.source }, { label: "Forklaring", value: source.description }, { label: "Dataflyt", value: source.data_flow }, { label: "Avhengigheter", value: source.dependencies }, { label: "Kjøreplan", value: source.schedule_text }, { label: "Sist OK", value: source.last_success_at }, { label: "Neste forventet", value: source.next_expected_at }, { label: "Siste melding", value: source.message }];
  const table: ModuleTable = { title: "Kjørehistorikk", columns: ["started_at", "finished_at", "status", "ok", "records_imported", "records_total", "duration_seconds", "message"], rows: runs };
  return <div className="space-y-5"><Back to="/datakilder" label="Til datakilder" /><Cards cards={cards} tone="violet" /><Panel title={String(source.title || jobName)} subtitle={String(source.job_name || jobName)}><Fields fields={sourceFields} /></Panel><DataTable table={table} config={config} coreUrl={coreUrl} reload={result.reload} /></div>;
}

export function BuildDetailPage({ build }: { build: string }) {
  const result = useApi(() => domainApi.get<BuildDetail>(`/api/admin/builds/${encodeURIComponent(build)}`), `build-${build}`);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  return <div className="space-y-5"><Back to="/build" label="Til buildlogg" /><Panel title={`Build ${data.build} · ${data.headline}`} subtitle={`${data.date}${data.isCurrent ? " · aktiv build" : ""}`}><div className="p-5"><p className="max-w-4xl text-sm leading-6 text-gray-600 dark:text-gray-300">{data.description}</p><div className="mt-5 flex flex-wrap gap-2">{data.applications.map((app) => <span className="rounded-full bg-violet-500/10 px-3 py-1 text-xs font-semibold text-violet-600 dark:text-violet-400" key={app}>{app}</span>)}</div></div></Panel><div className="grid gap-5 xl:grid-cols-2"><Panel title="Endringer"><ol className="space-y-3 p-5 text-sm text-gray-600 dark:text-gray-300">{data.changes.map((change, index) => <li className="grid grid-cols-[1.5rem_1fr] gap-2" key={`${index}-${change}`}><strong>{index + 1}.</strong><span>{change}</span></li>)}</ol></Panel><div className="space-y-5"><Panel title="Bestilling"><div className="whitespace-pre-wrap p-5 text-sm leading-6 text-gray-600 dark:text-gray-300">{data.request || "Ikke registrert"}</div></Panel><Panel title="Gjennomføring"><Fields fields={[{label:"Tidsbruk",value:data.workDuration},{label:"Kreditter",value:data.creditsUsed}]} /></Panel></div></div></div>;
}

export function DetailRoute({ config, pathname, coreUrl }: { config: DomainUiConfig; pathname: string; coreUrl: string }) {
  const visit = config.appId === "maintenance" ? pathname.match(/^\/besok\/(\d+)$/) : null;
  if (visit) return <MaintenanceVisitDetailPage id={visit[1]} config={config} coreUrl={coreUrl} />;
  const source = config.appId === "system" ? pathname.match(/^\/datakilder\/([^/]+)$/) : null;
  if (source) return <DataSourceDetailPage jobName={decodeURIComponent(source[1])} config={config} coreUrl={coreUrl} />;
  const build = config.appId === "system" ? pathname.match(/^\/build\/([^/]+)$/) : null;
  if (build) return <BuildDetailPage build={decodeURIComponent(build[1])} />;
  const settlement = config.appId === "sun" ? pathname.match(/^\/oppgjor\/(\d+)$/) : null;
  if (settlement) return <SettlementDetailPage domain="sun" id={settlement[1]} />;
  return null;
}
