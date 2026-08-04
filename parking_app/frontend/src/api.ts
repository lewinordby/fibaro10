import type {
  AppConfig,
  AuthUser,
  CarsDayResponse,
  ModuleAction,
  ModuleResponse,
  ParkingTimeDistributionResponse,
  ParkingVehicleDetailResponse,
  ParkingWeeklyAveragesResponse,
  ParkingWeeklyYearComparisonResponse,
  ParkingYearComparisonResponse,
  SettlementDetailResponse,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { Accept: "application/json", ...init?.headers },
    ...init,
  });
  if (response.status === 401) {
    window.location.assign("/auth/login");
    throw new Error("Innlogging kreves");
  }
  const payload = (await response.json().catch(() => null)) as { detail?: string; message?: string } | null;
  if (!response.ok) throw new Error(payload?.message || payload?.detail || `${response.status} ${response.statusText}`);
  return payload as T;
}

function query(path: string, params?: URLSearchParams) {
  const value = params?.toString();
  return value ? `${path}?${value}` : path;
}

export const api = {
  config: () => request<AppConfig>("/api/app/config"),
  user: () => request<AuthUser>("/api/auth/me"),
  module: (view: string, params?: URLSearchParams) => {
    const next = new URLSearchParams(params);
    next.set("view", view);
    return request<ModuleResponse>(query("/api/modules/parkering", next));
  },
  year: (year?: string) => request<ParkingYearComparisonResponse>(query("/api/parkering/year-comparison", year ? new URLSearchParams({ year }) : undefined)),
  timeDistribution: (params: URLSearchParams) => request<ParkingTimeDistributionResponse>(query("/api/parkering/time-distribution", params)),
  weeklyAverages: (params: URLSearchParams) => request<ParkingWeeklyAveragesResponse>(query("/api/parkering/weekly-averages", params)),
  weeklyYears: (years?: string) => request<ParkingWeeklyYearComparisonResponse>(query("/api/parkering/weekly-averages/years", years ? new URLSearchParams({ years }) : undefined)),
  vehicle: (plate: string) => request<ParkingVehicleDetailResponse>(`/api/parking/vehicles/${encodeURIComponent(plate)}`),
  carsDay: (day: string) => request<CarsDayResponse>(query("/api/cars/day", new URLSearchParams({ day }))),
  settlement: (id: string) => request<SettlementDetailResponse>(`/api/settlements/${encodeURIComponent(id)}`),
  action: (action: ModuleAction) => request<{ message?: string; status?: string }>(action.path, { method: action.method }),
};
