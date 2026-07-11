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
  tooltipBorder: "#748196",
  mutedText: "#dce4ef",
  axisText: "#d3dce8",
  axisLine: "#748196",
  grid: "rgba(148,163,184,0.26)",
  gridSoft: "rgba(148,163,184,0.17)",
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
  "#334155": "#cbd5e1",
  "#475569": "#cbd5e1",
  "#64748b": "#cbd5e1",
  "#94a3b8": "#dbeafe",
  "#dc2626": "#fb7185",
  "#b91c1c": "#f87171",
  "#991b1b": "#f87171",
  "#ef4444": "#fb7185",
  "#df705d": "#fb8f7f",
  "#be123c": "#fb7185",
  "#2563eb": "#60a5fa",
  "#1d4ed8": "#93c5fd",
  "#3f7fbd": "#93c5fd",
  "#4b7fbb": "#93c5fd",
  "#071943": "#bfdbfe",
  "#0ea5e9": "#38bdf8",
  "#38bdf8": "#7dd3fc",
  "#15803d": "#4ade80",
  "#166534": "#4ade80",
  "#16a34a": "#4ade80",
  "#22c55e": "#86efac",
  "#52a464": "#86efac",
  "#84cc16": "#bef264",
  "#0f766e": "#5eead4",
  "#0d9488": "#5eead4",
  "#14b8a6": "#5eead4",
  "#0891b2": "#22d3ee",
  "#06b6d4": "#67e8f9",
  "#2f8fa3": "#67e8f9",
  "#4e8793": "#67e8f9",
  "#f59e0b": "#fbbf24",
  "#ca8a04": "#fde047",
  "#d59a18": "#fbbf24",
  "#d97706": "#fb923c",
  "#f2b84b": "#fde68a",
  "#9a660f": "#facc15",
  "#ea580c": "#fb923c",
  "#92400e": "#fbbf24",
  "#7c3aed": "#c084fc",
  "#6d28d9": "#c084fc",
  "#8b5cf6": "#c084fc",
  "#726189": "#c4b5fd",
  "#5b6b84": "#cbd5e1",
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
  const normalized = color.trim().toLowerCase();
  return darkColorMap[normalized] ?? color;
}

export function chartSeriesPalette() {
  return isDarkScreenTheme() ? [...darkSeriesPalette] : [...lightSeriesPalette];
}

export function chartSeriesLineWidth(primary = false) {
  const base = primary ? 3 : 2;
  return isDarkScreenTheme() ? base + 0.35 : base;
}

export function chartAreaOpacity(primary = false) {
  if (isDarkScreenTheme()) return primary ? 0.16 : 0.11;
  return primary ? 0.08 : 0.06;
}

export function chartTooltip() {
  return {
    trigger: "axis",
    backgroundColor: chartColors.tooltipBackground,
    borderColor: chartColors.tooltipBorder,
    borderWidth: 1,
    textStyle: { color: chartColors.text, fontSize: 12 },
    extraCssText: isDarkScreenTheme()
      ? "box-shadow:0 18px 38px rgba(0,0,0,.38);border-radius:7px;"
      : "box-shadow:0 12px 28px rgba(15,23,42,.12);border-radius:7px;",
  };
}

export function chartDataZoom() {
  if (!isDarkScreenTheme()) {
    return {
      borderColor: "#dbe3ee",
      backgroundColor: "rgba(248,250,252,0.86)",
      fillerColor: "rgba(37,99,235,0.12)",
      dataBackground: {
        lineStyle: { color: "#cbd5e1" },
        areaStyle: { color: "rgba(148,163,184,0.12)" },
      },
      selectedDataBackground: {
        lineStyle: { color: "#64748b" },
        areaStyle: { color: "rgba(37,99,235,0.10)" },
      },
      handleStyle: {
        color: "#ffffff",
        borderColor: "#94a3b8",
      },
      moveHandleStyle: {
        color: "#64748b",
      },
      textStyle: { color: chartColors.axisText },
    };
  }
  return {
    borderColor: "rgba(148,163,184,0.34)",
    backgroundColor: "rgba(15,23,42,0.30)",
    fillerColor: "rgba(96,165,250,0.24)",
    dataBackground: {
      lineStyle: { color: "rgba(148,163,184,0.46)" },
      areaStyle: { color: "rgba(148,163,184,0.12)" },
    },
    selectedDataBackground: {
      lineStyle: { color: "rgba(226,232,240,0.58)" },
      areaStyle: { color: "rgba(96,165,250,0.16)" },
    },
    handleStyle: {
      color: "#e2e8f0",
      borderColor: "#cbd5e1",
    },
    moveHandleStyle: {
      color: "#64748b",
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
    inactiveColor: isDarkScreenTheme() ? "rgba(203,213,225,0.42)" : "#94a3b8",
    textStyle: { color: chartColors.mutedText, fontSize: 12, fontWeight: 650 },
    ...extra,
  };
}

export function chartAxisLine() {
  return { lineStyle: { color: chartColors.axisLine } };
}

export function chartAxisLabel(extra: Record<string, unknown> = {}) {
  return { color: chartColors.axisText, fontSize: 11, fontWeight: 560, ...extra };
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
