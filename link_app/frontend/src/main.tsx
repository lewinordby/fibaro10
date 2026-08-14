import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, ThemeProvider, getDomainConfig, type DomainAppExtensions } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";
import type { KobleReviewData } from "./types";

const LinkReviewSpecial = lazy(() => import("./components/LinkReviewSpecial").then((module) => ({ default: module.LinkReviewSpecial })));
const customViews = new Set(["oversikt", "kandidater", "biltreff", "sun2", "sun2-kontroll"]);

const linkExtensions: DomainAppExtensions = {
  renderModule: ({ data, module, view, reload }) => {
    if (module !== "koble" || !data.kobleReview) return null;
    const review = data.kobleReview as unknown as KobleReviewData;
    if (customViews.has(view)) return {
      content: <Suspense fallback={null}><LinkReviewSpecial review={review} view={view} reload={reload} /></Suspense>,
      hideActions: true,
      hideFilters: true,
      hideCards: true,
      hideTables: true,
    };
    const tables = view === "treffgrunnlag"
      ? data.tables.filter((table) => table.title === "Treffgrunnlag")
      : view === "jobb"
        ? data.tables.filter((table) => ["Jobbparametere", "Sist behandlet"].includes(table.title))
        : [];
    return { content: null, hideActions: view !== "jobb", hideCards: true, tables };
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode><ThemeProvider><DomainApp config={getDomainConfig("link")} extensions={linkExtensions} /></ThemeProvider></StrictMode>,
);
