export type ModuleView = {
  key: string;
  label: string;
};

export const MODULE_VIEWS: Record<string, ModuleView[]> = {
  parkering: [
    { key: "oversikt", label: "Oversikt" },
    { key: "prognose", label: "Prognose" },
    { key: "parkeringer", label: "Parkeringer" },
    { key: "kjoretoy", label: "Kjøretøy" },
    { key: "bilstatistikk", label: "Bilstatistikk" },
    { key: "omrade", label: "Område" },
  ],
  soling: [
    { key: "dagslinje", label: "Dagslinje" },
    { key: "prognose", label: "Prognose" },
    { key: "statistikk", label: "Statistikk" },
    { key: "enkeltimer", label: "Enkeltimer" },
    { key: "senger", label: "Senger" },
    { key: "medlemmer", label: "Medlemmer" },
  ],
  energi: [
    { key: "status", label: "Status" },
    { key: "kurser", label: "Kurser" },
    { key: "laster", label: "Laster" },
    { key: "forbruk-per-seng", label: "Forbruk/seng" },
    { key: "elvia", label: "Elvia" },
  ],
  ventilasjon: [
    { key: "dagslogg", label: "Dagslogg" },
    { key: "temp-logg", label: "Temp logg" },
    { key: "yr-logg", label: "Yr logg" },
    { key: "hendelser", label: "Hendelser" },
  ],
  lys: [
    { key: "dagslogg", label: "Dagslogg" },
    { key: "lux-logging", label: "Lux logging" },
    { key: "hendelser", label: "Hendelser" },
  ],
  renhold: [{ key: "oversikt", label: "Oversikt" }],
  admin: [
    { key: "build", label: "Build" },
    { key: "datakilder", label: "Datakilder" },
    { key: "ai", label: "AI" },
    { key: "teknisk", label: "Teknisk" },
  ],
};

export function defaultModuleView(module: string): string {
  return MODULE_VIEWS[module]?.[0]?.key ?? "oversikt";
}

export function modulePath(module: string, view?: string): string {
  return `/${module}/${view || defaultModuleView(module)}`;
}
