import { domainApi } from "./api";
import { Layout } from "./components/Layout";
import { ModuleContent } from "./components/ModuleContent";
import { ErrorState, Loading } from "./components/PageState";
import { useApi } from "./hooks";
import { AppRouter, useAppLocation } from "./router";
import type { DomainUiConfig, ModuleResponse, OperationsOverviewResponse } from "./types";

function stateLabel(state: boolean | null) {
  if (state === true) return "P\u00e5";
  if (state === false) return "Av";
  return "Ukjent";
}

function operationsModule(data: OperationsOverviewResponse): ModuleResponse {
  const cards = data.cards.filter((card) => ["Drift", "Energi", "Temperatur", "V\u00e6r"].includes(card.group || ""));
  return {
    title: "Driftsoversikt",
    subtitle: `${data.operatingWindow.label} \u00b7 ${data.operatingWindow.detail} \u00b7 Oppdatert ${new Date(data.generatedAt).toLocaleString("nb-NO")}`,
    cards,
    tables: [
      {
        title: "Lys",
        columns: ["funksjon", "status", "detalj"],
        rows: data.lightItems.map((item) => ({ funksjon: item.label, status: stateLabel(item.state), detalj: item.tooltip || "" })),
      },
      {
        title: "Viftestyring",
        columns: ["funksjon", "status", "kilde", "sist kontrollert"],
        rows: data.fanItems.map((item) => ({
          funksjon: item.label,
          status: stateLabel(item.state),
          kilde: item.statusSource || item.tooltip || "",
          "sist kontrollert": item.checkedAt || "",
        })),
      },
      {
        title: "Siste driftshendelser",
        columns: ["hendelse", "verdi", "detalj"],
        rows: data.latestItems.filter((item) => /energi|temp/i.test(item.label)).map((item) => ({ hendelse: item.label, verdi: item.value, detalj: item.detail || "" })),
      },
      {
        title: "Status datakilder",
        columns: ["nr", "datakilde", "status", "sist lest", "neste kj\u00f8ring"],
        rows: data.services.map((service) => ({
          nr: service.sourceNo ?? "",
          datakilde: service.label,
          status: service.status,
          "sist lest": service.detail || service.lastSuccessAt || "",
          "neste kj\u00f8ring": service.nextExpectedAt || "",
        })),
      },
    ],
  };
}

function RoutedDomainApp({ config }: { config: DomainUiConfig }) {
  const { pathname, search } = useAppLocation();
  const items = config.navigation.flatMap((group) => group.items);
  const item = items.find((entry) => entry.to === pathname) || items[0];
  const isOperationsOverview = item.module === "status" && item.view === "drift";
  const result = useApi(
    async () => isOperationsOverview ? operationsModule(await domainApi.operationsOverview()) : domainApi.module(item.module, item.view, new URLSearchParams(search)),
    `module-${item.module}-${item.view}-${search}`,
  );
  const appConfig = useApi(domainApi.config, "app-config");
  return <Layout config={config}>{result.loading || appConfig.loading ? <Loading /> : result.error || !result.data ? <ErrorState error={result.error} onRetry={result.reload} /> : <ModuleContent data={result.data} config={config} reload={result.reload} coreUrl={appConfig.data?.fibaro10AppUrl || "http://192.168.20.218:8110"} module={item.module} view={item.view} />}</Layout>;
}

export function DomainApp({ config }: { config: DomainUiConfig }) {
  return <AppRouter><RoutedDomainApp config={config} /></AppRouter>;
}
