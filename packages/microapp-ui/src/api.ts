import type { AppConfig, AuthUser, BusinessComparisonResponse, BusinessOverviewResponse, JsonRecord, ModuleAction, ModuleEditConfig, ModuleResponse, ModuleRow, YearComparisonResponse } from "./types";
import { scopeAppPayload, withCurrentAppApiPath } from "./navigation";

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const method = (init?.method || "GET").toUpperCase();
  const timeoutMs = isFormData ? 120_000 : method === "GET" ? 50_000 : 60_000;
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (init?.signal?.aborted) abort();
  else init?.signal?.addEventListener("abort", abort, { once: true });
  const timeout = window.setTimeout(abort, timeoutMs);
  try {
    const response = await fetch(withCurrentAppApiPath(path), {
      credentials: "same-origin",
      cache: method === "GET" ? "default" : "no-store",
      ...init,
      signal: controller.signal,
      headers: { Accept: "application/json", ...(isFormData ? {} : init?.headers) },
    });
    if (response.status === 401) {
      window.location.assign("/auth/login");
      throw new Error("Innlogging kreves");
    }
    const payload = (await response.json().catch(() => null)) as { detail?: string; message?: string } | null;
    if (!response.ok) throw new Error(payload?.message || payload?.detail || `${response.status} ${response.statusText}`);
    return scopeAppPayload(payload as T);
  } catch (error) {
    if (controller.signal.aborted && !init?.signal?.aborted) {
      throw new Error("Forespørselen tok for lang tid. Prøv igjen.", { cause: error });
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
    init?.signal?.removeEventListener("abort", abort);
  }
}

function endpointFromTemplate(template: string, row: ModuleRow) {
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key: string) => encodeURIComponent(String(row[key] ?? "")));
}

export const domainApi = {
  config: () => apiRequest<AppConfig>("/api/app/config"),
  user: () => apiRequest<AuthUser>("/api/auth/me"),
  businessOverview: (domain: "parking" | "sun") => apiRequest<BusinessOverviewResponse>(`/api/overview?scope=${domain}`),
  businessComparison: (params: URLSearchParams) => apiRequest<BusinessComparisonResponse>(`/api/status/comparison?${params.toString()}`),
  yearComparison: (domain: "soling" | "parkering", year?: string) => apiRequest<YearComparisonResponse>(`/api/${domain}/year-comparison${year ? `?year=${encodeURIComponent(year)}` : ""}`),
  get: <T = JsonRecord>(path: string) => apiRequest<T>(path),
  mutate: <T = JsonRecord>(path: string, method: "POST" | "PATCH" | "PUT" | "DELETE", values?: JsonRecord) => apiRequest<T>(path, {
    method,
    headers: values ? { "Content-Type": "application/json" } : undefined,
    body: values ? JSON.stringify(values) : undefined,
  }),
  saveSettings: (path: string, values: JsonRecord, reason: string) => apiRequest<JsonRecord>(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values, reason }),
  }),
  module: (module: string, view: string, params?: URLSearchParams) => {
    const next = new URLSearchParams(params);
    next.set("view", view);
    const query = next.toString();
    return apiRequest<ModuleResponse>(`/api/modules/${encodeURIComponent(module)}${query ? `?${query}` : ""}`);
  },
  action: (action: ModuleAction) => apiRequest<{ message?: string; status?: string }>(action.path, { method: action.method }),
  edit: (edit: ModuleEditConfig, row: ModuleRow, values: JsonRecord, create: boolean) => {
    const endpoint = create && edit.createEndpoint ? edit.createEndpoint : endpointFromTemplate(edit.endpoint, row);
    const method = create && edit.createEndpoint ? "POST" : edit.method ?? "PATCH";
    return apiRequest<{ message?: string }>(endpoint, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
  },
  upload: (endpoint: string, file: File) => {
    const form = new FormData();
    form.set("file", file);
    return apiRequest<{ message?: string }>(endpoint, { method: "POST", body: form });
  },
};
