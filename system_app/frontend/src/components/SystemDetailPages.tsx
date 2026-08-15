import { useEffect } from "react";
import { AppLink, DataTable, ErrorState, Loading, MetricCard, MosaicIcon, Panel, displayCell, useApi } from "@lilletorget/microapp-ui";
import { domainApi } from "@lilletorget/microapp-ui/api";
import type { DomainUiConfig, JsonRecord, ModuleCard, ModuleTable } from "@lilletorget/microapp-ui/types";

type Field = { label: string; value: unknown; detail?: string };
type ImportStatusDetail = { source: JsonRecord; runs: JsonRecord[]; summary: { runs: number; ok: number; failed: number; unknown: number } };
type BuildDetail = { build: string; version?: string; date: string; headline: string; title?: string; description: string; applications: string[]; changes: string[]; request: string; workDuration: string; creditsUsed: string; isCurrent?: boolean };

function Back({ to, label }: { to: string; label: string }) {
  return <AppLink className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-800 dark:hover:text-gray-100" to={to}><MosaicIcon name="arrow-left" size={16} />{label}</AppLink>;
}
function Cards({ cards, tone = "gray" }: { cards: ModuleCard[]; tone?: "gray" | "green" | "yellow" | "violet" }) {
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map((card) => <MetricCard key={card.title} label={card.title} value={card.value} unit={card.unit} detail={card.detail} tone={tone} />)}</div>;
}

function Fields({ fields }: { fields: Field[] }) {
  return <dl className="grid gap-x-8 gap-y-4 p-5 sm:grid-cols-2 xl:grid-cols-3">{fields.map((field) => <div key={field.label}><dt className="text-xs font-semibold uppercase text-gray-400">{field.label}</dt><dd className="mt-1 break-words text-sm font-medium text-gray-800 dark:text-gray-100">{displayCell(field.label, field.value)}</dd>{field.detail ? <small className="text-gray-400">{field.detail}</small> : null}</div>)}</dl>;
}

export function DataSourceDetailPage({ jobName, config, coreUrl }: { jobName: string; config: DomainUiConfig; coreUrl: string }) {
  const result = useApi(() => domainApi.get<ImportStatusDetail>(`/api/import-status/${encodeURIComponent(jobName)}`), `data-source-${jobName}`);
  useEffect(() => { const timer = window.setInterval(result.reload, 60_000); return () => window.clearInterval(timer); }, [result.reload]);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const { source, runs, summary } = result.data;
  const operationalFields: Field[] = [{ label: "Datakilde nr.", value: source.source_no }, { label: "Område", value: source.category }, { label: "Kjøreplan", value: source.schedule_text }, { label: "Alder", value: source.age }, { label: "Sist kjørt", value: source.last_run_at }, { label: "Sist OK", value: source.last_success_at }, { label: "Siste feil", value: source.last_failed_at }, { label: "Neste forventet", value: source.next_expected_at }, { label: "Siste melding", value: source.message }];
  const technicalFields: Field[] = [{ label: "Jobbnavn", value: source.job_name }, { label: "Kilde", value: source.source }, { label: "Forklaring", value: source.description }, { label: "Dataflyt", value: source.data_flow }, { label: "Avhengigheter", value: source.dependencies }, { label: "Forventet intervall", value: source.expected_interval_minutes, detail: "minutter" }, { label: "Varsel etter", value: source.warning_after_minutes, detail: "minutter" }, { label: "Siste rader", value: source.records_imported }, { label: "Rader totalt", value: source.records_total }, { label: "Varighet", value: source.duration_seconds, detail: "sekunder" }];
  const table: ModuleTable = { title: "Kjørehistorikk", columns: ["started_at", "finished_at", "status", "ok", "records_imported", "records_total", "duration_seconds", "message"], rows: runs };
  const sourceOk = String(source.status || "").toLowerCase() === "ok";
  return <div className="space-y-5"><Back to="/datakilder" label="Datakilder" /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Kjøringer" value={summary.runs} unit="stk" detail="I vist historikk" tone="violet" /><MetricCard label="Vellykket" value={summary.ok} unit="stk" detail="Fullført uten feil" tone="green" /><MetricCard label="Feilet" value={summary.failed} unit="stk" detail="Krever kontroll" tone={summary.failed ? "red" : "gray"} /><MetricCard label="Status" value={String(source.status_text || source.status || "-")} detail={String(source.age || "")} tone={sourceOk ? "green" : "red"} /></div><Panel title={String(source.title || jobName)} subtitle={String(source.description || source.job_name || jobName)}><Fields fields={operationalFields} /></Panel><details className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"><summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-gray-700 dark:text-gray-200">Teknisk datagrunnlag</summary><div className="border-t border-gray-100 dark:border-gray-700"><Fields fields={technicalFields} /></div></details><DataTable table={table} config={config} coreUrl={coreUrl} reload={result.reload} /></div>;
}

export function BuildDetailPage({ build }: { build: string }) {
  const result = useApi(() => domainApi.get<BuildDetail>(`/api/admin/builds/${encodeURIComponent(build)}`), `build-${build}`);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  return <div className="space-y-5"><Back to="/build" label="Til buildlogg" /><Panel title={`Build ${data.build} · ${data.headline}`} subtitle={`${data.date}${data.isCurrent ? " · aktiv build" : ""}`}><div className="p-5"><p className="max-w-4xl text-sm leading-6 text-gray-600 dark:text-gray-300">{data.description}</p><div className="mt-5 flex flex-wrap gap-2">{data.applications.map((app) => <span className="rounded-full bg-violet-500/10 px-3 py-1 text-xs font-semibold text-violet-600 dark:text-violet-400" key={app}>{app}</span>)}</div></div></Panel><div className="grid gap-5 xl:grid-cols-2"><Panel title="Endringer"><ol className="space-y-3 p-5 text-sm text-gray-600 dark:text-gray-300">{data.changes.map((change, index) => <li className="grid grid-cols-[1.5rem_1fr] gap-2" key={`${index}-${change}`}><strong>{index + 1}.</strong><span>{change}</span></li>)}</ol></Panel><div className="space-y-5"><Panel title="Bestilling"><div className="whitespace-pre-wrap p-5 text-sm leading-6 text-gray-600 dark:text-gray-300">{data.request || "Ikke registrert"}</div></Panel><Panel title="Gjennomføring"><Fields fields={[{label:"Tidsbruk",value:data.workDuration},{label:"Kreditter",value:data.creditsUsed}]} /></Panel></div></div></div>;
}

export function SystemDetailRoute({ pathname, config, coreUrl }: { pathname: string; config: DomainUiConfig; coreUrl: string }) {
  const sourceMatch = pathname.match(/^\/datakilder\/([^/]+)$/);
  if (sourceMatch) return <DataSourceDetailPage jobName={decodeURIComponent(sourceMatch[1])} config={config} coreUrl={coreUrl} />;
  const buildMatch = pathname.match(/^\/build\/([^/]+)$/);
  if (buildMatch) return <BuildDetailPage build={decodeURIComponent(buildMatch[1])} />;
  return null;
}
