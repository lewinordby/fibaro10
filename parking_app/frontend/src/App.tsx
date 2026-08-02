import { lazy, Suspense } from "react";
import { Loading } from "@lilletorget/microapp-ui/primitives";
import { useAppLocation } from "@lilletorget/microapp-ui/router";
import { Layout } from "./components/Layout";

const ModulePage = lazy(() => import("./pages/ModulePage"));
const YearPage = lazy(() => import("./pages/YearPage"));
const TimeDistributionPage = lazy(() => import("./pages/TimeDistributionPage"));
const WeeklyPage = lazy(() => import("./pages/WeeklyPage"));
const VehiclePage = lazy(() => import("./pages/VehiclePage"));
const SettlementPage = lazy(() => import("./pages/SettlementPage"));

const moduleRoutes: Record<string, string> = {
  "/": "oversikt",
  "/parkeringer": "parkeringer",
  "/dagslinje": "dagslinje",
  "/kjoretoy": "kjoretoy",
  "/omrade": "omrade",
  "/prognose": "prognose",
  "/oppgjor": "oppgjor",
  "/bilstatistikk": "bilstatistikk",
  "/oppslag": "oppslag",
};

export default function App() {
  const { pathname } = useAppLocation();
  const vehicle = pathname.match(/^\/kjoretoy\/([^/]+)$/);
  const settlement = pathname.match(/^\/oppgjor\/(\d+)$/);
  let page = moduleRoutes[pathname] ? <ModulePage view={moduleRoutes[pathname]} /> : <ModulePage view="oversikt" />;
  if (pathname === "/arsutvikling") page = <YearPage />;
  else if (pathname === "/tidspunkt") page = <TimeDistributionPage />;
  else if (pathname === "/ukesnitt") page = <WeeklyPage />;
  else if (vehicle) page = <VehiclePage plate={decodeURIComponent(vehicle[1])} />;
  else if (settlement) page = <SettlementPage id={settlement[1]} />;
  return <Layout><Suspense fallback={<Loading />}>{page}</Suspense></Layout>;
}
