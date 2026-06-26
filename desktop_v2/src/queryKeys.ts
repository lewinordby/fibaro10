export const queryKeys = {
  auth: {
    currentUser: () => ["auth", "current-user"] as const,
  },
  overview: () => ["overview"] as const,
  buildLog: () => ["admin", "build-log"] as const,
  buildLogEntry: (build: string) => ["admin", "build-log", build] as const,
  mobileScreens: () => ["mobile", "screens"] as const,
  module: (module: string, view: string, serverQuery = "", timelineDay = "", params = "") =>
    ["module", module, view, serverQuery, timelineDay, params] as const,
  parkingVehicle: (plate: string) => ["parking", "vehicle", plate] as const,
  revenueMonth: (month = "") => ["revenue", "month", month] as const,
  statusComparison: (period: string, compare: string, anchor: string) =>
    ["status", "comparison", period, compare, anchor] as const,
  sunYearComparison: (year: string) => ["sun", "year-comparison", year] as const,
  parkingYearComparison: (year: string) => ["parking", "year-comparison", year] as const,
  revenueYearComparison: (year: string) => ["revenue", "year-comparison", year] as const,
  settlement: (domain: "parking" | "sun", id: string) => ["settlement", domain, id] as const,
};
