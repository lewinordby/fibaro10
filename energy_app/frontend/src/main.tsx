import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, ThemeProvider, type DomainUiConfig } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";

const config: DomainUiConfig = { appId: "energy", name: "Lilletorget Energi", shortName: "Energi", icon: "energy", accent: "green", navigation: [
  { label: "Energi", items: [
    { to: "/", label: "Status", icon: "dashboard", title: "Energistatus", description: "Sanntidseffekt, fordeling og historisk utvikling.", module: "energi", view: "status", corePath: "/energi/status" },
    { to: "/elvia-kontroll", label: "Elvia-kontroll", icon: "compare", title: "Elvia-kontroll", description: "Sammenlign Elvia-import med målt forbruk fra HC3.", module: "energi", view: "elvia-kontroll", corePath: "/energi/elvia-kontroll" },
    { to: "/kurs-last", label: "Kurs og last", icon: "link", title: "Kurs og last", description: "Visuell modell av kurser, Z-Wave-enheter, målere og laster.", module: "energi", view: "kurs-last", corePath: "/energi/kurs-last" },
    { to: "/kurser", label: "Kurser", icon: "energy", title: "Kurser", description: "Oppsett og redigering av elektriske kurser.", module: "energi", view: "kurser", corePath: "/energi/kurser" },
    { to: "/laster", label: "Laster", icon: "apps", title: "Laster", description: "Alle registrerte laster og tilknyttede målere.", module: "energi", view: "laster", corePath: "/energi/laster" },
    { to: "/forbruk-per-seng", label: "Forbruk per seng", icon: "sun", title: "Forbruk per solseng", description: "Beregnet og målt energibruk per solseng.", module: "energi", view: "forbruk-per-seng", corePath: "/energi/forbruk-per-seng" },
    { to: "/elvia", label: "Elvia-import", icon: "calendar", title: "Elvia-import", description: "Last opp og kontroller forbruksfiler fra Elvia.", module: "energi", view: "elvia", corePath: "/energi/elvia" },
    { to: "/verktoy", label: "Verktøy", icon: "tools", title: "Energiverktøy", description: "Diagnostikk og vedlikehold av energigrunnlaget.", module: "energi", view: "verktoy", corePath: "/energi/verktoy" },
  ]},
] };
createRoot(document.getElementById("root")!).render(<StrictMode><ThemeProvider><DomainApp config={config} /></ThemeProvider></StrictMode>);
