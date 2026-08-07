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
  step?: "start" | "middle" | "end";
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
  rows: ModuleRow[];
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

export type ParkingTimelineItem = {
  id: string;
  left: number;
  width: number;
  label: string;
  plate?: string | null;
  title: string;
  kind: "paid" | "ongoing" | "unpaid" | "overflow";
  start?: string | null;
  end?: string | null;
  durationMinutes: number;
  paid: number;
  status?: string | null;
  href: string;
};

export type ParkingTimelineSpace = {
  spaceId: string;
  label: string;
  sessions: ParkingTimelineItem[];
};

export type ParkingTimeline = {
  selectedDay: string;
  selectedDayLabel: string;
  prevDay: string;
  nextDay: string;
  capacity: number;
  occupancyScaleMax: number;
  spaceRows: Array<{ key: string; label: string; spaces: ParkingTimelineSpace[] }>;
  overflowSessions: ParkingTimelineItem[];
  occupancy: Array<{ left: number; width: number; count: number; height: number; title: string }>;
  ticks: Array<{ label: string; left: number }>;
  nowMarker: number | null;
  summary: {
    sessionsCount: number;
    paidAmountKr: number;
    durationMinutes: number;
    durationHours: number;
    avgMinutes: number;
    peakCount: number;
    peakTimeLabel?: string | null;
    utilizationPercent: number;
    overflowCount: number;
  };
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
  parkingTimeline?: ParkingTimeline | null;
  uploadEndpoint?: string;
};

export type ParkingYearPoint = {
  day: number;
  cumulativeAmount: number;
  cumulativeCount: number;
  cumulativeMinutes: number;
};

export type ParkingYearSeries = {
  key: string;
  year: number;
  label: string;
  daysWithData: number;
  totalAmount: number;
  totalCount: number;
  totalMinutes: number;
  points: ParkingYearPoint[];
};

export type ParkingYearComparisonResponse = {
  anchorYear: number;
  comparisonYear: number;
  navigation: { label: string; previousAnchor: string; nextAnchor: string; canPrevious: boolean; canNext: boolean };
  axis: { days: number };
  availableYears: number[];
  series: ParkingYearSeries[];
  selected: ParkingYearSeries;
  comparison: ParkingYearSeries;
  comparisonFull: ParkingYearSeries;
  delta: { amount: number; count: number; minutes: number };
};

export type ParkingTimeCell = {
  weekdayIndex: number;
  weekday: string;
  hour: number;
  hourLabel: string;
  sessions: number;
  paid: number;
  minutes: number;
  hours: number;
  avgPaidPerSession: number;
  avgMinutesPerSession: number;
  avgPaidPerDay: number;
  avgSessionsPerDay: number;
  avgMinutesPerDay: number;
};

export type ParkingTimeDistributionResponse = {
  period: { key: string; label: string; dateFrom: string; dateTo: string; daysCount: number; detail: string; options: Array<{ key: string; label: string }> };
  summary: { sessions: number; paid: number; minutes: number; hours: number; avgPaidPerSession: number; avgMinutesPerSession: number; avgPaidPerDay: number; avgSessionsPerDay: number };
  weekdays: Array<ParkingTimeCell & { days: number; hours: ParkingTimeCell[] }>;
  hours: ParkingTimeCell[];
  topSlots: ParkingTimeCell[];
};

export type ParkingWeeklyPoint = {
  key: string;
  label: string;
  shortLabel: string;
  rangeLabel: string;
  sessions: number;
  paid: number;
  minutes: number;
  durationCoveragePct: number;
  avgPaidPerSession: number | null;
  avgMinutesPerSession: number | null;
  isPartial: boolean;
};

export type ParkingWeeklyAveragesResponse = {
  period: { key: string; label: string; dateFrom: string; dateTo: string; detail: string; options: Array<{ key: string; label: string }> };
  summary: { sessions: number; paid: number; minutes: number; durationCoveragePct: number; avgPaidPerSession: number; avgMinutesPerSession: number; weeksWithData: number };
  latest: ParkingWeeklyPoint | null;
  previous: ParkingWeeklyPoint | null;
  delta: { paidPct: number | null; minutesPct: number | null };
  weeks: ParkingWeeklyPoint[];
};

export type ParkingWeeklyYearSeries = {
  year: number;
  label: string;
  sessions: number;
  weeksWithData: number;
  durationCoveragePct: number;
  avgPaidPerSession: number;
  avgMinutesPerSession: number;
  points: Array<{ week: number; avgPaidPerSession: number | null; avgMinutesPerSession: number | null; isAvailable: boolean }>;
};

export type ParkingWeeklyYearComparisonResponse = {
  currentYear: number;
  availableYears: number[];
  defaultYears: number[];
  selectedYears: number[];
  series: ParkingWeeklyYearSeries[];
};

export type ParkingVehicleDetailResponse = {
  plate: string;
  title: string;
  subtitle: string;
  cards: ModuleCard[];
  fields: Array<{ label: string; value: unknown; detail?: string }>;
  warnings: string[];
  sessions: ModuleRow[];
  actions?: ModuleAction[];
};

export type ParkingLookupRow = {
  plate: string;
  navn?: string | null;
  omrade?: string | null;
  vehicle?: string | null;
  make?: string | null;
  model?: string | null;
  year?: number | null;
  parkering_count?: number | null;
  last_seen?: string | null;
};

export type ParkingLookupResponse = {
  count: number;
  limit: number;
  offset: number;
  rows: ParkingLookupRow[];
};

export type SettlementDetailResponse = {
  id: number;
  title: string;
  subtitle: string;
  cards: ModuleCard[];
  original: { filename: string; contentType: string; sizeLabel: string; previewKind: "pdf" | "image" | "text" | "unsupported"; previewUrl: string; downloadUrl: string };
  sections: Array<{ title: string; rows: Array<{ label: string; value: unknown; detail?: string }> }>;
  raw: JsonRecord;
};

export type CarsDayDetection = {
  recognitionId?: number | null;
  occurredAt?: string | null;
  cameraName?: string | null;
  observedPlate?: string | null;
  unifiScore?: number | null;
  snapshotStatus?: string | null;
  snapshotUrl?: string | null;
};

export type CarsDayDetectionsResponse = {
  plate: string;
  selectedDay: string;
  detectionCount: number;
  detections: CarsDayDetection[];
};

export type CarsRegistryValidation = {
  status: string;
  is_valid?: boolean | null;
  country_code?: string | null;
  country?: string | null;
  source?: string | null;
  vehicle_label?: string | null;
  local_match: boolean;
  message: string;
};

export type CarsDayItem = {
  plate: string;
  displayValue: string;
  detectionCount: number;
  firstDetectedAt?: string | null;
  lastDetectedAt?: string | null;
  knownInProtect: boolean;
  cameraNames: string[];
  detections: CarsDayDetection[];
  averageUnifiScore?: number | null;
  maximumUnifiScore?: number | null;
  observedPlateValues: string[];
  mergedVariantCount: number;
  requiresReview: boolean;
  registryValidation: CarsRegistryValidation;
  vehicle?: { name?: string | null; area?: string | null; title?: string | null; path: string } | null;
  hasPaidSession: boolean;
  paidSessionCount: number;
  paidTotalKr: number;
  paymentStatus: string;
};

export type CarsDayResponse = {
  generatedAt?: string | null;
  selectedDay: string;
  selectedDayLabel: string;
  prevDay: string;
  nextDay: string;
  isToday: boolean;
  matchPolicy: { label: string; detail: string };
  observationWindow: { firstDetectedAt?: string | null; lastDetectedAt?: string | null; spanMinutes: number };
  summary: {
    uniquePlates: number;
    detections: number;
    paidPlates: number;
    coveredPlates: number;
    withoutPayment: number;
    mergedOcrVariants: number;
    reviewPlates: number;
    validatedPlates: number;
    likelyMisreads: number;
    pendingValidation: number;
  };
  items: CarsDayItem[];
};
