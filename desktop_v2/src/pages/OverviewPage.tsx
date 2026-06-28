import { ArrowRightOutlined, CheckCircleOutlined, ClockCircleOutlined, WarningOutlined } from "@ant-design/icons";
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
  week: ["two-weeks-ago"],
  month: ["two-months-ago"],
};

const DASHBOARD_CONFIG: Record<DashboardView, { title: string; detail: string; tone: string }> = {
  omsetning: {
    title: "Omsetning",
    detail: "I dag, uke og måned med samme datatidspunkt i sammenligningene.",
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

function sharePercentText(amount: number, total: number) {
  if (!Number.isFinite(amount) || !Number.isFinite(total) || total <= 0) return "-";
  return `${Math.round((amount / total) * 100)}%`;
}

function comparisonAmount(value: number | undefined, fallback: number) {
  return Number.isFinite(value) ? Number(value) : fallback;
}

function fullReferenceText(currentTotal: number, fullTotal: number) {
  const gap = fullTotal - currentTotal;
  if (!Number.isFinite(gap) || Math.abs(gap) < 0.5) return "Lik full referanse";
  if (gap > 0) return `Mangler ${nok(gap)} kr`;
  return `Over ${nok(Math.abs(gap))} kr`;
}

function fullReferenceClass(currentTotal: number, fullTotal: number) {
  const gap = fullTotal - currentTotal;
  if (!Number.isFinite(gap) || Math.abs(gap) < 0.5) return "neutral";
  return gap > 0 ? "negative" : "positive";
}

function referenceLabel(fullLabel: string | undefined, fallback: string) {
  const source = (fullLabel || fallback)
    .replace(/^Hele\s+/i, "")
    .replace(/^Sammenlignet med\s+/i, "")
    .replace(/^tilsvarende datatidspunkt\s+/i, "")
    .trim();
  return source ? `${source.charAt(0).toUpperCase()}${source.slice(1)}` : fallback;
}

function comparisonTimeText(comparison: StatusPeriodComparison) {
  if (comparison.solAsOfLabel === comparison.parkingAsOfLabel) return comparison.solAsOfLabel;
  return `sol ${comparison.solAsOfLabel} / park ${comparison.parkingAsOfLabel}`;
}

function groupCards(cards: MetricCardData[], group: string) {
  return cards.filter((card) => card.group === group);
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

function ComparisonRow({
  comparison,
  currentTotal,
  periodKey,
  comparisonKey,
}: {
  comparison: StatusPeriodComparison;
  currentTotal: number;
  periodKey: string;
  comparisonKey: string;
}) {
  const sameTimeDelta = currentTotal - comparison.total;
  const percent = percentDelta(currentTotal, comparison.total);
  const fullSol = comparisonAmount(comparison.fullSol, comparison.sol);
  const fullParking = comparisonAmount(comparison.fullParking, comparison.parking);
  const fullTotal = comparisonAmount(comparison.fullTotal, fullSol + fullParking);
  const fullLabel = comparison.fullLabel || "Hele referansen";
  const simpleLabel = referenceLabel(comparison.fullLabel, comparison.label);
  const sameTimeClass = deltaClass(currentTotal, comparison.total);
  const fullClass = fullReferenceClass(currentTotal, fullTotal);

  return (
    <Link
      className="status-period-comparison-row"
      title="Vis tidslinje for sammenligningen"
      to={`/omsetning/sammenligning?period=${encodeURIComponent(periodKey)}&compare=${encodeURIComponent(comparisonKey)}`}
    >
      <div className="status-period-comparison-title-row">
        <strong>{simpleLabel}</strong>
        <span>til {comparisonTimeText(comparison)}</span>
      </div>
      <div className="status-period-comparison-lines">
        <div className="status-period-comparison-line">
          <span>Samme tidspunkt</span>
          <strong>{nok(comparison.total)} kr</strong>
          <em className={sameTimeClass}>
            {signedNok(sameTimeDelta)}
            {percent ? ` (${percent})` : ""}
          </em>
        </div>
        <div className="status-period-comparison-line">
          <span>{fullLabel}</span>
          <strong>{nok(fullTotal)} kr</strong>
          <em className={fullClass}>{fullReferenceText(currentTotal, fullTotal)}</em>
        </div>
      </div>
    </Link>
  );
}

function RevenuePeriodCard({ period }: { period: StatusPeriod }) {
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
  const solShare = sharePercentText(period.sol, period.total);
  const parkingShare = sharePercentText(period.parking, period.total);

  return (
    <Card className="status-period-card">
      <div className="status-period-head">
        <div>
          <span>{period.title}</span>
          <em>
            Sol {period.solAsOfLabel} · parkering {period.parkingAsOfLabel}
          </em>
        </div>
        <strong>{nok(period.total)} kr</strong>
      </div>
      <div className="status-period-rows">
        <div className="status-period-row tone-sun2">
          <span>Soling</span>
          <strong>{nok(period.sol)} kr</strong>
          <em>{period.solCount} stk</em>
        </div>
        <div className="status-period-row tone-parking">
          <span>Parkering</span>
          <strong>{nok(period.parking)} kr</strong>
          <em>{period.parkingCount} stk</em>
        </div>
      </div>
      <div className="status-period-facts" aria-label={`Målepunkter for ${period.title}`}>
        <span>
          Snitt: sol {averageAmountText(period.sol, period.solCount)} / park {averageAmountText(period.parking, period.parkingCount)}
        </span>
        <span>
          Fordeling: sol {solShare} / park {parkingShare}
        </span>
      </div>
      <div className="status-period-comparisons">
        <div className="status-period-comparisons-title">Sammenligning</div>
        {comparisons.map((comparison, index) => (
          <ComparisonRow
            comparison={comparison}
            comparisonKey={index === 0 ? "previous" : EXTRA_COMPARISON_KEYS[period.key]?.[index - 1] || `extra-${index - 1}`}
            currentTotal={period.total}
            key={comparison.label}
            periodKey={period.key}
          />
        ))}
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

function StatusSection({ title, detail, children }: { title: string; detail?: string; children: ReactNode }) {
  return (
    <section className="status-section">
      <div className="status-section-head">
        <span>{title}</span>
        {detail ? <em>{detail}</em> : null}
      </div>
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
          <Typography.Text type="secondary">{item.detail}</Typography.Text>
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

function DashboardHeader({ view, updatedAt }: { view: DashboardView; updatedAt: string }) {
  const config = DASHBOARD_CONFIG[view];
  return (
    <section className={`dashboard-view-head tone-${config.tone}`}>
      <div>
        <span>Dashboard</span>
        <strong>{config.title}</strong>
      </div>
      <p>{config.detail}</p>
      <em>Sist oppdatert {updatedAt}</em>
    </section>
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
  const revenueCards = overview.cards.filter(isCombinedRevenueSource);
  const parkingCards = groupCards(overview.cards, "Parkering");
  const sunCards = groupCards(overview.cards, "Soling");
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
      <>
        <StatusSection title="Omsetning" detail="I dag, uke og måned med korrekt datatidspunkt">
          <div className="status-period-grid">
            {overview.statusPeriods.map((period) => (
              <RevenuePeriodCard period={period} key={period.key} />
            ))}
          </div>
        </StatusSection>
        <StatusSection title="Fordeling" detail="Omsetning, soling og parkering fra samme grunnlag">
          <SupportMetricStrip cards={revenueCards} />
        </StatusSection>
      </>
    );
  }

  function renderParkingDashboard() {
    return (
      <>
        <StatusSection title="Parkering" detail="Dagens parkering og sammenligning mot forrige uke">
          <SupportMetricStrip cards={parkingCards} />
        </StatusSection>
        <div className="status-info-grid">
          <OverviewInfoPanel title="Siste parkering">
            <LatestEventList items={latestByLabel(overview.latestItems, ["parkering"])} itemTitle={itemTitle} />
          </OverviewInfoPanel>
          <OverviewInfoPanel title="Arbeidsflater">
            <DashboardActionGrid view="parkering" />
          </OverviewInfoPanel>
        </div>
      </>
    );
  }

  function renderSunDashboard() {
    return (
      <>
        <StatusSection title="Soling" detail="Dagens soling og uketall fra Sun2">
          <SupportMetricStrip cards={sunCards} />
        </StatusSection>
        <div className="status-info-grid">
          <OverviewInfoPanel title="Siste soling">
            <LatestEventList items={latestByLabel(overview.latestItems, ["soling"])} itemTitle={itemTitle} />
          </OverviewInfoPanel>
          <OverviewInfoPanel title="Arbeidsflater">
            <DashboardActionGrid view="soling" />
          </OverviewInfoPanel>
        </div>
      </>
    );
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
      <DashboardHeader view={view} updatedAt={updatedAt} />
      {view === "omsetning" ? renderRevenueDashboard() : null}
      {view === "parkering" ? renderParkingDashboard() : null}
      {view === "soling" ? renderSunDashboard() : null}
      {view === "drift" ? renderOperationsDashboard() : null}
    </Space>
  );
}
