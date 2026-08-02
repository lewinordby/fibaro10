import type { AppsResponse, AppConfig, AuthUser } from "./types";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin", headers: { Accept: "application/json" } });
  if (response.status === 401) {
    window.location.assign("/auth/login");
    throw new Error("Innlogging kreves");
  }
  const payload = await response.json().catch(() => null) as { detail?: string } | null;
  if (!response.ok) throw new Error(payload?.detail || `${response.status} ${response.statusText}`);
  return payload as T;
}

export const api = {
  apps: () => get<AppsResponse>("/api/apps"),
  config: () => get<AppConfig>("/api/app/config"),
  user: () => get<AuthUser>("/api/auth/me")
};
