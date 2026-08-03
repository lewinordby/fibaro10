import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { DomainApp, ThemeProvider, type DomainUiConfig } from "@lilletorget/microapp-ui";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";

const config: DomainUiConfig = { appId: "system", name: "Lilletorget System", shortName: "System", icon: "settings", accent: "violet", navigation: [
  { label: "System", items: [
    { to: "/", label: "Drift", icon: "dashboard", title: "Systemdrift", description: "Tjenestestatus, jobber og sentrale systemkontroller.", module: "admin", view: "drift", corePath: "/admin/drift" },
    { to: "/datakilder", label: "Datakilder", icon: "link", title: "Datakilder", description: "Status, kjøreplan, avhengigheter og forklaring per datakilde.", module: "admin", view: "datakilder", corePath: "/admin/datakilder" },
    { to: "/systemkart", label: "Systemkart", icon: "apps", title: "Systemkart", description: "Komponenter, tjenester og forbindelser i løsningen.", module: "admin", view: "systemkart", corePath: "/admin/systemkart" },
    { to: "/undersystemer", label: "Undersystemer", icon: "external", title: "Undersystemer", description: "Klikkbare lenker til alle løsninger med webgrensesnitt.", module: "undersystemer", view: "oversikt", corePath: "/undersystemer/oversikt" },
    { to: "/varslinger", label: "Varslinger", icon: "bell", title: "Varslinger og abonnement", description: "ntfy-emner, forklaringer og abonnementslister.", module: "varslinger", view: "oversikt", corePath: "/varslinger/oversikt" },
  ]},
  { label: "Kvalitet", items: [
    { to: "/kontroll", label: "Kontroll", icon: "compare", title: "Systemkontroll", description: "Samlede kontroller av datagrunnlag og prosesser.", module: "admin", view: "kontroll", corePath: "/admin/kontroll" },
    { to: "/datakvalitet", label: "Datakvalitet", icon: "warning", title: "Datakvalitet", description: "Manglende, utdaterte og avvikende data.", module: "admin", view: "datakvalitet", corePath: "/admin/datakvalitet" },
    { to: "/analyse", label: "Analyse", icon: "chart", title: "Analyse", description: "Systemanalyse og oppfølging av avvik.", module: "admin", view: "analyse", corePath: "/admin/analyse" },
    { to: "/oppgaver", label: "Oppgaver", icon: "tools", title: "Systemoppgaver", description: "Planlagte og manuelle systemoppgaver.", module: "admin", view: "oppgaver", corePath: "/admin/oppgaver" },
  ]},
  { label: "Administrasjon", items: [
    { to: "/brukere", label: "Brukere", icon: "users", title: "Brukeradministrasjon", description: "Opprett, rediger og kontroller brukere.", module: "admin", view: "brukere", corePath: "/admin/brukere" },
    { to: "/build", label: "Buildlogg", icon: "clock", title: "Buildlogg", description: "Buildnummer, bestillinger, endringer og berørte apper.", module: "admin", view: "build", corePath: "/admin/build" },
    { to: "/teknisk", label: "Teknisk", icon: "settings", title: "Teknisk oversikt", description: "Tekniske innstillinger og diagnostikk.", module: "admin", view: "teknisk", corePath: "/admin/teknisk" },
    { to: "/verktoy", label: "Verktøy", icon: "tools", title: "Systemverktøy", description: "Administrative verktøy og vedlikeholdsfunksjoner.", module: "admin", view: "verktoy", corePath: "/admin/verktoy" },
    { to: "/ai", label: "AI", icon: "idea", title: "AI-funksjoner", description: "Status og innstillinger for lokale og eksterne AI-funksjoner.", module: "admin", view: "ai", corePath: "/admin/ai" },
  ]},
  { label: "Dokumentasjon", items: [
    { to: "/manual", label: "Manual", icon: "book", title: "Manual", description: "Kort innføring og inngang til alle kapitler.", module: "manual", view: "oversikt", corePath: "/manual/oversikt" },
    { to: "/manual/daglig-bruk", label: "Daglig bruk", icon: "book", title: "Daglig bruk", description: "De viktigste arbeidsflytene i hverdagen.", module: "manual", view: "daglig-bruk", corePath: "/manual/daglig-bruk" },
    { to: "/manual/datagrunnlag", label: "Datagrunnlag", icon: "book", title: "Datagrunnlag", description: "Hvor data kommer fra og hvordan de behandles.", module: "manual", view: "datagrunnlag", corePath: "/manual/datagrunnlag" },
    { to: "/manual/feilsoking", label: "Feilsøking", icon: "warning", title: "Feilsøking", description: "Systematiske kontroller ved vanlige feil.", module: "manual", view: "feilsoking", corePath: "/manual/feilsoking" },
  ]},
  { label: "Utvikling", items: [
    { to: "/ideer", label: "Ideer", icon: "idea", title: "Ideer", description: "Forslag til ny funksjonalitet før de flyttes inn i fagappene.", module: "ideer", view: "oversikt", corePath: "/ideer/oversikt" },
    { to: "/mobil", label: "Mobilflater", icon: "apps", title: "Mobilflater", description: "Samlet oversikt over skjermene i mobilappen.", module: "mobil", view: "oversikt", corePath: "/mobil/oversikt" },
  ]},
] };
createRoot(document.getElementById("root")!).render(<StrictMode><ThemeProvider><DomainApp config={config} /></ThemeProvider></StrictMode>);
