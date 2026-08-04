import type { AppConfig, AuthUser, BusinessComparisonResponse, BusinessOverviewResponse, JsonRecord, ModuleAction, ModuleEditConfig, ModuleResponse, ModuleRow, OperationsOverviewResponse, SunSessionImageBrowser, YearComparisonResponse } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers: { Accept: "application/json", ...(isFormData ? {} : init?.headers) },
  });
  if (response.status === 401) {
    window.location.assign("/auth/login");
    throw new Error("Innlogging kreves");
  }
  const payload = (await response.json().catch(() => null)) as { detail?: string; message?: string } | null;
  if (!response.ok) throw new Error(payload?.message || payload?.detail || `${response.status} ${response.statusText}`);
  return payload as T;
}

function endpointFromTemplate(template: string, row: ModuleRow) {
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key: string) => encodeURIComponent(String(row[key] ?? "")));
}

export const domainApi = {
  config: () => request<AppConfig>("/api/app/config"),
  user: () => request<AuthUser>("/api/auth/me"),
  operationsOverview: () => request<OperationsOverviewResponse>("/api/overview"),
  businessOverview: () => request<BusinessOverviewResponse>("/api/overview"),
  businessComparison: (params: URLSearchParams) => request<BusinessComparisonResponse>(`/api/status/comparison?${params.toString()}`),
  yearComparison: (domain: "soling" | "parkering", year?: string) => request<YearComparisonResponse>(`/api/${domain}/year-comparison${year ? `?year=${encodeURIComponent(year)}` : ""}`),
  get: <T = JsonRecord>(path: string) => request<T>(path),
  mutate: <T = JsonRecord>(path: string, method: "POST" | "PATCH" | "PUT" | "DELETE", values?: JsonRecord) => request<T>(path, {
    method,
    headers: values ? { "Content-Type": "application/json" } : undefined,
    body: values ? JSON.stringify(values) : undefined,
  }),
  saveSettings: (path: string, values: JsonRecord, reason: string) => request<JsonRecord>(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values, reason }),
  }),
  module: (module: string, view: string, params?: URLSearchParams) => {
    const next = new URLSearchParams(params);
    next.set("view", view);
    const query = next.toString();
    return request<ModuleResponse>(`/api/modules/${encodeURIComponent(module)}${query ? `?${query}` : ""}`);
  },
  action: (action: ModuleAction) => request<{ message?: string; status?: string }>(action.path, { method: action.method }),
  edit: (edit: ModuleEditConfig, row: ModuleRow, values: JsonRecord, create: boolean) => {
    const endpoint = create && edit.createEndpoint ? edit.createEndpoint : endpointFromTemplate(edit.endpoint, row);
    const method = create && edit.createEndpoint ? "POST" : edit.method ?? "PATCH";
    return request<{ message?: string }>(endpoint, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
  },
  upload: (endpoint: string, file: File) => {
    const form = new FormData();
    form.set("file", file);
    return request<{ message?: string }>(endpoint, { method: "POST", body: form });
  },
  sunSessionImages: (sessionId: number, snapshotId?: string | null) => {
    const params = new URLSearchParams();
    if (snapshotId) params.set("snapshot_id", snapshotId);
    const query = params.toString();
    return request<SunSessionImageBrowser>(`/api/soling/enkeltimer/${encodeURIComponent(sessionId)}/image-browser${query ? `?${query}` : ""}`);
  },
  selectSunSessionImage: async (sessionId: number, snapshotId: string) => {
    const params = new URLSearchParams({ snapshot_id: snapshotId });
    const result = await request<SunSessionImageBrowser | { browser: SunSessionImageBrowser }>(`/api/soling/enkeltimer/${encodeURIComponent(sessionId)}/image?${params}`, { method: "POST" });
    return "browser" in result ? result.browser : result;
  },
};
