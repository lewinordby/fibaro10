export type JsonRecord = Record<string, unknown>;

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

export type ServiceStatus = {
  jobName?: string | null;
  label: string;
  status: string;
  detail: string;
  lastSuccessAt?: string | null;
  nextExpectedAt?: string | null;
};

export type PeriodComparison = {
  label: string;
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  total: number;
  solAsOfLabel: string;
  parkingAsOfLabel: string;
  fullLabel?: string;
  fullSol?: number;
  fullSolCount?: number;
  fullParking?: number;
  fullParkingCount?: number;
  fullTotal?: number;
};

export type StatusPeriod = {
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
  extraComparisons?: PeriodComparison[];
  rank?: { rank: number; label: string; totalDays?: number } | null;
};

export type OverviewResponse = {
  generatedAt: string;
  statusPeriods: StatusPeriod[];
  services: ServiceStatus[];
};

export type ModuleCard = {
  title: string;
  value: string;
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
};

export type ModuleChart = {
  title: string;
  subtitle?: string;
  type?: "line" | "bar";
  x: string[];
  height?: number;
  series: ModuleChartSeries[];
};

export type ModuleTable = {
  title: string;
  columns: string[];
  rows: JsonRecord[];
};

export type ModuleResponse = {
  title: string;
  subtitle: string;
  cards: ModuleCard[];
  charts?: ModuleChart[];
  tables: ModuleTable[];
};

export type RevenueDay = {
  day: string;
  dayLabel: string;
  weekday: string;
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  total: number;
  isToday: boolean;
  isWeekend: boolean;
};

export type RevenueMonthResponse = {
  summary: {
    label: string;
    month: string;
    previousMonth: string;
    nextMonth: string;
    currentMonth: string;
    total: number;
    sol: number;
    parking: number;
    solCount: number;
    parkingCount: number;
    averageDayCount: number;
    averagePerDay: number;
    maxTotal: number;
    topDay: RevenueDay | null;
    todayRow: RevenueDay | null;
  };
  rows: RevenueDay[];
};

export type ComparisonEvent = {
  left: number;
  amount: number;
};

export type ComparisonLane = {
  key: string;
  source: "current" | "comparison" | "reference";
  periodLabel: string;
  kind: "sun" | "parking";
  endLeft?: number;
  events: ComparisonEvent[];
};

export type ComparisonSummary = {
  label: string;
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  total: number;
  solAsOfLabel: string;
  parkingAsOfLabel: string;
};

export type ComparisonDelta = {
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  total: number;
};

export type ComparisonReference = {
  key: string;
  label: string;
  summary: ComparisonSummary;
  delta: ComparisonDelta;
  lanes: ComparisonLane[];
};

export type ComparisonResponse = {
  generatedAt: string | null;
  title: string;
  comparisonLabel: string;
  periodKey: string;
  anchor: string;
  navigation: {
    label: string;
    previousAnchor: string;
    nextAnchor: string;
    canNext: boolean;
  };
  axis: { start: string | null; end: string | null; seconds: number };
  current: ComparisonSummary;
  comparison: ComparisonSummary;
  delta: ComparisonDelta;
  lanes: ComparisonLane[];
  referenceComparisons?: ComparisonReference[];
};

export type YearPoint = {
  day: number;
  cumulativeAmount: number;
};

export type YearSeries = {
  key: string;
  source: string;
  year: number;
  label: string;
  color: string;
  daysInYear: number;
  asOfDay: number;
  daysWithData: number;
  totalAmount: number;
  points: YearPoint[];
};

export type YearComparisonResponse = {
  title: string;
  anchorYear: number;
  comparisonYear: number;
  navigation: {
    label: string;
    previousAnchor: string;
    nextAnchor: string;
    canNext: boolean;
  };
  axis: { days: number };
  availableYears: number[];
  series: YearSeries[];
  selected: YearSeries;
  comparison: YearSeries;
  comparisonFull: YearSeries;
  delta: { amount: number };
  asOf: {
    selectedLabel: string;
    selectedDate: string;
    comparisonLabel: string;
    comparisonDate: string;
  };
};
