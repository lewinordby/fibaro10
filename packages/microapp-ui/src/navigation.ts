import navigationData from "./navigation.json";
import type { AppDockId, DomainAppDefinition, DomainUiConfig, NavigationGroup, NavigationItem } from "./types";

const definitions: DomainAppDefinition[] = navigationData.apps.map((app) => ({
  appId: app.id as AppDockId,
  name: app.name,
  shortName: app.shortName,
  basePath: app.basePath,
  icon: app.icon as DomainAppDefinition["icon"],
  accent: app.accent as DomainAppDefinition["accent"],
  port: app.port,
  url: app.url,
  navigation: app.groups as unknown as NavigationGroup[],
}));

export const appDefinitions = definitions;

export function getAppDefinition(appId: AppDockId): DomainAppDefinition {
  const definition = definitions.find((app) => app.appId === appId);
  if (!definition) throw new Error(`Ukjent app: ${appId}`);
  return definition;
}

export function getDomainConfig(appId: AppDockId): DomainUiConfig {
  return getAppDefinition(appId);
}

function itemMatches(item: NavigationItem, pathname: string) {
  if (item.to === pathname || item.aliases?.includes(pathname)) return true;
  return item.to !== "/" && pathname.startsWith(`${item.to}/`);
}

export function findNavigationItem(config: DomainUiConfig, pathname: string): NavigationItem {
  const items = config.navigation.flatMap((group) => group.items);
  return items
    .filter((item) => itemMatches(item, pathname))
    .sort((left, right) => right.to.length - left.to.length)[0] || items[0];
}

export function findNavigationGroup(config: DomainUiConfig, item: NavigationItem): NavigationGroup {
  return config.navigation.find((group) => group.items.includes(item)) || config.navigation[0];
}

function isLocalDevelopmentHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

function normalizeBasePath(path: string): string {
  const normalized = `/${path}`.replace(/\/{2,}/g, "/").replace(/\/$/, "");
  return normalized === "/" ? "" : normalized;
}

export function getCurrentAppBasePath(pathname = window.location.pathname): string {
  const match = definitions
    .map((app) => normalizeBasePath(app.basePath))
    .filter(Boolean)
    .sort((left, right) => right.length - left.length)
    .find((basePath) => pathname === basePath || pathname.startsWith(`${basePath}/`));
  return match || "";
}

export function removeCurrentAppBasePath(pathname: string): string {
  const basePath = getCurrentAppBasePath(pathname);
  if (!basePath) return pathname || "/";
  const localPath = pathname.slice(basePath.length);
  return localPath || "/";
}

export function withCurrentAppBasePath(path: string): string {
  if (!path.startsWith("/") || path.startsWith("//")) return path;
  const basePath = getCurrentAppBasePath();
  if (!basePath || path === basePath || path.startsWith(`${basePath}/`)) return path;
  return path === "/" ? `${basePath}/` : `${basePath}${path}`;
}

export function withCurrentAppApiPath(path: string): string {
  if (isLocalDevelopmentHost(window.location.hostname)) return path;
  return withCurrentAppBasePath(path);
}

export function scopeAppPayload<T>(value: T): T {
  const basePath = getCurrentAppBasePath();
  if (!basePath) return value;
  const visit = (candidate: unknown): unknown => {
    if (typeof candidate === "string") {
      return candidate.startsWith("/api/") ? withCurrentAppApiPath(candidate) : candidate;
    }
    if (Array.isArray(candidate)) return candidate.map(visit);
    if (candidate && typeof candidate === "object") {
      return Object.fromEntries(Object.entries(candidate).map(([key, item]) => [key, visit(item)]));
    }
    return candidate;
  };
  return visit(value) as T;
}

/** Use direct ports only while developing locally; installed and LAN clients use trusted HTTPS names. */
export function resolveAppUrl(
  app: Pick<DomainAppDefinition, "port" | "url" | "basePath">,
  currentHref = window.location.href,
): string {
  const current = new URL(currentHref);
  if (isLocalDevelopmentHost(current.hostname)) {
    current.protocol = "http:";
    current.port = String(app.port);
    current.pathname = `${normalizeBasePath(app.basePath)}/`;
    current.search = "";
    current.hash = "";
    return current.toString();
  }
  return new URL(app.url).toString();
}

type CoreRouteMatch = {
  app: DomainAppDefinition;
  item: NavigationItem;
  corePath: string;
};

function coreRouteMatches(pathname: string): CoreRouteMatch[] {
  return definitions.flatMap((app) =>
    app.navigation.flatMap((group) =>
      group.items
        .map((item) => ({
          app,
          item,
          corePath: item.corePath || `/${item.module}/${item.view}`,
        }))
        .filter(({ corePath }) => pathname === corePath || pathname.startsWith(`${corePath}/`)),
    ),
  );
}

/** Resolve a Fibaro10 route to the owning microapp, including nested detail routes. */
export function resolveCorePath(path: string | undefined, currentAppId: AppDockId): string | null {
  if (!path) return null;
  const parsed = new URL(path, window.location.origin);
  if (parsed.origin !== window.location.origin && /^https?:\/\//.test(path)) return path;
  const match = coreRouteMatches(parsed.pathname).sort(
    (left, right) => right.corePath.length - left.corePath.length,
  )[0];
  if (!match) return null;
  const suffix = parsed.pathname.slice(match.corePath.length);
  const base = match.item.to === "/" ? "" : match.item.to;
  const targetPath = `${base}${suffix}${parsed.search}${parsed.hash}` || "/";
  if (match.app.appId === currentAppId) return targetPath;
  const target = new URL(resolveAppUrl(match.app));
  const localPath = targetPath.split(/[?#]/, 1)[0] || "/";
  const basePath = normalizeBasePath(match.app.basePath);
  target.pathname = localPath === "/" ? `${basePath}/` : `${basePath}${localPath}`;
  target.search = parsed.search;
  target.hash = parsed.hash;
  return target.toString();
}
