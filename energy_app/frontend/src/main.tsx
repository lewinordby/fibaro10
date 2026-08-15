import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, Loading, ThemeProvider, getDomainConfig, type DomainAppExtensions } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";
import type { EnergyCircuitLoadsData, EnergyElviaData, EnergySunbedsData } from "./types";

const EnergySunbedsSpecial = lazy(() => import("./components/EnergySpecial").then((module) => ({ default: module.EnergySunbedsSpecial })));
const EnergyElviaSpecial = lazy(() => import("./components/EnergySpecial").then((module) => ({ default: module.EnergyElviaSpecial })));
const EnergyCircuitLoadsSpecial = lazy(() => import("./components/EnergySpecial").then((module) => ({ default: module.EnergyCircuitLoadsSpecial })));

const energyExtensions: DomainAppExtensions = {
  renderModule: ({ data, module, view, reload }) => {
    if (module !== "energi") return null;
    if (view === "elvia" && data.energyElvia) return { content: <Suspense fallback={<Loading />}><EnergyElviaSpecial data={data.energyElvia as EnergyElviaData} reload={reload} /></Suspense>, hideUpload: true, hideCards: true, hideCharts: true, hideTables: true };
    if (view === "forbruk-per-seng" && data.energySunbeds) return { content: <Suspense fallback={<Loading />}><EnergySunbedsSpecial data={data.energySunbeds as unknown as EnergySunbedsData} /></Suspense>, hideTables: true };
    if (view === "kurs-last" && data.energyCircuitLoads) return { content: <Suspense fallback={<Loading />}><EnergyCircuitLoadsSpecial data={data.energyCircuitLoads as unknown as EnergyCircuitLoadsData} reload={reload} /></Suspense>, hideTables: true };
    return null;
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode><ThemeProvider><DomainApp config={getDomainConfig("energy")} extensions={energyExtensions} /></ThemeProvider></StrictMode>,
);
