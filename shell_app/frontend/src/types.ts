export type AppRow = {
  id: string;
  name: string;
  category: string;
  description: string;
  url: string;
  tone: string;
  icon: string;
  available: boolean;
  status: "ok" | "warning" | "down" | "planned";
  statusText: string;
  build: string | null;
};

export type AppsResponse = {
  apps: AppRow[];
  summary: { available: number; healthy: number; planned: number };
};

export type AuthUser = {
  username: string;
  roleLabel: string;
};

export type AppConfig = {
  name: string;
  build: string;
  shellUrl: string;
};
