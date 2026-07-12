export type ModuleView = {
  key: string;
  label: string;
  hidden?: boolean;
};

export const MODULE_LABELS: Record<string, string> = {
  status: "Status",
  omsetning: "Omsetning",
  parkering: "Parkering",
  soling: "Soling",
  solrom: "Solrom",
  koble: "Koble",
  energi: "Energi",
  ventilasjon: "Ventilasjon",
  lys: "Lys",
  dorer: "Dører",
  vedlikehold: "Vedlikehold",
  ideer: "Ideer",
  mobil: "Mobil",
  renhold: "Renhold",
  manual: "Manual",
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
  solrom: "var(--domain-sun2)",
  energi: "var(--domain-energy)",
  ventilasjon: "var(--domain-vent)",
  lys: "var(--domain-light)",
  dorer: "var(--domain-building)",
  vedlikehold: "var(--domain-maintenance)",
  ideer: "var(--domain-ideas)",
  mobil: "var(--domain-mobile)",
  renhold: "var(--domain-maintenance)",
  manual: "var(--domain-manual)",
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
    { key: "sammenligning", label: "Periodesammenligning" },
    { key: "akkumulert", label: "Årssammenligning" },
    { key: "manedsoversikt", label: "Månedsoversikt" },
  ],
  parkering: [
    { key: "oversikt", label: "Oversikt" },
    { key: "parkeringer", label: "Parkeringer" },
    { key: "dagslinje", label: "Dagslinje" },
    { key: "tidspunkt", label: "Tidspunkt" },
    { key: "kjoretoy", label: "Kjøretøy" },
    { key: "omrade", label: "Områder" },
    { key: "prognose", label: "Prognose" },
    { key: "sammenligning", label: "Årssammenligning" },
    { key: "oppgjor", label: "Oppgjør" },
    { key: "oppslag", label: "Datakvalitet" },
    { key: "bilstatistikk", label: "Bilstatistikk", hidden: true },
  ],
  soling: [
    { key: "oversikt", label: "Oversikt" },
    { key: "sammenligning", label: "Årssammenligning" },
    { key: "dagslinje", label: "Dagslinje" },
    { key: "enkeltimer", label: "Enkeltimer" },
    { key: "oppgjor", label: "Oppgjør" },
    { key: "prognose", label: "Prognose" },
    { key: "produkter", label: "Produkter" },
    { key: "senger", label: "Senger" },
    { key: "medlemmer", label: "Medlemmer" },
    { key: "statistikk", label: "Statistikk" },
    { key: "detaljer", label: "Detaljer" },
  ],
  solrom: [
    { key: "oversikt", label: "Nå" },
    { key: "dagskontroll", label: "Dagskontroll" },
    { key: "rom", label: "Romdetalj", hidden: true },
  ],
  koble: [
    { key: "oversikt", label: "Oversikt" },
    { key: "sun2", label: "SUN2-kontroll" },
    { key: "biltreff", label: "Biltreff" },
    { key: "kandidater", label: "Kandidater" },
    { key: "treffgrunnlag", label: "Treffgrunnlag" },
    { key: "jobb", label: "Jobb" },
  ],
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
  dorer: [
    { key: "oversikt", label: "Oversikt" },
    { key: "oversikt-ny", label: "Oversikt - ny", hidden: true },
    { key: "romkontroll", label: "Romkontroll", hidden: true },
    { key: "romkontroll-ny", label: "Romkontroll - ny", hidden: true },
    { key: "romkontroll-ny2", label: "Romkontroll - ny2", hidden: true },
    { key: "soltimer", label: "Dør og soltime", hidden: true },
    { key: "solrom", label: "Solrom", hidden: true },
    { key: "solrom-ny", label: "Solrom - ny", hidden: true },
    { key: "andre", label: "Andre dører" },
    { key: "radata", label: "Rådata" },
  ],
  vedlikehold: [
    { key: "oversikt", label: "Oversikt" },
    { key: "besok", label: "Besøk" },
  ],
  ideer: [
    { key: "oversikt", label: "Oversikt" },
    { key: "kontroll", label: "Kontroll" },
    { key: "innsikt", label: "Innsikt" },
    { key: "automatisering", label: "Automatisering" },
    { key: "arbeidsflyt", label: "Arbeidsflyt" },
  ],
  mobil: [{ key: "oversikt", label: "Oversikt" }],
  renhold: [
    { key: "oversikt", label: "Oversikt" },
    { key: "roboter", label: "Roboter" },
  ],
  manual: [
    { key: "oversikt", label: "Oversikt" },
    { key: "daglig-bruk", label: "Daglig bruk" },
    { key: "menyvalg", label: "Menyvalg" },
    { key: "okonomi", label: "Økonomi" },
    { key: "bygg-drift", label: "Bygg og drift" },
    { key: "system", label: "System" },
    { key: "datagrunnlag", label: "Datagrunnlag" },
    { key: "rutiner", label: "Rutiner" },
    { key: "feilsoking", label: "Feilsøking" },
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
    { key: "ai", label: "AI" },
    { key: "teknisk", label: "Teknisk" },
    { key: "brukere", label: "Brukere" },
    { key: "verktoy", label: "Verktøy" },
  ],
};

export function defaultModuleView(module: string): string {
  return visibleModuleViews(module)[0]?.key ?? MODULE_VIEWS[module]?.[0]?.key ?? "oversikt";
}

export function visibleModuleViews(module: string): ModuleView[] {
  return (MODULE_VIEWS[module] ?? []).filter((item) => !item.hidden);
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
