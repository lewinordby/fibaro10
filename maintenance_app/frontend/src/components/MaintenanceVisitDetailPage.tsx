import { useEffect, useState } from "react";
import { AppLink, DataTable, ErrorState, Loading, MetricCard, Panel, displayCell, useApi } from "@lilletorget/microapp-ui";
import { domainApi } from "@lilletorget/microapp-ui/api";
import type { DomainUiConfig, JsonRecord, ModuleCard, ModuleEditConfig, ModuleTable } from "@lilletorget/microapp-ui/types";

type Field = { label: string; value: unknown; detail?: string };
type VisitDetail = { title: string; subtitle: string; visit: JsonRecord; cards: ModuleCard[]; fields: Field[]; taskTable: ModuleTable; taskEdit: ModuleEditConfig; visitEdit: ModuleEditConfig; raw?: JsonRecord };

function Back({ to, label }: { to: string; label: string }) {
  return <AppLink className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-800 dark:hover:text-gray-100" to={to}>← {label}</AppLink>;
}
function Cards({ cards, tone = "gray" }: { cards: ModuleCard[]; tone?: "gray" | "green" | "yellow" | "violet" }) {
  return <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">{cards.map((card) => <MetricCard key={card.title} label={card.title} value={card.value} unit={card.unit} detail={card.detail} tone={tone} />)}</div>;
}

function Fields({ fields }: { fields: Field[] }) {
  return <dl className="grid gap-x-8 gap-y-4 p-5 sm:grid-cols-2 xl:grid-cols-3">{fields.map((field) => <div key={field.label}><dt className="text-xs font-semibold uppercase text-gray-400">{field.label}</dt><dd className="mt-1 break-words text-sm font-medium text-gray-800 dark:text-gray-100">{displayCell(field.label, field.value)}</dd>{field.detail ? <small className="text-gray-400">{field.detail}</small> : null}</div>)}</dl>;
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
  const saveNote = async () => { setSaving(true); setMessage(""); try { await domainApi.edit(data.visitEdit, data.visit, { notes: note }, false); setMessage("Notatet er lagret"); result.reload(); } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); } finally { setSaving(false); } };
  return <div className="space-y-5"><Back to="/besok" label="Til besøk" /><Cards cards={data.cards} tone="green" /><div className="grid gap-5 xl:grid-cols-[22rem_1fr]"><div className="space-y-5"><Panel title="Besøksdetaljer"><Fields fields={data.fields} /></Panel><Panel title="Besøksnotat"><div className="p-5"><textarea className="form-textarea min-h-36 w-full" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Hva ble observert, utført eller bør følges opp?" /><div className="mt-3 flex items-center gap-3"><button className="btn bg-green-600 text-white hover:bg-green-700" disabled={saving} onClick={saveNote}>{saving ? "Lagrer ..." : "Lagre notat"}</button>{message ? <span className="text-sm text-gray-500">{message}</span> : null}</div></div></Panel><details className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"><summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-gray-700 dark:text-gray-200">Rådata fra OwnTracks</summary><pre className="max-h-80 overflow-auto border-t border-gray-100 p-5 text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">{JSON.stringify(data.raw || {}, null, 2)}</pre></details></div><DataTable table={data.taskTable} config={config} coreUrl={coreUrl} reload={result.reload} /></div></div>;
}
