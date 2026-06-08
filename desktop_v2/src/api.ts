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
  label: string;
  status: "ok" | "warn" | "bad" | "unknown";
  detail: string;
  ageMinutes?: number | null;
};

export type OverviewResponse = {
  generatedAt: string;
  operatingWindow: { label: string; detail: string; open: boolean };
  cards: MetricCard[];
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
};

export type ModuleResponse = {
  title: string;
  subtitle: string;
  cards: ModuleCard[];
  tables: ModuleTable[];
};

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function fetchOverview(): Promise<OverviewResponse> {
  return apiGet<OverviewResponse>("/api/v2/overview");
}

export function fetchRevenueMonth(month?: string): Promise<RevenueMonthResponse> {
  const query = month ? `?month=${encodeURIComponent(month)}` : "";
  return apiGet<RevenueMonthResponse>(`/api/v2/revenue/month${query}`);
}

export function fetchModule(module: string): Promise<ModuleResponse> {
  return apiGet<ModuleResponse>(`/api/v2/modules/${encodeURIComponent(module)}`);
}
