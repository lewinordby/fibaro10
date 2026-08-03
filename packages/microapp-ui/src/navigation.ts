import navigationData from "./navigation.json";
import type { AppDockId, DomainAppDefinition, DomainUiConfig, NavigationGroup, NavigationItem } from "./types";

const definitions: DomainAppDefinition[] = navigationData.apps.map((app) => ({
  appId: app.id as AppDockId,
  name: app.name,
  shortName: app.shortName,
  icon: app.icon as DomainAppDefinition["icon"],
  accent: app.accent as DomainAppDefinition["accent"],
  port: app.port,
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
