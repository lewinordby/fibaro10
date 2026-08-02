import { lazy, Suspense } from "react";
import { Loading } from "@lilletorget/microapp-ui/primitives";
import { useAppLocation } from "@lilletorget/microapp-ui/router";
import { Layout } from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";

const ComparisonPage = lazy(() => import("./pages/ComparisonPage"));
const MonthPage = lazy(() => import("./pages/MonthPage"));
const OverviewPage = lazy(() => import("./pages/OverviewPage"));
const YearPage = lazy(() => import("./pages/YearPage"));

export default function App() {
  const { pathname } = useAppLocation();
  const page = pathname === "/oversikt"
    ? <OverviewPage />
    : pathname === "/sammenligning"
      ? <ComparisonPage />
      : pathname === "/ar"
        ? <YearPage />
        : pathname === "/maned"
          ? <MonthPage />
          : <DashboardPage />;
  return (
    <Layout>
      <Suspense fallback={<Loading />}>{page}</Suspense>
    </Layout>
  );
}
