import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, ThemeProvider, type DomainUiConfig } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";

const config: DomainUiConfig = { appId: "maintenance", name: "Lilletorget Vedlikehold", shortName: "Vedlikehold", icon: "tools", accent: "green", navigation: [
  { label: "Vedlikehold", items: [
    { to: "/", label: "Oppgaver", icon: "tools", title: "Vedlikehold", description: "Registrer, søk og rediger vedlikeholdsoppgaver.", module: "vedlikehold", view: "oversikt", corePath: "/vedlikehold/oversikt" },
    { to: "/besok", label: "Besøk", icon: "calendar", title: "Besøk på Lilletorget", description: "Besøk med notater og tilknyttede oppgaver.", module: "vedlikehold", view: "besok", corePath: "/vedlikehold/besok" },
  ]},
] };
createRoot(document.getElementById("root")!).render(<StrictMode><ThemeProvider><DomainApp config={config} /></ThemeProvider></StrictMode>);
