export type JsonRecord = Record<string, unknown>;
export type ModuleRow = JsonRecord;

export type AppConfig = {
  name: string;
  build: string;
  commit: string;
  fibaro10AppUrl: string;
  shellAppUrl: string;
};

export type AuthUser = {
  username: string;
  role: string;
  roleLabel: string;
  isMaster: boolean;
};

export type ModuleCard = {
  title: string;
  value: string | number;
  unit?: string;
  detail?: string;
  tone?: string;
  href?: string;
};

export type ModuleChartSeries = {
  name: string;
  data: Array<number | null | [string, number | null]>;
  type?: "line" | "bar";
  unit?: string;
  color?: string;
  yAxisIndex?: number;
  step?: "start" | "middle" | "end";
  smooth?: boolean;
  hidden?: boolean;
};

export type ModuleChartMetric = {
  key: string;
  label: string;
  unit?: string;
  series: ModuleChartSeries[];
};

export type ModuleChart = {
  title: string;
  subtitle?: string;
  type?: "line" | "bar";
  x: string[];
  xAxisType?: "category" | "time";
  xAxisMin?: string | null;
  xAxisMax?: string | null;
  disableZoom?: boolean;
  height?: number;
  series: ModuleChartSeries[];
  metrics?: ModuleChartMetric[];
  defaultMetric?: string;
  defaultVisibleSeries?: string[];
  dayNavigation?: ModuleDayNavigation | null;
};

export type ModuleEditField = {
  key: string;
  label: string;
  type: "text" | "textarea" | "number" | "boolean" | "select" | "tags" | "datetime" | "password";
  required?: boolean;
  placeholder?: string;
  defaultValue?: unknown;
  section?: "meta" | "main";
  rows?: number;
  options?: Array<{ label: string; value: string | number | boolean }>;
};

export type ModuleEditConfig = {
  kind: string;
  title: string;
  idField?: string;
  endpoint: string;
  method?: "PATCH" | "POST";
  createEndpoint?: string;
  layout?: "default" | "split";
  width?: number;
  fields: ModuleEditField[];
  createFields?: ModuleEditField[];
};

export type ModuleTable = {
  title: string;
  columns: string[];
  rows: ModuleRow[];
  edit?: ModuleEditConfig;
  meta?: {
    totalRows?: number;
    page?: number;
    pageSize?: number;
    firstRow?: number;
    lastRow?: number;
    hasPrevious?: boolean;
    hasMore?: boolean;
    disablePagination?: boolean;
  };
};

export type ModuleAction = {
  key: string;
  label: string;
  method: "POST";
  path: string;
  confirm?: string;
  tone?: "primary" | "default";
};

export type ModuleFilter = {
  key: string;
  label: string;
  type: "text" | "date" | "datetime" | "number" | "select";
  value?: string | number | null;
  placeholder?: string;
  options?: Array<{ label: string; value: string | number }>;
};

export type ModuleDayNavigation = {
  selectedDay: string;
  selectedDayLabel: string;
  prevDay: string;
  nextDay: string;
  isToday?: boolean;
  context?: { label: string; value: string; detail?: string };
};

export type ModuleResponse = {
  title: string;
  subtitle: string;
  cards: ModuleCard[];
  charts?: ModuleChart[];
  tables: ModuleTable[];
  actions?: ModuleAction[];
  filters?: ModuleFilter[];
  dayNavigation?: ModuleDayNavigation | null;
  uploadEndpoint?: string;
  [key: string]: unknown;
};

export type BusinessPeriodComparison = {
  label: string;
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  total: number;
  fullLabel?: string;
  fullSol?: number;
  fullSolCount?: number;
  fullParking?: number;
  fullParkingCount?: number;
  fullTotal?: number;
};

export type BusinessStatusPeriod = {
  key: string;
  title: string;
  total: number;
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  solAsOfLabel: string;
  parkingAsOfLabel: string;
  previousLabel: string;
  previousTotal: number;
  previousSol: number;
  previousSolCount: number;
  previousParking: number;
  previousParkingCount: number;
  previousFullLabel?: string;
  previousFullTotal?: number;
  previousFullSol?: number;
  previousFullSolCount?: number;
  previousFullParking?: number;
  previousFullParkingCount?: number;
  extraComparisons?: BusinessPeriodComparison[];
  rank?: { rank: number; label: string; totalDays?: number } | null;
};

export type BusinessOverviewResponse = {
  generatedAt: string;
  statusPeriods: BusinessStatusPeriod[];
  services: Array<{
    sourceNo?: number;
    jobName?: string;
    label: string;
    status: string;
    detail?: string;
    lastSuccessAt?: string | null;
    nextExpectedAt?: string | null;
  }>;
};

export type BusinessComparisonEvent = { left: number; amount: number; label?: string };
export type BusinessComparisonLane = {
  source: "current" | "comparison" | "reference";
  kind: "sun" | "parking";
  label: string;
  endLeft?: number;
  events: BusinessComparisonEvent[];
};
export type BusinessComparisonSummary = {
  label: string;
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  total: number;
  solAsOfLabel?: string;
  parkingAsOfLabel?: string;
};
export type BusinessComparisonReference = {
  key: string;
  label: string;
  summary: BusinessComparisonSummary;
  lanes: BusinessComparisonLane[];
};
export type BusinessComparisonResponse = {
  comparisonLabel: string;
  navigation: { label: string; previousAnchor: string; nextAnchor: string; canNext: boolean };
  axis: { start?: string; seconds: number };
  current: BusinessComparisonSummary;
  comparison: BusinessComparisonSummary;
  lanes: BusinessComparisonLane[];
  referenceComparisons?: BusinessComparisonReference[];
};

export type YearComparisonPoint = {
  day: number;
  cumulativeAmount: number;
  cumulativeCount: number;
  cumulativeMinutes: number;
};

export type YearComparisonSeries = {
  key: string;
  year: number;
  label: string;
  daysWithData: number;
  totalAmount: number;
  totalCount: number;
  totalMinutes: number;
  points: YearComparisonPoint[];
};

export type YearComparisonResponse = {
  anchorYear: number;
  comparisonYear: number;
  navigation: { label: string; previousAnchor: string; nextAnchor: string; canPrevious: boolean; canNext: boolean };
  axis: { days: number };
  availableYears: number[];
  series: YearComparisonSeries[];
  selected: YearComparisonSeries;
  comparison: YearComparisonSeries;
  comparisonFull: YearComparisonSeries;
  delta: { amount: number; count: number; minutes: number };
};

export type Accent = "violet" | "sky" | "yellow" | "green" | "red";
export type AppDockId = "revenue" | "parking" | "sun" | "energy" | "operations" | "maintenance" | "system" | "link";

export type NavigationItem = {
  to: string;
  label: string;
  icon: import("./components/MosaicIcon").IconName;
  title: string;
  description: string;
  module: string;
  view: string;
  corePath?: string;
  aliases?: string[];
};

export type NavigationGroup = { label: string; icon: import("./components/MosaicIcon").IconName; items: NavigationItem[] };

export type DomainUiConfig = {
  appId: AppDockId;
  name: string;
  shortName: string;
  basePath: string;
  icon: import("./components/MosaicIcon").IconName;
  accent: Accent;
  navigation: NavigationGroup[];
};

export type DomainAppDefinition = DomainUiConfig & { port: number; url: string };
