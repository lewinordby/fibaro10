import { useMemo, type ReactNode } from "react";
import { domainApi } from "./api";
import { Layout } from "./components/Layout";
import { ModuleContent, type ModuleAppContent } from "./components/ModuleContent";
import { ErrorState, Loading } from "./components/PageState";
import { useApi } from "./hooks";
import { findNavigationItem } from "./navigation";
import { AppRouter, useAppLocation } from "./router";
import type { DomainUiConfig, ModuleResponse, NavigationItem } from "./types";

export type DomainModuleContext = {
  data: ModuleResponse;
  module: string;
  view: string;
  reload: () => void;
};

export type DomainRouteContext = {
  pathname: string;
  search: string;
  item: NavigationItem;
  config: DomainUiConfig;
};

export type DomainDetailContext = DomainRouteContext & { coreUrl: string };

export type DomainAppExtensions = {
  enhanceConfig?: (config: DomainUiConfig, data: ModuleResponse | null | undefined) => DomainUiConfig;
  isRoute?: (context: DomainRouteContext) => boolean;
  skipModuleLoad?: (context: DomainRouteContext) => boolean;
  loadModule?: (context: DomainRouteContext) => Promise<ModuleResponse> | null;
  renderRoute?: (context: DomainDetailContext) => ReactNode;
  renderModule?: (context: DomainModuleContext) => ModuleAppContent | null;
};

function emptyModule(): ModuleResponse {
  return { title: "", subtitle: "", cards: [], tables: [] };
}

function RoutedDomainApp({ config, extensions }: { config: DomainUiConfig; extensions?: DomainAppExtensions }) {
  const { pathname, search } = useAppLocation();
  const baseItem = findNavigationItem(config, pathname);
  const routeContext = { pathname, search, item: baseItem, config };
  const isExtensionRoute = Boolean(extensions?.isRoute?.(routeContext));
  const skipModuleLoad = isExtensionRoute || Boolean(extensions?.skipModuleLoad?.(routeContext));
  const result = useApi(
    async () => {
      if (skipModuleLoad) return emptyModule();
      const custom = extensions?.loadModule?.(routeContext);
      return custom || domainApi.module(baseItem.module, baseItem.view, new URLSearchParams(search));
    },
    `module-${baseItem.module}-${baseItem.view}-${search}`,
  );
  const appConfig = useApi(domainApi.config, "app-config");
  const effectiveConfig = useMemo(
    () => extensions?.enhanceConfig?.(config, result.data) || config,
    [config, extensions, result.data],
  );
  const item = findNavigationItem(effectiveConfig, pathname);
  const coreUrl = appConfig.data?.fibaro10AppUrl || "https://fibaro10.lilletorget.net";
  const detailContext = { pathname, search, item, config: effectiveConfig, coreUrl };
  return <Layout config={effectiveConfig}>{result.loading || appConfig.loading
    ? <Loading />
    : result.error || !result.data
      ? <ErrorState error={result.error} onRetry={result.reload} />
      : isExtensionRoute
        ? extensions?.renderRoute?.(detailContext)
        : <ModuleContent
            data={result.data}
            config={effectiveConfig}
            reload={result.reload}
            coreUrl={coreUrl}
            module={item.module}
            view={item.view}
            appContent={extensions?.renderModule?.({ data: result.data, module: item.module, view: item.view, reload: result.reload })}
          />}</Layout>;
}

export function DomainApp({ config, extensions }: { config: DomainUiConfig; extensions?: DomainAppExtensions }) {
  return <AppRouter><RoutedDomainApp config={config} extensions={extensions} /></AppRouter>;
}
