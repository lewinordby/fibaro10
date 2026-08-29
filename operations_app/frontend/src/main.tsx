import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import {
  DomainApp,
  Loading,
  ThemeProvider,
  getDomainConfig,
  type DomainAppExtensions,
  type DomainUiConfig,
  type ModuleResponse,
  type NavigationItem,
} from "@lilletorget/microapp-ui";
import { domainApi } from "@lilletorget/microapp-ui/api";
import "@lilletorget/mosaic-theme/font.css";
import type { RoborockModuleData } from "./roborock-types";
import type { ControlSettings, OperationsDashboardResponse } from "./types";
import "./style.css";

const RoborockSpecial = lazy(() => import("./components/RoborockSpecial").then((module) => ({ default: module.RoborockSpecial })));
const BollardsSpecial = lazy(() => import("./components/BollardsSpecial").then((module) => ({ default: module.BollardsSpecial })));
const DoorsSpecial = lazy(() => import("./components/DoorsSpecial").then((module) => ({ default: module.DoorsSpecial })));
const VentilationSpecial = lazy(() => import("./components/OperationsSpecial").then((module) => ({ default: module.VentilationSpecial })));
const ControlSettingsSpecial = lazy(() => import("./components/OperationsSpecial").then((module) => ({ default: module.ControlSettingsSpecial })));
const OperationsDashboard = lazy(() => import("./components/OperationsDashboard").then((module) => ({ default: module.OperationsDashboard })));

const doorViews = new Set([
  "oversikt", "andre", "solrom", "hendelseslogikk", "soltimer", "romkontroll-ny2",
  "oversikt-ny", "romkontroll", "romkontroll-ny", "solrom-ny",
  "solrom-dagskontroll", "solrom2-oversikt", "solrom2-dagskontroll",
  "solrom2-avvik", "dorer2-oversikt", "dorer2-bygg", "alarm", "avvik",
  "radata",
]);

function operationsModule(data: OperationsDashboardResponse): ModuleResponse {
  return { title: "Driftsoversikt", subtitle: "Samlet situasjonsbilde for bygget", cards: [], tables: [], operationsDashboard: data };
}

function withRobotNavigation(config: DomainUiConfig, data: ModuleResponse | null | undefined): DomainUiConfig {
  const robots = (data?.roborock as RoborockModuleData | null | undefined)?.robots;
  if (!robots?.length) return config;
  const navigation = config.navigation.map((group) => {
    const overview = group.items.find((candidate) => candidate.module === "renhold" && candidate.view === "oversikt");
    if (!overview) return group;
    const report: NavigationItem = {
      to: "/renhold/rapport",
      label: "Nattrapport",
      icon: "calendar",
      title: "Nattrapport",
      description: "Maskinell døgnrapport for rengjøring, batteri, vann og driftsklar status.",
      module: "renhold",
      view: "rapport",
      corePath: "/renhold/rapport",
    };
    const water: NavigationItem = {
      to: "/renhold/vann",
      label: "Vann",
      icon: "energy",
      title: "Vann og moppevask",
      description: "Vannstatus, moppevaskintervall, faktisk vaskebelastning og hendelser.",
      module: "renhold",
      view: "vann",
      corePath: "/renhold/vann",
    };
    const refill: NavigationItem = {
      to: "/renhold/pafylling",
      label: "Påfylling",
      icon: "refresh",
      title: "Påfyllingslogg",
      description: "Ukelogg for når renholdspersonalet fyller rentvannstanken i robotdokkene.",
      module: "renhold",
      view: "pafylling",
      corePath: "/renhold/pafylling",
    };
    const robotItems: NavigationItem[] = robots.map((robot) => {
      if (robot.integration_status === "pending") return {
        to: "/renhold/dreame",
        label: robot.name,
        icon: "robot",
        title: robot.name,
        description: "Oppsett og status for Dreame-integrasjonen.",
        module: "renhold",
        view: "dreame",
        corePath: "/renhold/dreame",
      };
      const encodedDuid = encodeURIComponent(robot.duid);
      return {
        to: `/renhold/robot/${encodedDuid}`,
        label: robot.name,
        icon: "robot",
        title: robot.name,
        description: `Status, telemetri og historikk for ${robot.name} (${robot.provider_label || "Roborock"}).`,
        module: "renhold",
        view: "robot",
        corePath: `/renhold/robot/${encodedDuid}`,
      };
    });
    return { ...group, items: [overview, report, water, refill, ...robotItems] };
  });
  return { ...config, navigation };
}

const operationsExtensions: DomainAppExtensions = {
  enhanceConfig: withRobotNavigation,
  skipModuleLoad: ({ item }) => item.module === "dorer" || item.module === "pullerter",
  loadModule: ({ item }) => item.module === "status" && item.view === "drift"
    ? domainApi.get<OperationsDashboardResponse>("/api/operations/overview").then(operationsModule)
    : null,
  renderModule: ({ data, module, view, reload }) => {
    const roborock = data.roborock as RoborockModuleData | null | undefined;
    const operationsDashboard = data.operationsDashboard as OperationsDashboardResponse | null | undefined;
    if (module === "status" && view === "drift" && operationsDashboard) return { content: <Suspense fallback={<Loading />}><OperationsDashboard data={operationsDashboard} /></Suspense>, hideFilters: true, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "renhold" && roborock) return { content: <Suspense fallback={<Loading />}><RoborockSpecial data={roborock} /></Suspense>, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "pullerter") return { content: <Suspense fallback={<Loading />}><BollardsSpecial /></Suspense>, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "dorer" && doorViews.has(view)) return { content: <Suspense fallback={<Loading />}><DoorsSpecial view={view} /></Suspense>, hideFilters: true, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "ventilasjon" && data.ventilation) return { content: <Suspense fallback={<Loading />}><VentilationSpecial data={data} view={view} reload={reload} /></Suspense>, hideCharts: true, hideTables: view === "innstillinger" };
    if (data.controlSettings) return { content: <Suspense fallback={<Loading />}><ControlSettingsSpecial settings={data.controlSettings as ControlSettings} reload={reload} /></Suspense>, hideTables: true };
    return null;
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode><ThemeProvider><DomainApp config={getDomainConfig("operations")} extensions={operationsExtensions} /></ThemeProvider></StrictMode>,
);
