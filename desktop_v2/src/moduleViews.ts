export type ModuleView = {
  key: string;
  label: string;
};

export const MODULE_LABELS: Record<string, string> = {
  status: "Status",
  omsetning: "Omsetning",
  parkering: "Parkering",
  soling: "Soling",
  energi: "Energi",
  ventilasjon: "Ventilasjon",
  lys: "Lys",
  renhold: "Renhold",
  admin: "Admin",
};

export const MODULE_VIEWS: Record<string, ModuleView[]> = {
  status: [{ key: "oversikt", label: "Oversikt" }],
  omsetning: [
    { key: "oversikt", label: "Oversikt" },
    { key: "manedsoversikt", label: "Månedsoversikt" },
    { key: "sammenligning", label: "Sammenligning" },
  ],
  parkering: [
    { key: "oversikt", label: "Oversikt" },
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
    { key: "dagslinje", label: "Dagslinje" },
    { key: "enkeltimer", label: "Enkeltimer" },
    { key: "senger", label: "Senger" },
    { key: "medlemmer", label: "Medlemmer" },
    { key: "prognose", label: "Prognose" },
    { key: "statistikk", label: "Statistikk" },
    { key: "detaljer", label: "Detaljer" },
  ],
  energi: [
    { key: "status", label: "Status" },
    { key: "kurser", label: "Kurser" },
    { key: "laster", label: "Laster" },
    { key: "forbruk-per-seng", label: "Forbruk/seng" },
    { key: "elvia", label: "Elvia" },
    { key: "verktoy", label: "Verktøy" },
  ],
  ventilasjon: [
    { key: "dagslogg", label: "Dagslogg" },
    { key: "temp-logg", label: "Temp/fukt" },
    { key: "yr-logg", label: "Yr logg" },
    { key: "hendelser", label: "Hendelser" },
    { key: "innstillinger", label: "Innstillinger" },
  ],
  lys: [
    { key: "dagslogg", label: "Dagslogg" },
    { key: "lux-logging", label: "Lux logging" },
    { key: "hendelser", label: "Hendelser" },
    { key: "innstillinger", label: "Innstillinger" },
  ],
  renhold: [
    { key: "oversikt", label: "Oversikt" },
    { key: "roboter", label: "Roboter" },
  ],
  admin: [
    { key: "oppgaver", label: "Oppgaver" },
    { key: "datakvalitet", label: "Datakvalitet" },
    { key: "analyse", label: "Analyse" },
    { key: "drift", label: "Drift" },
    { key: "build", label: "Build" },
    { key: "datakilder", label: "Datakilder" },
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

export function modulePath(module: string, view?: string): string {
  return `/${module}/${view || defaultModuleView(module)}`;
}
