import { Typography } from "antd";
import { lazy, Suspense } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { LoadingBlock } from "./components/AsyncState";
import { modulePath } from "./moduleViews";

const OverviewPage = lazy(() => import("./pages/OverviewPage"));
const RevenueMonthPage = lazy(() => import("./pages/RevenueMonthPage"));
const RevenueYearComparisonPage = lazy(() => import("./pages/RevenueYearComparisonPage"));
const OperationsPage = lazy(() => import("./pages/OperationsPage"));
const DataSourceDetailPage = lazy(() => import("./pages/DataSourceDetailPage"));
const Doors2Page = lazy(() => import("./pages/Doors2Page"));
const DoorsPage = lazy(() => import("./pages/DoorsPage"));
const Solroom2Page = lazy(() => import("./pages/Solroom2Page"));
const ModulePage = lazy(() => import("./pages/ModulePage"));
const MobileOverviewPage = lazy(() => import("./pages/MobileOverviewPage"));
const MaintenanceVisitDetailPage = lazy(() => import("./pages/MaintenanceVisitDetailPage"));
const ManualPage = lazy(() => import("./pages/ManualPage"));
const BuildDetailPage = lazy(() => import("./pages/BuildDetailPage"));
const BuildLogPage = lazy(() => import("./pages/BuildLogPage"));
const IdeasPage = lazy(() => import("./pages/IdeasPage"));
const ParkingSettlementsPage = lazy(() => import("./pages/ParkingSettlementsPage"));
const ParkingTimeDistributionPage = lazy(() => import("./pages/ParkingTimeDistributionPage"));
const ParkingVehicleDetailPage = lazy(() => import("./pages/ParkingVehicleDetailPage"));
const ParkingYearComparisonPage = lazy(() => import("./pages/ParkingYearComparisonPage"));
const SettlementDetailPage = lazy(() => import("./pages/SettlementDetailPage"));
const SunSettlementsPage = lazy(() => import("./pages/SunSettlementsPage"));
const SunYearComparisonPage = lazy(() => import("./pages/SunYearComparisonPage"));
const StatusComparisonPage = lazy(() => import("./pages/StatusComparisonPage"));

function LegacyRedirect({ to }: { to: string }) {
  const { search } = useLocation();
  return <Navigate to={`${to}${search}`} replace />;
}

export function AppRoutes() {
  return (
    <Suspense fallback={<LoadingBlock />}>
      <Routes>
        <Route index element={<Navigate to={modulePath("status")} replace />} />
        <Route path="/status" element={<Navigate to={modulePath("status")} replace />} />
        <Route path="/status/dashboard" element={<LegacyRedirect to={modulePath("status")} />} />
        <Route path="/status/nokkeltall" element={<LegacyRedirect to={modulePath("status", "drift")} />} />
        <Route path="/status/statistikk" element={<LegacyRedirect to={modulePath("omsetning", "oversikt")} />} />
        <Route path="/status/datakilder" element={<LegacyRedirect to={modulePath("admin", "datakilder")} />} />
        <Route path="/status/dagslinje" element={<LegacyRedirect to={modulePath("ventilasjon", "dagslogg")} />} />
        <Route path="/status/oversikt" element={<LegacyRedirect to={modulePath("status")} />} />
        <Route path="/status/omsetning" element={<OverviewPage dashboard="omsetning" />} />
        <Route path="/status/parkering" element={<OverviewPage dashboard="parkering" />} />
        <Route path="/status/soling" element={<OverviewPage dashboard="soling" />} />
        <Route path="/status/drift" element={<OverviewPage dashboard="drift" />} />
        <Route path="/status/sammenligning" element={<StatusComparisonPage />} />
        <Route path="/omsetning" element={<Navigate to={modulePath("omsetning")} replace />} />
        <Route path="/omsetning/manedsoversikt" element={<RevenueMonthPage />} />
        <Route path="/omsetning/akkumulert" element={<RevenueYearComparisonPage />} />
        <Route path="/omsetning/sammenligning" element={<StatusComparisonPage />} />
        <Route path="/omsetning/:view" element={<ModulePage module="omsetning" />} />
        <Route path="/parkering" element={<Navigate to={modulePath("parkering")} replace />} />
        <Route path="/parkering/statistikk" element={<LegacyRedirect to={modulePath("parkering", "bilstatistikk")} />} />
        <Route path="/parkering/navn-oppslag" element={<LegacyRedirect to={modulePath("parkering", "oppslag")} />} />
        <Route path="/parkering/omrade-oppslag" element={<LegacyRedirect to={modulePath("parkering", "oppslag")} />} />
        <Route path="/parkering/sammenligning" element={<ParkingYearComparisonPage />} />
        <Route path="/parkering/tidspunkt" element={<ParkingTimeDistributionPage />} />
        <Route path="/parkering/kjoretoy/:plate" element={<ParkingVehicleDetailPage />} />
        <Route path="/parkering/oppgjor" element={<ParkingSettlementsPage />} />
        <Route path="/parkering/oppgjor/:settlementId" element={<SettlementDetailPage />} />
        <Route path="/parkering/:view" element={<ModulePage module="parkering" />} />
        <Route path="/soling" element={<Navigate to={modulePath("soling")} replace />} />
        <Route path="/soling/sammenligning" element={<SunYearComparisonPage />} />
        <Route path="/soling/oppgjor" element={<SunSettlementsPage />} />
        <Route path="/soling/oppgjor/:settlementId" element={<SettlementDetailPage domain="soling" />} />
        <Route path="/soling/:view" element={<ModulePage module="soling" />} />
        <Route path="/koble" element={<Navigate to={modulePath("koble")} replace />} />
        <Route path="/koble/:view" element={<ModulePage module="koble" />} />
        <Route path="/energi" element={<Navigate to={modulePath("energi")} replace />} />
        <Route path="/energi/oversikt" element={<LegacyRedirect to={modulePath("energi", "status")} />} />
        <Route path="/energi/soling" element={<LegacyRedirect to={modulePath("energi", "forbruk-per-seng")} />} />
        <Route path="/energi/testside" element={<LegacyRedirect to={modulePath("energi", "verktoy")} />} />
        <Route path="/energi/:view" element={<ModulePage module="energi" />} />
        <Route path="/ventilasjon" element={<Navigate to={modulePath("ventilasjon")} replace />} />
        <Route path="/ventilasjon/dagslogg-temp" element={<LegacyRedirect to={modulePath("ventilasjon", "dagslogg")} />} />
        <Route path="/ventilasjon/:view" element={<ModulePage module="ventilasjon" />} />
        <Route path="/lys" element={<Navigate to={modulePath("lys")} replace />} />
        <Route path="/lys/dagslogg-lux" element={<LegacyRedirect to={modulePath("lys", "dagslogg")} />} />
        <Route path="/lys/:view" element={<ModulePage module="lys" />} />
        <Route path="/solrom" element={<Navigate to={modulePath("solrom")} replace />} />
        <Route path="/solrom/:view" element={<DoorsPage scope="solrom" />} />
        <Route path="/solrom-2" element={<Navigate to={modulePath("solrom-2")} replace />} />
        <Route path="/solrom-2/:view" element={<Solroom2Page />} />
        <Route path="/dorer2" element={<Navigate to={modulePath("dorer2")} replace />} />
        <Route path="/dorer2/:view" element={<Doors2Page />} />
        <Route path="/dorer" element={<Navigate to={modulePath("dorer")} replace />} />
        <Route path="/dorer/:view" element={<DoorsPage />} />
        <Route path="/vedlikehold" element={<Navigate to={modulePath("vedlikehold")} replace />} />
        <Route path="/vedlikehold/besok/:visitId" element={<MaintenanceVisitDetailPage />} />
        <Route path="/vedlikehold/:view" element={<ModulePage module="vedlikehold" />} />
        <Route path="/ideer" element={<Navigate to={modulePath("ideer")} replace />} />
        <Route path="/ideer/:view" element={<IdeasPage />} />
        <Route path="/mobil" element={<Navigate to={modulePath("mobil")} replace />} />
        <Route path="/mobil/oversikt" element={<MobileOverviewPage />} />
        <Route path="/mobil/:view" element={<MobileOverviewPage />} />
        <Route path="/renhold" element={<Navigate to={modulePath("renhold")} replace />} />
        <Route path="/renhold/robot/:duid" element={<LegacyRedirect to={modulePath("renhold", "roboter")} />} />
        <Route path="/renhold/:view" element={<ModulePage module="renhold" />} />
        <Route path="/manual" element={<Navigate to={modulePath("manual")} replace />} />
        <Route path="/manual/:view" element={<ManualPage />} />
        <Route path="/admin" element={<Navigate to={modulePath("admin")} replace />} />
        <Route path="/admin/drift" element={<OperationsPage />} />
        <Route path="/admin/datakilder/:jobName" element={<DataSourceDetailPage />} />
        <Route path="/admin/build" element={<BuildLogPage />} />
        <Route path="/admin/build/:build" element={<BuildDetailPage />} />
        <Route path="/admin/manual" element={<LegacyRedirect to={modulePath("manual")} />} />
        <Route path="/admin/:view" element={<ModulePage module="admin" />} />
        <Route
          path="*"
          element={
            <div className="empty-state">
              <Typography.Title level={3}>Siden finnes ikke ennå</Typography.Title>
              <Typography.Paragraph>
                Bruk menyen til venstre eller gå til <Link to={modulePath("status")}>oversikten</Link>.
              </Typography.Paragraph>
            </div>
          }
        />
      </Routes>
    </Suspense>
  );
}
