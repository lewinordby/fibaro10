import { domainColors } from "./domainColors";

export const chartColors = {
  tooltipBackground: "rgba(255,255,255,0.96)",
  tooltipBorder: "#dbe3ee",
  text: domainColors.ink,
  mutedText: "#475569",
  axisText: "#64748b",
  axisLine: "#cbd5e1",
  grid: "#e8edf4",
  gridSoft: domainColors.gridSoft,
} as const;

export function chartTooltip() {
  return {
    trigger: "axis",
    backgroundColor: chartColors.tooltipBackground,
    borderColor: chartColors.tooltipBorder,
    borderWidth: 1,
    textStyle: { color: chartColors.text, fontSize: 12 },
    extraCssText: "box-shadow:0 12px 28px rgba(15,23,42,.12);border-radius:8px;",
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
