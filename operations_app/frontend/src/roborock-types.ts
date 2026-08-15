import type { JsonRecord } from "@lilletorget/microapp-ui/types";

export type RoborockRobotSummary = {
  duid: string;
  provider?: "roborock" | "dreame";
  provider_label?: string;
  external_id?: string | null;
  integration_status?: "active" | "pending" | "error";
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
  latest_job_today?: RoborockJobSummary | null;
  latest_job_yesterday?: RoborockJobSummary | null;
  today?: RoborockDailySummary | null;
  yesterday?: RoborockDailySummary | null;
  active_cycle?: RoborockActiveCycleSummary | null;
  readiness?: RoborockReadinessSummary | null;
  consumables?: RoborockConsumableSummary | null;
  schedules?: RoborockScheduleSummary | null;
};

export type RoborockActiveCycleSummary = {
  started_at?: string | null;
  last_floor_at?: string | null;
  dock_since?: string | null;
  last_observed_at?: string | null;
  phase: "cleaning" | "returning" | "mop_return" | "washing_mop" | "emptying" | "charging_pause";
  phase_label: string;
  active_minutes?: number | null;
  cleaned_area_m2?: number | null;
  progress_percent?: number | null;
  battery?: number | null;
};

export type RoborockJobSummary = {
  begin_at?: string | null;
  end_at?: string | null;
  duration_minutes?: number | null;
  cleaned_area_m2?: number | null;
  status: "complete" | "running" | "stopped" | "error";
  status_label: string;
  error_label?: string | null;
};

export type RoborockConsumableSummary = {
  main_brush?: string | null;
  side_brush?: string | null;
  filter?: string | null;
  sensor?: string | null;
  mop?: string | null;
  detergent?: string | null;
  captured_at?: string | null;
};

export type RoborockScheduleSummary = {
  active_count: number;
  next_label?: string | null;
  rounds_label?: string | null;
};

export type RoborockDailySummary = {
  job_count: number;
  completed_count: number;
  running_count: number;
  error_count: number;
  duration_minutes: number;
  cleaned_area_m2: number;
};

export type RoborockReadinessSummary = {
  status: "ready" | "active" | "attention" | "offline" | "pending";
  label: string;
  issues: string[];
  telemetry_at?: string | null;
  data_age_minutes?: number | null;
  charge_label?: string | null;
  clear_water_label?: string | null;
  dirty_water_label?: string | null;
  dust_bag_label?: string | null;
  dock_error_label?: string | null;
  signal_label?: string | null;
};

export type RoborockOverviewSummary = {
  robot_count: number;
  connected_count?: number;
  pending_count?: number;
  ready_count: number;
  active_count: number;
  attention_count: number;
  offline_count: number;
  jobs_today: number;
  duration_today: number;
  area_today: number;
  updated_at?: string | null;
};

export type RoborockModuleData = {
  robots: RoborockRobotSummary[];
  summary?: RoborockOverviewSummary | null;
  timeline?: RoborockDayTimeline | null;
};

export type RoborockNightJob = {
  recordId: string;
  startedAt: string;
  endedAt?: string | null;
  durationMinutes?: number | null;
  areaM2: number;
  complete: boolean;
  errorCode?: number | null;
  cleaningType: "vacuum" | "mop" | "vacuum_mop";
  cleaningTypeLabel: string;
  modeLabel: string;
  rounds: number;
  batteryStart?: number | null;
  batteryEnd?: number | null;
  washCount?: number | null;
  expectedWashCount?: number | null;
  status: "ok" | "warning" | "error" | "running";
  statusLabel: string;
  issues: string[];
};

export type RoborockNightPlannedJob = {
  scheduleId: string;
  scheduledAt: string;
  actualStartedAt?: string | null;
  actualRecordId?: string | null;
  delayMinutes?: number | null;
  cleaningType: "vacuum" | "mop" | "vacuum_mop";
  cleaningTypeLabel: string;
  modeLabel: string;
  status: "completed" | "delayed" | "running" | "pending" | "missing" | "failed";
  statusLabel: string;
};

export type RoborockNightRobot = {
  duid: string;
  name: string;
  model?: string | null;
  status: "ok" | "warning" | "error" | "neutral";
  statusLabel: string;
  jobs: RoborockNightJob[];
  scheduleCheck: {
    basis: string;
    jobs: RoborockNightPlannedJob[];
    expected: number;
    completed: number;
    missing: number;
    delayed: number;
    failed: number;
    running: number;
    pending: number;
  };
  settings: {
    supported: boolean;
    intervalMinutes?: number | null;
    mode?: number | null;
    modeLabel?: string | null;
    automatic: boolean;
    items: Array<{
      key: string;
      label: string;
      value: string;
    }>;
  };
  totals: {
    jobs: number;
    completed: number;
    durationMinutes: number;
    areaM2: number;
    washCount: number;
  };
  readiness: {
    readyBeforeOpening: boolean;
    lastJobEndedAt?: string | null;
    batteryAtOpening?: number | null;
    fullChargeAt?: string | null;
  };
  findings: string[];
};

export type RoborockNightReport = {
  day: string;
  previousDay: string;
  nextDay: string;
  generatedAt: string;
  window: { startAt: string; endAt: string; readyBy: string };
  conclusion: {
    status: "ok" | "warning" | "error" | "neutral";
    title: string;
    detail: string;
  };
  summary: {
    robots: number;
    activeRobots: number;
    jobs: number;
    completed: number;
    durationMinutes: number;
    areaM2: number;
    warnings: number;
    jobWarnings: number;
    running: number;
    errors: number;
    readyBeforeOpening: number;
    plannedJobs: number;
    plannedCompleted: number;
    plannedMissing: number;
    plannedDelayed: number;
    plannedPending: number;
  };
  robots: RoborockNightRobot[];
};

export type RoborockWaterResource = {
  supported: boolean;
  label: string;
  attention: boolean;
};

export type RoborockWaterRobot = {
  duid: string;
  name: string;
  provider: string;
  model?: string | null;
  status: "ready" | "attention" | "unsupported";
  statusLabel: string;
  observedAt?: string | null;
  current: {
    dockSupported: boolean;
    cleanWater: RoborockWaterResource;
    dirtyWater: RoborockWaterResource;
    robotWater: RoborockWaterResource;
    detergent: RoborockWaterResource;
  };
  settings: {
    washSupported: boolean;
    intervalMinutes?: number | null;
    washModeLabel?: string | null;
    automatic: boolean;
    waterMode?: number | null;
    waterModeLabel?: string | null;
  };
  usage: {
    jobs: number;
    mopJobs: number;
    washCount: number;
    areaM2: number;
    durationMinutes: number;
    areaPerWashM2?: number | null;
  };
  lastCleanWaterEmptyAt?: string | null;
  lastCleanWaterRestoredAt?: string | null;
  lastDirtyWaterFullAt?: string | null;
  lastDirtyWaterClearedAt?: string | null;
  lastRobotWaterEmptyAt?: string | null;
  lastRobotWaterRestoredAt?: string | null;
};

export type RoborockWaterReport = {
  period: {
    days: number;
    fromDay: string;
    toDay: string;
    generatedAt: string;
  };
  summary: {
    robots: number;
    waterCapable: number;
    dockReady: number;
    dockAttention: number;
    washCount: number;
    mopJobs: number;
    areaM2: number;
    areaPerWashM2?: number | null;
    waterWarnings: number;
    restoredEvents: number;
  };
  robots: RoborockWaterRobot[];
  daily: Array<{
    day: string;
    jobs: number;
    mopJobs: number;
    washCount: number;
    areaM2: number;
    areaPerWashM2?: number | null;
    waterWarnings: number;
  }>;
  events: Array<{
    id: string;
    robotDuid: string;
    robotName: string;
    timestamp?: string | null;
    field: string;
    title: string;
    previousLabel: string;
    currentLabel: string;
    severity: "info" | "warning" | "critical" | string;
    kind: string;
  }>;
  measurementNote: string;
};

export type RoborockDayTimelineJob = {
  recordId: string;
  startedAt: string;
  endedAt?: string | null;
  cleaningType: "vacuum" | "mop" | "vacuum_mop" | "cleaning";
  cleaningTypeLabel: string;
  status: "complete" | "running" | "stopped" | "error";
  statusLabel: string;
  planned: boolean;
  areaM2: number;
};

export type RoborockDayTimeline = {
  day: string;
  generatedAt: string;
  window: { startAt: string; endAt: string };
  summary: {
    planned: number;
    plannedCompleted: number;
    missing: number;
    pending: number;
    actual: number;
  };
  robots: Array<{
    duid: string;
    name: string;
    planned: RoborockNightPlannedJob[];
    jobs: RoborockDayTimelineJob[];
  }>;
};

export type RoborockRobotDetail = {
  robot: JsonRecord;
  metadata: JsonRecord;
  network: JsonRecord;
  latestStatus: JsonRecord | null;
  activeCycle: RoborockActiveCycleSummary | null;
  schedules: JsonRecord[];
  jobs: JsonRecord[];
  statuses: JsonRecord[];
  consumables: JsonRecord | null;
  latestMap: (JsonRecord & { imageDataUrl?: string | null }) | null;
  latestTelemetry: JsonRecord | null;
  telemetrySamples: JsonRecord[];
  telemetryEvents: JsonRecord[];
  canControl: boolean;
  canManageCleaningZones: boolean;
  doorAutomation?: {
    enabled: boolean;
    doorDeviceId: number;
    openingThreshold: number;
    minimumIntervalMinutes: number;
    zoneNumbers: number[];
    profileId: number;
    profile?: JsonRecord | null;
    configuredZones: Array<{
      zoneNumber: number;
      name: string;
      segmentId?: number | null;
      mapped: boolean;
    }>;
    openingCount: number;
    counterStartedAt?: string | null;
    lastOpeningAt?: string | null;
    doorIsOpen?: boolean | null;
    openingHours: {
      openAt?: string | null;
      closeAt?: string | null;
      openFrom: string;
      closeAtLabel: string;
    };
    status: string;
    statusLabel: string;
    statusDetail: string;
    eligible: boolean;
    pendingStart: boolean;
    nextAllowedAt?: string | null;
    remainingIntervalSeconds: number;
    validationIssues: string[];
    lastAttemptAt?: string | null;
    lastStartedAt?: string | null;
    lastRequestId?: string | null;
    lastError?: string | null;
    updatedAt?: string | null;
  } | null;
  cleaningZoneImport?: {
    status?: string;
    checkedAt?: string | null;
    imported?: number;
    message?: string | null;
  } | null;
  cleaningZones: Array<{
    zoneNumber: number;
    name: string;
    segmentId: string;
    sourceScheduleId?: string | null;
    sourceCron?: string | null;
    importedAt?: string | null;
    importedBy?: string | null;
  }>;
  cleaningProfiles: Array<{
    id: number;
    slug: string;
    name: string;
    description: string;
    cleaningType: "vacuum" | "mop" | "vacuum_mop";
    cleaningTypeLabel: string;
    fanPower: number;
    fanLabel: string;
    waterBoxMode: number;
    waterLabel: string;
    mopMode: number;
    mopLabel: string;
    repeat: number;
    roundsLabel: string;
    summary: string;
    active: boolean;
    builtin: boolean;
  }>;
  cleaningProfileOptions: {
    model?: string | null;
    cleaningTypes: Array<{ value: "vacuum" | "mop" | "vacuum_mop"; label: string }>;
    fanPower: Array<{ value: number; label: string }>;
    waterBoxMode: Array<{ value: number; label: string }>;
    mopMode: Array<{ value: number; label: string }>;
    repeat: Array<{ value: number; label: string }>;
    excludedModes?: string[];
  };
  controlHistory: Array<{
    id: number;
    request_id: string;
    action: string;
    requested_at?: string | null;
    finished_at?: string | null;
    requested_by?: string | null;
    status: string;
    message?: string | null;
    before_state?: JsonRecord | null;
    after_state?: JsonRecord | null;
    profile?: JsonRecord | null;
  }>;
  telemetryFields: Array<{
    category: string;
    field: string;
    label: string;
    value: unknown;
    valueLabel: string;
    supported: boolean;
  }>;
  rawStatusFields: Array<{ field: string; value: unknown }>;
  telemetryProbes: Array<{
    command: string;
    supported: boolean;
    status: string;
    checkedAt?: string | null;
    resultType?: string | null;
    value?: unknown;
    error?: string | null;
  }>;
};
