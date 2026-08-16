import type {
  AppConfig,
  AuthUser,
  CarsDayDetectionsResponse,
  CarsDayResponse,
  ModuleAction,
  ModuleResponse,
  ParkingTimeDistributionResponse,
  ParkingLookupResponse,
  ParkingVehicleDetailResponse,
  ParkingWeeklyAveragesResponse,
  ParkingWeeklyYearComparisonResponse,
  ParkingYearComparisonResponse,
  SettlementDetailResponse,
} from "./types";
import { apiRequest } from "@lilletorget/microapp-ui";

function query(path: string, params?: URLSearchParams) {
  const value = params?.toString();
  return value ? `${path}?${value}` : path;
}

export const api = {
  config: () => apiRequest<AppConfig>("/api/app/config"),
  user: () => apiRequest<AuthUser>("/api/auth/me"),
  module: (view: string, params?: URLSearchParams) => {
    const next = new URLSearchParams(params);
    next.set("view", view);
    return apiRequest<ModuleResponse>(query("/api/modules/parkering", next));
  },
  year: (year?: string) => apiRequest<ParkingYearComparisonResponse>(query("/api/parkering/year-comparison", year ? new URLSearchParams({ year }) : undefined)),
  timeDistribution: (params: URLSearchParams) => apiRequest<ParkingTimeDistributionResponse>(query("/api/parkering/time-distribution", params)),
  weeklyAverages: (params: URLSearchParams) => apiRequest<ParkingWeeklyAveragesResponse>(query("/api/parkering/weekly-averages", params)),
  weeklyYears: (years?: string) => apiRequest<ParkingWeeklyYearComparisonResponse>(query("/api/parkering/weekly-averages/years", years ? new URLSearchParams({ years }) : undefined)),
  vehicle: (plate: string) => apiRequest<ParkingVehicleDetailResponse>(`/api/parking/vehicles/${encodeURIComponent(plate)}`),
  lookup: (mode: "navn" | "omrade", limit: number, offset: number) => apiRequest<ParkingLookupResponse>(query(`/api/parkering/kjoretoy/mangler-${mode}`, new URLSearchParams({ limit: String(limit), offset: String(offset) }))),
  carsDay: (day: string) => apiRequest<CarsDayResponse>(query("/api/cars/day", new URLSearchParams({ day }))),
  carDetections: (plate: string, day: string) => apiRequest<CarsDayDetectionsResponse>(query(`/api/cars/day/${encodeURIComponent(plate)}/detections`, new URLSearchParams({ day }))),
  settlement: (id: string) => apiRequest<SettlementDetailResponse>(`/api/settlements/${encodeURIComponent(id)}`),
  action: (action: ModuleAction) => apiRequest<{ message?: string; status?: string }>(action.path, { method: action.method }),
};
