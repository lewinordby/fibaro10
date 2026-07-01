export type ModuleView = {
  key: string;
  label: string;
};

export const MODULE_LABELS: Record<string, string> = {
  status: "Status",
  omsetning: "Omsetning",
  parkering: "Parkering",
  soling: "Soling",
  koble: "Koble",
  energi: "Energi",
  ventilasjon: "Ventilasjon",
  lys: "Lys",
  mobil: "Mobil",
  renhold: "Renhold",
  admin: "Admin",
};

export const MODULE_NAVIGATION_LABELS: Record<string, string> = {
  status: "Dashboard",
};

export const MODULE_COLORS: Record<string, string> = {
  status: "var(--domain-status)",
  omsetning: "var(--domain-revenue)",
  parkering: "var(--domain-parking)",
  soling: "var(--domain-sun2)",
  energi: "var(--domain-energy)",
  ventilasjon: "var(--domain-vent)",
  lys: "var(--domain-light)",
  mobil: "var(--domain-mobile)",
  renhold: "#0f766e",
  admin: "#64748b",
};

export const MODULE_VIEWS: Record<string, ModuleView[]> = {
  status: [
    { key: "omsetning", label: "Omsetning" },
    { key: "parkering", label: "Parkering" },
    { key: "soling", label: "Soling" },
    { key: "drift", label: "Drift" },
  ],
  omsetning: [
    { key: "oversikt", label: "Oversikt" },
    { key: "manedsoversikt", label: "Månedsoversikt" },
    { key: "akkumulert", label: "Årssammenligning" },
    { key: "sammenligning", label: "Periodesammenligning" },
  ],
  parkering: [
    { key: "oversikt", label: "Oversikt" },
    { key: "sammenligning", label: "Årssammenligning" },
    { key: "dagslinje", label: "Dagslinje" },
    { key: "parkeringer", label: "Parkeringer" },
    { key: "kjoretoy", label: "Kjøretøy" },
    { key: "prognose", label: "Prognose" },
    { key: "omrade", label: "Område" },
    { key: "bilstatistikk", label: "Bilstatistikk" },
    { key: "oppgjor", label: "Oppgjør" },
    { key: "oppslag", label: "Oppslag" },
  ],
  soling: [
    { key: "oversikt", label: "Oversikt" },
    { key: "sammenligning", label: "Årssammenligning" },
    { key: "dagslinje", label: "Dagslinje" },
    { key: "enkeltimer", label: "Enkeltimer" },
    { key: "senger", label: "Senger" },
    { key: "medlemmer", label: "Medlemmer" },
    { key: "produkter", label: "Produkter" },
    { key: "prognose", label: "Prognose" },
    { key: "oppgjor", label: "Oppgjør" },
    { key: "statistikk", label: "Statistikk" },
    { key: "detaljer", label: "Detaljer" },
  ],
  koble: [{ key: "oversikt", label: "Oversikt" }],
  energi: [
    { key: "status", label: "Status" },
    { key: "elvia-kontroll", label: "Elvia-kontroll" },
    { key: "kurser", label: "Kurser" },
    { key: "laster", label: "Laster" },
    { key: "forbruk-per-seng", label: "Forbruk per seng" },
    { key: "elvia", label: "Elvia" },
    { key: "verktoy", label: "Verktøy" },
  ],
  ventilasjon: [
    { key: "dagslogg", label: "Dagslogg" },
    { key: "temp-logg", label: "Temperatur og fukt" },
    { key: "yr-logg", label: "Yr-logg" },
    { key: "hendelser", label: "Hendelser" },
    { key: "innstillinger", label: "Innstillinger" },
  ],
  lys: [
    { key: "dagslogg", label: "Dagslogg" },
    { key: "lux-logging", label: "Lux-logg" },
    { key: "hendelser", label: "Hendelser" },
    { key: "innstillinger", label: "Innstillinger" },
  ],
  mobil: [{ key: "oversikt", label: "Oversikt" }],
  renhold: [
    { key: "oversikt", label: "Oversikt" },
    { key: "roboter", label: "Roboter" },
  ],
  admin: [
    { key: "oppgaver", label: "Oppgaver" },
    { key: "kontroll", label: "Kontroll" },
    { key: "datakvalitet", label: "Datakvalitet" },
    { key: "analyse", label: "Analyse" },
    { key: "drift", label: "Drift" },
    { key: "build", label: "Buildlogg" },
    { key: "datakilder", label: "Datakilder" },
    { key: "systemkart", label: "Systemkart" },
    { key: "owntracks", label: "OwnTracks" },
    { key: "ai", label: "AI" },
    { key: "teknisk", label: "Teknisk" },
    { key: "brukere", label: "Brukere" },
    { key: "manual", label: "Manual" },
    { key: "verktoy", label: "Verktøy" },
  ],
};

export function defaultModuleView(module: string): string {
  return MODULE_VIEWS[module]?.[0]?.key ?? "oversikt";
}

export function moduleLabel(module: string): string {
  return MODULE_LABELS[module] ?? module;
}

export function moduleNavigationLabel(module: string): string {
  return MODULE_NAVIGATION_LABELS[module] ?? moduleLabel(module);
}

export function moduleColor(module: string): string {
  return MODULE_COLORS[module] ?? "var(--domain-status)";
}

export function modulePath(module: string, view?: string): string {
  return `/${module}/${view || defaultModuleView(module)}`;
}
