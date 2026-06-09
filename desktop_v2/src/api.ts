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

export type ModuleResponse = {
  title: string;
  subtitle: string;
  cards: ModuleCard[];
  charts?: ModuleChart[];
  tables: ModuleTable[];
  actions?: ModuleAction[];
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
  return apiGet<OverviewResponse>("/api/v2/overview");
}

export function fetchRevenueMonth(month?: string): Promise<RevenueMonthResponse> {
  const query = month ? `?month=${encodeURIComponent(month)}` : "";
  return apiGet<RevenueMonthResponse>(`/api/v2/revenue/month${query}`);
}

export function fetchModule(module: string, view?: string): Promise<ModuleResponse> {
  const query = view ? `?view=${encodeURIComponent(view)}` : "";
  return apiGet<ModuleResponse>(`/api/v2/modules/${encodeURIComponent(module)}${query}`);
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
