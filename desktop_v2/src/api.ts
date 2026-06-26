export type JsonRecord = Record<string, unknown>;
export type ModuleRow = JsonRecord;

export type MetricCard = {
  group: string;
  title: string;
  value: string;
  unit?: string;
  detail?: string;
  href?: string;
  tone?: string;
};

export type LatestItem = {
  label: string;
  value: string;
  detail?: string;
  href?: string;
};

export type ServiceStatus = {
  sourceNo?: number | null;
  jobName?: string;
  label: string;
  status: "ok" | "warn" | "bad" | "unknown";
  detail: string;
  ageMinutes?: number | null;
};

export type StatusPeriodComparison = {
  label: string;
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  total: number;
  solAsOfLabel: string;
  parkingAsOfLabel: string;
};

export type StatusPeriod = {
  key: string;
  title: string;
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  total: number;
  previousSol: number;
  previousSolCount: number;
  previousParking: number;
  previousParkingCount: number;
  previousTotal: number;
  previousLabel: string;
  solAsOfLabel: string;
  parkingAsOfLabel: string;
  previousSolAsOfLabel: string;
  previousParkingAsOfLabel: string;
  extraComparisons?: StatusPeriodComparison[];
};

export type OverviewResponse = {
  generatedAt: string;
  operatingWindow: { label: string; detail: string; open: boolean };
  cards: MetricCard[];
  statusPeriods: StatusPeriod[];
  latestItems: LatestItem[];
  services: ServiceStatus[];
  lightItems: { label: string; state: boolean | null }[];
  fanItems: { label: string; state: boolean | null }[];
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

export type StatusComparisonEvent = {
  id: string;
  kind: string;
  left: number;
  width: number;
  label: string;
  title: string;
  start: string | null;
  end: string | null;
  amount: number;
  href?: string;
};

export type StatusComparisonLane = {
  key: string;
  source: "current" | "comparison" | "reference";
  label: string;
  periodLabel: string;
  kind: "sun" | "parking";
  start: string | null;
  end: string | null;
  endLeft?: number;
  count: number;
  paid: number;
  events: StatusComparisonEvent[];
};

export type StatusComparisonSummary = {
  label: string;
  start: string | null;
  sunEnd: string | null;
  parkingEnd: string | null;
  solAsOfLabel: string;
  parkingAsOfLabel: string;
  sol: number;
  solCount: number;
  parking: number;
  parkingCount: number;
  total: number;
};

export type StatusComparisonReference = {
  key: string;
  label: string;
  summary: StatusComparisonSummary;
  delta: {
    sol: number;
    solCount: number;
    parking: number;
    parkingCount: number;
    total: number;
  };
  lanes: StatusComparisonLane[];
};

export type StatusComparisonResponse = {
  generatedAt: string | null;
  periodKey: string;
  comparisonKey: string;
  anchor: string;
  title: string;
  comparisonLabel: string;
  navigation: {
    anchor: string;
    label: string;
    previousAnchor: string;
    nextAnchor: string;
    canPrevious: boolean;
    canNext: boolean;
    previousLabel: string;
    nextLabel: string;
  };
  axis: {
    start: string | null;
    end: string | null;
    seconds: number;
    ticks: Array<{ label: string; left: number }>;
  };
  current: StatusComparisonSummary;
  comparison: StatusComparisonSummary;
  delta: {
    sol: number;
    solCount: number;
    parking: number;
    parkingCount: number;
    total: number;
  };
  lanes: StatusComparisonLane[];
  referenceComparisons?: StatusComparisonReference[];
};

export type SunYearComparisonPoint = {
  day: number;
  date: string;
  label: string;
  amount: number;
  count: number;
  minutes: number;
  cumulativeAmount: number;
  cumulativeCount: number;
  cumulativeMinutes: number;
};

export type SunYearComparisonSeries = {
  key: string;
  source: "current" | "comparison" | "comparison-full" | "reference";
  year: number;
  label: string;
  color: string;
  daysInYear: number;
  asOfDay: number;
  daysWithData: number;
  totalAmount: number;
  totalCount: number;
  totalMinutes: number;
  points: SunYearComparisonPoint[];
};

export type SunYearComparisonResponse = {
  generatedAt: string | null;
  title: string;
  anchorYear: number;
  comparisonYear: number;
  navigation: {
    anchor: string;
    label: string;
    previousAnchor: string;
    nextAnchor: string;
    canPrevious: boolean;
    canNext: boolean;
    previousLabel: string;
    nextLabel: string;
  };
  axis: {
    days: number;
    ticks: Array<{ label: string; day: number }>;
  };
  availableYears: number[];
  series: SunYearComparisonSeries[];
  selected: SunYearComparisonSeries;
  comparison: SunYearComparisonSeries;
  comparisonFull: SunYearComparisonSeries;
  delta: {
    amount: number;
    count: number;
    minutes: number;
  };
  asOf: {
    selectedLabel: string;
    selectedDate: string;
    comparisonLabel: string;
    comparisonDate: string;
  };
};

export type ParkingYearComparisonPoint = SunYearComparisonPoint;
export type ParkingYearComparisonSeries = SunYearComparisonSeries;
export type ParkingYearComparisonResponse = SunYearComparisonResponse;
export type RevenueYearComparisonPoint = SunYearComparisonPoint;
export type RevenueYearComparisonSeries = SunYearComparisonSeries;
export type RevenueYearComparisonResponse = SunYearComparisonResponse;

export type AuthUser = {
  username: string | null;
  role: string;
  roleLabel: string;
  isMaster: boolean;
  canSettings: boolean;
  appBuild: string;
};

export type MobilePreviewScreen = {
  key: string;
  title: string;
  subtitle: string;
  sourcePath: string;
  frameUrl: string;
};

export type MobilePreviewResponse = {
  refreshSeconds: number;
  screens: MobilePreviewScreen[];
};

export type BuildLogEntry = {
  version: string;
  build: string;
  date: string;
  headline: string;
  title: string;
  description: string;
  applications: string[];
  changes: string[];
  request: string;
  workDuration: string;
  creditsUsed: string;
  path: string;
  isCurrent: boolean;
};

export type BuildLogResponse = {
  currentBuild: string;
  rows: BuildLogEntry[];
};

export type HealthStatus = "ok" | "warn" | "bad";

export type HealthCheck = {
  status?: string;
  detail?: string;
  [key: string]: unknown;
};

export type HealthSource = {
  jobName?: string;
  title?: string;
  label?: string;
  status?: string;
  detail?: string;
  ageMinutes?: number | null;
  [key: string]: unknown;
};

export type HealthResponse = {
  status: HealthStatus;
  app: {
    version: string;
    build: string;
    commit: string;
    startedAt: string;
  };
  checks: Record<string, HealthCheck>;
  sources: HealthSource[];
  storage: string[];
};

export type ModuleCard = {
  title: string;
  value: string;
  unit?: string;
  detail?: string;
  tone?: string;
  href?: string;
};

export type ModuleTable = {
  title: string;
  columns: string[];
  rows: ModuleRow[];
  edit?: ModuleEditConfig;
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
  dayNavigation?: {
    selectedDay: string;
    selectedDayLabel: string;
    prevDay: string;
    nextDay: string;
    isToday?: boolean;
  };
};

export type ModuleEditField = {
  key: string;
  label: string;
  type: "text" | "textarea" | "number" | "boolean" | "select" | "password";
  required?: boolean;
  options?: Array<{ label: string; value: string | number | boolean }>;
};

export type ModuleEditConfig = {
  kind: string;
  title: string;
  idField?: string;
  endpoint: string;
  method?: "PATCH" | "POST";
  createEndpoint?: string;
  fields: ModuleEditField[];
  createFields?: ModuleEditField[];
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
};

export type SunSessionSnapshot = {
  id: string;
  capturedAt: string;
  label: string;
  filename?: string;
  imageUrl: string;
  deltaSeconds?: number | null;
  isLinked?: boolean;
  source?: string;
};

export type SunSessionSavedImage = {
  id: number;
  snapshotId: string;
  capturedAt: string | null;
  label: string;
  imageUrl: string;
  offsetSeconds: number;
  offsetLabel: string;
  deltaSeconds?: number | null;
  isPrimary?: boolean;
  source?: string;
};

export type SunSessionImageBrowser = {
  sessionId: number;
  startedAt: string | null;
  targetAt: string | null;
  targetLabel: string;
  seriesOffsets: number[];
  snapshotRoot: string;
  archiveDay?: string;
  snapshotsFound: number;
  linked: SunSessionSavedImage | null;
  savedImages: SunSessionSavedImage[];
  current: SunSessionSnapshot | null;
  previousSnapshotId: string | null;
  nextSnapshotId: string | null;
  canPrevious: boolean;
  canNext: boolean;
};

export type SunTimelineItem = {
  left: number;
  width: number;
  label: string;
  title: string;
  kind: "standard" | "member" | "no-member";
  href: string;
};

export type SunTimelineRoom = {
  roomId: string;
  label: string;
  sessions: SunTimelineItem[];
  count: number;
  minutes: number;
  paid: number;
};

export type SunTimelineEnergyHour = {
  hour: number;
  left: number;
  width: number;
  height: number;
  internalHeight: number;
  consumptionKwh: number;
  productionKwh: number;
  internalKwh: number;
  internalSamples: number;
  title: string;
};

export type SunTimeline = {
  selectedDay: string;
  selectedDayLabel: string;
  prevDay: string;
  nextDay: string;
  rooms: SunTimelineRoom[];
  aggregateSessions: SunTimelineItem[];
  totals: {
    sessionsCount: number;
    durationMinutes: number;
    durationHours: number;
    paidAmountKr: number;
  };
  busiestRoom: SunTimelineRoom | null;
  topRevenueRoom: SunTimelineRoom | null;
  ticks: Array<{ label: string; left: number }>;
  nowMarker: number | null;
  energyHours: SunTimelineEnergyHour[];
  energySummary: {
    hoursCount: number;
    totalKwh: number;
    maxKwh: number;
    peakHour: SunTimelineEnergyHour | null;
    internalHoursCount: number;
    internalTotalKwh: number;
    internalMaxKwh: number;
    internalSamples: number;
    internalPeakHour: SunTimelineEnergyHour | null;
  };
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
  area?: string | null;
  owner?: string | null;
  ownerArea?: string | null;
  href: string;
  spaceId?: string;
};

export type ParkingTimelineSpace = {
  spaceId: string;
  label: string;
  rowKey: string;
  rowLabel: string;
  sessions: ParkingTimelineItem[];
  count: number;
  minutes: number;
  paid: number;
};

export type ParkingTimelineSpaceRow = {
  key: string;
  label: string;
  count: number;
  spaces: ParkingTimelineSpace[];
};

export type ParkingTimeline = {
  selectedDay: string;
  selectedDayLabel: string;
  prevDay: string;
  nextDay: string;
  capacity: number;
  occupancyScaleMax: number;
  layout: Array<{ key: string; label: string; count: number }>;
  spaceRows: ParkingTimelineSpaceRow[];
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

export type VentilationMeasurement = {
  key: string;
  label: string;
  temperature?: number | null;
  humidity?: number | null;
  detail?: string;
};

export type VentilationMeasurementGroup = {
  key: string;
  title: string;
  fields: VentilationMeasurement[];
};

export type VentilationFan = {
  key: string;
  label: string;
  state: boolean | null;
  detail?: string;
};

export type VentilationWeather = {
  bucketStart?: string | null;
  text?: string | null;
  airTemperature?: number | null;
  relativeHumidity?: number | null;
  windSpeed?: number | null;
  windGust?: number | null;
  cloudAreaFraction?: number | null;
  precipitationNext1h?: number | null;
};

export type VentilationLatest = {
  bucketStart?: string | null;
  timestamp?: string | null;
  mode?: string | null;
  source?: string | null;
  groups: VentilationMeasurementGroup[];
  fans: VentilationFan[];
  weather: VentilationWeather;
};

export type VentilationDaySeries = {
  key: string;
  label: string;
  kind?: "temperature" | "humidity";
  unit?: string;
  color: string;
  default?: boolean;
  latest?: string;
  min?: string;
  max?: string;
};

export type VentilationFanEvent = {
  fan_key: string;
  fan_name: string;
  fan_short: string;
  color: string;
  x: number;
  time: string;
  action: string;
  class: "on" | "off";
  detail: string;
};

export type VentilationDay = {
  selectedDay: string;
  selectedDayLabel: string;
  prevDay: string;
  nextDay: string;
  isToday: boolean;
  nowMarker: number | null;
  summary: JsonRecord;
  series: VentilationDaySeries[];
  fans: Array<{ key: string; name: string; short?: string; color?: string; sample_attr?: string; default?: boolean }>;
  fanEvents: VentilationFanEvent[];
  samples: JsonRecord[];
};

export type VentilationSettingField = {
  key: string;
  label: string;
  type: "time" | "int" | "float" | "bool" | "text";
  unit?: string;
  help?: string;
  value: string | number | boolean | null;
};

export type VentilationSettingGroup = {
  title: string;
  description?: string;
  fields: VentilationSettingField[];
};

export type VentilationSettings = {
  version: number;
  updatedAt?: string | null;
  updatedBy?: string | null;
  groups: VentilationSettingGroup[];
  rules: string[];
  summaryRows: JsonRecord[];
  notes: Array<{ title: string; text: string }>;
  history: JsonRecord[];
  updateEndpoint: string;
};

export type VentilationData = {
  view: string;
  latest: VentilationLatest;
  day: VentilationDay;
  settings?: VentilationSettings;
};

export type EnergyElviaSummaryItem = {
  period?: string | null;
  period_label?: string | null;
  consumption_kwh: number;
  production_kwh: number;
  hours_count: number;
  estimated_hours_count: number;
  days_count: number;
};

export type EnergyElviaStatus = {
  jobName?: string | null;
  title?: string | null;
  status?: string | null;
  statusText?: string | null;
  source?: string | null;
  message?: string | null;
  lastRunAt?: string | null;
  lastStartedAt?: string | null;
  lastSuccessAt?: string | null;
  lastFailedAt?: string | null;
  recordsImported?: number | null;
  recordsTotal?: number | null;
  durationSeconds?: number | null;
};

export type EnergyElviaData = {
  summary: {
    total: EnergyElviaSummaryItem;
    firstAt?: string | null;
    lastAt?: string | null;
  };
  yearly: EnergyElviaSummaryItem[];
  topDays: EnergyElviaSummaryItem[];
  topMonths: EnergyElviaSummaryItem[];
  imports: JsonRecord[];
  rows: JsonRecord[];
  latestImport?: JsonRecord | null;
  status?: EnergyElviaStatus | null;
  uploadEndpoint: string;
};

export type EnergySunbedSummary = {
  sessions_total: number;
  energy_samples_total: number;
  roof_exhaust_adjusted_samples: number;
  roof_exhaust_adjustment_w: number;
  baseline_samples: number;
  single_samples: number;
  overlap_samples: number;
  missing_baseline_samples: number;
  rejected_low_samples: number;
  rejected_warmup_cooldown_samples: number;
  rejected_short_sessions: number;
  rejected_short_samples: number;
  global_baseline_w?: number | null;
  rooms_count: number;
  warmup_minutes: number;
  cooldown_minutes: number;
  stop_before_end_minutes: number;
  min_samples_per_session: number;
  sample_interval_seconds: number;
};

export type EnergySunbedRoom = {
  room_id?: string | null;
  label: string;
  sun2_bed_id?: string | null;
  bed_model?: string | null;
  samples_count: number;
  sessions_count: number;
  duration_minutes?: number | null;
  avg_w?: number | null;
  median_w?: number | null;
  estimate_w?: number | null;
  p25_w?: number | null;
  p75_w?: number | null;
  min_w?: number | null;
  max_w?: number | null;
  avg_observed_w?: number | null;
  avg_baseline_w?: number | null;
  kwh_10_min?: number | null;
  kwh_15_min?: number | null;
  kwh_20_min?: number | null;
  estimated_kwh?: number | null;
  confidence: string;
};

export type EnergySunbedObservation = {
  session_id: number;
  room_id?: string | null;
  label: string;
  start: string | null;
  end: string | null;
  duration_minutes?: number | null;
  samples_count: number;
  avg_w?: number | null;
  median_w?: number | null;
  avg_observed_w?: number | null;
  avg_baseline_w?: number | null;
  estimated_kwh?: number | null;
};

export type EnergySunbedsData = {
  dateFrom: string;
  dateTo: string;
  maxDays: number;
  maxPower: number;
  rooms: EnergySunbedRoom[];
  observations: EnergySunbedObservation[];
  summary: EnergySunbedSummary;
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
  sunTimeline?: SunTimeline | null;
  parkingTimeline?: ParkingTimeline | null;
  ventilation?: VentilationData;
  energyElvia?: EnergyElviaData | null;
  energySunbeds?: EnergySunbedsData | null;
  uploadEndpoint?: string;
};

export type ParkingVehicleField = {
  label: string;
  value: unknown;
  detail?: string;
};

export type ParkingVehicleDetailResponse = {
  plate: string;
  title: string;
  subtitle: string;
  cards: ModuleCard[];
  fields: ParkingVehicleField[];
  warnings: string[];
  sessions: ModuleRow[];
  actions?: ModuleAction[];
};

export type SettlementField = {
  label: string;
  field: string;
  value: unknown;
  source: string;
  note?: string;
  confidence?: number | null;
  group?: "amount" | "control";
  expected?: unknown;
  expectedLabel?: string;
  expectedSource?: string;
  expectedDetail?: string;
  difference?: unknown;
  status?: "ok" | "warn" | "missing" | string;
};

export type SettlementSection = {
  title: string;
  rows: SettlementField[];
};

export type SettlementOriginal = {
  filename: string;
  contentType: string;
  size?: number | null;
  sizeLabel: string;
  sha256?: string | null;
  previewKind: "pdf" | "image" | "text" | "unsupported";
  previewUrl: string;
  downloadUrl: string;
};

export type SettlementDetailResponse = {
  id: number;
  title: string;
  subtitle: string;
  cards: ModuleCard[];
  original: SettlementOriginal;
  sections: SettlementSection[];
  raw: JsonRecord;
};

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    const errorPayload = payload as { detail?: unknown; message?: unknown } | null;
    const message = errorPayload
      ? String(errorPayload.message || errorPayload.detail || `${response.status} ${response.statusText}`)
      : `${response.status} ${response.statusText}`;
    throw new Error(message);
  }
  return payload as T;
}

export function fetchOverview(): Promise<OverviewResponse> {
  return apiGet<OverviewResponse>("/api/overview");
}

export function fetchRevenueMonth(month?: string): Promise<RevenueMonthResponse> {
  const query = month ? `?month=${encodeURIComponent(month)}` : "";
  return apiGet<RevenueMonthResponse>(`/api/revenue/month${query}`);
}

export function fetchStatusComparison(period: string, compare: string, anchor?: string | null): Promise<StatusComparisonResponse> {
  const queryParams = new URLSearchParams({ period, compare });
  if (anchor) queryParams.set("anchor", anchor);
  const query = queryParams.toString();
  return apiGet<StatusComparisonResponse>(`/api/status/comparison?${query}`);
}

export function fetchSunYearComparison(year?: string | null): Promise<SunYearComparisonResponse> {
  const query = year ? `?year=${encodeURIComponent(year)}` : "";
  return apiGet<SunYearComparisonResponse>(`/api/soling/year-comparison${query}`);
}

export function fetchParkingYearComparison(year?: string | null): Promise<ParkingYearComparisonResponse> {
  const query = year ? `?year=${encodeURIComponent(year)}` : "";
  return apiGet<ParkingYearComparisonResponse>(`/api/parkering/year-comparison${query}`);
}

export function fetchRevenueYearComparison(year?: string | null): Promise<RevenueYearComparisonResponse> {
  const query = year ? `?year=${encodeURIComponent(year)}` : "";
  return apiGet<RevenueYearComparisonResponse>(`/api/omsetning/year-comparison${query}`);
}

export function fetchCurrentUser(): Promise<AuthUser> {
  return apiGet<AuthUser>("/api/auth/me");
}

export function fetchMobilePreviewScreens(): Promise<MobilePreviewResponse> {
  return apiGet<MobilePreviewResponse>("/api/mobile-preview/screens");
}

export function fetchBuildLog(): Promise<BuildLogResponse> {
  return apiGet<BuildLogResponse>("/api/admin/builds");
}

export function fetchBuildLogEntry(build: string): Promise<BuildLogEntry> {
  return apiGet<BuildLogEntry>(`/api/admin/builds/${encodeURIComponent(build)}`);
}

export function fetchHealth(details = false): Promise<HealthResponse> {
  return apiGet<HealthResponse>(`/health${details ? "?details=true" : ""}`);
}

export async function logoutUser(): Promise<void> {
  const response = await fetch("/konto/logg-ut", {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "text/html" },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
}

export function fetchModule(
  module: string,
  view?: string,
  q?: string,
  day?: string,
  filters?: URLSearchParams,
): Promise<ModuleResponse> {
  const params = new URLSearchParams(filters);
  if (view) params.set("view", view);
  if (q?.trim()) params.set("q", q.trim());
  if (day) params.set("day", day);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiGet<ModuleResponse>(`/api/modules/${encodeURIComponent(module)}${query}`);
}

export function fetchParkingVehicleDetail(plate: string): Promise<ParkingVehicleDetailResponse> {
  return apiGet<ParkingVehicleDetailResponse>(`/api/parking/vehicles/${encodeURIComponent(plate)}`);
}

export function fetchSettlementDetail(settlementId: string): Promise<SettlementDetailResponse> {
  return apiGet<SettlementDetailResponse>(`/api/settlements/${encodeURIComponent(settlementId)}`);
}

export function fetchSunSettlementDetail(settlementId: string): Promise<SettlementDetailResponse> {
  return apiGet<SettlementDetailResponse>(`/api/soling/settlements/${encodeURIComponent(settlementId)}`);
}

export function fetchSunSessionImageBrowser(sessionId: number, snapshotId?: string | null): Promise<SunSessionImageBrowser> {
  const params = new URLSearchParams();
  if (snapshotId) params.set("snapshot_id", snapshotId);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiGet<SunSessionImageBrowser>(`/api/soling/enkeltimer/${encodeURIComponent(sessionId)}/image-browser${query}`);
}

export async function selectSunSessionImage(sessionId: number, snapshotId: string): Promise<SunSessionImageBrowser> {
  const params = new URLSearchParams({ snapshot_id: snapshotId });
  const response = await fetch(`/api/soling/enkeltimer/${encodeURIComponent(sessionId)}/image?${params.toString()}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  const payload = (await response.json().catch(() => null)) as JsonRecord | null;
  if (!response.ok) {
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`));
  }
  return (payload ?? {}) as SunSessionImageBrowser;
}

export async function setSunSessionPrimaryImage(sessionId: number, imageId: number): Promise<JsonRecord> {
  const response = await fetch(
    `/api/soling/enkeltimer/${encodeURIComponent(sessionId)}/bilder/${encodeURIComponent(imageId)}/primary`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    },
  );
  const payload = (await response.json().catch(() => null)) as JsonRecord | null;
  if (!response.ok) {
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`));
  }
  return payload ?? {};
}

export async function runModuleAction(action: ModuleAction): Promise<JsonRecord> {
  const response = await fetch(action.path, {
    method: action.method,
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  const payload = (await response.json().catch(() => null)) as JsonRecord | null;
  if (!response.ok) {
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`));
  }
  return payload ?? {};
}

function endpointFromTemplate(template: string, row: ModuleRow) {
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key: string) => encodeURIComponent(String(row[key] ?? "")));
}

export async function submitModuleEdit(
  edit: ModuleEditConfig,
  row: ModuleRow,
  values: JsonRecord,
  create = false,
): Promise<JsonRecord> {
  const endpoint = create && edit.createEndpoint ? edit.createEndpoint : endpointFromTemplate(edit.endpoint, row);
  const method = create && edit.createEndpoint ? "POST" : edit.method ?? "PATCH";
  const response = await fetch(endpoint, {
    method,
    credentials: "same-origin",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  const payload = (await response.json().catch(() => null)) as JsonRecord | null;
  if (!response.ok) {
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`));
  }
  return payload ?? {};
}

export async function saveConfig(
  endpoint: string,
  values: JsonRecord,
  reason: string,
): Promise<JsonRecord> {
  const response = await fetch(endpoint, {
    method: "PATCH",
    credentials: "same-origin",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ values, reason }),
  });
  const payload = (await response.json().catch(() => null)) as JsonRecord | null;
  if (!response.ok) {
    const errors = Array.isArray(payload?.errors) ? `: ${payload.errors.join(", ")}` : "";
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`) + errors);
  }
  return payload ?? {};
}

export async function uploadElviaFile(endpoint: string, file: File): Promise<JsonRecord> {
  return uploadFile(endpoint, file);
}

export async function uploadSettlementFile(endpoint: string, file: File): Promise<JsonRecord> {
  return uploadFile(endpoint, file);
}

async function uploadFile(endpoint: string, file: File): Promise<JsonRecord> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(endpoint, {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    body: form,
  });
  const payload = (await response.json().catch(() => null)) as JsonRecord | null;
  if (!response.ok) {
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`));
  }
  return payload ?? {};
}
