import { useEffect, useRef } from "react";
import type { Chart as ChartInstance, ChartConfiguration, ChartDataset, Point } from "chart.js";
import { useTheme } from "./ThemeContext";

let chartModulePromise: Promise<typeof import("chart.js")> | null = null;

function loadChartModule() {
  if (!chartModulePromise) {
    chartModulePromise = import("chart.js").then((chartModule) => {
      const ChartJS = chartModule.Chart;
      ChartJS.register(...chartModule.registerables);
      ChartJS.defaults.font.family = '"Inter", sans-serif';
      ChartJS.defaults.font.weight = 500;
      ChartJS.defaults.plugins.tooltip.borderWidth = 1;
      ChartJS.defaults.plugins.tooltip.displayColors = false;
      ChartJS.defaults.plugins.tooltip.mode = "nearest";
      ChartJS.defaults.plugins.tooltip.intersect = false;
      ChartJS.defaults.plugins.tooltip.position = "nearest";
      ChartJS.defaults.plugins.tooltip.caretSize = 0;
      ChartJS.defaults.plugins.tooltip.caretPadding = 20;
      ChartJS.defaults.plugins.tooltip.cornerRadius = 8;
      ChartJS.defaults.plugins.tooltip.padding = 8;
      return chartModule;
    });
  }
  return chartModulePromise;
}

function css(variable: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}

function opacity(hex: string, alpha: number) {
  const value = hex.replace("#", "");
  const red = Number.parseInt(value.slice(0, 2), 16);
  const green = Number.parseInt(value.slice(2, 4), 16);
  const blue = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

export const mosaicChartColors = {
  violet: "#8470ff",
  sky: "#67bfff",
  green: "#3ec972",
  red: "#ff5656",
  yellow: "#f0bb33",
  gray: "#6b7280",
};

export type MosaicChartDataset = {
  label: string;
  data: Array<number | null | Point>;
  type?: "line" | "bar";
  color: string;
  unit?: string;
  yAxisID?: "y" | "y1";
  fill?: boolean;
  stepped?: boolean;
  dashed?: boolean;
  dotted?: boolean;
  stack?: string;
  hidden?: boolean;
};

export type MosaicChartConfig = {
  type: "line" | "bar";
  labels?: Array<string | number>;
  datasets: MosaicChartDataset[];
  xType?: "category" | "linear";
  xMin?: number;
  xMax?: number;
  yUnit?: string;
  y1Unit?: string;
  y1Min?: number;
  y1Max?: number;
  stacked?: boolean;
  beginAtZero?: boolean;
  yInteger?: boolean;
  tooltipUnit?: string;
  xTick?: (value: number | string, index: number) => string;
  yTick?: (value: number) => string;
};

export function Chart({ config, height = 360 }: { config: MosaicChartConfig; height?: number }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const { currentTheme } = useTheme();
  const chartLabel = `Diagram med ${config.datasets.length} serier: ${config.datasets.map((dataset) => dataset.label).join(", ")}`;

  useEffect(() => {
    if (!canvas.current) return;
    let disposed = false;
    let chart: ChartInstance<"line" | "bar", Array<number | null | Point>, string | number> | null = null;

    const renderChart = async () => {
      const { Chart: ChartJS } = await loadChartModule();
      if (disposed || !canvas.current) return;
      const dark = currentTheme === "dark";
      const textColor = dark ? css("--color-gray-400") : css("--color-gray-500");
      const gridColor = dark ? opacity(css("--color-gray-700"), .6) : css("--color-gray-100");
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const datasets = config.datasets.map((dataset) => ({
      label: dataset.label,
      data: dataset.data,
      type: dataset.type,
      yAxisID: dataset.yAxisID,
      borderColor: dataset.color,
      backgroundColor: dataset.fill ? opacity(dataset.color, .16) : dataset.color,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 3,
      pointBackgroundColor: dataset.color,
      pointHoverBackgroundColor: dataset.color,
      pointBorderWidth: 0,
      pointHoverBorderWidth: 0,
      tension: .2,
      fill: dataset.fill ?? false,
      stepped: dataset.stepped ? "after" : false,
      borderDash: dataset.dotted ? [2, 4] : dataset.dashed ? [7, 5] : undefined,
      stack: dataset.stack,
      hidden: dataset.hidden,
      borderRadius: dataset.type === "bar" || config.type === "bar" ? 3 : undefined,
      maxBarThickness: 34,
      })) as ChartDataset<"line" | "bar", Array<number | null | Point>>[];

      const chartConfig: ChartConfiguration<"line" | "bar", Array<number | null | Point>, string | number> = {
      type: config.type,
      data: { labels: config.labels, datasets },
      options: {
        layout: { padding: { top: 12, bottom: 8, left: 12, right: 12 } },
        maintainAspectRatio: false,
        resizeDelay: 200,
        interaction: { intersect: false, mode: "nearest" },
        animation: { duration: reducedMotion ? 0 : 350 },
        scales: {
          x: {
            type: config.xType || "category",
            min: config.xMin,
            max: config.xMax,
            stacked: config.stacked,
            border: { display: false },
            grid: { display: false },
            ticks: {
              color: textColor,
              maxRotation: 45,
              autoSkip: true,
              callback(value, index) {
                const raw = config.xType === "linear" ? Number(value) : (config.labels?.[index] ?? value);
                return config.xTick ? config.xTick(raw, index) : String(raw);
              },
            },
          },
          y: {
            stacked: config.stacked,
            beginAtZero: config.beginAtZero ?? true,
            border: { display: false },
            grid: { color: gridColor },
            ticks: {
              color: textColor,
              precision: config.yInteger ? 0 : undefined,
              maxTicksLimit: 6,
              callback: (value) => config.yTick ? config.yTick(Number(value)) : String(value),
            },
            title: config.yUnit ? { display: true, text: config.yUnit, color: textColor } : undefined,
          },
          ...(config.datasets.some((dataset) => dataset.yAxisID === "y1") ? {
            y1: {
              position: "right" as const,
              beginAtZero: true,
              min: config.y1Min,
              max: config.y1Max,
              border: { display: false },
              grid: { display: false },
              ticks: { color: textColor, maxTicksLimit: 6 },
              title: config.y1Unit ? { display: true, text: config.y1Unit, color: textColor } : undefined,
            },
          } : {}),
        },
        plugins: {
          legend: { display: true, position: "top", align: "end", labels: { color: textColor, usePointStyle: true, pointStyle: "circle", boxWidth: 8, boxHeight: 8 } },
          tooltip: {
            bodyColor: dark ? css("--color-gray-400") : css("--color-gray-500"),
            backgroundColor: dark ? css("--color-gray-700") : css("--color-white"),
            borderColor: dark ? css("--color-gray-600") : css("--color-gray-200"),
            callbacks: { label: (context) => {
              const unit = config.datasets[context.datasetIndex]?.unit || config.tooltipUnit || "";
              return `${context.dataset.label}: ${Number(context.parsed.y || 0).toLocaleString("nb-NO")}${unit ? ` ${unit}` : ""}`;
            } },
          },
        },
      },
      };

      chart = new ChartJS(canvas.current, chartConfig);
    };

    void renderChart();
    return () => {
      disposed = true;
      chart?.destroy();
    };
  }, [config, currentTheme]);

  return <div style={{ height }}><canvas ref={canvas} role="img" aria-label={chartLabel}>Diagrammet viser {config.datasets.map((dataset) => dataset.label).join(", ")}.</canvas></div>;
}
