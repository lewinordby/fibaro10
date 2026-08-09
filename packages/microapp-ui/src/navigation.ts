import navigationData from "./navigation.json";
import type { AppDockId, DomainAppDefinition, DomainUiConfig, NavigationGroup, NavigationItem } from "./types";

const definitions: DomainAppDefinition[] = navigationData.apps.map((app) => ({
  appId: app.id as AppDockId,
  name: app.name,
  shortName: app.shortName,
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

/** Use direct ports only while developing locally; installed and LAN clients use trusted HTTPS names. */
export function resolveAppUrl(
  app: Pick<DomainAppDefinition, "port" | "url">,
  currentHref = window.location.href,
): string {
  const current = new URL(currentHref);
  if (isLocalDevelopmentHost(current.hostname)) {
    current.protocol = "http:";
    current.port = String(app.port);
    current.pathname = "/";
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
  target.pathname = targetPath.split(/[?#]/, 1)[0] || "/";
  target.search = parsed.search;
  target.hash = parsed.hash;
  return target.toString();
}
