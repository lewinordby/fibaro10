import { useMemo, useState } from "react";
import { useApi } from "@lilletorget/microapp-ui/hooks";
import { ErrorState, Loading, MetricCard, MosaicIcon, Panel } from "@lilletorget/microapp-ui/primitives";
import { AppLink } from "@lilletorget/microapp-ui/router";
import { api } from "../api";

const PAGE_SIZE = 100;

function formatSeen(value?: string | null) {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("nb-NO", { dateStyle: "short", timeStyle: "short" });
}

export default function LookupPage({ mode }: { mode: "navn" | "omrade" }) {
  const [offset, setOffset] = useState(0);
  const result = useApi(() => api.lookup(mode, PAGE_SIZE, offset), `parking-lookup-${mode}-${offset}`);
  const title = mode === "navn" ? "Manglende navn" : "Manglende område";
  const fieldLabel = mode === "navn" ? "Navn" : "Område";
  const plates = useMemo(() => result.data?.rows.map((row) => row.plate).join("\n") || "", [result.data]);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const { count, rows } = result.data;
  const first = count ? offset + 1 : 0;
  const last = Math.min(offset + rows.length, count);
  const download = `/api/parkering/kjoretoy/mangler-${mode}?limit=${PAGE_SIZE}&offset=${offset}&format=txt`;

  return (
    <div className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-3">
        <MetricCard label={title} value={count.toLocaleString("nb-NO")} unit="biler" tone="sky" detail="Totalt i arbeidskøen" />
        <MetricCard label="Viser" value={`${first}-${last}`} unit="av" detail={`${PAGE_SIZE} per side`} />
        <MetricCard label="Neste steg" value={fieldLabel} detail="Åpne kjøretøyet for kontroll og redigering" />
      </div>
      <Panel
        title={title}
        subtitle="Listen brukes av nettlesertillegget og kan også kontrolleres direkte her."
        actions={
          <div className="flex gap-2">
            <button className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" type="button" onClick={() => navigator.clipboard.writeText(plates)} disabled={!plates} title="Kopier registreringsnumrene">
              <MosaicIcon name="copy" /><span className="ml-2">Kopier</span>
            </button>
            <a className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" href={download} download>
              <MosaicIcon name="arrow-down" /><span className="ml-2">TXT</span>
            </a>
          </div>
        }
      >
        <div className="overflow-x-auto">
          <table className="table-auto w-full dark:text-gray-300">
            <thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/50 dark:text-gray-500">
              <tr><th className="px-4 py-3 text-left">Reg.nr.</th><th className="px-4 py-3 text-left">Kjøretøy</th><th className="px-4 py-3 text-left">Navn</th><th className="px-4 py-3 text-left">Område</th><th className="px-4 py-3 text-right">Parkeringer</th><th className="px-4 py-3 text-left">Sist sett</th></tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">
              {rows.map((row) => (
                <tr className="hover:bg-gray-50/70 dark:hover:bg-gray-700/20" key={row.plate}>
                  <td className="px-4 py-3"><AppLink className="font-semibold text-sky-600 hover:underline dark:text-sky-400" to={`/kjoretoy/${encodeURIComponent(row.plate)}`}>{row.plate}</AppLink></td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-200">{row.vehicle || [row.make, row.model, row.year].filter(Boolean).join(" ") || "Ukjent kjøretøy"}</td>
                  <td className="px-4 py-3">{row.navn || <span className="text-amber-600 dark:text-amber-400">Mangler</span>}</td>
                  <td className="px-4 py-3">{row.omrade || <span className="text-amber-600 dark:text-amber-400">Mangler</span>}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{(row.parkering_count || 0).toLocaleString("nb-NO")}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-gray-500 dark:text-gray-400">{formatSeen(row.last_seen)}</td>
                </tr>
              ))}
              {!rows.length ? <tr><td className="px-5 py-10 text-center text-gray-400" colSpan={6}>Ingen kjøretøy mangler {fieldLabel.toLowerCase()}.</td></tr> : null}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3 dark:border-gray-700/60">
          <span className="text-xs text-gray-500">{first}-{last} av {count.toLocaleString("nb-NO")}</span>
          <div className="flex gap-2">
            <button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}><MosaicIcon name="arrow-left" /><span className="ml-2">Forrige</span></button>
            <button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" type="button" disabled={offset + rows.length >= count} onClick={() => setOffset(offset + PAGE_SIZE)}><span className="mr-2">Neste</span><MosaicIcon name="arrow-right" /></button>
          </div>
        </div>
      </Panel>
    </div>
  );
}
