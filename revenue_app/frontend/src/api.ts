import type {
  AppConfig,
  AuthUser,
  ComparisonResponse,
  ModuleResponse,
  OverviewResponse,
  RevenueMonthResponse,
  YearComparisonResponse,
} from "./types";
import { apiRequest } from "@lilletorget/microapp-ui";

export const api = {
  config: () => apiRequest<AppConfig>("/api/app/config"),
  user: () => apiRequest<AuthUser>("/api/auth/me"),
  dashboard: () => apiRequest<OverviewResponse>("/api/overview?scope=revenue"),
  overview: () => apiRequest<ModuleResponse>("/api/modules/omsetning?view=oversikt"),
  comparison: (params: URLSearchParams) => apiRequest<ComparisonResponse>(`/api/status/comparison?${params}`),
  year: (year?: string) => apiRequest<YearComparisonResponse>(`/api/omsetning/year-comparison${year ? `?year=${encodeURIComponent(year)}` : ""}`),
  month: (month?: string) => apiRequest<RevenueMonthResponse>(`/api/revenue/month${month ? `?month=${encodeURIComponent(month)}` : ""}`),
};
