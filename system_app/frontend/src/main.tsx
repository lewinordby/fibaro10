import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, ThemeProvider, getDomainConfig, type DomainAppExtensions } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";
import type { SystemNotificationsData, SystemSubsystemsData } from "./types";

const MobilePreviewSpecial = lazy(() => import("./components/MobilePreviewSpecial").then((module) => ({ default: module.MobilePreviewSpecial })));
const IdeasSpecial = lazy(() => import("./components/IdeasSpecial").then((module) => ({ default: module.IdeasSpecial })));
const NotificationsSpecial = lazy(() => import("./components/SystemSpecial").then((module) => ({ default: module.NotificationsSpecial })));
const SubsystemsSpecial = lazy(() => import("./components/SystemSpecial").then((module) => ({ default: module.SubsystemsSpecial })));
const SystemDetailRoute = lazy(() => import("./components/SystemDetailPages").then((module) => ({ default: module.SystemDetailRoute })));

const systemExtensions: DomainAppExtensions = {
  isRoute: ({ pathname }) => /^\/(?:datakilder|build)\/[^/]+$/.test(pathname),
  renderRoute: ({ pathname, config, coreUrl }) => <Suspense fallback={null}><SystemDetailRoute pathname={pathname} config={config} coreUrl={coreUrl} /></Suspense>,
  renderModule: ({ data, module }) => {
    if (module === "mobil") return { content: <Suspense fallback={null}><MobilePreviewSpecial table={data.tables[0]} /></Suspense>, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "ideer") return { content: <Suspense fallback={null}><IdeasSpecial rows={data.tables[0]?.rows || []} /></Suspense>, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "varslinger" && data.systemNotifications) return { content: <Suspense fallback={null}><NotificationsSpecial data={data.systemNotifications as unknown as SystemNotificationsData} /></Suspense>, hideCards: true, hideCharts: true, hideTables: true };
    if (module === "undersystemer" && data.systemSubsystems) return { content: <Suspense fallback={null}><SubsystemsSpecial data={data.systemSubsystems as unknown as SystemSubsystemsData} /></Suspense>, hideCards: true, hideCharts: true, hideTables: true };
    return null;
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode><ThemeProvider><DomainApp config={getDomainConfig("system")} extensions={systemExtensions} /></ThemeProvider></StrictMode>,
);
