import { nok, percentDelta, shortDateTime, signedNok } from "@lilletorget/microapp-ui/format";
import { useApi } from "@lilletorget/microapp-ui/hooks";
import { ErrorState, Loading, MosaicIcon } from "@lilletorget/microapp-ui/primitives";
import { AppLink } from "@lilletorget/microapp-ui/router";
import { api } from "../api";
import type { PeriodComparison, StatusPeriod } from "../types";

function tone(value: number) {
  return value > 0 ? "text-green-700 dark:text-green-400" : value < 0 ? "text-red-700 dark:text-red-400" : "text-gray-500 dark:text-gray-400";
}

function DeltaIcon({ value }: { value: number }) {
  if (value > 0) return <MosaicIcon name="arrow-up" />;
  if (value < 0) return <MosaicIcon name="arrow-down" />;
  return <MosaicIcon name="arrow-right" />;
}

function comparisonForPrevious(period: StatusPeriod): PeriodComparison {
  return {
    label: period.previousLabel,
    total: period.previousTotal,
    sol: period.previousSol,
    solCount: period.previousSolCount,
    parking: period.previousParking,
    parkingCount: period.previousParkingCount,
    solAsOfLabel: "",
    parkingAsOfLabel: "",
    fullLabel: period.previousFullLabel,
    fullTotal: period.previousFullTotal,
    fullSol: period.previousFullSol,
    fullSolCount: period.previousFullSolCount,
    fullParking: period.previousFullParking,
    fullParkingCount: period.previousFullParkingCount,
  };
}

function shortComparisonLabel(value: string) {
  return value
    .replace(/^Sammenlignet med tilsvarende datatidspunkt\s*/i, "Mot ")
    .replace(/^Sammenlignet med\s*/i, "Mot ")
    .replace(/^Tilsvarende datatidspunkt\s*/i, "Mot ")
    .replace(/^Mot i (?=\d{4})/i, "Mot ");
}

function driverComparisonLabel(periodKey: string, comparison: PeriodComparison, index: number) {
  if (periodKey === "today" && index === 1) return "Forrige uke";
  return shortComparisonLabel(comparison.label);
}

const driverGrid = "grid-cols-[minmax(0,1.2fr)_repeat(3,minmax(0,.8fr))]";

function DriverRow({ kind, amount, count, comparisons }: { kind: "sun" | "parking"; amount: number; count: number; comparisons: Array<PeriodComparison | undefined> }) {
  const sun = kind === "sun";
  return (
    <div className={`grid min-h-14 ${driverGrid} items-center border-t border-gray-100 px-3 py-2 sm:px-4 dark:border-gray-700/60`}>
      <span className="flex min-w-0 items-center gap-3">
        <span className={`h-3 w-3 shrink-0 rounded-full ${sun ? "bg-yellow-500" : "bg-sky-500"}`} />
        <span className="min-w-0">
          <b className="block text-sm font-semibold text-gray-800 dark:text-gray-100">{sun ? "Soling" : "Parkering"}</b>
          <small className="block truncate text-[10px] text-gray-400 dark:text-gray-500">{count} stk · {count ? nok(amount / count) : 0} kr snitt</small>
        </span>
      </span>
      <strong className="tabular-nums truncate text-right text-xs font-semibold text-gray-800 sm:text-sm dark:text-gray-100">{nok(amount)} kr</strong>
      {comparisons.map((comparison, index) => {
        if (!comparison) return <em className="text-right text-sm not-italic text-gray-400" key={index}>-</em>;
        const referenceAmount = sun ? comparison.sol : comparison.parking;
        const delta = amount - referenceAmount;
        return <em className={`tabular-nums truncate text-right text-xs font-semibold not-italic sm:text-sm ${tone(delta)}`} key={`${comparison.label}-${index}`}>{signedNok(delta)}</em>;
      })}
    </div>
  );
}

function PeriodCard({ period }: { period: StatusPeriod }) {
  const comparisons = [comparisonForPrevious(period), ...(period.extraComparisons ?? [])].slice(0, 2);
  const driverComparisons = [comparisons[0], comparisons[1]];
  const comparisonPath = period.key === "year" ? "/ar" : `/sammenligning?period=${period.key}`;
  const sunShare = period.total > 0 ? Math.max(0, Math.min(100, (period.sol / period.total) * 100)) : 50;

  return (
    <article className="overflow-hidden bg-white dark:bg-gray-800 shadow-sm rounded-xl">
      <header className="flex min-h-19 items-start justify-between gap-5 px-5 pb-4 pt-5">
        <div>
          <span className="text-base font-semibold text-gray-800 dark:text-gray-100">{period.title}</span>
          <small className="mt-1 block text-xs text-gray-400 dark:text-gray-500">Sol {period.solAsOfLabel} · parkering {period.parkingAsOfLabel}</small>
        </div>
        <div className="tabular-nums text-right">
          {period.rank ? <em className="mb-1 block text-[10px] font-semibold uppercase not-italic text-violet-600 dark:text-violet-400">{period.rank.label}</em> : null}
          <strong className="text-2xl font-bold text-gray-800 dark:text-gray-100">{nok(period.total)} kr</strong>
        </div>
      </header>

      <div className="px-5 pb-4">
        <div className="flex h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700">
          <span className="bg-yellow-500" style={{ width: `${sunShare}%` }} />
          <span className="grow bg-sky-500" />
        </div>
        <div className="mt-2 flex justify-between text-[10px] font-medium text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-yellow-500" />Soling {Math.round(sunShare)}%</span>
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-sky-500" />Parkering {Math.round(100 - sunShare)}%</span>
        </div>
      </div>

      <div className="grid grid-cols-2 border-y border-gray-100 dark:border-gray-700/60">
        {comparisons.map((comparison, index) => {
          const delta = period.total - comparison.total;
          return (
            <AppLink className={`flex min-h-16 items-center justify-between gap-3 px-4 py-3 transition hover:bg-gray-50 dark:hover:bg-gray-700/25 ${index ? "border-l border-gray-100 dark:border-gray-700/60" : ""}`} to={comparisonPath} key={`${comparison.label}-${index}`}>
              <span className="min-w-0">
                <span className="block truncate text-[10px] font-semibold uppercase text-gray-400 dark:text-gray-500">{shortComparisonLabel(comparison.label)}</span>
                <strong className={`tabular-nums mt-1 block text-base ${tone(delta)}`}>{signedNok(delta)} <small className="text-xs">{percentDelta(period.total, comparison.total)}</small></strong>
              </span>
              <span className={`shrink-0 ${tone(delta)}`}><DeltaIcon value={delta} /></span>
            </AppLink>
          );
        })}
      </div>

      <div className="m-4 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700/60">
        <div>
          <div className={`grid h-8 ${driverGrid} items-center bg-gray-50 px-3 text-[9px] font-semibold uppercase text-gray-400 sm:px-4 dark:bg-gray-900/30 dark:text-gray-500`}>
            <span>Inntektskilde</span><span className="text-right">Hittil</span>
            {driverComparisons.map((comparison, index) => {
              const label = comparison ? driverComparisonLabel(period.key, comparison, index) : "-";
              return <span className="truncate text-right" title={label} key={comparison?.label || index}>{label}</span>;
            })}
          </div>
          <DriverRow kind="sun" amount={period.sol} count={period.solCount} comparisons={driverComparisons} />
          <DriverRow kind="parking" amount={period.parking} count={period.parkingCount} comparisons={driverComparisons} />
        </div>
      </div>

      <footer className="grid grid-cols-2 border-t border-gray-100 bg-gray-50/80 dark:border-gray-700/60 dark:bg-gray-900/25">
        {comparisons.map((comparison, index) => {
          const progress = comparison.fullTotal && comparison.fullTotal > 0 ? Math.min(100, Math.max(0, (period.total / comparison.fullTotal) * 100)) : 0;
          return (
            <span className={`grid min-h-18 grid-cols-[1fr_auto] content-center gap-x-3 px-5 py-3 ${index ? "border-l border-gray-200 dark:border-gray-700/60" : ""}`} key={`${comparison.fullLabel}-${index}`}>
              <b className="truncate text-[10px] font-semibold text-gray-500 dark:text-gray-400">{comparison.fullLabel || comparison.label}</b>
              <em className="tabular-nums text-xs font-semibold not-italic text-gray-700 dark:text-gray-200">{comparison.fullTotal == null ? "-" : `${nok(comparison.fullTotal)} kr`}</em>
              <small className="text-[10px] text-gray-400 dark:text-gray-500">{comparison.fullTotal == null ? "Ingen fullverdi" : period.total >= comparison.fullTotal ? "Passert" : `${nok(comparison.fullTotal - period.total)} kr gjenstår`}</small>
              <span className="mt-1 h-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"><i className="block h-full rounded-full bg-violet-500" style={{ width: `${progress}%` }} /></span>
            </span>
          );
        })}
      </footer>
    </article>
  );
}

export default function DashboardPage() {
  const { data, loading, error, reload } = useApi(api.dashboard, "dashboard");
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;
  const easypark = data.services.find((service) => service.jobName === "easypark_parking_import" || service.label.toLowerCase().includes("easypark"));
  const periods = ["today", "week", "month", "year"]
    .map((key) => data.statusPeriods.find((period) => period.key === key))
    .filter((period): period is StatusPeriod => Boolean(period));

  return (
    <div className="space-y-6">
      <div className="flex min-h-12 items-center gap-3 bg-white dark:bg-gray-800 shadow-sm rounded-xl px-5 py-3 text-xs text-gray-500 dark:text-gray-400">
        <MosaicIcon name="clock" className="text-violet-500" />
        <span>Soling og parkering sammenlignes på sine respektive siste datatidspunkt.</span>
        <b className="ml-auto text-gray-700 dark:text-gray-200">EasyPark sist {shortDateTime(easypark?.lastSuccessAt)}</b>
        {easypark?.nextExpectedAt ? <em className="not-italic text-gray-400 dark:text-gray-500">Neste import {shortDateTime(easypark.nextExpectedAt)}</em> : null}
      </div>
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {periods.map((period) => <PeriodCard period={period} key={period.key} />)}
      </section>
    </div>
  );
}
