import type {
  AppConfig,
  AuthUser,
  ComparisonResponse,
  ModuleResponse,
  OverviewResponse,
  RevenueMonthResponse,
  YearComparisonResponse,
} from "./types";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (response.status === 401) {
    window.location.assign("/auth/login");
    throw new Error("Innlogging kreves");
  }
  const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
  if (!response.ok) throw new Error(payload?.detail || `${response.status} ${response.statusText}`);
  return payload as T;
}

export const api = {
  config: () => get<AppConfig>("/api/app/config"),
  user: () => get<AuthUser>("/api/auth/me"),
  dashboard: () => get<OverviewResponse>("/api/overview"),
  overview: () => get<ModuleResponse>("/api/modules/omsetning?view=oversikt"),
  comparison: (params: URLSearchParams) => get<ComparisonResponse>(`/api/status/comparison?${params}`),
  year: (year?: string) => get<YearComparisonResponse>(`/api/omsetning/year-comparison${year ? `?year=${encodeURIComponent(year)}` : ""}`),
  month: (month?: string) => get<RevenueMonthResponse>(`/api/revenue/month${month ? `?month=${encodeURIComponent(month)}` : ""}`),
};

