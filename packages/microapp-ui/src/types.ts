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
  hidden?: boolean;
};

export type ModuleChart = {
  title: string;
  subtitle?: string;
  type?: "line" | "bar";
  x: string[];
  height?: number;
  series: ModuleChartSeries[];
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

export type SunTimeline = {
  selectedDay: string;
  selectedDayLabel: string;
  prevDay: string;
  nextDay: string;
  rooms: SunTimelineRoom[];
  aggregateSessions: SunTimelineItem[];
  totals: { sessionsCount: number; durationMinutes: number; durationHours: number; paidAmountKr: number };
  ticks: Array<{ label: string; left: number }>;
  nowMarker: number | null;
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
  ventilation?: VentilationData | null;
  controlSettings?: ControlSettings | null;
  energySunbeds?: EnergySunbedsData | null;
  energyCircuitLoads?: EnergyCircuitLoadsData | null;
  uploadEndpoint?: string;
};

export type VentilationMeasurement = { key: string; label: string; temperature?: number | null; humidity?: number | null; detail?: string };
export type VentilationMeasurementGroup = { key: string; title: string; fields: VentilationMeasurement[] };
export type VentilationFan = { key: string; label: string; state: boolean | null; detail?: string; statusSource?: string | null; checkedAt?: string | null };
export type VentilationDaySeries = { key: string; label: string; kind?: "temperature" | "humidity"; unit?: string; color: string; default?: boolean };
export type VentilationFanEvent = { fan_key: string; fan_name: string; fan_short: string; color: string; x: number; time: string; action: string; class: "on" | "off"; detail: string };
export type SettingField = { key: string; label: string; type: "time" | "int" | "float" | "bool" | "text"; unit?: string; help?: string; value: string | number | boolean | null };
export type SettingsData = { version: number; updatedAt?: string | null; updatedBy?: string | null; groups: Array<{ title: string; description?: string; fields: SettingField[] }>; rules: string[]; updateEndpoint: string };
export type ControlSettings = SettingsData & { system: string; title: string; subtitle?: string };
export type VentilationData = {
  view: string;
  latest: {
    bucketStart?: string | null;
    mode?: string | null;
    groups: VentilationMeasurementGroup[];
    fans: VentilationFan[];
    weather: { text?: string | null; airTemperature?: number | null; relativeHumidity?: number | null; windSpeed?: number | null; cloudAreaFraction?: number | null };
  };
  day: {
    selectedDay: string;
    selectedDayLabel: string;
    prevDay: string;
    nextDay: string;
    isToday: boolean;
    nowMarker: number | null;
    series: VentilationDaySeries[];
    fans: Array<{ key: string; name: string; short?: string; color?: string; sample_attr?: string }>;
    fanEvents: VentilationFanEvent[];
    samples: JsonRecord[];
  };
  settings?: SettingsData;
};

export type EnergySunbedRoom = { room_id?: string | null; label: string; sun2_bed_id?: string | null; bed_model?: string | null; samples_count: number; sessions_count: number; avg_w?: number | null; estimate_w?: number | null; p25_w?: number | null; p75_w?: number | null; kwh_15_min?: number | null; estimated_kwh?: number | null; confidence: string };
export type EnergySunbedObservation = { session_id: number; label: string; start: string | null; duration_minutes?: number | null; samples_count: number; avg_w?: number | null; avg_observed_w?: number | null; avg_baseline_w?: number | null; estimated_kwh?: number | null };
export type EnergySunbedsData = { dateFrom: string; dateTo: string; maxDays: number; maxPower: number; rooms: EnergySunbedRoom[]; observations: EnergySunbedObservation[]; summary: JsonRecord };
export type EnergyLoadItem = { id: number; name: string; loadType?: string | null; area?: string | null; powerProfile?: string | null; expectedPowerW?: number | null; minPowerW?: number | null; maxPowerW?: number | null; energyNodeId?: number | null; active?: boolean | null; critical?: boolean | null; note?: string | null };
export type EnergyNode = { id: number; name: string; circuitNo?: number | null; parentNodeId?: number | null; nodeType: string; manufacturer?: string | null; model?: string | null; hc3DeviceId?: number | null; hc3PowerDeviceId?: number | null; hc3EnergyDeviceId?: number | null; hc3SwitchDeviceId?: number | null; hasMeter: boolean; hasSwitch: boolean; active: boolean; currentPowerW?: number | null; switchState?: boolean | null; liveStatus?: string | null; loads: EnergyLoadItem[]; children: EnergyNode[] };
export type EnergyCircuit = { key: string; circuitNo?: number | null; description?: string | null; breaker?: string | null; status?: string | null; isSunbed: boolean; loadCount: number; nodeCount: number; expectedPowerW: number; currentPowerW?: number | null; measurementMode: string; measurementDetail: string; directLoads: EnergyLoadItem[]; nodes: EnergyNode[] };
export type EnergyCircuitLoadsData = { canManage?: boolean; summary: JsonRecord; aggregateMeters: Array<{ key: string; label: string; realtimeId: number; accumulatedId: number; description?: string | null; mappedNodeCount?: number }>; circuits: EnergyCircuit[] };

export type OperationsOverviewResponse = {
  generatedAt: string;
  operatingWindow: { label: string; detail: string; open: boolean };
  cards: Array<ModuleCard & { group?: string }>;
  latestItems: Array<{ label: string; value: string; detail?: string; href?: string }>;
  services: Array<{
    sourceNo?: number;
    jobName?: string;
    label: string;
    status: string;
    detail?: string;
    lastSuccessAt?: string | null;
    nextExpectedAt?: string | null;
  }>;
  lightItems: Array<{ label: string; state: boolean | null; tooltip?: string | null }>;
  fanItems: Array<{
    label: string;
    state: boolean | null;
    tooltip?: string | null;
    statusSource?: string | null;
    checkedAt?: string | null;
  }>;
};

export type Accent = "violet" | "sky" | "yellow" | "green" | "red";

export type NavigationItem = {
  to: string;
  label: string;
  icon: import("./components/MosaicIcon").IconName;
  title: string;
  description: string;
  module: string;
  view: string;
  corePath?: string;
};

export type NavigationGroup = { label: string; items: NavigationItem[] };

export type DomainUiConfig = {
  name: string;
  shortName: string;
  icon: import("./components/MosaicIcon").IconName;
  accent: Accent;
  navigation: NavigationGroup[];
};
