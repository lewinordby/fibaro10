import { nok } from "./format";

type YearComparisonBase = {
  anchorYear: number;
  comparisonYear: number;
  availableYears: number[];
};

type YearComparisonAxis = {
  axis: {
    ticks: Array<{ day: number; label: string }>;
  };
};

export function comparisonDateLabel(value?: string | null) {
  if (!value) return "-";
  return new Date(`${value}T00:00:00`).toLocaleDateString("nb-NO", { day: "2-digit", month: "2-digit" });
}

export function signedNok(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 kr";
  return `${value > 0 ? "+" : "-"}${nok(Math.abs(value))} kr`;
}

export function signedCount(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 stk";
  return `${value > 0 ? "+" : "-"}${Math.abs(value)} stk`;
}

export function deltaTone(value: number) {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

export function compactAmountAxisValue(value: number) {
  if (Math.abs(value) >= 1000) return `${Math.round(value / 1000)}k`;
  return `${Math.round(value)}`;
}

export function defaultSelectedYears(data: YearComparisonBase) {
  return [data.anchorYear, data.comparisonYear].filter((year, index, years) => years.indexOf(year) === index);
}

export function activeYearsFromParams(data: YearComparisonBase, yearsParam: string | null) {
  const available = new Set(data.availableYears);
  const parsed = (yearsParam || "")
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((year) => Number.isFinite(year) && available.has(year));
  const unique = parsed.filter((year, index, years) => years.indexOf(year) === index);
  return unique.length ? unique : defaultSelectedYears(data);
}

export function yearMonthLabel(data: YearComparisonAxis, value: number) {
  const day = Math.round(Number(value));
  const tick = data.axis.ticks.reduce<{ label: string; day: number } | null>((best, item) => {
    if (item.day <= day && (!best || item.day > best.day)) return item;
    return best;
  }, null);
  return tick?.label ?? "";
}
