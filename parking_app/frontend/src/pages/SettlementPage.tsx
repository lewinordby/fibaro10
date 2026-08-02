import { api } from "../api";
import { ModuleCards } from "../components/ModuleContent";
import { Panel } from "../components/Mosaic";
import { ErrorState, Loading } from "../components/PageState";
import { displayCell } from "../format";
import { useApi } from "../hooks";
import { AppLink } from "../router";

export default function SettlementPage({ id }: { id: string }) {
  const result = useApi(() => api.settlement(id), `settlement-${id}`);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">{data.title}</h2><p className="text-sm text-gray-500">{data.subtitle}</p></div><AppLink className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" to="/oppgjor">Tilbake til oppgjør</AppLink></div>
    <ModuleCards cards={data.cards} />
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[20rem_1fr]">
      <div className="space-y-6">{data.sections.map((section) => <Panel title={section.title} key={section.title}><dl className="divide-y divide-gray-100 dark:divide-gray-700/60">{section.rows.map((row) => <div className="px-5 py-3" key={row.label}><dt className="text-xs text-gray-500">{row.label}</dt><dd className="mt-0.5 text-lg font-semibold tabular-nums text-gray-800 dark:text-gray-100">{displayCell(row.label.toLowerCase(), row.value)}</dd>{row.detail ? <p className="text-xs text-gray-500">{row.detail}</p> : null}</div>)}</dl></Panel>)}</div>
      <Panel title="Originalt oppgjør" subtitle={`${data.original.filename} · ${data.original.sizeLabel}`} actions={<a className="btn bg-sky-500 text-white hover:bg-sky-600" href={data.original.downloadUrl}>Last ned</a>}>
        {data.original.previewKind === "pdf" ? <iframe className="h-[75vh] min-h-[680px] w-full bg-white" src={data.original.previewUrl} title={data.original.filename} /> : null}
        {data.original.previewKind === "image" ? <div className="flex min-h-[680px] items-start justify-center bg-gray-50 p-5 dark:bg-gray-900/30"><img className="max-h-[75vh] max-w-full object-contain" src={data.original.previewUrl} alt={data.original.filename} /></div> : null}
        {!["pdf", "image"].includes(data.original.previewKind) ? <div className="flex min-h-96 items-center justify-center p-8 text-center text-gray-500">Forhåndsvisning er ikke tilgjengelig. Bruk Last ned.</div> : null}
      </Panel>
    </div>
  </div>;
}
