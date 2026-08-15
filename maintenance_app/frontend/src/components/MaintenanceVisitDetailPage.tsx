import { useEffect, useState } from "react";
import {
  AppLink,
  DataTable,
  ErrorState,
  Loading,
  MetricCard,
  MosaicIcon,
  Panel,
  displayCell,
  useApi,
} from "@lilletorget/microapp-ui";
import { domainApi } from "@lilletorget/microapp-ui/api";
import type {
  DomainUiConfig,
  JsonRecord,
  ModuleCard,
  ModuleEditConfig,
  ModuleTable,
} from "@lilletorget/microapp-ui/types";

type Field = { label: string; value: unknown; detail?: string };
type VisitDetail = {
  title: string;
  subtitle: string;
  visit: JsonRecord;
  cards: ModuleCard[];
  fields: Field[];
  taskTable: ModuleTable;
  taskEdit: ModuleEditConfig;
  visitEdit: ModuleEditConfig;
  raw?: JsonRecord;
};

function VisitCards({ cards }: { cards: ModuleCard[] }) {
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map((card) => (
    <MetricCard
      key={card.title}
      label={card.title}
      value={card.value}
      unit={card.unit}
      detail={card.detail}
      tone="green"
    />
  ))}</div>;
}

function VisitFields({ fields }: { fields: Field[] }) {
  return <dl className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-1">{fields.map((field) => (
    <div key={field.label}>
      <dt className="text-xs font-semibold uppercase text-gray-400">{field.label}</dt>
      <dd className="mt-1 break-words text-sm font-medium text-gray-800 dark:text-gray-100">
        {displayCell(field.label, field.value)}
      </dd>
      {field.detail ? <small className="text-gray-400">{field.detail}</small> : null}
    </div>
  ))}</dl>;
}

export function MaintenanceVisitDetailPage({
  id,
  config,
  coreUrl,
}: {
  id: string;
  config: DomainUiConfig;
  coreUrl: string;
}) {
  const result = useApi(
    () => domainApi.get<VisitDetail>(`/api/maintenance/site-visits/${id}`),
    `maintenance-visit-${id}`,
  );
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [saveError, setSaveError] = useState(false);

  useEffect(() => {
    setNote(String(result.data?.visit.notes || ""));
    setMessage("");
    setSaveError(false);
  }, [result.data]);

  if (result.loading) return <Loading />;
  if (result.error || !result.data) {
    return <ErrorState error={result.error} onRetry={result.reload} />;
  }

  const data = result.data;
  const savedNote = String(data.visit.notes || "");
  const dirty = note !== savedNote;
  const saveNote = async () => {
    setSaving(true);
    setMessage("");
    setSaveError(false);
    try {
      await domainApi.edit(data.visitEdit, data.visit, { notes: note }, false);
      setMessage("Notatet er lagret");
      result.reload();
    } catch (error) {
      setSaveError(true);
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  };

  return <div className="space-y-5">
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <AppLink
          className="mb-2 inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-800 dark:hover:text-gray-100"
          to="/besok"
        >
          <MosaicIcon name="arrow-left" size={16} /> Besøk
        </AppLink>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{data.title}</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{data.subtitle}</p>
      </div>
    </header>

    <VisitCards cards={data.cards} />

    <div className="grid gap-5 xl:grid-cols-[minmax(16rem,1fr)_minmax(0,3fr)]">
      <div className="space-y-5">
        <Panel title="Besøksnotat">
          <div className="p-5">
            <textarea
              className="form-textarea min-h-28 w-full"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Hva ble observert, utført eller bør følges opp?"
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                className="btn bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
                disabled={saving || !dirty}
                onClick={saveNote}
              >
                {saving ? "Lagrer ..." : "Lagre notat"}
              </button>
              {message ? <span
                aria-live="polite"
                className={`text-sm ${saveError ? "text-red-500" : "text-green-600 dark:text-green-400"}`}
              >{message}</span> : null}
            </div>
          </div>
        </Panel>
        <Panel title="Besøksdetaljer"><VisitFields fields={data.fields} /></Panel>
        <details className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-gray-700 dark:text-gray-200">
            Teknisk OwnTracks-grunnlag
          </summary>
          <pre className="max-h-80 overflow-auto border-t border-gray-100 p-5 text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
            {JSON.stringify(data.raw || {}, null, 2)}
          </pre>
        </details>
      </div>
      <DataTable
        table={data.taskTable}
        config={config}
        coreUrl={coreUrl}
        reload={result.reload}
      />
    </div>
  </div>;
}
