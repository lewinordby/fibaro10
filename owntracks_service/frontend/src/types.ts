export type ViewKey = "dashboard" | "places" | "occupancy" | "map" | "visits" | "waypoints" | "suggestions" | "diagnostics" | "messages" | "events" | "build";
export type TimeFilterMode = "relative" | "custom";

export type HealthPayload = {
  status: string;
  service: string;
  app: { name: string; version: string; build: string; commit: string };
  database: string;
  ingest: { mode: string; path: string; authTokenEnabled: boolean };
  public: { baseUrl: string; publishUrl: string; adminUrl: string };
  qualityPolicy?: {
    maxCalculationAccuracyM: number;
    minOverviewVisitSeconds?: number;
    rawDataRetained: boolean;
    appliesTo: string[];
  };
  state: {
    lastMessageAt: string | null;
    lastStoreError: string | null;
    messagesReceived: number;
    messagesStored: number;
    messagesDuplicate: number;
  };
  counts: {
    devices: number;
    locations: number;
    waypoints: number;
    events: number;
    zoneVisits: number;
  };
  time: string;
};

export type ModulePayload = {
  title: string;
  subtitle: string;
  cards: Array<{ title: string; value: string | number; unit?: string; subtitle?: string }>;
  tables: Array<{ title: string; columns: string[]; rows: Array<Record<string, any>> }>;
  metadata: {
    state: HealthPayload["state"];
    build: HealthPayload["app"];
    buildLog: { currentBuild: string; rows: Array<Record<string, any>> };
  };
};

export type LocationRow = {
  id: number;
  topic: string;
  username?: string;
  device?: string;
  receivedAt?: string;
  timestamp?: string;
  messageType?: string;
  event?: string;
  origin?: "phone" | "server";
  isSynthetic?: boolean;
  lat?: number;
  lon?: number;
  distanceFromPreviousM?: number | null;
  accuracyM?: number;
  usableForCalculation?: boolean;
  accuracyLimitM?: number;
  batteryPercent?: number;
  staleMinutes?: number;
  gapMinutes?: number;
};

export type MessageGroupRow = {
  id: string;
  topic: string;
  timestamp?: string;
  firstReceivedAt?: string;
  lastReceivedAt?: string;
  count: number;
  messageTypes: string[];
  events: string[];
  lat?: number;
  lon?: number;
  distanceFromPreviousM?: number | null;
  accuracyM?: number;
  usableForCalculation?: boolean;
  accuracyLimitM?: number;
  batteryPercent?: number;
};

export type DeviceRow = {
  id: number;
  topic: string;
  username?: string;
  device?: string;
  lastSeenAt?: string;
  lastLat?: number;
  lastLon?: number;
  lastAccuracyM?: number;
  lastUsableForCalculation?: boolean;
  lastBatteryPercent?: number;
};

export type WaypointRow = {
  id: number;
  topic: string;
  waypointName: string;
  source?: string;
  category?: string;
  address?: string;
  notes?: string;
  isActive?: boolean;
  lat?: number;
  lon?: number;
  radiusM?: number;
  isInside?: boolean;
  lastState?: string;
  lastEvent?: string;
  lastSeenAt?: string;
};

export type WaypointSuggestionRow = {
  id: string;
  topic: string;
  username?: string;
  device?: string;
  suggestedName: string;
  address?: string;
  lat: number;
  lon: number;
  radiusM: number;
  sampleCount: number;
  visits: number;
  totalDuration: string;
  totalDurationSeconds: number;
  firstSeenAt?: string;
  lastSeenAt?: string;
  maxAccuracyM?: number;
  confidence?: number;
};

export type WaypointSuggestionsPayload = {
  parameters: Record<string, string | number | boolean>;
  suggestions: WaypointSuggestionRow[];
};

export type VisitRow = {
  id: number;
  topic: string;
  waypointName: string;
  startedAt?: string;
  endedAt?: string;
  durationSeconds?: number;
  duration?: string;
  status?: string;
  startLat?: number;
  startLon?: number;
  endLat?: number;
  endLon?: number;
  lastLat?: number;
  lastLon?: number;
  enterSource?: string;
  leaveSource?: string;
  confidence?: number;
};

export type VisitDisplayRow = VisitRow & {
  category?: string;
  address?: string;
  totalDurationSeconds?: number;
};

export type ZoneSummaryRow = {
  id: string;
  topic: string;
  username?: string;
  device?: string;
  waypointName: string;
  visits: number;
  openVisits: number;
  totalDuration: string;
  totalDurationSeconds: number;
  avgDuration: string;
  avgDurationSeconds: number;
  firstSeenAt?: string;
  lastSeenAt?: string;
  lastStartedAt?: string;
  lastEndedAt?: string;
  lastDuration?: string;
  currentStartedAt?: string;
  currentLastSeenAt?: string;
  currentDurationSeconds?: number;
  currentDuration?: string;
  lastEnterAt?: string;
  lastLeaveAt?: string;
  lastStatus?: string;
  lastConfidence?: number;
  enterSources?: string[];
  waypoint?: WaypointRow;
};

export type ZoneSummaryPayload = {
  hours: number;
  start?: string;
  end?: string;
  filterMode?: TimeFilterMode;
  generatedAt?: string;
  totals: {
    zones: number;
    visits: number;
    rawVisits?: number;
    hiddenShortVisits?: number;
    minOverviewVisitSeconds?: number;
    openVisits: number;
    totalDurationSeconds: number;
    totalDuration: string;
  };
  summary: ZoneSummaryRow[];
  places?: ZoneSummaryRow[];
  activeVisits: VisitRow[];
  recentVisits: VisitRow[];
};

export type EventRow = {
  id: number;
  topic: string;
  waypointName: string;
  eventType?: string;
  sourceMessageType?: string;
  origin?: "phone" | "server";
  isSynthetic?: boolean;
  timestamp?: string;
  receivedAt?: string;
  lat?: number;
  lon?: number;
  accuracyM?: number;
  ignoredForState?: boolean;
  ignoredReason?: string;
};

export type MapPayload = {
  hours: number;
  start?: string;
  end?: string;
  filterMode?: TimeFilterMode;
  locations: LocationRow[];
  mapLocations?: LocationRow[];
  devices: DeviceRow[];
  waypoints: WaypointRow[];
  zoneVisits: VisitRow[];
  qualityPolicy?: {
    maxCalculationAccuracyM: number;
    rawLocations: number;
    mapLocations: number;
    ignoredForAccuracy: number;
    minOverviewVisitSeconds?: number;
    rawZoneVisits?: number;
    zoneVisits?: number;
    hiddenShortVisits?: number;
    rawDataRetained: boolean;
  };
};

export type DiagnosticRecommendation = {
  severity: "ok" | "info" | "warning" | "bad";
  title: string;
  text: string;
};

export type DiagnosticWaypoint = {
  id: number;
  waypointName: string;
  source?: string;
  radiusM?: number;
  insideLocationCount: number;
  nearLocationCount: number;
  minDistanceM?: number;
  lastSeenAt?: string;
  lastPositionAt?: string;
  isInside?: boolean;
};

export type DiagnosticGapRow = {
  from: LocationRow;
  to: LocationRow;
  gapMinutes: number;
};

export type DiagnosticsPayload = {
  hours: number;
  generatedAt?: string;
  parameters: {
    staleMinutes: number;
    gapMinutes: number;
    maxAccuracyM: number;
    minWaypointRadiusM?: number;
  };
  counts: {
    messages: number;
    locations: number;
    usableLocations?: number;
    transitions: number;
    statusMessages: number;
    staleLocations: number;
    duplicateLocations: number;
    poorAccuracyLocations: number;
    largeGaps: number;
  };
  accuracy: {
    avgM?: number;
    p50M?: number;
    p90M?: number;
    maxM?: number;
  };
  gaps: {
    avgMinutes?: number;
    p90Minutes?: number;
    maxMinutes?: number;
    rows: DiagnosticGapRow[];
  };
  latest?: LocationRow;
  staleSamples: LocationRow[];
  waypoints: DiagnosticWaypoint[];
  recommendations: DiagnosticRecommendation[];
};
