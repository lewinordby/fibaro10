import {
  LogoutOutlined,
  BarChartOutlined,
  BulbOutlined,
  CalendarOutlined,
  CarOutlined,
  ExperimentOutlined,
  SettingOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Avatar, Button, Dropdown, Layout, Menu, Segmented, Typography } from "antd";
import type { MenuProps } from "antd";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { fetchCurrentUser, logoutUser, type AuthUser } from "./api";
import { LoadingBlock } from "./components/AsyncState";
import { defaultModuleView, modulePath, MODULE_VIEWS } from "./moduleViews";

const { Header, Sider, Content } = Layout;

const OverviewPage = lazy(() => import("./pages/OverviewPage"));
const RevenueMonthPage = lazy(() => import("./pages/RevenueMonthPage"));
const OperationsPage = lazy(() => import("./pages/OperationsPage"));
const ModulePage = lazy(() => import("./pages/ModulePage"));
const BuildDetailPage = lazy(() => import("./pages/BuildDetailPage"));
const BuildLogPage = lazy(() => import("./pages/BuildLogPage"));
const ParkingVehicleDetailPage = lazy(() => import("./pages/ParkingVehicleDetailPage"));
const StatusComparisonPage = lazy(() => import("./pages/StatusComparisonPage"));

const mainModules = [
  { module: "omsetning", icon: <BarChartOutlined />, label: "Omsetning" },
  { module: "parkering", icon: <CarOutlined />, label: "Parkering" },
  { module: "soling", icon: <CalendarOutlined />, label: "Soling" },
  { module: "energi", icon: <ThunderboltOutlined />, label: "Energi" },
  { module: "ventilasjon", icon: <ExperimentOutlined />, label: "Ventilasjon" },
  { module: "lys", icon: <BulbOutlined />, label: "Lys" },
  { module: "renhold", icon: <ToolOutlined />, label: "Renhold" },
  { module: "admin", icon: <SettingOutlined />, label: "Admin" },
];

const menuItems: MenuProps["items"] = mainModules.map((item) => ({
  key: modulePath(item.module),
  icon: item.icon,
  label: item.label,
}));

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

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<AuthUser | null>(null);
  const module = activeModule(location.pathname);
  const viewItems = module ? MODULE_VIEWS[module] ?? [] : [];
  const rawActiveView = module ? location.pathname.split("/")[2] || defaultModuleView(module) : "";
  const activeView = module && viewItems.some((item) => item.key === rawActiveView) ? rawActiveView : defaultModuleView(module || "");
  const activeMenuKey = selectedKey(location.pathname);

  useEffect(() => {
    let active = true;
    fetchCurrentUser()
      .then((value) => {
        if (active) setUser(value);
      })
      .catch(() => {
        if (active) setUser(null);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Layout className={`app-shell domain-${module ?? "status"}`}>
      <Sider width={218} className="app-sider">
        <Link className="brand" to={modulePath("status", "oversikt")} aria-label="Gå til statusoversikt">
          <div className="brand-mark">L</div>
          <div>
            <div className="brand-title">Fibaro10</div>
            <div className="brand-subtitle">Lilletorget drift</div>
          </div>
        </Link>
        <Menu
          className="app-menu"
          mode="inline"
          selectedKeys={activeMenuKey ? [activeMenuKey] : []}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
        <BuildFooter build={user?.appBuild} />
      </Sider>
      <Layout>
        <Header className="app-header">
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
              <Route path="/omsetning/sammenligning" element={<StatusComparisonPage />} />
              <Route path="/omsetning/:view" element={<ModulePage module="omsetning" />} />
              <Route path="/parkering" element={<Navigate to={modulePath("parkering")} replace />} />
              <Route path="/parkering/statistikk" element={<LegacyRedirect to={modulePath("parkering", "bilstatistikk")} />} />
              <Route path="/parkering/navn-oppslag" element={<LegacyRedirect to={modulePath("parkering", "oppslag")} />} />
              <Route path="/parkering/omrade-oppslag" element={<LegacyRedirect to={modulePath("parkering", "oppslag")} />} />
              <Route path="/parkering/kjoretoy/:plate" element={<ParkingVehicleDetailPage />} />
              <Route path="/parkering/:view" element={<ModulePage module="parkering" />} />
              <Route path="/soling" element={<Navigate to={modulePath("soling")} replace />} />
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
