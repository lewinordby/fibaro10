import {
  LogoutOutlined,
  BarChartOutlined,
  BulbOutlined,
  CalendarOutlined,
  CarOutlined,
  ExperimentOutlined,
  HomeOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MobileOutlined,
  SettingOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Avatar, Button, Dropdown, Layout, Segmented, Typography } from "antd";
import type { MenuProps } from "antd";
import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { fetchCurrentUser, logoutUser, type AuthUser } from "./api";
import { LoadingBlock } from "./components/AsyncState";
import { defaultModuleView, modulePath, MODULE_VIEWS } from "./moduleViews";
import { queryKeys } from "./queryKeys";

const { Header, Sider, Content } = Layout;
const MENU_HIDDEN_STORAGE_KEY = "fibaro10:mainMenuHidden";
const BRAND_ASSET_VERSION = "20260626-shell";

const OverviewPage = lazy(() => import("./pages/OverviewPage"));
const RevenueMonthPage = lazy(() => import("./pages/RevenueMonthPage"));
const RevenueYearComparisonPage = lazy(() => import("./pages/RevenueYearComparisonPage"));
const OperationsPage = lazy(() => import("./pages/OperationsPage"));
const ModulePage = lazy(() => import("./pages/ModulePage"));
const MobileOverviewPage = lazy(() => import("./pages/MobileOverviewPage"));
const BuildDetailPage = lazy(() => import("./pages/BuildDetailPage"));
const BuildLogPage = lazy(() => import("./pages/BuildLogPage"));
const ParkingSettlementsPage = lazy(() => import("./pages/ParkingSettlementsPage"));
const ParkingVehicleDetailPage = lazy(() => import("./pages/ParkingVehicleDetailPage"));
const ParkingYearComparisonPage = lazy(() => import("./pages/ParkingYearComparisonPage"));
const SettlementDetailPage = lazy(() => import("./pages/SettlementDetailPage"));
const SunSettlementsPage = lazy(() => import("./pages/SunSettlementsPage"));
const SunYearComparisonPage = lazy(() => import("./pages/SunYearComparisonPage"));
const StatusComparisonPage = lazy(() => import("./pages/StatusComparisonPage"));

type MainModule = {
  module: string;
  icon: ReactNode;
  label: string;
  color: string;
};

const mainModules: MainModule[] = [
  { module: "omsetning", icon: <BarChartOutlined />, label: "Omsetning", color: "var(--domain-revenue)" },
  { module: "parkering", icon: <CarOutlined />, label: "Parkering", color: "var(--domain-parking)" },
  { module: "soling", icon: <CalendarOutlined />, label: "Soling", color: "var(--domain-sun2)" },
  { module: "energi", icon: <ThunderboltOutlined />, label: "Energi", color: "var(--domain-energy)" },
  { module: "ventilasjon", icon: <ExperimentOutlined />, label: "Ventilasjon", color: "var(--domain-vent)" },
  { module: "lys", icon: <BulbOutlined />, label: "Lys", color: "var(--domain-light)" },
  { module: "renhold", icon: <ToolOutlined />, label: "Renhold", color: "#0f766e" },
  { module: "mobil", icon: <MobileOutlined />, label: "Mobil", color: "var(--domain-mobile)" },
  { module: "admin", icon: <SettingOutlined />, label: "Admin", color: "#64748b" },
];

const mainModuleGroups = [
  { label: "Økonomi", modules: mainModules.slice(0, 3) },
  { label: "Bygg og drift", modules: mainModules.slice(3, 7) },
  { label: "System", modules: mainModules.slice(7) },
];

function selectedKey(pathname: string): string {
  const menuModule = mainModules.find((item) => pathname.startsWith(`/${item.module}`));
  return menuModule ? modulePath(menuModule.module) : "";
}

function activeModule(pathname: string): string | null {
  const module = pathname.split("/")[1];
  return MODULE_VIEWS[module] ? module : null;
}

function userInitial(user?: AuthUser | null): string {
  const name = user?.username?.trim();
  return name ? name.slice(0, 1).toUpperCase() : "";
}

function UserProfileMenu({ user, onAccount }: { user: AuthUser | null; onAccount: () => void }) {
  const [loggingOut, setLoggingOut] = useState(false);

  const items = useMemo<MenuProps["items"]>(
    () => [
      {
        key: "identity",
        disabled: true,
        label: (
          <div className="profile-menu-identity">
            <strong>{user?.username || "Ukjent bruker"}</strong>
            <span>{user?.roleLabel || "Innlogget"}</span>
          </div>
        ),
      },
      { type: "divider" },
      { key: "account", icon: <UserOutlined />, label: "Konto" },
      { key: "logout", icon: <LogoutOutlined />, label: "Logg ut", danger: true },
    ],
    [user],
  );

  async function handleMenuClick({ key }: { key: string }) {
    if (key === "account") {
      onAccount();
      return;
    }
    if (key !== "logout" || loggingOut) return;
    setLoggingOut(true);
    try {
      await logoutUser();
    } finally {
      window.location.replace("/auth/login");
    }
  }

  return (
    <Dropdown menu={{ items, onClick: handleMenuClick }} trigger={["click"]} placement="bottomRight">
      <Button className="profile-button" type="text" loading={loggingOut} aria-label="Brukerprofil og utlogging">
        <Avatar className="profile-avatar" size={28} icon={user ? undefined : <UserOutlined />}>
          {userInitial(user)}
        </Avatar>
        <span className="profile-name">{user?.username || "Bruker"}</span>
      </Button>
    </Dropdown>
  );
}

function LegacyRedirect({ to }: { to: string }) {
  const { search } = useLocation();
  return <Navigate to={`${to}${search}`} replace />;
}

function BuildFooter({ build }: { build?: string }) {
  return (
    <Link className="sider-build-link" to={modulePath("admin", "build")} aria-label="Åpne buildlogg">
      <span>Build</span>
      <strong>{build || "-"}</strong>
    </Link>
  );
}

function BrandHome({ className = "" }: { className?: string }) {
  return (
    <Link className={`brand-home-link ${className}`.trim()} to={modulePath("status", "oversikt")} aria-label="Gå til statusoversikt">
      <span className="brand-wordmark-wrap" aria-hidden="true">
        <img className="brand-wordmark" src={`/static/lilletorget-wordmark.png?v=${BRAND_ASSET_VERSION}`} alt="" />
      </span>
      <span className="brand-subtitle">Solsenter & parkering</span>
      <span className="brand-chip">Driftssystem</span>
    </Link>
  );
}

function SideNavigation({ activeKey }: { activeKey: string }) {
  return (
    <nav className="sider-nav" aria-label="Hovedmeny">
      {mainModuleGroups.map((group) => (
        <section className="sider-nav-group" key={group.label}>
          <div className="sider-nav-label">{group.label}</div>
          <div className="sider-nav-list">
            {group.modules.map((item) => {
              const path = modulePath(item.module);
              const active = activeKey === path;
              return (
                <Link
                  className={`sider-nav-item ${active ? "active" : ""} app-menu-${item.module}`}
                  key={item.module}
                  style={{ "--menu-item-color": item.color } as CSSProperties}
                  to={path}
                >
                  <span className="sider-nav-icon" aria-hidden="true">
                    {item.icon}
                  </span>
                  <span className="sider-nav-text">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </section>
      ))}
    </nav>
  );
}

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuHidden, setMenuHidden] = useState(() => window.localStorage.getItem(MENU_HIDDEN_STORAGE_KEY) === "1");
  const { data: user = null } = useQuery<AuthUser | null>({
    queryKey: queryKeys.auth.currentUser(),
    queryFn: fetchCurrentUser,
    retry: false,
    staleTime: 60_000,
  });
  const module = activeModule(location.pathname);
  const viewItems = module ? MODULE_VIEWS[module] ?? [] : [];
  const rawActiveView = module ? location.pathname.split("/")[2] || defaultModuleView(module) : "";
  const activeView = module && viewItems.some((item) => item.key === rawActiveView) ? rawActiveView : defaultModuleView(module || "");
  const activeMenuKey = selectedKey(location.pathname);

  useEffect(() => {
    window.localStorage.setItem(MENU_HIDDEN_STORAGE_KEY, menuHidden ? "1" : "0");
  }, [menuHidden]);

  return (
    <Layout className={`app-shell domain-${module ?? "status"} ${menuHidden ? "main-menu-hidden" : ""}`}>
      <Sider width={218} collapsedWidth={0} collapsed={menuHidden} trigger={null} className="app-sider">
        <BrandHome className="sider-brand" />
        <SideNavigation activeKey={activeMenuKey} />
        <BuildFooter build={user?.appBuild} />
      </Sider>
      <Layout>
        <Header className="app-header">
          <div className="app-header-left">
            <Button
              className="main-menu-toggle"
              type="text"
              icon={menuHidden ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setMenuHidden((value) => !value)}
              aria-label={menuHidden ? "Vis hovedmeny" : "Skjul hovedmeny"}
              title={menuHidden ? "Vis hovedmeny" : "Skjul hovedmeny"}
            />
            <Link className="header-home-link" to={modulePath("status", "oversikt")} aria-label="Gå til statusoversikt">
              <HomeOutlined />
              <span>Hjem</span>
            </Link>
          </div>
          <div className="app-header-main">
            {module && viewItems.length > 1 ? (
              <Segmented
                className="module-view-switcher top-view-switcher"
                value={activeView}
                options={viewItems.map((item) => ({ label: item.label, value: item.key }))}
                onChange={(next) => navigate(modulePath(module, String(next)))}
              />
            ) : null}
          </div>
          <UserProfileMenu user={user} onAccount={() => navigate(modulePath("admin", "brukere"))} />
        </Header>
        <Content className="app-content">
          <Suspense fallback={<LoadingBlock />}>
            <Routes>
              <Route index element={<Navigate to={modulePath("status")} replace />} />
              <Route path="/status" element={<Navigate to={modulePath("status")} replace />} />
              <Route path="/status/dashboard" element={<LegacyRedirect to={modulePath("status", "oversikt")} />} />
              <Route path="/status/nokkeltall" element={<LegacyRedirect to={modulePath("status", "oversikt")} />} />
              <Route path="/status/statistikk" element={<LegacyRedirect to={modulePath("omsetning", "oversikt")} />} />
              <Route path="/status/datakilder" element={<LegacyRedirect to={modulePath("admin", "datakilder")} />} />
              <Route path="/status/dagslinje" element={<LegacyRedirect to={modulePath("ventilasjon", "dagslogg")} />} />
              <Route path="/status/oversikt" element={<OverviewPage />} />
              <Route path="/status/omsetning" element={<Navigate to={modulePath("omsetning", "manedsoversikt")} replace />} />
              <Route path="/status/drift" element={<Navigate to={modulePath("admin", "drift")} replace />} />
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
              <Route path="/parkering/kjoretoy/:plate" element={<ParkingVehicleDetailPage />} />
              <Route path="/parkering/oppgjor" element={<ParkingSettlementsPage />} />
              <Route path="/parkering/oppgjor/:settlementId" element={<SettlementDetailPage />} />
              <Route path="/parkering/:view" element={<ModulePage module="parkering" />} />
              <Route path="/soling" element={<Navigate to={modulePath("soling")} replace />} />
              <Route path="/soling/sammenligning" element={<SunYearComparisonPage />} />
              <Route path="/soling/oppgjor" element={<SunSettlementsPage />} />
              <Route path="/soling/oppgjor/:settlementId" element={<SettlementDetailPage domain="soling" />} />
              <Route path="/soling/:view" element={<ModulePage module="soling" />} />
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
              <Route path="/mobil" element={<Navigate to={modulePath("mobil")} replace />} />
              <Route path="/mobil/oversikt" element={<MobileOverviewPage />} />
              <Route path="/mobil/:view" element={<MobileOverviewPage />} />
              <Route path="/renhold" element={<Navigate to={modulePath("renhold")} replace />} />
              <Route path="/renhold/robot/:duid" element={<LegacyRedirect to={modulePath("renhold", "roboter")} />} />
              <Route path="/renhold/:view" element={<ModulePage module="renhold" />} />
              <Route path="/admin" element={<Navigate to={modulePath("admin")} replace />} />
              <Route path="/admin/drift" element={<OperationsPage />} />
              <Route path="/admin/build" element={<BuildLogPage />} />
              <Route path="/admin/build/:build" element={<BuildDetailPage />} />
              <Route path="/admin/:view" element={<ModulePage module="admin" />} />
              <Route
                path="*"
                element={
                  <div className="empty-state">
                    <Typography.Title level={3}>Siden finnes ikke ennå</Typography.Title>
                    <Typography.Paragraph>
                      Bruk menyen til venstre eller gå til <Link to={modulePath("status", "oversikt")}>oversikten</Link>.
                    </Typography.Paragraph>
                  </div>
                }
              />
            </Routes>
          </Suspense>
        </Content>
      </Layout>
    </Layout>
  );
}
