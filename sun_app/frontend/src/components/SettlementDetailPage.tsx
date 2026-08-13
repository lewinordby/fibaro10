import { AppLink, ErrorState, Loading, MetricCard, Panel, displayCell, useApi } from "@lilletorget/microapp-ui";
import { domainApi } from "@lilletorget/microapp-ui/api";
import type { JsonRecord, ModuleCard } from "@lilletorget/microapp-ui/types";

type Field = { label: string; value: unknown; detail?: string };
type DetailOriginal = { filename: string; contentType: string; sizeLabel: string; previewKind: string; previewUrl: string; downloadUrl: string };
type SettlementDetail = { id: number; title: string; subtitle: string; cards: ModuleCard[]; original: DetailOriginal; sections: Array<{ title: string; rows: Field[] }>; raw: JsonRecord };

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
