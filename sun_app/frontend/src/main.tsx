import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, ThemeProvider, type DomainUiConfig } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";

const config: DomainUiConfig = {
  appId: "sun",
  name: "Lilletorget Soling", shortName: "Soling", icon: "sun", accent: "yellow",
  navigation: [
    { label: "Soling", items: [
      { to: "/", label: "Oversikt", icon: "dashboard", title: "Solingsoversikt", description: "Ukesutvikling, nøkkeltall og siste solinger.", module: "soling", view: "oversikt", corePath: "/soling/oversikt" },
      { to: "/sammenligning", label: "Årssammenligning", icon: "compare", title: "Årssammenligning", description: "Akkumulert utvikling sammenlignet mellom år.", module: "soling", view: "sammenligning", corePath: "/soling/sammenligning" },
      { to: "/dagslinje", label: "Dagslinje", icon: "clock", title: "Dagslinje", description: "Soltimer, rom og energibruk gjennom valgt dag.", module: "soling", view: "dagslinje", corePath: "/soling/dagslinje" },
      { to: "/enkeltimer", label: "Enkelttimer", icon: "calendar", title: "Enkelttimer", description: "Alle soltimer med bilder, medlem og Sun2-ID.", module: "soling", view: "enkeltimer", corePath: "/soling/enkeltimer" },
      { to: "/prognose", label: "Prognose", icon: "trend", title: "Prognose", description: "Forventet soling mot faktisk utvikling.", module: "soling", view: "prognose", corePath: "/soling/prognose" },
      { to: "/oppgjor", label: "Oppgjør", icon: "calendar", title: "Oppgjør", description: "Kreditnotaer kontrollert mot sol- og produktsalg.", module: "soling", view: "oppgjor", corePath: "/soling/oppgjor" },
      { to: "/produkter", label: "Produkter", icon: "chart", title: "Produktsalg", description: "Produktsalg per dag og periode.", module: "soling", view: "produkter", corePath: "/soling/produkter" },
      { to: "/senger", label: "Senger", icon: "sun", title: "Solsenger", description: "Bruk, omsetning og status per solseng.", module: "soling", view: "senger", corePath: "/soling/senger" },
      { to: "/medlemmer", label: "Medlemmer", icon: "users", title: "Medlemmer", description: "Medlemsaktivitet og relaterte soltimer.", module: "soling", view: "medlemmer", corePath: "/soling/medlemmer" },
      { to: "/statistikk", label: "Statistikk", icon: "chart", title: "Statistikk", description: "Detaljerte analyser av soling.", module: "soling", view: "statistikk", corePath: "/soling/statistikk" },
    ]},
  ],
};

createRoot(document.getElementById("root")!).render(<StrictMode><ThemeProvider><DomainApp config={config} /></ThemeProvider></StrictMode>);
