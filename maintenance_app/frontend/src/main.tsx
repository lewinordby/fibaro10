import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, ThemeProvider, getDomainConfig, type DomainAppExtensions } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";

const MaintenanceVisitDetailPage = lazy(() => import("./components/MaintenanceVisitDetailPage").then((module) => ({ default: module.MaintenanceVisitDetailPage })));

const maintenanceExtensions: DomainAppExtensions = {
  isRoute: ({ pathname }) => /^\/besok\/\d+$/.test(pathname),
  renderRoute: ({ pathname, config, coreUrl }) => {
    const visit = pathname.match(/^\/besok\/(\d+)$/);
    return visit ? <Suspense fallback={null}><MaintenanceVisitDetailPage id={visit[1]} config={config} coreUrl={coreUrl} /></Suspense> : null;
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode><ThemeProvider><DomainApp config={getDomainConfig("maintenance")} extensions={maintenanceExtensions} /></ThemeProvider></StrictMode>,
);
