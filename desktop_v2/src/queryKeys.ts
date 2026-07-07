export const queryKeys = {
  auth: {
    currentUser: () => ["auth", "current-user"] as const,
  },
  overview: () => ["overview"] as const,
  health: (details = false) => ["health", details] as const,
  importStatusDetail: (jobName: string) => ["import-status", jobName] as const,
  buildLog: () => ["admin", "build-log"] as const,
  buildLogEntry: (build: string) => ["admin", "build-log", build] as const,
  mobileScreens: () => ["mobile", "screens"] as const,
  doorStatus: () => ["hc3", "doors", "status"] as const,
  module: (module: string, view: string, serverQuery = "", timelineDay = "", params = "") =>
    ["module", module, view, serverQuery, timelineDay, params] as const,
  maintenanceSiteVisit: (visitId: string) => ["maintenance", "site-visit", visitId] as const,
  parkingVehicle: (plate: string) => ["parking", "vehicle", plate] as const,
  revenueMonth: (month = "") => ["revenue", "month", month] as const,
  statusComparison: (period: string, compare: string, anchor: string, references = "") =>
    ["status", "comparison", period, compare, anchor, references] as const,
  sunYearComparison: (year: string) => ["sun", "year-comparison", year] as const,
  parkingYearComparison: (year: string) => ["parking", "year-comparison", year] as const,
  revenueYearComparison: (year: string) => ["revenue", "year-comparison", year] as const,
  settlement: (domain: "parking" | "sun", id: string) => ["settlement", domain, id] as const,
};
