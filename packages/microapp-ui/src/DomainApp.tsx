import { useMemo } from "react";
import { domainApi } from "./api";
import { CountDashboardSpecial } from "./components/CountDashboardSpecial";
import { CountComparisonSpecial } from "./components/CountComparisonSpecial";
import { DetailRoute } from "./components/DetailPages";
import { Layout } from "./components/Layout";
import { ModuleContent } from "./components/ModuleContent";
import { YearComparisonSpecial } from "./components/YearComparisonSpecial";
import { ErrorState, Loading } from "./components/PageState";
import { useApi } from "./hooks";
import { findNavigationItem } from "./navigation";
import { AppRouter, useAppLocation } from "./router";
import type { DomainUiConfig, ModuleResponse, NavigationItem, OperationsOverviewResponse, RoborockRobotSummary } from "./types";

function stateLabel(state: boolean | null) {
  if (state === true) return "P\u00e5";
  if (state === false) return "Av";
  return "Ukjent";
}

function operationsModule(data: OperationsOverviewResponse): ModuleResponse {
  const cards = data.cards.filter((card) => ["Drift", "Energi", "Temperatur", "V\u00e6r"].includes(card.group || ""));
  return {
    title: "Driftsoversikt",
    subtitle: `${data.operatingWindow.label} \u00b7 ${data.operatingWindow.detail} \u00b7 Oppdatert ${new Date(data.generatedAt).toLocaleString("nb-NO")}`,
    cards,
    tables: [
      {
        title: "Lys",
        columns: ["funksjon", "status", "detalj"],
        rows: data.lightItems.map((item) => ({ funksjon: item.label, status: stateLabel(item.state), detalj: item.tooltip || "" })),
      },
      {
        title: "Viftestyring",
        columns: ["funksjon", "status", "kilde", "sist kontrollert"],
        rows: data.fanItems.map((item) => ({
          funksjon: item.label,
          status: stateLabel(item.state),
          kilde: item.statusSource || item.tooltip || "",
          "sist kontrollert": item.checkedAt || "",
        })),
      },
      {
        title: "Siste driftshendelser",
        columns: ["hendelse", "verdi", "detalj"],
        rows: data.latestItems.filter((item) => /energi|temp/i.test(item.label)).map((item) => ({ hendelse: item.label, verdi: item.value, detalj: item.detail || "" })),
      },
      {
        title: "Status datakilder",
        columns: ["nr", "datakilde", "status", "sist lest", "neste kj\u00f8ring"],
        rows: data.services.map((service) => ({
          nr: service.sourceNo ?? "",
          datakilde: service.label,
          status: service.status,
          "sist lest": service.detail || service.lastSuccessAt || "",
          "neste kj\u00f8ring": service.nextExpectedAt || "",
        })),
      },
    ],
  };
}

function withRobotNavigation(config: DomainUiConfig, robots: RoborockRobotSummary[] | undefined): DomainUiConfig {
  if (config.appId !== "operations" || !robots?.length) return config;
  const navigation = config.navigation.map((group) => {
    const overview = group.items.find((candidate) => candidate.module === "renhold" && candidate.view === "oversikt");
    if (!overview) return group;
    const robotItems: NavigationItem[] = robots.map((robot) => {
      const encodedDuid = encodeURIComponent(robot.duid);
      return {
        to: `/renhold/robot/${encodedDuid}`,
        label: robot.name,
        icon: "robot",
        title: robot.name,
        description: `Status, telemetri og historikk for ${robot.name}.`,
        module: "renhold",
        view: "robot",
        corePath: `/renhold/robot/${encodedDuid}`,
      };
    });
    return { ...group, items: [overview, ...robotItems] };
  });
  return { ...config, navigation };
}

function RoutedDomainApp({ config }: { config: DomainUiConfig }) {
  const { pathname, search } = useAppLocation();
  const baseItem = findNavigationItem(config, pathname);
  const isCountDashboard = baseItem.module === "status" && baseItem.view === "soling";
  const isCountComparison = baseItem.module === "status" && baseItem.view === "soling-comparison";
  const isYearComparison = config.appId === "sun" && baseItem.module === "soling" && baseItem.view === "sammenligning";
  const isOperationsOverview = baseItem.module === "status" && baseItem.view === "drift";
  const isSelfLoadingOperationsView = config.appId === "operations" && (
    baseItem.module === "dorer" || baseItem.module === "pullerter"
  );
  const isDetailRoute = (
    (config.appId === "maintenance" && /^\/besok\/\d+$/.test(pathname))
    || (config.appId === "system" && /^\/(?:datakilder|build)\/[^/]+$/.test(pathname))
    || (config.appId === "sun" && /^\/oppgjor\/\d+$/.test(pathname))
  );
  const result = useApi(
    async () => isDetailRoute || isCountDashboard || isCountComparison || isYearComparison || isSelfLoadingOperationsView
      ? { title: "", subtitle: "", cards: [], tables: [] }
      : isOperationsOverview
        ? operationsModule(await domainApi.operationsOverview())
        : domainApi.module(baseItem.module, baseItem.view, new URLSearchParams(search)),
    `module-${baseItem.module}-${baseItem.view}-${search}`,
  );
  const appConfig = useApi(domainApi.config, "app-config");
  const effectiveConfig = useMemo(
    () => withRobotNavigation(config, result.data?.roborock?.robots),
    [config, result.data?.roborock?.robots],
  );
  const item = findNavigationItem(effectiveConfig, pathname);
  const coreUrl = appConfig.data?.fibaro10AppUrl || "https://fibaro10.lilletorget.net";
  return <Layout config={effectiveConfig}>{result.loading || appConfig.loading
    ? <Loading />
    : result.error || !result.data
      ? <ErrorState error={result.error} onRetry={result.reload} />
      : isDetailRoute
        ? <DetailRoute config={config} pathname={pathname} coreUrl={coreUrl} />
        : isCountDashboard
          ? <CountDashboardSpecial domain="sun" />
          : isCountComparison
            ? <CountComparisonSpecial domain="sun" />
          : isYearComparison
            ? <YearComparisonSpecial domain="soling" />
        : <ModuleContent data={result.data} config={config} reload={result.reload} coreUrl={coreUrl} module={item.module} view={item.view} />}</Layout>;
}

export function DomainApp({ config }: { config: DomainUiConfig }) {
  return <AppRouter><RoutedDomainApp config={config} /></AppRouter>;
}
