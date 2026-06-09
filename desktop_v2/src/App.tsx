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
import { modulePath } from "./moduleViews";

const { Header, Sider, Content } = Layout;

const menuItems: MenuProps["items"] = [
  { key: "/oversikt", icon: <DashboardOutlined />, label: "Oversikt" },
  { key: "/omsetning", icon: <AreaChartOutlined />, label: "Omsetning" },
  { key: "/drift", icon: <DatabaseOutlined />, label: "Drift" },
  { key: modulePath("parkering"), icon: <CarOutlined />, label: "Parkering" },
  { key: modulePath("soling"), icon: <CalendarOutlined />, label: "Soling" },
  { key: modulePath("energi"), icon: <ThunderboltOutlined />, label: "Energi" },
  { key: modulePath("ventilasjon"), icon: <ExperimentOutlined />, label: "Ventilasjon" },
  { key: modulePath("lys"), icon: <BulbOutlined />, label: "Lys" },
  { key: modulePath("renhold"), icon: <ToolOutlined />, label: "Renhold" },
  { key: modulePath("admin"), icon: <SettingOutlined />, label: "Admin" },
];

function selectedKey(pathname: string): string {
  if (pathname === "/" || pathname.startsWith("/oversikt")) return "/oversikt";
  if (pathname.startsWith("/omsetning")) return "/omsetning";
  if (pathname.startsWith("/drift")) return "/drift";
  if (pathname.startsWith("/parkering")) return modulePath("parkering");
  if (pathname.startsWith("/soling")) return modulePath("soling");
  if (pathname.startsWith("/energi")) return modulePath("energi");
  if (pathname.startsWith("/ventilasjon")) return modulePath("ventilasjon");
  if (pathname.startsWith("/lys")) return modulePath("lys");
  if (pathname.startsWith("/renhold")) return modulePath("renhold");
  if (pathname.startsWith("/admin")) return modulePath("admin");
  return pathname;
}

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Layout className="app-shell">
      <Sider width={218} className="app-sider">
        <div className="brand">
          <div className="brand-mark">L</div>
          <div>
            <div className="brand-title">Fibaro10</div>
            <div className="brand-subtitle">Lilletorget drift</div>
          </div>
        </div>
        <Menu
          className="app-menu"
          mode="inline"
          selectedKeys={[selectedKey(location.pathname)]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space direction="vertical" size={0}>
            <Typography.Text className="eyebrow">Primær drift</Typography.Text>
            <Typography.Title level={2} className="page-title">
              Lilletorget
            </Typography.Title>
          </Space>
          <Space>
            <Button icon={<AlertOutlined />} onClick={() => navigate("/drift")}>
              Datakilder
            </Button>
            <Button type="primary" onClick={() => navigate(modulePath("admin", "build"))}>
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
            <Route path="/parkering" element={<Navigate to={modulePath("parkering")} replace />} />
            <Route path="/parkering/:view" element={<ModulePage module="parkering" />} />
            <Route path="/soling" element={<Navigate to={modulePath("soling")} replace />} />
            <Route path="/soling/:view" element={<ModulePage module="soling" />} />
            <Route path="/energi" element={<Navigate to={modulePath("energi")} replace />} />
            <Route path="/energi/:view" element={<ModulePage module="energi" />} />
            <Route path="/ventilasjon" element={<Navigate to={modulePath("ventilasjon")} replace />} />
            <Route path="/ventilasjon/:view" element={<ModulePage module="ventilasjon" />} />
            <Route path="/lys" element={<Navigate to={modulePath("lys")} replace />} />
            <Route path="/lys/:view" element={<ModulePage module="lys" />} />
            <Route path="/renhold" element={<Navigate to={modulePath("renhold")} replace />} />
            <Route path="/renhold/:view" element={<ModulePage module="renhold" />} />
            <Route path="/admin" element={<Navigate to={modulePath("admin")} replace />} />
            <Route path="/admin/:view" element={<ModulePage module="admin" />} />
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
