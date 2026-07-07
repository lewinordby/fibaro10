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
  tooltipBackground: "rgba(25,28,34,0.98)",
  tooltipBorder: "#3b4350",
  mutedText: "#aeb7c4",
  axisText: "#7f8895",
  axisLine: "#454e5d",
  grid: "#2a303a",
  gridSoft: "#232933",
} as const;

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
