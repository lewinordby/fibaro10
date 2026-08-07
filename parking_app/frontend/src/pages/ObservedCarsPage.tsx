import { useMemo, useState } from "react";
import { nok } from "@lilletorget/microapp-ui/format";
import { useApi } from "@lilletorget/microapp-ui/hooks";
import { ErrorState, Loading, MetricCard, Panel } from "@lilletorget/microapp-ui/primitives";
import { AppLink, useAppLocation, useAppSearchParams } from "@lilletorget/microapp-ui/router";
import { api } from "../api";
import type { CarsDayItem } from "../types";

const SCORE_OPTIONS = [0, 40, 50, 60, 70, 80, 90];
const REGISTRY_COUNTRIES = new Set(["NO", "SE", "DK"]);

function today() { return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Oslo" }); }
function stamp(value?: string | null) { return value ? new Date(value).toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Europe/Oslo" }) : "-"; }
function known(item: CarsDayItem) { return Boolean(item.vehicle || item.knownInProtect || (item.registryValidation.is_valid && (item.registryValidation.local_match || REGISTRY_COUNTRIES.has(String(item.registryValidation.country_code || "").toUpperCase())))); }
function score(item: CarsDayItem) { return item.maximumUnifiScore ?? item.averageUnifiScore ?? null; }

function Status({ item }: { item: CarsDayItem }) {
  if (item.registryValidation.is_valid) return <span className="rounded-full bg-green-500/10 px-2.5 py-1 text-xs font-semibold text-green-700 dark:text-green-300">Registerfunnet</span>;
  if (item.requiresReview) return <span className="rounded-full bg-yellow-500/10 px-2.5 py-1 text-xs font-semibold text-yellow-700 dark:text-yellow-300">Kontroller</span>;
  return <span className="rounded-full bg-gray-500/10 px-2.5 py-1 text-xs font-semibold text-gray-500">Ikke funnet</span>;
}

export default function ObservedCarsPage() {
  const { search } = useAppLocation();
  const [params, setParams] = useAppSearchParams();
  const day = params.get("day") || today();
  const result = useApi(() => api.carsDay(day), `cars-day-${day}-${search}`);
  const [query, setQuery] = useState("");
  const [registryOnly, setRegistryOnly] = useState(false);
  const [minimumScore, setMinimumScore] = useState(0);
  const [payment, setPayment] = useState("all");
  const data = result.data;
  const items = useMemo(() => (data?.items || []).filter((item) => {
    if (registryOnly && !known(item)) return false;
    if (minimumScore && (score(item) == null || Number(score(item)) < minimumScore)) return false;
    if (payment === "paid" && !item.hasPaidSession) return false;
    if (payment === "unpaid" && item.hasPaidSession) return false;
    const needle = query.trim().toLocaleLowerCase("nb-NO");
    if (!needle) return true;
    return [item.plate, item.vehicle?.title, item.vehicle?.name, item.registryValidation.vehicle_label, item.registryValidation.country, ...item.cameraNames].filter(Boolean).join(" ").toLocaleLowerCase("nb-NO").includes(needle);
  }), [data, minimumScore, payment, query, registryOnly]);
  const setDay = (value: string) => { const next = new URLSearchParams(params); next.set("day", value); setParams(next); };
  if (result.loading && !data) return <Loading />;
  if (result.error || !data) return <ErrorState error={result.error} onRetry={result.reload} />;
  return <div className="space-y-5">
    <Panel><div className="flex flex-wrap items-center justify-between gap-3 p-4"><div><p className="text-xs font-semibold uppercase text-gray-400">Valgt dag</p><strong className="text-lg text-gray-800 dark:text-gray-100">{data.selectedDayLabel}</strong></div><div className="flex flex-wrap items-center gap-2"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => setDay(data.prevDay)}>Forrige</button><input className="form-input" type="date" max={today()} value={day} onChange={(event) => setDay(event.target.value)} /><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={data.isToday} onClick={() => setDay(data.nextDay)}>Neste</button><button className="btn bg-sky-500 text-white hover:bg-sky-600" onClick={() => setDay(today())}>I dag</button></div></div></Panel>
    <div className="grid grid-cols-2 gap-4 xl:grid-cols-6"><MetricCard label="Unike biler" value={data.summary.uniquePlates} unit="stk" detail={`${data.summary.mergedOcrVariants} OCR-varianter samlet`} tone="sky" /><MetricCard label="Deteksjoner" value={data.summary.detections} unit="stk" detail={`${stamp(data.observationWindow.firstDetectedAt)}-${stamp(data.observationWindow.lastDetectedAt)}`} tone="sky" /><MetricCard label="Registerfunnet" value={data.summary.validatedPlates} unit="stk" detail="Norge, Sverige eller Danmark" tone="green" /><MetricCard label="Med betaling" value={data.summary.paidPlates} unit="stk" detail={`${data.summary.coveredPlates} sett i betalt tidsrom`} tone="green" /><MetricCard label="Uten betaling" value={data.summary.withoutPayment} unit="stk" detail="Ingen betaling denne dagen" tone="yellow" /><MetricCard label="Kontroller" value={data.summary.reviewPlates} unit="stk" detail={`${data.summary.pendingValidation} venter`} tone="yellow" /></div>
    <Panel title="Biler denne dagen" subtitle={`${items.length} av ${data.summary.uniquePlates} biler · ${data.matchPolicy.label}`} actions={<button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={result.reload}>Oppdater</button>}>
      <div className="flex flex-wrap items-center gap-3 border-b border-gray-100 p-4 dark:border-gray-700/60"><input className="form-input min-w-64 flex-1" placeholder="Søk reg.nr, kjøretøy eller kamera" value={query} onChange={(event) => setQuery(event.target.value)} /><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={registryOnly} onChange={(event) => setRegistryOnly(event.target.checked)} />Kun kjente eller registerfunnet</label><select className="form-select" value={minimumScore} onChange={(event) => setMinimumScore(Number(event.target.value))}>{SCORE_OPTIONS.map((value) => <option value={value} key={value}>{value ? `Minst ${value} i score` : "Alle scorer"}</option>)}</select><select className="form-select" value={payment} onChange={(event) => setPayment(event.target.value)}><option value="all">Alle betalinger</option><option value="paid">Med betaling</option><option value="unpaid">Uten betaling</option></select></div>
      <div className="divide-y divide-gray-100 dark:divide-gray-700/60">{items.map((item) => <CarRow day={day} item={item} key={item.plate} />)}{!items.length ? <div className="p-8 text-center text-sm text-gray-500">Ingen biler i valgt filter.</div> : null}</div>
    </Panel>
  </div>;
}

function CarRow({ day, item }: { day: string; item: CarsDayItem }) {
  const [open, setOpen] = useState(false);
  const vehicle = item.vehicle?.title || item.vehicle?.name || item.registryValidation.vehicle_label || "Ukjent kjøretøy";
  return <article><div className="grid w-full grid-cols-[minmax(9rem,1.1fr)_minmax(11rem,1.5fr)_7rem_8rem_8rem_2rem] items-center gap-4 px-5 py-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800/40"><div>{item.vehicle?.path ? <AppLink className="text-base font-bold text-sky-600 hover:underline" to={item.vehicle.path.replace(/^\/parkering/, "")}>{item.plate}</AppLink> : <strong>{item.plate}</strong>}<p className="mt-0.5 text-xs text-gray-400">{item.cameraNames.join(", ") || "Ukjent kamera"}</p></div><div><strong className="text-sm text-gray-800 dark:text-gray-100">{vehicle}</strong><div className="mt-1"><Status item={item} /></div></div><div className="text-sm"><strong className="tabular-nums">{score(item) ?? "-"}</strong><p className="text-xs text-gray-400">Høyeste score</p></div><div className="text-sm"><strong className="tabular-nums">{stamp(item.firstDetectedAt)}</strong><p className="text-xs text-gray-400">Første</p></div><div className="text-sm"><strong className={item.hasPaidSession ? "text-green-600" : "text-yellow-600"}>{item.hasPaidSession ? `${nok(item.paidTotalKr)} kr` : "Ingen"}</strong><p className="text-xs text-gray-400">Betaling</p></div><button className="flex size-8 items-center justify-center rounded-md text-lg text-gray-500 hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-700 dark:hover:text-gray-100" type="button" aria-expanded={open} aria-label={open ? `Skjul bilder for ${item.plate}` : `Vis bilder for ${item.plate}`} onClick={() => setOpen((value) => !value)}>{open ? "-" : "+"}</button></div>{open ? <CarDetections day={day} item={item} /> : null}</article>;
}

function CarDetections({ day, item }: { day: string; item: CarsDayItem }) {
  const result = useApi(() => api.carDetections(item.plate, day), `car-detections-${day}-${item.plate}`);
  if (result.loading && !result.data) return <div className="p-5"><Loading /></div>;
  if (result.error || !result.data) return <div className="p-5"><ErrorState error={result.error} onRetry={result.reload} /></div>;
  return <div className="grid gap-4 bg-gray-50/70 p-5 dark:bg-gray-900/30 sm:grid-cols-2 xl:grid-cols-4">{result.data.detections.map((detection, index) => <a className="group block overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" href={detection.snapshotUrl || undefined} target="_blank" rel="noreferrer" key={`${detection.recognitionId || index}`}><div className="aspect-video bg-gray-100 dark:bg-gray-900">{detection.snapshotUrl ? <img className="h-full w-full object-cover transition group-hover:scale-[1.01]" src={detection.snapshotUrl} alt={`${item.plate} ${stamp(detection.occurredAt)}`} loading="lazy" /> : <div className="flex h-full items-center justify-center text-xs text-gray-400">{detection.snapshotStatus || "Uten bilde"}</div>}</div><div className="flex items-center justify-between gap-3 p-3 text-xs"><span>{stamp(detection.occurredAt)} · {detection.cameraName || "Kamera"}</span><strong>{detection.unifiScore == null ? "-" : `${detection.unifiScore}/100`}</strong></div></a>)}{!result.data.detections.length ? <p className="text-sm text-gray-500">Ingen kamerabilder funnet.</p> : null}</div>;
}
