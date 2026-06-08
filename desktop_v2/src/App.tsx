import {
  AlertOutlined,
  AreaChartOutlined,
  BulbOutlined,
  CalendarOutlined,
  CarOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  SettingOutlined,
  ToolOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Space, Typography } from "antd";
import type { MenuProps } from "antd";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import OverviewPage from "./pages/OverviewPage";
import RevenueMonthPage from "./pages/RevenueMonthPage";
import OperationsPage from "./pages/OperationsPage";
import ModulePage from "./pages/ModulePage";

const { Header, Sider, Content } = Layout;

const menuItems: MenuProps["items"] = [
  { key: "/oversikt", icon: <DashboardOutlined />, label: "Oversikt" },
  { key: "/omsetning", icon: <AreaChartOutlined />, label: "Omsetning" },
  { key: "/drift", icon: <DatabaseOutlined />, label: "Drift" },
  {
    key: "/parkering",
    icon: <CarOutlined />,
    label: "Parkering",
    children: [
      { key: "/parkering/oversikt", label: "Oversikt" },
      { key: "/parkering/prognose", label: "Prognose" },
      { key: "/parkering/parkeringer", label: "Parkeringer" },
      { key: "/parkering/kjoretoy", label: "Kjøretøy" },
      { key: "/parkering/bilstatistikk", label: "Bilstatistikk" },
      { key: "/parkering/omrade", label: "Område" },
    ],
  },
  {
    key: "/soling",
    icon: <CalendarOutlined />,
    label: "Soling",
    children: [
      { key: "/soling/dagslinje", label: "Dagslinje" },
      { key: "/soling/prognose", label: "Prognose" },
      { key: "/soling/statistikk", label: "Statistikk" },
      { key: "/soling/enkeltimer", label: "Enkeltimer" },
      { key: "/soling/senger", label: "Senger" },
      { key: "/soling/medlemmer", label: "Medlemmer" },
    ],
  },
  {
    key: "/energi",
    icon: <ThunderboltOutlined />,
    label: "Energi",
    children: [
      { key: "/energi/status", label: "Status" },
      { key: "/energi/kurser", label: "Kurser" },
      { key: "/energi/laster", label: "Laster" },
      { key: "/energi/forbruk-per-seng", label: "Forbruk/seng" },
      { key: "/energi/elvia", label: "Elvia" },
    ],
  },
  {
    key: "/ventilasjon",
    icon: <ExperimentOutlined />,
    label: "Ventilasjon",
    children: [
      { key: "/ventilasjon/dagslogg", label: "Dagslogg" },
      { key: "/ventilasjon/temp-logg", label: "Temp logg" },
      { key: "/ventilasjon/yr-logg", label: "Yr logg" },
      { key: "/ventilasjon/hendelser", label: "Hendelser" },
    ],
  },
  {
    key: "/lys",
    icon: <BulbOutlined />,
    label: "Lys",
    children: [
      { key: "/lys/dagslogg", label: "Dagslogg" },
      { key: "/lys/lux-logging", label: "Lux logging" },
      { key: "/lys/hendelser", label: "Hendelser" },
    ],
  },
  { key: "/renhold/oversikt", icon: <ToolOutlined />, label: "Renhold" },
  {
    key: "/admin",
    icon: <SettingOutlined />,
    label: "Admin",
    children: [
      { key: "/admin/build", label: "Build" },
      { key: "/admin/datakilder", label: "Datakilder" },
      { key: "/admin/ai", label: "AI" },
      { key: "/admin/teknisk", label: "Teknisk" },
    ],
  },
];

function selectedKey(pathname: string): string {
  return pathname === "/" ? "/oversikt" : pathname;
}

function openKeys(pathname: string): string[] {
  return ["/parkering", "/soling", "/energi", "/ventilasjon", "/lys", "/admin"].filter((key) =>
    pathname.startsWith(key),
  );
}

function moduleRoute(module: string, fallback: string) {
  return <ModulePage module={module} view={fallback} />;
}

function moduleSubRoute(module: string) {
  return <ModulePage module={module} />;
}

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Layout className="app-shell">
      <Sider width={236} className="app-sider">
        <div className="brand">
          <div className="brand-mark">L</div>
          <div>
            <div className="brand-title">Fibaro10</div>
            <div className="brand-subtitle">Desktop v2</div>
          </div>
        </div>
        <Menu
          className="app-menu"
          mode="inline"
          selectedKeys={[selectedKey(location.pathname)]}
          defaultOpenKeys={openKeys(location.pathname)}
          items={menuItems}
          onClick={({ key }) => {
            navigate(key);
          }}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space direction="vertical" size={0}>
            <Typography.Text className="eyebrow">Ny revisjon</Typography.Text>
            <Typography.Title level={2} className="page-title">
              Driftsflate for Lilletorget
            </Typography.Title>
          </Space>
          <Space>
            <Button icon={<AlertOutlined />} onClick={() => navigate("/drift")}>
              Datakilder
            </Button>
            <Button type="primary" onClick={() => navigate("/admin")}>
              Build og teknisk
            </Button>
          </Space>
        </Header>
        <Content className="app-content">
          <Routes>
            <Route index element={<Navigate to="/oversikt" replace />} />
            <Route path="/oversikt" element={<OverviewPage />} />
            <Route path="/omsetning" element={<RevenueMonthPage />} />
            <Route path="/drift" element={<OperationsPage />} />
            <Route path="/parkering" element={moduleRoute("parkering", "oversikt")} />
            <Route path="/parkering/:view" element={moduleSubRoute("parkering")} />
            <Route path="/soling" element={moduleRoute("soling", "dagslinje")} />
            <Route path="/soling/:view" element={moduleSubRoute("soling")} />
            <Route path="/energi" element={moduleRoute("energi", "status")} />
            <Route path="/energi/:view" element={moduleSubRoute("energi")} />
            <Route path="/ventilasjon" element={moduleRoute("ventilasjon", "dagslogg")} />
            <Route path="/ventilasjon/:view" element={moduleSubRoute("ventilasjon")} />
            <Route path="/lys" element={moduleRoute("lys", "dagslogg")} />
            <Route path="/lys/:view" element={moduleSubRoute("lys")} />
            <Route path="/renhold" element={moduleRoute("renhold", "oversikt")} />
            <Route path="/renhold/:view" element={moduleSubRoute("renhold")} />
            <Route path="/admin" element={moduleRoute("admin", "build")} />
            <Route path="/admin/:view" element={moduleSubRoute("admin")} />
            <Route
              path="*"
              element={
                <div className="empty-state">
                  <Typography.Title level={3}>Siden finnes ikke i v2 ennå</Typography.Title>
                  <Typography.Paragraph>
                    Bruk menyen til venstre eller gå til <Link to="/oversikt">oversikten</Link>.
                  </Typography.Paragraph>
                </div>
              }
            />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}
