import type { JsonRecord } from "@lilletorget/microapp-ui/types";
import type { RoborockDailySummary, RoborockReadinessSummary } from "../../roborock-types";

export const emptyDay: RoborockDailySummary = {
  job_count: 0,
  completed_count: 0,
  running_count: 0,
  error_count: 0,
  duration_minutes: 0,
  cleaned_area_m2: 0,
};

export function parsedDate(value: unknown) {
  if (!value) return null;
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function stamp(value: unknown) {
  const parsed = parsedDate(value);
  return parsed
    ? parsed.toLocaleString("nb-NO", { dateStyle: "short", timeStyle: "medium", timeZone: "Europe/Oslo" })
    : value ? String(value) : "-";
}

export function jobTime(value: unknown) {
  const parsed = parsedDate(value);
  return parsed ? parsed.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Oslo" }) : "-";
}

export function relativeStamp(value: unknown) {
  const parsed = parsedDate(value);
  if (!parsed) return "Ikke mottatt";
  const minutes = Math.max(0, Math.round((Date.now() - parsed.getTime()) / 60_000));
  if (minutes < 1) return "akkurat nå";
  if (minutes < 60) return `${minutes} min siden`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} t siden`;
  return stamp(value);
}

export function decimal(value: unknown, digits = 0) {
  const number = Number(value || 0);
  return number.toLocaleString("nb-NO", { maximumFractionDigits: digits });
}

export function recordValue(value: unknown): JsonRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as JsonRecord : {};
}

export function durationLabel(value: unknown) {
  const minutes = Math.max(0, Math.round(Number(value || 0)));
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (!hours) return `${remainder} min`;
  return remainder ? `${hours} t ${remainder} min` : `${hours} t`;
}

const roborockStateLabels: Record<string, string> = {
  charging: "Lader",
  cleaning: "Rengjør",
  docking: "Dokker",
  emptying: "Tømmer støvbeholder",
  emptying_dust_container: "Tømmer støvbeholder",
  error: "Feil",
  going_to_target: "Går til målpunkt",
  idle: "Klar",
  mapping: "Kartlegger",
  paused: "Pause",
  returning: "Returnerer til dokk",
  returning_home: "Returnerer til dokk",
  segment_cleaning: "Rengjør rom",
  sleeping: "Hviler",
  spot_cleaning: "Flekkrengjøring",
  updating: "Oppdaterer",
  washing_mop: "Vasker mopp",
  washing_the_mop: "Vasker mopp",
  zone_cleaning: "Sonerengjøring",
};

export function robotStateLabel(value: unknown) {
  const text = String(value || "").trim();
  return roborockStateLabels[text.toLowerCase()] || text || "Ingen status";
}

export function telemetryTone(value: unknown) {
  const text = String(value ?? "").toLocaleLowerCase("nb-NO");
  if (["ikke støttet", "-"].includes(text)) return "text-gray-400";
  if (["ok", "ingen feil", "nei", "0"].includes(text)) return "text-green-600 dark:text-green-400";
  if (text.includes("full") || text.includes("tom") || text.includes("feil") || text.includes("mangler")) return "text-red-500";
  return "text-gray-700 dark:text-gray-200";
}

export function readinessStyle(status: RoborockReadinessSummary["status"] | undefined) {
  if (status === "attention") return { badge: "bg-red-500/10 text-red-600 dark:text-red-400", dot: "bg-red-500", icon: "bg-red-500/10 text-red-500" };
  if (status === "pending") return { badge: "bg-amber-500/10 text-amber-700 dark:text-amber-300", dot: "bg-amber-500", icon: "bg-amber-500/10 text-amber-600 dark:text-amber-300" };
  if (status === "offline") return { badge: "bg-gray-500/10 text-gray-600 dark:text-gray-300", dot: "bg-gray-400", icon: "bg-gray-500/10 text-gray-500" };
  if (status === "active") return { badge: "bg-sky-500/10 text-sky-700 dark:text-sky-400", dot: "bg-sky-500", icon: "bg-sky-500/10 text-sky-600 dark:text-sky-400" };
  return { badge: "bg-green-500/10 text-green-700 dark:text-green-400", dot: "bg-green-500", icon: "bg-green-500/10 text-green-600 dark:text-green-400" };
}
