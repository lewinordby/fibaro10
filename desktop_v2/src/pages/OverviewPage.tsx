import {
  AimOutlined,
  ArrowDownOutlined,
  ArrowRightOutlined,
  ArrowUpOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  MinusOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Card, List, Space, Tag, Tooltip, Typography } from "antd";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  fetchOverview,
  type LatestItem,
  type MetricCard as MetricCardData,
  type ServiceStatus,
  type StatusPeriod,
  type StatusPeriodComparison,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { nok } from "../format";
import { useApiQuery } from "../hooks";
import { appPath } from "../navigation";
import { queryKeys } from "../queryKeys";

type DashboardView = "omsetning" | "parkering" | "soling" | "drift";
type StripState = { label: string; state: boolean | null; tooltip?: string };
type StripItem = { label: string; state?: boolean | null; states?: StripState[]; tooltip?: string };
type DashboardAction = { label: string; detail: string; href: string; tone: string };

const SPOT_FRONT_LABELS = new Set(["Spot foran glassvegg", "Spot foran massasje"]);

const DATASOURCE_PRIORITY = [
  "hc3_energy_1min",
  "hc3_light_5min",
  "hc3_ventilation_5min",
  "sun2_sessions_import",
  "easypark_parking_import",
  "yr_weather_refresh",
  "roborock_sync",
  "parking_vehicle_svv_sync",
];

const EXTRA_COMPARISON_KEYS: Record<string, string[]> = {
  today: ["same-weekday-last-week"],
  week: ["same-week-last-year"],
  month: ["same-month-last-year"],
  year: ["two-years-ago"],
};

const DASHBOARD_CONFIG: Record<DashboardView, { title: string; detail: string; tone: string }> = {
  omsetning: {
    title: "Omsetning",
    detail: "I dag, uke, måned og år med samme datatidspunkt i sammenligningene.",
    tone: "revenue",
  },
  parkering: {
    title: "Parkering",
    detail: "Status, utvikling og snarveier til parkeringstall og kjøretøy.",
    tone: "parking",
  },
  soling: {
    title: "Soling",
    detail: "Dagens soling, uketall og snarveier til timer, senger og produkter.",
    tone: "sun2",
  },
  drift: {
    title: "Drift",
    detail: "Åpning, datakilder, lys, ventilasjon, energi, temperatur og vær.",
    tone: "status",
  },
};

const DASHBOARD_ACTIONS: Record<DashboardView, DashboardAction[]> = {
  omsetning: [
    { label: "Omsetning oversikt", detail: "Ukesutvikling og toppperioder", href: "/omsetning/oversikt", tone: "revenue" },
    { label: "Månedsoversikt", detail: "Dag for dag inneværende måned", href: "/omsetning/manedsoversikt", tone: "revenue" },
    { label: "Periodesammenligning", detail: "Akkumulert dag, uke og måned", href: "/omsetning/sammenligning", tone: "revenue" },
    { label: "Årssammenligning", detail: "Akkumulert omsetning per år", href: "/omsetning/akkumulert", tone: "revenue" },
  ],
  parkering: [
    { label: "Parkering oversikt", detail: "Hovedtall og siste parkeringer", href: "/parkering/oversikt", tone: "parking" },
    { label: "Parkeringer", detail: "Dagsliste og kamerakoblinger", href: "/parkering/parkeringer", tone: "parking" },
    { label: "Kjøretøy", detail: "Biler, eiere og oppslag", href: "/parkering/kjoretoy", tone: "parking" },
    { label: "Område", detail: "Områdevalg og manglende område", href: "/parkering/omrade", tone: "parking" },
  ],
  soling: [
    { label: "Soling oversikt", detail: "Årstall, utvikling og nøkkeltall", href: "/soling/oversikt", tone: "sun2" },
    { label: "Dagslinje", detail: "Timer, bilder og energikort", href: "/soling/dagslinje", tone: "sun2" },
    { label: "Enkeltimer", detail: "Soltimer med bildevalg", href: "/soling/enkeltimer", tone: "sun2" },
    { label: "Produkter", detail: "Produktsalg og kontrollgrunnlag", href: "/soling/produkter", tone: "sun2" },
  ],
  drift: [
    { label: "Datakilder", detail: "Importstatus og kildehelse", href: "/admin/datakilder", tone: "status" },
    { label: "Energi", detail: "Realtime strøm og Elvia-kontroll", href: "/energi/status", tone: "energy" },
    { label: "Ventilasjon", detail: "Temperatur, fukt og viftehendelser", href: "/ventilasjon/dagslogg", tone: "vent" },
    { label: "Lys", detail: "Dagslogg, lux og lysstyring", href: "/lys/dagslogg", tone: "light" },
  ],
};

function stateTag(state: boolean | null) {
  if (state === true) return <Tag color="green">På</Tag>;
  if (state === false) return <Tag color="default">Av</Tag>;
  return <Tag>Ukjent</Tag>;
}

function stateTagWithTooltip(state: boolean | null, tooltip?: string) {
  const tag = stateTag(state);
  if (!tooltip) return tag;
  return (
    <Tooltip title={tooltip}>
      <span className="status-strip-tag-wrap" aria-label={tooltip}>
        {tag}
      </span>
    </Tooltip>
  );
}

function statusIcon(status: string) {
  if (status === "ok") return <CheckCircleOutlined className="status-ok" />;
  if (status === "bad") return <WarningOutlined className="status-bad" />;
  return <ClockCircleOutlined className="status-warn" />;
}

function isCombinedRevenueSource(card: MetricCardData) {
  return card.group === "Omsetning" || card.group === "Soling" || card.group === "Parkering";
}

function isOverviewSupportCard(card: MetricCardData) {
  if (isCombinedRevenueSource(card)) return false;
  return card.title !== "Åpning" && card.title !== "Datakilder";
}

function serviceRank(service: ServiceStatus) {
  const directRank = DATASOURCE_PRIORITY.indexOf(service.jobName || "");
  if (directRank >= 0) return directRank;
  if (service.label.toLowerCase().includes("easypark")) {
    return DATASOURCE_PRIORITY.indexOf("easypark_parking_import");
  }
  return DATASOURCE_PRIORITY.length + 1;
}

function sortedDatasources(services: ServiceStatus[]) {
  return services
    .map((service, index) => ({ service, index }))
    .sort((a, b) => serviceRank(a.service) - serviceRank(b.service) || a.index - b.index)
    .map((row) => row.service);
}

function datasourceCounts(services: ServiceStatus[]) {
  const total = services.length;
  const ok = services.filter((service) => service.status === "ok").length;
  const warn = services.filter((service) => service.status === "warn").length;
  const bad = services.filter((service) => service.status === "bad").length;
  return { total, ok, warn, bad, problem: warn + bad };
}

function shortDateTime(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function datasourceDetail(service: ServiceStatus) {
  const next = shortDateTime(service.nextExpectedAt);
  if (service.jobName === "easypark_parking_import" && next) {
    return `${service.detail} - neste ${next}`;
  }
  return service.detail;
}

function signedNok(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 kr";
  return `${value > 0 ? "+" : "-"}${nok(Math.abs(value))} kr`;
}

function percentDelta(current: number, previous: number) {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) return "";
  const percent = ((current - previous) / previous) * 100;
  if (Math.abs(percent) < 0.5) return "0%";
  return `${percent > 0 ? "+" : "-"}${Math.abs(percent).toFixed(0)}%`;
}

function deltaClass(current: number, previous: number) {
  if (current > previous) return "positive";
  if (current < previous) return "negative";
  return "neutral";
}

function averageAmountText(amount: number, count: number) {
  if (!Number.isFinite(amount) || !Number.isFinite(count) || count <= 0) return "-";
  return `${nok(amount / count)} kr`;
}

function comparisonAmount(value: number | undefined, fallback: number) {
  return Number.isFinite(value) ? Number(value) : fallback;
}

function referenceLabel(fullLabel: string | undefined, fallback: string) {
  const source = (fullLabel || fallback)
    .replace(/^Hele\s+/i, "")
    .replace(/^Sammenlignet med\s+/i, "")
    .replace(/^tilsvarende datatidspunkt\s+/i, "")
    .trim();
  return source ? `${source.charAt(0).toUpperCase()}${source.slice(1)}` : fallback;
}

function latestByLabel(items: LatestItem[], labels: string[]) {
  const normalizedLabels = labels.map((label) => label.toLowerCase());
  return items.filter((item) => normalizedLabels.some((label) => item.label.toLowerCase().includes(label)));
}

function lightStripItems(items: Array<{ label: string; state: boolean | null }>): StripItem[] {
  const glassSpot = items.find((item) => item.label === "Spot foran glassvegg");
  const massageSpot = items.find((item) => item.label === "Spot foran massasje");
  let spotFrontInserted = false;
  const stripItems: StripItem[] = [];

  for (const item of items) {
    if (SPOT_FRONT_LABELS.has(item.label)) {
      if (spotFrontInserted) continue;
      spotFrontInserted = true;
      stripItems.push({
        label: "Spot foran",
        states: [
          { label: "glassvegg", state: glassSpot?.state ?? null, tooltip: "Spot foran glassvegg" },
          { label: "massasje", state: massageSpot?.state ?? null, tooltip: "Spot foran massasje" },
        ],
      });
      continue;
    }
    stripItems.push({ ...item, tooltip: item.label });
  }

  return stripItems;
}

function StatusStrip({ title, items }: { title: string; items: StripItem[] }) {
  return (
    <div className="status-strip">
      <div className="status-strip-head">
        <div className="status-strip-title">{title}</div>
      </div>
      <div className="status-strip-items">
        {items.map((item) => (
          <div className="status-strip-item" key={item.label}>
            <span>{item.label}</span>
            {item.states ? (
              <span className="status-strip-state-group">
                {item.states.map((state) => (
                  <span key={state.label}>{stateTagWithTooltip(state.state, state.tooltip)}</span>
                ))}
              </span>
            ) : (
              stateTagWithTooltip(item.state ?? null, item.tooltip)
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function periodComparisonPath(periodKey: string, comparisonKey: string) {
  return periodKey === "year"
    ? "/omsetning/akkumulert"
    : `/omsetning/sammenligning?period=${encodeURIComponent(periodKey)}&compare=${encodeURIComponent(comparisonKey)}&references=none`;
}

function fullReferenceGap(currentAmount: number, fullAmount: number) {
  const gap = fullAmount - currentAmount;
  if (!Number.isFinite(gap) || Math.abs(gap) < 0.5) return "Lik";
  if (gap > 0) return `Gjenstår ${nok(gap)} kr`;
  return `Over ${nok(Math.abs(gap))} kr`;
}

function fullReferenceGapClass(currentAmount: number, fullAmount: number) {
  const gap = fullAmount - currentAmount;
  if (!Number.isFinite(gap) || Math.abs(gap) < 0.5) return "neutral";
  return gap > 0 ? "negative" : "positive";
}

type PeriodComparisonView = {
  comparison: StatusPeriodComparison;
  comparisonKey: string;
  shortLabel: string;
  path: string;
  fullSol: number;
  fullParking: number;
  fullTotal: number;
};

type RevenueLineKey = "soling" | "parkering";

type RevenuePeriodLine = {
  key: RevenueLineKey;
  label: string;
  tone: string;
  currentAmount: number;
  currentCount?: number;
};

type ActivityDashboardKind = "parking" | "sun2";

type ActivityDashboardConfig = {
  kind: ActivityDashboardKind;
  title: string;
  pluralTitle: string;
  periodPrefix: string;
  lineLabel: string;
  tone: string;
  comparisonPath: string;
  asOf: (period: StatusPeriod) => string;
  count: (period: StatusPeriod | StatusPeriodComparison) => number;
  amount: (period: StatusPeriod | StatusPeriodComparison) => number;
  fullCount: (comparison: StatusPeriodComparison) => number | undefined;
  fullAmount: (comparison: StatusPeriodComparison) => number | undefined;
};

const ACTIVITY_DASHBOARDS: Record<ActivityDashboardKind, ActivityDashboardConfig> = {
  parking: {
    kind: "parking",
    title: "Parkering",
    pluralTitle: "Parkeringer",
    periodPrefix: "Parkeringer",
    lineLabel: "Parkering",
    tone: "parking",
    comparisonPath: "/parkering/sammenligning",
    asOf: (period) => period.parkingAsOfLabel,
    count: (period) => period.parkingCount,
    amount: (period) => period.parking,
    fullCount: (comparison) => comparison.fullParkingCount,
    fullAmount: (comparison) => comparison.fullParking,
  },
  sun2: {
    kind: "sun2",
    title: "Soling",
    pluralTitle: "Solinger",
    periodPrefix: "Solinger",
    lineLabel: "Soling",
    tone: "sun2",
    comparisonPath: "/soling/sammenligning",
    asOf: (period) => period.solAsOfLabel,
    count: (period) => period.solCount,
    amount: (period) => period.sol,
    fullCount: (comparison) => comparison.fullSolCount,
    fullAmount: (comparison) => comparison.fullSol,
  },
};

function buildComparisonViews(period: StatusPeriod): PeriodComparisonView[] {
  const comparisons: StatusPeriodComparison[] = [
    {
      label: period.previousLabel,
      sol: period.previousSol,
      solCount: period.previousSolCount,
      parking: period.previousParking,
      parkingCount: period.previousParkingCount,
      total: period.previousTotal,
      solAsOfLabel: period.previousSolAsOfLabel,
      parkingAsOfLabel: period.previousParkingAsOfLabel,
      fullLabel: period.previousFullLabel,
      fullSol: period.previousFullSol,
      fullSolCount: period.previousFullSolCount,
      fullParking: period.previousFullParking,
      fullParkingCount: period.previousFullParkingCount,
      fullTotal: period.previousFullTotal,
    },
    ...(period.extraComparisons ?? []),
  ];

  return comparisons.map((comparison, index) => {
    const comparisonKey = index === 0 ? "previous" : EXTRA_COMPARISON_KEYS[period.key]?.[index - 1] || `extra-${index - 1}`;
    const fullSol = comparisonAmount(comparison.fullSol, comparison.sol);
    const fullParking = comparisonAmount(comparison.fullParking, comparison.parking);
    return {
      comparison,
      comparisonKey,
      shortLabel: referenceLabel(comparison.fullLabel, comparison.label),
      path: periodComparisonPath(period.key, comparisonKey),
      fullSol,
      fullParking,
      fullTotal: comparisonAmount(comparison.fullTotal, fullSol + fullParking),
    };
  });
}

function comparisonYear(item: PeriodComparisonView) {
  const source = `${item.comparison.label} ${item.comparison.fullLabel ?? ""}`;
  return source.match(/\b(19|20)\d{2}\b/)?.[0];
}

function periodComparisonLabel(periodKey: string, item: PeriodComparisonView) {
  if (periodKey === "today" && item.comparisonKey === "previous") return "I går samme tidspunkt";
  if (periodKey === "today" && item.comparisonKey === "same-weekday-last-week") return "Samme ukedag forrige uke";
  if (periodKey === "week" && item.comparisonKey === "previous") return "Forrige uke samme tidspunkt";
  if (periodKey === "week" && item.comparisonKey === "same-week-last-year") {
    return `Samme uke ${comparisonYear(item) ?? ""}`.trim();
  }
  if (periodKey === "month" && item.comparisonKey === "previous") return "Forrige måned samme tidspunkt";
  if (periodKey === "month" && item.comparisonKey === "same-month-last-year") {
    return `Samme måned ${comparisonYear(item) ?? ""}`.trim();
  }
  if (periodKey === "year" && item.comparisonKey === "previous") return comparisonYear(item) ?? "I fjor";
  if (periodKey === "year" && item.comparisonKey === "two-years-ago") return comparisonYear(item) ?? item.shortLabel;
  return item.shortLabel;
}

function periodTopComparisonLabel(period: StatusPeriod, item: PeriodComparisonView) {
  return `Mot ${periodComparisonLabel(period.key, item).toLowerCase()}`;
}

function periodColumnComparisonLabel(period: StatusPeriod, item: PeriodComparisonView) {
  if (period.key === "today" && item.comparisonKey === "previous") return "Mot i går";
  if (period.key === "today" && item.comparisonKey === "same-weekday-last-week") return "Mot forrige uke";
  if (period.key === "week" && item.comparisonKey === "previous") return "Mot forrige uke";
  if (period.key === "week" && item.comparisonKey === "same-week-last-year") return `Mot samme uke ${comparisonYear(item) ?? ""}`.trim();
  if (period.key === "month" && item.comparisonKey === "previous") return "Mot forrige måned";
  if (period.key === "month" && item.comparisonKey === "same-month-last-year") return `Mot samme måned ${comparisonYear(item) ?? ""}`.trim();
  if (period.key === "year" && item.comparisonKey === "previous") return `Mot ${comparisonYear(item) ?? "i fjor"}`;
  if (period.key === "year" && item.comparisonKey === "two-years-ago") return `Mot ${comparisonYear(item) ?? item.shortLabel}`;
  return `Mot ${item.shortLabel.toLowerCase()}`;
}

function periodFullReferenceLabel(periodKey: string, item: PeriodComparisonView) {
  if (periodKey === "today" && item.comparisonKey === "previous") return "I går totalt";
  if (periodKey === "today" && item.comparisonKey === "same-weekday-last-week") return "Samme ukedag forrige uke totalt";
  return `Hele ${item.shortLabel.toLowerCase()}`;
}

function periodDisplayTitle(period: StatusPeriod) {
  if (period.key === "today") return "Omsetning hittil i dag";
  if (period.key === "week") return "Omsetning hittil denne uken";
  if (period.key === "month") return "Omsetning hittil denne måneden";
  if (period.key === "year") return "Omsetning hittil i år";
  return `Omsetning hittil: ${period.title}`;
}

function periodCurrentColumnLabel(period: StatusPeriod) {
  if (period.key === "today") return "I dag hittil";
  if (period.key === "week") return "Uke hittil";
  if (period.key === "month") return "Måned hittil";
  if (period.key === "year") return "År hittil";
  return "Hittil";
}

function periodDataBasisText(period: StatusPeriod) {
  if (period.solAsOfLabel === period.parkingAsOfLabel) {
    return `Per ${period.solAsOfLabel}`;
  }
  return `Soling ${period.solAsOfLabel} · parkering ${period.parkingAsOfLabel}`;
}

function revenuePeriodLines(period: StatusPeriod): RevenuePeriodLine[] {
  return [
    {
      key: "soling",
      label: "Soling",
      tone: "sun2",
      currentAmount: period.sol,
      currentCount: period.solCount,
    },
    {
      key: "parkering",
      label: "Parkering",
      tone: "parking",
      currentAmount: period.parking,
      currentCount: period.parkingCount,
    },
  ];
}

function comparisonLineAmount(lineKey: RevenueLineKey, comparison: StatusPeriodComparison) {
  if (lineKey === "soling") return comparison.sol;
  if (lineKey === "parkering") return comparison.parking;
  return comparison.total;
}

function DirectionIcon({ currentAmount, referenceAmount }: { currentAmount: number; referenceAmount: number }) {
  const state = deltaClass(currentAmount, referenceAmount);
  const Icon = state === "positive" ? ArrowUpOutlined : state === "negative" ? ArrowDownOutlined : MinusOutlined;
  return (
    <span className={`revenue-period-direction ${state}`}>
      <Icon />
    </span>
  );
}

function DeltaValue({
  currentAmount,
  referenceAmount,
  className,
}: {
  currentAmount: number;
  referenceAmount: number;
  className?: string;
}) {
  const percent = percentDelta(currentAmount, referenceAmount);
  const state = deltaClass(currentAmount, referenceAmount);
  return (
    <div className={`revenue-period-delta ${state}${className ? ` ${className}` : ""}`}>
      <strong>{signedNok(currentAmount - referenceAmount)}</strong>
      {percent ? <span>({percent})</span> : null}
    </div>
  );
}

function PeriodComparisonPill({ period, item }: { period: StatusPeriod; item: PeriodComparisonView }) {
  return (
    <Link className="revenue-period-compare-pill" to={item.path}>
      <span>{periodTopComparisonLabel(period, item)}</span>
      <DeltaValue currentAmount={period.total} referenceAmount={item.comparison.total} />
      <DirectionIcon currentAmount={period.total} referenceAmount={item.comparison.total} />
    </Link>
  );
}

function LogoSunIcon() {
  return (
    <svg className="revenue-logo-sun" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <circle cx="24" cy="24" r="12.5" />
      <path d="M24 4.5v8" />
      <path d="M24 35.5v8" />
      <path d="M4.5 24h8" />
      <path d="M35.5 24h8" />
      <path d="M10.2 10.2l5.6 5.6" />
      <path d="M32.2 32.2l5.6 5.6" />
      <path d="M37.8 10.2l-5.6 5.6" />
      <path d="M15.8 32.2l-5.6 5.6" />
    </svg>
  );
}

function LogoParkingIcon() {
  return (
    <svg className="revenue-logo-parking" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <path d="M16 40V8h13.5C36 8 40 12.2 40 18.2S36 28.5 29.5 28.5H23" />
    </svg>
  );
}

function RevenueLineIcon({ line }: { line: RevenuePeriodLine }) {
  return (
    <span className={`revenue-driver-icon tone-${line.tone}`}>
      {line.key === "soling" ? <LogoSunIcon /> : <LogoParkingIcon />}
    </span>
  );
}

function RevenueDriverRow({
  line,
  comparisons,
}: {
  line: RevenuePeriodLine;
  comparisons: PeriodComparisonView[];
}) {
  return (
    <div className={`revenue-driver-row tone-${line.tone}`}>
      <div className="revenue-driver-line">
        <RevenueLineIcon line={line} />
        <div>
          <strong>{line.label}</strong>
          {Number.isFinite(line.currentCount) ? (
            <em>
              {line.currentCount} stk · {averageAmountText(line.currentAmount, line.currentCount as number)} snitt
            </em>
          ) : null}
        </div>
      </div>
      <div className="revenue-driver-current">
        <strong>{nok(line.currentAmount)} kr</strong>
      </div>
      {comparisons.map((item) => {
        const referenceAmount = comparisonLineAmount(line.key, item.comparison);
        return (
          <div className="revenue-driver-delta-cell" key={item.comparisonKey}>
            <DeltaValue currentAmount={line.currentAmount} referenceAmount={referenceAmount} />
          </div>
        );
      })}
    </div>
  );
}

function RevenuePeriodCard({ period }: { period: StatusPeriod }) {
  const comparisons = buildComparisonViews(period);
  const shownComparisons = comparisons.slice(0, 2);
  const lines = revenuePeriodLines(period);

  return (
    <Card className="status-period-card revenue-period-card">
      <div className="revenue-period-head">
        <div>
          <span className="revenue-period-title">{periodDisplayTitle(period)}</span>
          <em>{periodDataBasisText(period)}</em>
        </div>
        <strong>{nok(period.total)} kr</strong>
      </div>

      <div className={`revenue-period-compare-grid ${shownComparisons.length < 2 ? "single" : ""}`} aria-label="Sammenligning mot samme tidspunkt">
        {shownComparisons.map((item) => (
          <PeriodComparisonPill item={item} key={item.comparisonKey} period={period} />
        ))}
      </div>

      <div className="revenue-drivers" aria-label="Omsetningsfordeling">
        <div className={`revenue-driver-table ${shownComparisons.length < 2 ? "single" : ""}`}>
          <div className="revenue-driver-head">
            <span>Linje</span>
            <span>{periodCurrentColumnLabel(period)}</span>
            {shownComparisons.map((item) => (
              <span key={item.comparisonKey}>{periodColumnComparisonLabel(period, item)}</span>
            ))}
          </div>
          {lines.map((line) => (
            <RevenueDriverRow comparisons={shownComparisons} key={line.key} line={line} />
          ))}
        </div>
      </div>

      <div className="revenue-period-full-card">
        <span className="revenue-period-full-icon">
          <AimOutlined />
        </span>
        <div>
          <div className="revenue-period-full-items">
            {comparisons.map((item) => (
              <Link className="revenue-period-full-item" key={item.comparisonKey} to={item.path}>
                <span>{periodFullReferenceLabel(period.key, item)}: {nok(item.fullTotal)} kr</span>
                <em className={fullReferenceGapClass(period.total, item.fullTotal)}>{fullReferenceGap(period.total, item.fullTotal)}</em>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

function signedCount(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 stk";
  return `${value > 0 ? "+" : "-"}${Math.abs(Math.round(value))} stk`;
}

function averageKrPerCount(amount: number, count: number) {
  if (!Number.isFinite(amount) || !Number.isFinite(count) || count <= 0) return "-";
  return `${nok(amount / count)} kr`;
}

function activityPeriodDisplayTitle(period: StatusPeriod, config: ActivityDashboardConfig) {
  if (period.key === "today") return `${config.periodPrefix} hittil i dag`;
  if (period.key === "week") return `${config.periodPrefix} hittil denne uken`;
  if (period.key === "month") return `${config.periodPrefix} hittil denne måneden`;
  if (period.key === "year") return `${config.periodPrefix} hittil i år`;
  return `${config.periodPrefix} hittil: ${period.title}`;
}

function activityComparisonPath(config: ActivityDashboardConfig, periodKey: string, comparisonKey: string) {
  if (periodKey === "year") return config.comparisonPath;
  return `/status/sammenligning?period=${encodeURIComponent(periodKey)}&compare=${encodeURIComponent(comparisonKey)}&metric=count`;
}

function activityFullReferenceGap(currentCount: number, fullCount: number) {
  const gap = fullCount - currentCount;
  if (!Number.isFinite(gap) || gap === 0) return "Lik";
  if (gap > 0) return `Gjenstår ${Math.round(gap)} stk`;
  return `Over ${Math.abs(Math.round(gap))} stk`;
}

function CountDeltaValue({
  current,
  reference,
  className,
}: {
  current: number;
  reference: number;
  className?: string;
}) {
  const percent = percentDelta(current, reference);
  const state = deltaClass(current, reference);
  return (
    <div className={`revenue-period-delta ${state}${className ? ` ${className}` : ""}`}>
      <strong>{signedCount(current - reference)}</strong>
      {percent ? <span>({percent})</span> : null}
    </div>
  );
}

function ActivityDriverRow({
  config,
  comparisons,
  count,
  amount,
}: {
  config: ActivityDashboardConfig;
  comparisons: PeriodComparisonView[];
  count: number;
  amount: number;
}) {
  return (
    <div className={`revenue-driver-row tone-${config.tone}`}>
      <div className="revenue-driver-line">
        <span className={`revenue-driver-icon tone-${config.tone}`}>
          {config.kind === "sun2" ? <LogoSunIcon /> : <LogoParkingIcon />}
        </span>
        <div>
          <strong>{config.lineLabel}</strong>
          <em>
            {nok(amount)} kr · {averageKrPerCount(amount, count)} snitt
          </em>
        </div>
      </div>
      <div className="revenue-driver-current">
        <strong>{Math.round(count)} stk</strong>
      </div>
      {comparisons.map((item) => (
        <div className="revenue-driver-delta-cell" key={item.comparisonKey}>
          <CountDeltaValue current={count} reference={config.count(item.comparison)} />
        </div>
      ))}
    </div>
  );
}

function ActivityPeriodCard({ period, config }: { period: StatusPeriod; config: ActivityDashboardConfig }) {
  const comparisons = buildComparisonViews(period).slice(0, 2).map((item) => ({
    ...item,
    path: activityComparisonPath(config, period.key, item.comparisonKey),
  }));
  const count = config.count(period);
  const amount = config.amount(period);

  return (
    <Card className={`status-period-card revenue-period-card activity-period-card tone-${config.tone}`}>
      <div className="revenue-period-head">
        <div>
          <span className="revenue-period-title">{activityPeriodDisplayTitle(period, config)}</span>
          <em>Per {config.asOf(period)}</em>
        </div>
        <strong>
          {Math.round(count)}
          <span>stk</span>
        </strong>
      </div>

      <div className={`revenue-period-compare-grid ${comparisons.length < 2 ? "single" : ""}`} aria-label="Antall sammenlignet med referanser">
        {comparisons.map((item) => {
          const referenceCount = config.count(item.comparison);
          return (
            <Link className="revenue-period-compare-pill" to={item.path} key={item.comparisonKey}>
              <span>{periodTopComparisonLabel(period, item)}</span>
              <CountDeltaValue current={count} reference={referenceCount} />
              <DirectionIcon currentAmount={count} referenceAmount={referenceCount} />
            </Link>
          );
        })}
      </div>

      <div className="revenue-drivers" aria-label={`${config.title} fordeling`}>
        <div className={`revenue-driver-table ${comparisons.length < 2 ? "single" : ""}`}>
          <div className="revenue-driver-head">
            <span>Linje</span>
            <span>{periodCurrentColumnLabel(period)}</span>
            {comparisons.map((item) => (
              <span key={item.comparisonKey}>{periodColumnComparisonLabel(period, item)}</span>
            ))}
          </div>
          <ActivityDriverRow amount={amount} comparisons={comparisons} config={config} count={count} />
        </div>
      </div>

      <div className="revenue-period-full-card">
        <span className="revenue-period-full-icon">
          <AimOutlined />
        </span>
        <div>
          <div className="revenue-period-full-items">
            {comparisons.map((item) => {
              const currentCount = count;
              const fullCount = comparisonAmount(config.fullCount(item.comparison), config.count(item.comparison));
              const fullAmount = comparisonAmount(config.fullAmount(item.comparison), config.amount(item.comparison));
              return (
                <Link className="revenue-period-full-item" key={item.comparisonKey} to={item.path}>
                  <span>
                    {periodFullReferenceLabel(period.key, item)}: {Math.round(fullCount)} stk / {nok(fullAmount)} kr
                  </span>
                  <em className={fullReferenceGapClass(currentCount, fullCount)}>
                    {activityFullReferenceGap(currentCount, fullCount)}
                  </em>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </Card>
  );
}

function StatusSummary({
  label,
  detail,
  updatedAt,
  sourceCounts,
}: {
  label: string;
  detail: string;
  updatedAt: string;
  sourceCounts: ReturnType<typeof datasourceCounts>;
}) {
  const sourceState = sourceCounts.bad ? "bad" : sourceCounts.warn ? "warn" : "ok";
  return (
    <div className="status-summary">
      <div className="status-summary-state">
        <span>Status akkurat nå</span>
        <strong>{label}</strong>
        <em>{detail}</em>
      </div>
      <div className="status-summary-meta">
        <Link className={`status-summary-source-pill ${sourceState}`} to="/admin/datakilder">
          <span>Datakilder</span>
          <strong>
            {sourceCounts.ok}/{sourceCounts.total} OK
          </strong>
          <em>{sourceCounts.problem ? `${sourceCounts.problem} må sjekkes` : "Alt ferskt"}</em>
        </Link>
        <div className="status-summary-updated">
          <span>Sist oppdatert</span>
          <strong>{updatedAt}</strong>
        </div>
      </div>
    </div>
  );
}

function OverviewInfoPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="status-info-card" title={title}>
      {children}
    </Card>
  );
}

function StatusSection({
  title,
  detail,
  children,
  hideHeader = false,
}: {
  title: string;
  detail?: string;
  children: ReactNode;
  hideHeader?: boolean;
}) {
  return (
    <section className={`status-section${hideHeader ? " status-section--no-head" : ""}`} aria-label={hideHeader ? title : undefined}>
      {hideHeader ? null : (
        <div className="status-section-head">
          <span>{title}</span>
          {detail ? <em>{detail}</em> : null}
        </div>
      )}
      {children}
    </section>
  );
}

function LatestEventList({
  items,
  itemTitle,
}: {
  items: Array<{ href?: string; label: string; detail?: string; value: string }>;
  itemTitle: (item: { href?: string; label: string }) => ReactNode;
}) {
  return (
    <List
      className="status-event-list"
      dataSource={items}
      locale={{ emptyText: "Ingen hendelser å vise" }}
      renderItem={(item) => (
        <List.Item>
          <List.Item.Meta title={itemTitle(item)} description={item.detail || ""} />
          <span className="list-value">{item.value}</span>
        </List.Item>
      )}
    />
  );
}

function DatasourceList({ services }: { services: ServiceStatus[] }) {
  return (
    <List
      className="status-source-list"
      dataSource={services}
      locale={{ emptyText: "Ingen datakilder å vise" }}
      renderItem={(item) => (
        <List.Item>
          <Space>
            {statusIcon(item.status)}
            {item.sourceNo ? <span className="status-source-number">#{item.sourceNo}</span> : null}
            <span>{item.label}</span>
          </Space>
          <Typography.Text type="secondary">{datasourceDetail(item)}</Typography.Text>
        </List.Item>
      )}
    />
  );
}

function SupportMetricStrip({ cards }: { cards: MetricCardData[] }) {
  if (!cards.length) return <div className="empty-state">Ingen nøkkeltall å vise.</div>;
  return (
    <div className="status-support-strip">
      {cards.map((card) => {
        const content = (
          <div className={`status-support-item tone-${card.tone ?? "status"}`}>
            <div className="status-support-head">
              <span>{card.title}</span>
              <em>{card.group}</em>
            </div>
            <strong>
              {card.value}
              {card.unit ? <span>{card.unit}</span> : null}
            </strong>
            <small>{card.detail || "\u00a0"}</small>
          </div>
        );
        const internalPath = appPath(card.href);
        if (internalPath) {
          return (
            <Link className="status-support-link" to={internalPath} key={`${card.group}-${card.title}`}>
              {content}
            </Link>
          );
        }
        if (card.href) {
          return (
            <a className="status-support-link" href={card.href} key={`${card.group}-${card.title}`}>
              {content}
            </a>
          );
        }
        return (
          <div className="status-support-link" key={`${card.group}-${card.title}`}>
            {content}
          </div>
        );
      })}
    </div>
  );
}

function DashboardActionGrid({ view }: { view: DashboardView }) {
  return (
    <div className="dashboard-action-grid">
      {DASHBOARD_ACTIONS[view].map((action) => (
        <Link className={`dashboard-action tone-${action.tone}`} to={action.href} key={action.href}>
          <span>{action.label}</span>
          <small>{action.detail}</small>
          <ArrowRightOutlined className="dashboard-action-icon" />
        </Link>
      ))}
    </div>
  );
}

export default function OverviewPage({ dashboard = "omsetning" }: { dashboard?: DashboardView }) {
  const { data, loading, error } = useApiQuery(queryKeys.overview(), fetchOverview, {
    refetchInterval: 60_000,
  });

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const overview = data;
  const view = DASHBOARD_CONFIG[dashboard] ? dashboard : "omsetning";
  const supportCards = overview.cards.filter(isOverviewSupportCard);
  const overviewServices = sortedDatasources(overview.services);
  const overviewSourceCounts = datasourceCounts(overviewServices);
  const updatedAt = new Date(overview.generatedAt).toLocaleString("nb-NO");

  function itemTitle(item: { href?: string; label: string }) {
    const internalPath = appPath(item.href);
    if (internalPath) return <Link to={internalPath}>{item.label}</Link>;
    if (item.href) return <a href={item.href}>{item.label}</a>;
    return item.label;
  }

  function renderRevenueDashboard() {
    return (
      <StatusSection title="Omsetning" hideHeader>
        <div className="status-period-grid">
          {overview.statusPeriods.map((period) => (
            <RevenuePeriodCard period={period} key={period.key} />
          ))}
        </div>
      </StatusSection>
    );
  }

  function renderActivityDashboard(kind: ActivityDashboardKind) {
    const config = ACTIVITY_DASHBOARDS[kind];
    const latestLabels = kind === "parking" ? ["parkering"] : ["soling"];

    return (
      <>
        <StatusSection title={config.title} hideHeader>
          <div className="status-period-grid">
            {overview.statusPeriods.map((period) => (
              <ActivityPeriodCard period={period} config={config} key={`${config.kind}-${period.key}`} />
            ))}
          </div>
        </StatusSection>
        <div className="status-info-grid">
          <OverviewInfoPanel title={`Siste ${config.title.toLowerCase()}`}>
            <LatestEventList items={latestByLabel(overview.latestItems, latestLabels)} itemTitle={itemTitle} />
          </OverviewInfoPanel>
          <OverviewInfoPanel title="Arbeidsflater">
            <DashboardActionGrid view={kind === "parking" ? "parkering" : "soling"} />
          </OverviewInfoPanel>
        </div>
      </>
    );
  }

  function renderParkingDashboard() {
    return renderActivityDashboard("parking");
  }

  function renderSunDashboard() {
    return renderActivityDashboard("sun2");
  }

  function renderOperationsDashboard() {
    return (
      <>
        <Card className="status-command-card">
          <StatusSummary
            label={overview.operatingWindow.label}
            detail={overview.operatingWindow.detail}
            sourceCounts={overviewSourceCounts}
            updatedAt={updatedAt}
          />
          <div className="status-strip-stack">
            <StatusStrip title="Lys" items={lightStripItems(overview.lightItems)} />
            <StatusStrip title="Ventilasjon" items={overview.fanItems} />
          </div>
        </Card>
        <StatusSection title="Nøkkeltall" detail="Energi, temperatur og vær akkurat nå">
          <SupportMetricStrip cards={supportCards} />
        </StatusSection>
        <div className="status-info-grid">
          <OverviewInfoPanel title="Siste driftshendelser">
            <LatestEventList items={latestByLabel(overview.latestItems, ["energi", "temp"])} itemTitle={itemTitle} />
          </OverviewInfoPanel>
          <OverviewInfoPanel title="Status datakilder">
            <DatasourceList services={overviewServices} />
          </OverviewInfoPanel>
        </div>
        <StatusSection title="Arbeidsflater">
          <DashboardActionGrid view="drift" />
        </StatusSection>
      </>
    );
  }

  return (
    <Space
      direction="vertical"
      size={16}
      className={`page-stack status-page status-overview-page status-dashboard-page dashboard-${view} tone-${DASHBOARD_CONFIG[view].tone}`}
    >
      {view === "omsetning" ? renderRevenueDashboard() : null}
      {view === "parkering" ? renderParkingDashboard() : null}
      {view === "soling" ? renderSunDashboard() : null}
      {view === "drift" ? renderOperationsDashboard() : null}
    </Space>
  );
}
