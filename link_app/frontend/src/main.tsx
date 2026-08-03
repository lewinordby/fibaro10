import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, ThemeProvider, type DomainUiConfig } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";

const config: DomainUiConfig = { name: "Lilletorget Koble", shortName: "Koble", icon: "link", accent: "violet", navigation: [
  { label: "Koblinger", items: [
    { to: "/", label: "Kandidater", icon: "link", title: "Koble parkering og soling", description: "Sannsynlige koblinger mellom kj\u00f8ret\u00f8y og Sun2-ID.", module: "koble", view: "oversikt", corePath: "/koble/oversikt" },
    { to: "/kontroll", label: "Sun2-kontroll", icon: "compare", title: "Sun2-kontroll", description: "Visuell kontroll av gjentatte treff og motbevis.", module: "koble", view: "sun2-kontroll", corePath: "/koble/sun2-kontroll" },
    { to: "/biltreff", label: "Biltreff", icon: "parking", title: "Biltreff", description: "Biler med gjentatte treff mot samme Sun2-ID.", module: "koble", view: "biltreff", corePath: "/koble/biltreff" },
    { to: "/treffgrunnlag", label: "Treffgrunnlag", icon: "chart", title: "Treffgrunnlag", description: "Parkeringer og soltimer som ligger bak kandidatene.", module: "koble", view: "treffgrunnlag", corePath: "/koble/treffgrunnlag" },
  ]},
  { label: "Motor", items: [
    { to: "/jobb", label: "Jobbstatus", icon: "settings", title: "Koblingsjobb", description: "Status, parametere og styring av koblingsmotoren.", module: "koble", view: "jobb", corePath: "/koble/jobb" },
  ]},
] };

createRoot(document.getElementById("root")!).render(<StrictMode><ThemeProvider><DomainApp config={config} /></ThemeProvider></StrictMode>);
