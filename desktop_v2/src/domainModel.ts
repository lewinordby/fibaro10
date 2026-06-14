import type { ModuleCard } from "./api";
import { domainLabels } from "./designTokens";
import { modulePath } from "./moduleViews";

type DomainKey = keyof typeof domainLabels;

const titleMatchers: Record<string, Array<{ words: string[]; href: string }>> = {
  omsetning: [
    { words: ["måned", "måneds"], href: modulePath("omsetning", "manedsoversikt") },
    { words: ["sammenligning", "uke", "i dag"], href: "/omsetning/sammenligning" },
    { words: ["sol"], href: modulePath("soling", "oversikt") },
    { words: ["park"], href: modulePath("parkering", "oversikt") },
  ],
  parkering: [
    { words: ["toppbelegg", "belegg"], href: modulePath("parkering", "dagslinje") },
    { words: ["kjøretøy", "bil", "område", "navn"], href: modulePath("parkering", "kjoretoy") },
    { words: ["prognose"], href: modulePath("parkering", "prognose") },
    { words: ["parkering", "pågående", "beløp", "treff"], href: modulePath("parkering", "parkeringer") },
  ],
  soling: [
    { words: ["dagslinje"], href: modulePath("soling", "dagslinje") },
    { words: ["seng", "rom"], href: modulePath("soling", "senger") },
    { words: ["medlem"], href: modulePath("soling", "medlemmer") },
    { words: ["prognose"], href: modulePath("soling", "prognose") },
    { words: ["soling", "timer", "omsetning", "treff"], href: modulePath("soling", "enkeltimer") },
  ],
  energi: [
    { words: ["solseng", "seng"], href: modulePath("energi", "forbruk-per-seng") },
    { words: ["kurs"], href: modulePath("energi", "kurser") },
    { words: ["last", "effekt"], href: modulePath("energi", "laster") },
    { words: ["elvia", "import", "forbruk"], href: modulePath("energi", "elvia") },
    { words: ["inntak", "diff", "strøm"], href: modulePath("energi", "status") },
  ],
  ventilasjon: [
    { words: ["yr", "vær"], href: modulePath("ventilasjon", "yr-logg") },
    { words: ["temp", "kjeller", "fukt"], href: modulePath("ventilasjon", "temp-logg") },
    { words: ["vifte", "vifter"], href: modulePath("ventilasjon", "dagslogg") },
  ],
  lys: [
    { words: ["lux", "sample"], href: modulePath("lys", "lux-logging") },
    { words: ["hendelse"], href: modulePath("lys", "hendelser") },
    { words: ["lys"], href: modulePath("lys", "dagslogg") },
  ],
  renhold: [
    { words: ["robot"], href: modulePath("renhold", "roboter") },
  ],
  admin: [
    { words: ["build"], href: modulePath("admin", "build") },
    { words: ["datakilde", "treg", "feil"], href: modulePath("admin", "datakilder") },
    { words: ["bruker"], href: modulePath("admin", "brukere") },
  ],
};

const defaultModuleHref: Record<string, string> = {
  omsetning: modulePath("omsetning", "oversikt"),
  parkering: modulePath("parkering", "oversikt"),
  soling: modulePath("soling", "oversikt"),
  energi: modulePath("energi", "status"),
  ventilasjon: modulePath("ventilasjon", "dagslogg"),
  lys: modulePath("lys", "dagslogg"),
  renhold: modulePath("renhold", "oversikt"),
  admin: modulePath("admin", "drift"),
};

function normalizeText(value: string): string {
  return value.toLocaleLowerCase("nb-NO");
}

function textForCard(card: ModuleCard): string {
  return normalizeText(`${card.title} ${card.detail ?? ""} ${card.tone ?? ""}`);
}

export function toneLabel(tone?: string, fallback?: string): string {
  if (tone && tone in domainLabels) return domainLabels[tone as DomainKey];
  return fallback || domainLabels.status;
}

export function moduleMetricFallbackHref(module: string, view: string, card: ModuleCard): string | undefined {
  const text = textForCard(card);
  const match = titleMatchers[module]?.find((item) => item.words.some((word) => text.includes(word)));
  const currentPath = modulePath(module, view);
  if (match) return match.href === currentPath ? undefined : match.href;
  const defaultHref = defaultModuleHref[module];
  if (!defaultHref || defaultHref === currentPath) return undefined;
  return defaultHref;
}
