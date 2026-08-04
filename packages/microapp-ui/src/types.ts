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

export type SunSessionSnapshot = {
  id: string;
  capturedAt: string;
  label: string;
  filename: string;
  imageUrl: string;
  deltaSeconds: number | null;
  isLinked: boolean;
};

export type SunSessionImageBrowser = {
  sessionId: number;
  startedAt: string | null;
  targetAt: string | null;
  targetLabel: string;
  seriesOffsets: number[];
  snapshotRoot: string;
  archiveDay: string;
  snapshotsFound: number;
  linked: SunSessionSavedImage | null;
  savedImages: SunSessionSavedImage[];
  current: SunSessionSnapshot | null;
  previousSnapshotId: string | null;
  nextSnapshotId: string | null;
  canPrevious: boolean;
  canNext: boolean;
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
  kobleReview?: KobleReviewData | null;
  ventilation?: VentilationData | null;
  controlSettings?: ControlSettings | null;
  energyElvia?: EnergyElviaData | null;
  energySunbeds?: EnergySunbedsData | null;
  energyCircuitLoads?: EnergyCircuitLoadsData | null;
  systemNotifications?: SystemNotificationsData | null;
  systemSubsystems?: SystemSubsystemsData | null;
  roborock?: RoborockModuleData | null;
  uploadEndpoint?: string;
};

export type SystemNotificationChannel = {
  key: string;
  title: string;
  area: string;
  description: string;
  triggers: string[];
  priority: string;
  configured: boolean;
  publishingEnabled: boolean;
  subscribeUrl?: string;
  webUrl?: string;
};

export type SystemNotificationsData = {
  provider: string;
  providerUrl?: string;
  privacy: string;
  summary: { channels: number; configured: number; publishing: number };
  subscriptions: SystemNotificationChannel[];
  setup: string[];
};

export type SystemSubsystem = {
  component: string;
  title: string;
  area: string;
  role: string;
  runtime: string;
  compose_service?: string;
  status: string;
  criticality: string;
  access: "external" | "local" | "internal";
  primary_url?: string;
  links: Array<{ kind: "public" | "local" | "health"; label: string; url: string }>;
};

export type SystemSubsystemsData = {
  summary: { components: number; active: number; critical: number; web_interfaces: number };
  subsystems: SystemSubsystem[];
};

export type RoborockRobotSummary = {
  duid: string;
  name: string;
  model?: string | null;
  cloud_online?: boolean | null;
  local_ip?: string | null;
  last_seen_at?: string | null;
  last_error?: string | null;
  state_name?: string | null;
  battery?: number | null;
  error_code?: number | null;
  status_at?: string | null;
};

export type RoborockModuleData = { robots: RoborockRobotSummary[] };

export type RoborockRobotDetail = {
  robot: JsonRecord;
  metadata: JsonRecord;
  network: JsonRecord;
  latestStatus: JsonRecord | null;
  schedules: JsonRecord[];
  jobs: JsonRecord[];
  statuses: JsonRecord[];
  consumables: JsonRecord | null;
  latestMap: (JsonRecord & { imageDataUrl?: string | null }) | null;
};

export type ParkingTimeline = {
  selectedDay: string;
  selectedDayLabel: string;
  prevDay: string;
  nextDay: string;
  capacity: number;
  occupancyScaleMax: number;
  spaceRows: Array<{
    key: string;
    label: string;
    spaces: Array<{
      spaceId: string;
      label: string;
      sessions: Array<{
        id: string;
        left: number;
        width: number;
        title: string;
        kind: "paid" | "ongoing" | "unpaid" | "overflow";
        href: string;
      }>;
    }>;
  }>;
  overflowSessions: JsonRecord[];
  occupancy: Array<{ left: number; width: number; count: number; height: number; title: string }>;
  ticks: Array<{ label: string; left: number }>;
  nowMarker: number | null;
  summary: JsonRecord;
};

export type KobleReviewMatch = {
  id: number;
  parkingStartAt?: string | null;
  sunStartedAt?: string | null;
  deltaMinutes?: number | null;
  roomLabel?: string | null;
  userName?: string | null;
  durationMinutes?: number | null;
  paidAmountKr?: number | null;
  feeIncVat?: number | null;
  sourceSystem?: string | null;
};

export type KobleReviewCandidate = {
  id: number;
  status: string;
  confidence: number;
  assessment?: string | null;
  plate: string;
  sun2Id: string;
  vehicleName?: string | null;
  vehicleArea?: string | null;
  userName?: string | null;
  matchesCount: number;
  parkingMatchCount: number;
  matchDaysCount: number;
  plateCandidateCount: number;
  sun2CandidateCount: number;
  competitorMatchesCount: number;
  firstMatchAt?: string | null;
  lastMatchAt?: string | null;
  avgDeltaMinutes?: number | null;
  parkingCount?: number | null;
  paidTotal?: number | null;
  matchedPaidTotal?: number | null;
  note?: string | null;
  path?: string | null;
  matches: KobleReviewMatch[];
};

export type KobleQualifiedRow = {
  id: number;
  status: string;
  confidence: number;
  plate: string;
  sun2Id: string;
  vehicleName?: string | null;
  vehicleArea?: string | null;
  userName?: string | null;
  matchesCount: number;
  parkingMatchCount: number;
  matchDaysCount: number;
  lastMatchAt?: string | null;
  avgDeltaMinutes?: number | null;
  parkingCount?: number | null;
  paidTotal?: number | null;
  matchedPaidTotal?: number | null;
  path?: string | null;
};

export type KobleQualifiedSun2Row = KobleQualifiedRow & {
  sun2VehicleCount: number;
  parkingWithoutSunCount: number;
  parkingMatchShare: number;
};

export type KobleReviewData = {
  generatedAt?: string | null;
  generation: number;
  minMatches: number;
  maxMinutes: number;
  visibleCandidateCount: number;
  candidateCount: number;
  strongCandidateCount: number;
  rawPairCount?: number;
  rawOneOffPairCount?: number;
  processedCount: number;
  matchedCount: number;
  qualifiedPlateCount?: number;
  qualifiedPairCount?: number;
  qualifiedPaidTotal?: number;
  qualifiedMatchedPaidTotal?: number;
  qualifiedSun2Rows?: KobleQualifiedSun2Row[];
  qualifiedRows?: KobleQualifiedRow[];
  candidates: KobleReviewCandidate[];
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

export type EnergyElviaData = {
  summary: { total: EnergyElviaSummaryItem; firstAt?: string | null; lastAt?: string | null };
  yearly: EnergyElviaSummaryItem[];
  topDays: EnergyElviaSummaryItem[];
  topMonths: EnergyElviaSummaryItem[];
  imports: JsonRecord[];
  rows: JsonRecord[];
  latestImport?: JsonRecord | null;
  status?: JsonRecord | null;
  uploadEndpoint: string;
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
export type EnergyLoadItem = { id: number; name: string; loadType?: string | null; area?: string | null; powerProfile?: "unknown" | "fixed" | "variable" | string | null; expectedPowerW?: number | null; minPowerW?: number | null; maxPowerW?: number | null; measuredDirect?: boolean | null; energyNodeId?: number | null; fibaroDeviceId?: number | null; fibaroMeterId?: number | null; zwaveSwitchId?: number | null; controllable?: boolean | null; active?: boolean | null; critical?: boolean | null; note?: string | null };
export type EnergyAggregateMeter = { key: string; label: string; realtimeId: number; accumulatedId: number; description?: string | null; special?: boolean; mappedNodeCount?: number; memberPowerIds?: number[] };
export type EnergyNodeLive = { nodeId: number; status: string; checkedAt?: string | null; currentPowerW?: number | null; currentEnergyKwh?: number | null; switchState?: boolean | null; deviceName?: string | null; powerDeviceName?: string | null; energyDeviceName?: string | null; switchDeviceName?: string | null; dead?: boolean | null; enabled?: boolean | null; error?: string | null };
export type EnergyAggregateLive = { key: string; status: string; currentPowerW?: number | null; currentEnergyKwh?: number | null; error?: string | null };
export type Hc3EnergyDevice = { id: number; name?: string | null; type?: string | null; baseType?: string | null; parentId?: number | null; roomId?: number | null; manufacturer?: string | null; model?: string | null; value?: unknown; powerW?: number | null; energyKwh?: number | null; switchState?: boolean | null; hasPower?: boolean; hasEnergy?: boolean; hasSwitch?: boolean; dead?: boolean | null; enabled?: boolean | null; visible?: boolean | null };
export type Hc3EnergyDevicesResponse = { source: string; error?: string | null; count: number; devices: Hc3EnergyDevice[] };
export type EnergyNodesLiveResponse = { checkedAt: string; configured: boolean; nodes: Record<string, EnergyNodeLive>; aggregateMeters?: Record<string, EnergyAggregateLive> };
export type EnergyNode = { id: number; name: string; circuitNo?: number | null; parentNodeId?: number | null; nodeType: string; manufacturer?: string | null; model?: string | null; deviceType?: string | null; hc3DeviceId?: number | null; hc3PowerDeviceId?: number | null; hc3EnergyDeviceId?: number | null; hc3SwitchDeviceId?: number | null; aggregateGroupKey?: string | null; aggregateMeter?: EnergyAggregateMeter | null; endpointKey?: string | null; hasMeter: boolean; hasSwitch: boolean; area?: string | null; active: boolean; note?: string | null; loadCount: number; activeLoadCount: number; expectedPowerW: number; currentPowerW?: number | null; switchState?: boolean | null; liveStatus?: string | null; liveCheckedAt?: string | null; topologyWarning?: string | null; loads: EnergyLoadItem[]; children: EnergyNode[] };
export type EnergyCircuit = { key: string; circuitNo?: number | null; description?: string | null; breaker?: string | null; breakerType?: string | null; status?: string | null; isSunbed: boolean; note?: string | null; loadCount: number; activeLoadCount: number; nodeCount: number; expectedPowerW: number; currentPowerW?: number | null; measuredLoadCount: number; unmeasuredLoadCount: number; measurementMode: string; measurementDetail: string; directLoads: EnergyLoadItem[]; nodes: EnergyNode[] };
export type EnergyCircuitLoadsData = { canManage?: boolean; summary: JsonRecord; aggregateMeters: EnergyAggregateMeter[]; circuits: EnergyCircuit[] };

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
  services: OperationsOverviewResponse["services"];
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
  icon: import("./components/MosaicIcon").IconName;
  accent: Accent;
  navigation: NavigationGroup[];
};

export type DomainAppDefinition = DomainUiConfig & { port: number };
