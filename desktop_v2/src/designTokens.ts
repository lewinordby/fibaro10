export const semanticColors = {
  ink: "#111827",
  muted: "#6b7280",
  line: "#e6ebf0",
  surface: "#ffffff",
  surfaceSoft: "#f8fafc",
  blue: "#2563eb",
  red: "#dc2626",
  green: "#15803d",
  amber: "#f59e0b",
  cyan: "#0891b2",
} as const;

export const domainColors = {
  revenue: semanticColors.red,
  parking: semanticColors.blue,
  sun2: semanticColors.amber,
  energy: semanticColors.green,
  vent: semanticColors.cyan,
  weather: "#64748b",
  light: "#ca8a04",
  status: "#475569",
  comparison: "#64748b",
  ink: semanticColors.ink,
  grid: "#e5e7eb",
  gridSoft: "#eef2f7",
} as const;

export const domainLabels = {
  revenue: "Omsetning",
  parking: "Parkering",
  sun2: "Soling",
  energy: "Energi",
  vent: "Ventilasjon",
  weather: "Vær",
  light: "Lys",
  status: "Status",
} as const;

export const antdTheme = {
  token: {
    colorPrimary: semanticColors.blue,
    colorSuccess: semanticColors.green,
    colorWarning: semanticColors.amber,
    colorError: "#b91c1c",
    colorInfo: semanticColors.blue,
    borderRadius: 6,
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  components: {
    Card: {
      borderRadiusLG: 6,
      paddingLG: 18,
    },
    Layout: {
      bodyBg: semanticColors.surfaceSoft,
      siderBg: "#1f2937",
      triggerBg: "#1f2937",
    },
  },
} as const;
