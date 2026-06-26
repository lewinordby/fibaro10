export const semanticColors = {
  ink: "#111827",
  muted: "#64748b",
  line: "#e2e8f0",
  surface: "#ffffff",
  surfaceSoft: "#f6f8fb",
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
    borderRadius: 8,
    colorText: semanticColors.ink,
    colorTextSecondary: semanticColors.muted,
    colorBorder: semanticColors.line,
    colorBgLayout: semanticColors.surfaceSoft,
    colorBgContainer: semanticColors.surface,
    controlHeight: 32,
    controlHeightSM: 28,
    controlHeightLG: 36,
    fontSize: 13,
    fontSizeSM: 12,
    lineHeight: 1.35,
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  components: {
    Button: {
      borderRadius: 7,
      controlHeight: 32,
      fontWeight: 650,
    },
    Card: {
      borderRadiusLG: 8,
      paddingLG: 12,
      headerHeight: 38,
    },
    Input: {
      borderRadius: 7,
    },
    Layout: {
      bodyBg: semanticColors.surfaceSoft,
      siderBg: "#ffffff",
      triggerBg: "#ffffff",
    },
    Menu: {
      itemBorderRadius: 7,
      itemHeight: 36,
    },
    Segmented: {
      itemSelectedBg: semanticColors.blue,
      itemSelectedColor: "#ffffff",
      trackBg: "#eef2f7",
    },
    Table: {
      borderColor: "#e8edf4",
      headerBg: "#f8fafc",
      headerColor: "#475569",
      rowHoverBg: "#f8fbff",
      cellFontSize: 12,
      cellFontSizeSM: 11,
      cellPaddingBlock: 7,
      cellPaddingInline: 9,
      headerSplitColor: "#e8edf4",
    },
    Tabs: {
      horizontalMargin: "0 0 10px 0",
      itemSelectedColor: semanticColors.blue,
      inkBarColor: semanticColors.blue,
    },
    Tag: {
      borderRadiusSM: 6,
    },
  },
} as const;
