import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import {
  DomainApp,
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
import type { ControlSettings, OperationsOverviewResponse, VentilationData } from "./types";
import "./style.css";

const RoborockSpecial = lazy(() => import("./components/RoborockSpecial").then((module) => ({ default: module.RoborockSpecial })));
const BollardsSpecial = lazy(() => import("./components/BollardsSpecial").then((module) => ({ default: module.BollardsSpecial })));
const DoorsSpecial = lazy(() => import("./components/DoorsSpecial").then((module) => ({ default: module.DoorsSpecial })));
const VentilationSpecial = lazy(() => import("./components/OperationsSpecial").then((module) => ({ default: module.VentilationSpecial })));
const ControlSettingsSpecial = lazy(() => import("./components/OperationsSpecial").then((module) => ({ default: module.ControlSettingsSpecial })));

const doorViews = new Set([
  "oversikt", "andre", "solrom", "soltimer", "romkontroll-ny2",
  "oversikt-ny", "romkontroll", "romkontroll-ny", "solrom-ny",
  "solrom-dagskontroll", "solrom2-oversikt", "solrom2-dagskontroll",
  "solrom2-avvik", "dorer2-oversikt", "dorer2-bygg", "alarm", "avvik",
  "radata",
]);

function stateLabel(state: boolean | null) {
  if (state === true) return "På";
  if (state === false) return "Av";
  return "Ukjent";
}

function operationsModule(data: OperationsOverviewResponse): ModuleResponse {
  const cards = data.cards.filter((card) => ["Drift", "Energi", "Temperatur", "Vær"].includes(card.group || ""));
  return {
    title: "Driftsoversikt",
    subtitle: `${data.operatingWindow.label} · ${data.operatingWindow.detail} · Oppdatert ${new Date(data.generatedAt).toLocaleString("nb-NO")}`,
    cards,
    tables: [
      { title: "Lys", columns: ["funksjon", "status", "detalj"], rows: data.lightItems.map((item) => ({ funksjon: item.label, status: stateLabel(item.state), detalj: item.tooltip || "" })) },
      { title: "Viftestyring", columns: ["funksjon", "status", "kilde", "sist kontrollert"], rows: data.fanItems.map((item) => ({ funksjon: item.label, status: stateLabel(item.state), kilde: item.statusSource || item.tooltip || "", "sist kontrollert": item.checkedAt || "" })) },
      { title: "Siste driftshendelser", columns: ["hendelse", "verdi", "detalj"], rows: data.latestItems.filter((item) => /energi|temp/i.test(item.label)).map((item) => ({ hendelse: item.label, verdi: item.value, detalj: item.detail || "" })) },
      { title: "Status datakilder", columns: ["nr", "datakilde", "status", "sist lest", "neste kjøring"], rows: data.services.map((service) => ({ nr: service.sourceNo ?? "", datakilde: service.label, status: service.status, "sist lest": service.detail || service.lastSuccessAt || "", "neste kjøring": service.nextExpectedAt || "" })) },
    ],
  };
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
    return { ...group, items: [overview, report, ...robotItems] };
  });
  return { ...config, navigation };
}

const operationsExtensions: DomainAppExtensions = {
  enhanceConfig: withRobotNavigation,
  skipModuleLoad: ({ item }) => item.module === "dorer" || item.module === "pullerter",
  loadModule: ({ item }) => item.module === "status" && item.view === "drift"
    ? domainApi.get<OperationsOverviewResponse>("/api/overview").then(operationsModule)
    : null,
  renderModule: ({ data, module, view, reload }) => {
    const roborock = data.roborock as RoborockModuleData | null | undefined;
    if (module === "renhold" && roborock) return { content: <Suspense fallback={null}><RoborockSpecial data={roborock} /></Suspense>, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "pullerter") return { content: <Suspense fallback={null}><BollardsSpecial /></Suspense>, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "dorer" && doorViews.has(view)) return { content: <Suspense fallback={null}><DoorsSpecial view={view} /></Suspense>, hideFilters: true, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "ventilasjon" && data.ventilation) return { content: <Suspense fallback={null}><VentilationSpecial data={data} view={view} reload={reload} /></Suspense>, hideCharts: true, hideTables: view === "innstillinger" };
    if (data.controlSettings) return { content: <Suspense fallback={null}><ControlSettingsSpecial settings={data.controlSettings as ControlSettings} reload={reload} /></Suspense>, hideTables: true };
    return null;
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode><ThemeProvider><DomainApp config={getDomainConfig("operations")} extensions={operationsExtensions} /></ThemeProvider></StrictMode>,
);
