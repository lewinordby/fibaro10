import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, ThemeProvider, type DomainUiConfig } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";

const config: DomainUiConfig = { appId: "operations", name: "Lilletorget Bygg og drift", shortName: "Bygg og drift", icon: "building", accent: "sky", navigation: [
  { label: "Drift", items: [
    { to: "/", label: "Driftsoversikt", icon: "dashboard", title: "Driftsoversikt", description: "Samlet status for tekniske funksjoner i bygget.", module: "status", view: "drift", corePath: "/status/drift" },
  ]},
  { label: "Ventilasjon", items: [
    { to: "/ventilasjon", label: "Dagslogg", icon: "ventilation", title: "Ventilasjon dagslogg", description: "Temperatur, fuktighet og viftestatus gjennom dagen.", module: "ventilasjon", view: "dagslogg", corePath: "/ventilasjon/dagslogg" },
    { to: "/ventilasjon/temp-logg", label: "Temperatur og fukt", icon: "chart", title: "Temperatur og fuktighet", description: "Historiske målinger gruppert etter område.", module: "ventilasjon", view: "temp-logg", corePath: "/ventilasjon/temp-logg" },
    { to: "/ventilasjon/yr-logg", label: "Yr-logg", icon: "calendar", title: "Yr-logg", description: "Lagrede værdata fra Yr.", module: "ventilasjon", view: "yr-logg", corePath: "/ventilasjon/yr-logg" },
    { to: "/ventilasjon/hendelser", label: "Hendelser", icon: "clock", title: "Ventilasjonshendelser", description: "Start, stopp og endringer i ventilasjonen.", module: "ventilasjon", view: "hendelser", corePath: "/ventilasjon/hendelser" },
    { to: "/ventilasjon/innstillinger", label: "Innstillinger", icon: "settings", title: "Ventilasjonsinnstillinger", description: "Regler og parametere for automatisk styring.", module: "ventilasjon", view: "innstillinger", corePath: "/ventilasjon/innstillinger" },
  ]},
  { label: "Lys", items: [
    { to: "/lys", label: "Dagslogg", icon: "light", title: "Lys dagslogg", description: "Lux, skydekke og solhøyde gjennom dagen.", module: "lys", view: "dagslogg", corePath: "/lys/dagslogg" },
    { to: "/lys/lux-logging", label: "Lux-logging", icon: "chart", title: "Lux-logging", description: "Historiske lysmålinger og datakvalitet.", module: "lys", view: "lux-logging", corePath: "/lys/lux-logging" },
    { to: "/lys/hendelser", label: "Hendelser", icon: "clock", title: "Lyshendelser", description: "Registrerte endringer i lysstyringen.", module: "lys", view: "hendelser", corePath: "/lys/hendelser" },
    { to: "/lys/innstillinger", label: "Innstillinger", icon: "settings", title: "Lysinnstillinger", description: "Regler og terskler for automatisk lysstyring.", module: "lys", view: "innstillinger", corePath: "/lys/innstillinger" },
  ]},
  { label: "Dører", items: [
    { to: "/dorer", label: "Oversikt", icon: "door", title: "Døroversikt", description: "Rask status for solrom og øvrige dører.", module: "dorer", view: "oversikt", corePath: "/dorer/oversikt" },
    { to: "/dorer/solrom", label: "Solrom", icon: "sun", title: "Solrom", description: "Dørstatus, soltider og forventet slutt per rom.", module: "dorer", view: "solrom", corePath: "/dorer/solrom" },
    { to: "/dorer/romkontroll", label: "Romkontroll", icon: "compare", title: "Romkontroll", description: "Tidslinje og hendelser koblet mot soltimer og effekt.", module: "dorer", view: "romkontroll-ny2", corePath: "/dorer/romkontroll-ny2" },
    { to: "/dorer/alarm", label: "Alarm", icon: "bell", title: "Døralarmer", description: "Aktive og historiske alarmer for dører og solrom.", module: "dorer", view: "alarm", corePath: "/dorer/alarm" },
    { to: "/dorer/avvik", label: "Avvik", icon: "warning", title: "Døravvik", description: "Åpne/lukke-hendelser, soltimer og avvik samlet.", module: "dorer", view: "avvik", corePath: "/dorer/avvik" },
    { to: "/dorer/andre", label: "Andre dører", icon: "door", title: "Andre dører", description: "Status og historikk for øvrige dører i bygget.", module: "dorer", view: "andre", corePath: "/dorer/andre" },
    { to: "/dorer/radata", label: "Rådata", icon: "apps", title: "Dørdata", description: "Alle registrerte sensorhendelser.", module: "dorer", view: "radata", corePath: "/dorer/radata" },
  ]},
  { label: "Anlegg", items: [
    { to: "/pullerter", label: "Pullerter", icon: "building", title: "Pullerter og fasade", description: "Visuell og AI-basert kontroll av pullerter, fasade og trapp.", module: "pullerter", view: "oversikt", corePath: "/pullerter/oversikt" },
    { to: "/renhold", label: "Renhold", icon: "robot", title: "Renhold", description: "Status, historikk og oppfølging av robotvaskere.", module: "renhold", view: "oversikt", corePath: "/renhold/oversikt" },
    { to: "/renhold/roboter", label: "Robotvaskere", icon: "robot", title: "Robotvaskere", description: "Detaljer per robot og siste rengjøringer.", module: "renhold", view: "roboter", corePath: "/renhold/roboter" },
  ]},
] };
createRoot(document.getElementById("root")!).render(<StrictMode><ThemeProvider><DomainApp config={config} /></ThemeProvider></StrictMode>);
