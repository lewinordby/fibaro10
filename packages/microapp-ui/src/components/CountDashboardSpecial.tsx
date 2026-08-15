import { nok, percentDelta, shortDateTime } from "../format";
import { useApi } from "../hooks";
import { AppLink } from "../router";
import type { BusinessPeriodComparison, BusinessStatusPeriod } from "../types";
import { MosaicIcon } from "./MosaicIcon";
import { ErrorState, Loading } from "./PageState";
import { domainApi } from "../api";

type Domain = "parking" | "sun";

function values(period: BusinessStatusPeriod | BusinessPeriodComparison, domain: Domain, previous = false) {
  if (previous && "previousTotal" in period) {
    return domain === "parking"
      ? { count: period.previousParkingCount, amount: period.previousParking }
      : { count: period.previousSolCount, amount: period.previousSol };
  }
  return domain === "parking"
    ? { count: period.parkingCount, amount: period.parking }
    : { count: period.solCount, amount: period.sol };
}

function fullValues(period: BusinessPeriodComparison, domain: Domain) {
  return domain === "parking"
    ? { count: period.fullParkingCount, amount: period.fullParking }
    : { count: period.fullSolCount, amount: period.fullSol };
}

function signed(value: number) {
  return `${value > 0 ? "+" : ""}${nok(value)}`;
}

function tone(value: number) {
  return value > 0 ? "text-green-700 dark:text-green-400" : value < 0 ? "text-red-700 dark:text-red-400" : "text-gray-500 dark:text-gray-400";
}

function previousComparison(period: BusinessStatusPeriod): BusinessPeriodComparison {
  return {
    label: period.previousLabel,
    sol: period.previousSol,
    solCount: period.previousSolCount,
    parking: period.previousParking,
    parkingCount: period.previousParkingCount,
    total: period.previousTotal,
    fullLabel: period.previousFullLabel,
    fullSol: period.previousFullSol,
    fullSolCount: period.previousFullSolCount,
    fullParking: period.previousFullParking,
    fullParkingCount: period.previousFullParkingCount,
    fullTotal: period.previousFullTotal,
  };
}

function compactLabel(label: string) {
  return label
    .replace(/^Sammenlignet med tilsvarende datatidspunkt\s*/i, "")
    .replace(/^Sammenlignet med\s*/i, "")
    .replace(/^Tilsvarende datatidspunkt\s*/i, "")
    .replace(/^Mot\s*/i, "");
}

function PeriodCard({ period, domain }: { period: BusinessStatusPeriod; domain: Domain }) {
  const current = values(period, domain);
  const comparisons = [previousComparison(period), ...(period.extraComparisons || [])].slice(0, 2);
  const noun = domain === "parking" ? "parkeringer" : "solinger";
  const accent = domain === "parking" ? "bg-sky-500" : "bg-yellow-500";
  const comparisonPath = period.key === "year"
    ? (domain === "parking" ? "/arsutvikling" : "/sammenligning")
    : `/periode?period=${period.key}`;
  return <article className="overflow-hidden rounded-xl bg-white shadow-sm dark:bg-gray-800">
    <header className="flex min-h-20 items-start justify-between gap-5 px-5 pb-4 pt-5">
      <div><h2 className="text-base font-semibold text-gray-800 dark:text-gray-100">{period.title}</h2><small className="mt-1 block text-xs text-gray-400">{domain === "parking" ? period.parkingAsOfLabel : period.solAsOfLabel}</small></div>
      <div className="text-right tabular-nums">{period.rank && period.key === "today" ? <span className="mb-1 block text-[10px] font-semibold uppercase text-gray-400">{period.rank.label}</span> : null}<strong className="text-2xl font-bold text-gray-800 dark:text-gray-100">{nok(current.count)} <small className="text-sm font-semibold text-gray-400">stk</small></strong></div>
    </header>
    <div className="grid grid-cols-2 border-y border-gray-100 dark:border-gray-700/60">
      {comparisons.map((comparison, index) => { const reference = values(comparison, domain); const delta = current.count - reference.count; const separator = comparisonPath.includes("?") ? "&" : "?"; return <AppLink className={`flex min-h-16 items-center justify-between gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/25 ${index ? "border-l border-gray-100 dark:border-gray-700/60" : ""}`} to={`${comparisonPath}${separator}reference=${index}`} key={`${comparison.label}-${index}`}><span><small className="block text-[10px] font-semibold uppercase text-gray-400">{compactLabel(comparison.label)}</small><strong className={`mt-1 block text-base tabular-nums ${tone(delta)}`}>{signed(delta)} <small className="text-xs">{percentDelta(current.count, reference.count)}</small></strong></span><MosaicIcon name={delta >= 0 ? "arrow-up" : "arrow-down"} className={tone(delta)} /></AppLink>; })}
    </div>
    <div className="m-4 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700/60">
      <div className="grid grid-cols-[1.2fr_.7fr_.8fr_.8fr] bg-gray-50 px-4 py-2 text-[9px] font-semibold uppercase text-gray-400 dark:bg-gray-900/30"><span>Nøkkeltall</span><span className="text-right">Hittil</span>{comparisons.map((item) => <span className="truncate text-right" key={item.label}>{compactLabel(item.label)}</span>)}</div>
      <div className="grid min-h-12 grid-cols-[1.2fr_.7fr_.8fr_.8fr] items-center border-t border-gray-100 px-4 py-2 text-sm dark:border-gray-700/60"><span className="flex items-center gap-2 font-semibold"><i className={`h-2.5 w-2.5 rounded-full ${accent}`} />Antall {noun}</span><strong className="text-right tabular-nums">{nok(current.count)}</strong>{comparisons.map((item) => { const delta = current.count - values(item, domain).count; return <strong className={`text-right tabular-nums ${tone(delta)}`} key={item.label}>{signed(delta)}</strong>; })}</div>
      <div className="grid min-h-12 grid-cols-[1.2fr_.7fr_.8fr_.8fr] items-center border-t border-gray-100 px-4 py-2 text-sm dark:border-gray-700/60"><span className="font-semibold">Omsetning</span><strong className="text-right tabular-nums">{nok(current.amount)} kr</strong>{comparisons.map((item) => { const delta = current.amount - values(item, domain).amount; return <strong className={`text-right tabular-nums ${tone(delta)}`} key={item.label}>{signed(delta)} kr</strong>; })}</div>
      <div className="grid min-h-11 grid-cols-[1.2fr_.7fr_.8fr_.8fr] items-center border-t border-gray-100 px-4 py-2 text-xs text-gray-500 dark:border-gray-700/60"><span>Snitt per {domain === "parking" ? "parkering" : "soling"}</span><span className="text-right tabular-nums">{current.count ? nok(current.amount / current.count) : 0} kr</span>{comparisons.map((item) => { const reference = values(item, domain); return <span className="text-right tabular-nums" key={item.label}>{reference.count ? nok(reference.amount / reference.count) : 0} kr</span>; })}</div>
    </div>
    <footer className="grid grid-cols-2 border-t border-gray-100 bg-gray-50/80 dark:border-gray-700/60 dark:bg-gray-900/25">
      {comparisons.map((item, index) => { const full = fullValues(item, domain); const missing = full.count == null ? null : full.count - current.count; return <span className={`grid min-h-16 grid-cols-[1fr_auto] content-center gap-x-3 px-5 py-3 ${index ? "border-l border-gray-200 dark:border-gray-700/60" : ""}`} key={item.label}><b className="truncate text-[10px] font-semibold text-gray-500">{item.fullLabel || item.label}</b><em className="text-xs font-semibold not-italic tabular-nums text-gray-700 dark:text-gray-200">{full.count == null ? "-" : `${nok(full.count)} stk`}</em><small className="col-span-2 text-[10px] text-gray-400">{missing == null ? "Ingen fullverdi" : missing <= 0 ? "Passert" : `${nok(missing)} ${noun} gjenstår`}</small></span>; })}
    </footer>
  </article>;
}

export function CountDashboardSpecial({ domain }: { domain: Domain }) {
  const result = useApi(() => domainApi.businessOverview(domain), `${domain}-dashboard`);
  if (result.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const easypark = result.data.services.find((item) => item.jobName === "easypark_parking_import" || item.label.toLowerCase().includes("easypark"));
  const periods = ["today", "week", "month", "year"].map((key) => result.data!.statusPeriods.find((item) => item.key === key)).filter((item): item is BusinessStatusPeriod => Boolean(item));
  return <div className="space-y-6"><div className="flex min-h-12 flex-wrap items-center gap-3 rounded-xl bg-white px-5 py-3 text-xs text-gray-500 shadow-sm dark:bg-gray-800"><MosaicIcon name="clock" className={domain === "parking" ? "text-sky-500" : "text-yellow-500"} /><span>Sammenligningene bruker samme datatidspunkt som den valgte datakilden.</span>{domain === "parking" ? <><b className="ml-auto text-gray-700 dark:text-gray-200">EasyPark sist {shortDateTime(easypark?.lastSuccessAt)}</b>{easypark?.nextExpectedAt ? <em className="not-italic text-gray-400">Neste {shortDateTime(easypark.nextExpectedAt)}</em> : null}</> : null}</div><section className="grid grid-cols-1 gap-6 xl:grid-cols-2">{periods.map((period) => <PeriodCard period={period} domain={domain} key={period.key} />)}</section></div>;
}
