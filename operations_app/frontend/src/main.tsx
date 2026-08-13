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
import "@lilletorget/mosaic-theme/font.css";
import type { RoborockModuleData } from "./roborock-types";
import "./style.css";

const RoborockSpecial = lazy(() => import("./components/RoborockSpecial").then((module) => ({ default: module.RoborockSpecial })));

function withRobotNavigation(config: DomainUiConfig, data: ModuleResponse | null | undefined): DomainUiConfig {
  const robots = (data?.roborock as RoborockModuleData | null | undefined)?.robots;
  if (!robots?.length) return config;
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

const operationsExtensions: DomainAppExtensions = {
  enhanceConfig: withRobotNavigation,
  renderModule: ({ data, module }) => {
    const roborock = data.roborock as RoborockModuleData | null | undefined;
    return module === "renhold" && roborock
      ? <Suspense fallback={null}><RoborockSpecial data={roborock} /></Suspense>
      : null;
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode><ThemeProvider><DomainApp config={getDomainConfig("operations")} extensions={operationsExtensions} /></ThemeProvider></StrictMode>,
);
