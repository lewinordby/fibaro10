import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { CountComparisonSpecial, CountDashboardSpecial, DomainApp, ThemeProvider, YearComparisonSpecial, getDomainConfig, type DomainAppExtensions } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";
import type { SunTimeline } from "./types";

const SunSessionsSpecial = lazy(() => import("./components/SunSessionsSpecial").then((module) => ({ default: module.SunSessionsSpecial })));
const SunTimelineSpecial = lazy(() => import("./components/SunTimelineSpecial").then((module) => ({ default: module.SunTimelineSpecial })));
const SettlementDetailPage = lazy(() => import("./components/SettlementDetailPage").then((module) => ({ default: module.SettlementDetailPage })));

const sunExtensions: DomainAppExtensions = {
  isRoute: ({ pathname, item }) => (
    (item.module === "status" && ["soling", "soling-comparison"].includes(item.view))
    || (item.module === "soling" && item.view === "sammenligning")
    || /^\/oppgjor\/\d+$/.test(pathname)
  ),
  renderRoute: ({ pathname, item }) => {
    const settlement = pathname.match(/^\/oppgjor\/(\d+)$/);
    if (settlement) return <Suspense fallback={null}><SettlementDetailPage domain="sun" id={settlement[1]} /></Suspense>;
    if (item.module === "status" && item.view === "soling") return <CountDashboardSpecial domain="sun" />;
    if (item.module === "status" && item.view === "soling-comparison") return <CountComparisonSpecial domain="sun" />;
    if (item.module === "soling" && item.view === "sammenligning") return <YearComparisonSpecial domain="soling" />;
    return null;
  },
  renderModule: ({ data, module, view, reload }) => {
    const timeline = data.sunTimeline as SunTimeline | null | undefined;
    if (timeline) return { content: <Suspense fallback={null}><SunTimelineSpecial timeline={timeline} /></Suspense>, hideDayNavigation: true };
    return module === "soling" && view === "enkeltimer"
      ? { content: <Suspense fallback={null}><SunSessionsSpecial table={data.tables.find((table) => table.title === "Enkeltimer")} reload={reload} /></Suspense>, hideTables: true }
      : null;
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode><ThemeProvider><DomainApp config={getDomainConfig("sun")} extensions={sunExtensions} /></ThemeProvider></StrictMode>,
);
