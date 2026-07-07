import { domainColors } from "./domainColors";
import { isDarkScreenTheme } from "./designTokens";

const lightChartColors = {
  tooltipBackground: "rgba(255,255,255,0.96)",
  tooltipBorder: "#dbe3ee",
  mutedText: "#475569",
  axisText: "#64748b",
  axisLine: "#cbd5e1",
  grid: "#e8edf4",
  gridSoft: "#eef2f7",
} as const;

const darkChartColors = {
  tooltipBackground: "rgba(15,23,42,0.98)",
  tooltipBorder: "#64748b",
  mutedText: "#d7dee8",
  axisText: "#cbd5e1",
  axisLine: "#64748b",
  grid: "rgba(148,163,184,0.3)",
  gridSoft: "rgba(148,163,184,0.2)",
} as const;

const lightSeriesPalette = [
  "#2563eb",
  "#f59e0b",
  "#dc2626",
  "#15803d",
  "#0891b2",
  "#7c3aed",
  "#0f766e",
  "#ea580c",
];

const darkSeriesPalette = [
  "#60a5fa",
  "#fbbf24",
  "#fb7185",
  "#4ade80",
  "#22d3ee",
  "#c084fc",
  "#5eead4",
  "#fb923c",
];

const darkColorMap: Record<string, string> = {
  "#111827": "#f8fafc",
  "#475569": "#cbd5e1",
  "#64748b": "#cbd5e1",
  "#dc2626": "#fb7185",
  "#b91c1c": "#f87171",
  "#991b1b": "#f87171",
  "#2563eb": "#60a5fa",
  "#1d4ed8": "#93c5fd",
  "#15803d": "#4ade80",
  "#166534": "#4ade80",
  "#0f766e": "#5eead4",
  "#0891b2": "#22d3ee",
  "#f59e0b": "#fbbf24",
  "#ca8a04": "#fde047",
  "#ea580c": "#fb923c",
  "#92400e": "#fbbf24",
  "#7c3aed": "#c084fc",
  "#6d28d9": "#c084fc",
  "#be123c": "#fb7185",
};

const CHART_THEME_EVENT = "fibaro10:chart-theme-change";

function activeChartColors() {
  return isDarkScreenTheme() ? darkChartColors : lightChartColors;
}

export const chartColors = {
  get tooltipBackground() { return activeChartColors().tooltipBackground; },
  get tooltipBorder() { return activeChartColors().tooltipBorder; },
  get text() { return domainColors.ink; },
  get mutedText() { return activeChartColors().mutedText; },
  get axisText() { return activeChartColors().axisText; },
  get axisLine() { return activeChartColors().axisLine; },
  get grid() { return activeChartColors().grid; },
  get gridSoft() { return activeChartColors().gridSoft; },
} as const;

export function notifyChartThemeChanged() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(CHART_THEME_EVENT));
}

export function chartThemeKey() {
  return isDarkScreenTheme() ? "dark" : "standard";
}

export function chartSeriesColor(color: string | undefined, index = 0) {
  if (!color) return chartSeriesPalette()[index % chartSeriesPalette().length];
  if (!isDarkScreenTheme()) return color;
  return darkColorMap[color.toLowerCase()] ?? color;
}

export function chartSeriesPalette() {
  return isDarkScreenTheme() ? [...darkSeriesPalette] : [...lightSeriesPalette];
}

export function chartSeriesLineWidth(primary = false) {
  const base = primary ? 3 : 2;
  return isDarkScreenTheme() ? base + 0.35 : base;
}

export function chartTooltip() {
  return {
    trigger: "axis",
    backgroundColor: chartColors.tooltipBackground,
    borderColor: chartColors.tooltipBorder,
    borderWidth: 1,
    textStyle: { color: chartColors.text, fontSize: 12 },
    extraCssText: isDarkScreenTheme()
      ? "box-shadow:0 18px 38px rgba(0,0,0,.38);border-radius:8px;"
      : "box-shadow:0 12px 28px rgba(15,23,42,.12);border-radius:8px;",
  };
}

export function chartDataZoom() {
  if (!isDarkScreenTheme()) return {};
  return {
    borderColor: "rgba(148,163,184,0.24)",
    backgroundColor: "rgba(15,23,42,0.18)",
    fillerColor: "rgba(96,165,250,0.18)",
    dataBackground: {
      lineStyle: { color: "rgba(148,163,184,0.34)" },
      areaStyle: { color: "rgba(148,163,184,0.08)" },
    },
    selectedDataBackground: {
      lineStyle: { color: "rgba(226,232,240,0.44)" },
      areaStyle: { color: "rgba(96,165,250,0.12)" },
    },
    handleStyle: {
      color: "#cbd5e1",
      borderColor: "#94a3b8",
    },
    moveHandleStyle: {
      color: "#334155",
    },
    textStyle: { color: chartColors.axisText },
  };
}

export function chartLegend(extra: Record<string, unknown> = {}) {
  return {
    top: 0,
    icon: "roundRect",
    itemWidth: 18,
    itemHeight: 8,
    textStyle: { color: chartColors.mutedText, fontSize: 12, fontWeight: 650 },
    ...extra,
  };
}

export function chartAxisLine() {
  return { lineStyle: { color: chartColors.axisLine } };
}

export function chartAxisLabel(extra: Record<string, unknown> = {}) {
  return { color: chartColors.axisText, fontSize: 11, ...extra };
}

export function chartSplitLine(color: string = chartColors.grid) {
  return { lineStyle: { color } };
}

export function chartTitleTextStyle(extra: Record<string, unknown> = {}) {
  return { color: chartColors.text, fontSize: 13, fontWeight: 760, ...extra };
}

export function subscribeChartTheme(listener: () => void) {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener(CHART_THEME_EVENT, listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(CHART_THEME_EVENT, listener);
    window.removeEventListener("storage", listener);
  };
}
