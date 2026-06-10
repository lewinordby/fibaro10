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
    maxTotal: number;
    topDay: RevenueDay | null;
    todayRow: RevenueDay | null;
  };
  rows: RevenueDay[];
};

export type AuthUser = {
  username: string | null;
  role: string;
  roleLabel: string;
  isMaster: boolean;
  canSettings: boolean;
  appBuild: string;
};

export type ModuleCard = {
  title: string;
  value: string;
  unit?: string;
  detail?: string;
  tone?: string;
};

export type ModuleTable = {
  title: string;
  columns: string[];
  rows: Record<string, unknown>[];
  edit?: ModuleEditConfig;
};

export type ModuleChartSeries = {
  name: string;
  data: Array<number | null>;
  type?: "line" | "bar";
  unit?: string;
  color?: string;
  yAxisIndex?: number;
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
  height?: number;
  series: ModuleChartSeries[];
  metrics?: ModuleChartMetric[];
  defaultMetric?: string;
  defaultVisibleSeries?: string[];
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
  consumptionKwh: number;
  productionKwh: number;
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
  ticks: Array<{ label: string; left: number }>;
  nowMarker: number | null;
  energyHours: SunTimelineEnergyHour[];
  energySummary: {
    hoursCount: number;
    totalKwh: number;
    maxKwh: number;
    peakHour: SunTimelineEnergyHour | null;
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
  summary: Record<string, unknown>;
  series: VentilationDaySeries[];
  fans: Array<{ key: string; name: string; short?: string; color?: string; default?: boolean }>;
  fanEvents: VentilationFanEvent[];
  samples: Record<string, unknown>[];
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
  summaryRows: Record<string, unknown>[];
  notes: Array<{ title: string; text: string }>;
  history: Record<string, unknown>[];
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
  imports: Record<string, unknown>[];
  rows: Record<string, unknown>[];
  latestImport?: Record<string, unknown> | null;
  status?: EnergyElviaStatus | null;
  uploadEndpoint: string;
};

export type ModuleResponse = {
  title: string;
  subtitle: string;
  cards: ModuleCard[];
  charts?: ModuleChart[];
  tables: ModuleTable[];
  actions?: ModuleAction[];
  filters?: ModuleFilter[];
  sunTimeline?: SunTimeline | null;
  ventilation?: VentilationData;
  energyElvia?: EnergyElviaData | null;
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
  sessions: Record<string, unknown>[];
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

export function fetchCurrentUser(): Promise<AuthUser> {
  return apiGet<AuthUser>("/api/auth/me");
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

export async function runModuleAction(action: ModuleAction): Promise<Record<string, unknown>> {
  const response = await fetch(action.path, {
    method: action.method,
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  const payload = (await response.json().catch(() => null)) as Record<string, unknown> | null;
  if (!response.ok) {
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`));
  }
  return payload ?? {};
}

function endpointFromTemplate(template: string, row: Record<string, unknown>) {
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key: string) => encodeURIComponent(String(row[key] ?? "")));
}

export async function submitModuleEdit(
  edit: ModuleEditConfig,
  row: Record<string, unknown>,
  values: Record<string, unknown>,
  create = false,
): Promise<Record<string, unknown>> {
  const endpoint = create && edit.createEndpoint ? edit.createEndpoint : endpointFromTemplate(edit.endpoint, row);
  const method = create && edit.createEndpoint ? "POST" : edit.method ?? "PATCH";
  const response = await fetch(endpoint, {
    method,
    credentials: "same-origin",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  const payload = (await response.json().catch(() => null)) as Record<string, unknown> | null;
  if (!response.ok) {
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`));
  }
  return payload ?? {};
}

export async function saveConfig(
  endpoint: string,
  values: Record<string, unknown>,
  reason: string,
): Promise<Record<string, unknown>> {
  const response = await fetch(endpoint, {
    method: "PATCH",
    credentials: "same-origin",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ values, reason }),
  });
  const payload = (await response.json().catch(() => null)) as Record<string, unknown> | null;
  if (!response.ok) {
    const errors = Array.isArray(payload?.errors) ? `: ${payload.errors.join(", ")}` : "";
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`) + errors);
  }
  return payload ?? {};
}

export async function uploadElviaFile(endpoint: string, file: File): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(endpoint, {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    body: form,
  });
  const payload = (await response.json().catch(() => null)) as Record<string, unknown> | null;
  if (!response.ok) {
    throw new Error(String(payload?.message || payload?.detail || `${response.status} ${response.statusText}`));
  }
  return payload ?? {};
}
