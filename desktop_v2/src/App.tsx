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
  { key: "/parkering", icon: <CarOutlined />, label: "Parkering" },
  { key: "/soling", icon: <CalendarOutlined />, label: "Soling" },
  { key: "/energi", icon: <ThunderboltOutlined />, label: "Energi" },
  { key: "/ventilasjon", icon: <ExperimentOutlined />, label: "Ventilasjon" },
  { key: "/lys", icon: <BulbOutlined />, label: "Lys" },
  { key: "/renhold", icon: <ToolOutlined />, label: "Renhold" },
  { key: "/admin", icon: <SettingOutlined />, label: "Admin" },
];

function selectedKey(pathname: string): string {
  if (pathname.startsWith("/omsetning")) return "/omsetning";
  if (pathname.startsWith("/drift")) return "/drift";
  if (pathname.startsWith("/parkering")) return "/parkering";
  if (pathname.startsWith("/soling")) return "/soling";
  if (pathname.startsWith("/energi")) return "/energi";
  if (pathname.startsWith("/ventilasjon")) return "/ventilasjon";
  if (pathname.startsWith("/lys")) return "/lys";
  if (pathname.startsWith("/renhold")) return "/renhold";
  if (pathname.startsWith("/admin")) return "/admin";
  return "/oversikt";
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
            <Route path="/parkering" element={<ModulePage module="parkering" />} />
            <Route path="/soling" element={<ModulePage module="soling" />} />
            <Route path="/energi" element={<ModulePage module="energi" />} />
            <Route path="/ventilasjon" element={<ModulePage module="ventilasjon" />} />
            <Route path="/lys" element={<ModulePage module="lys" />} />
            <Route path="/renhold" element={<ModulePage module="renhold" />} />
            <Route path="/admin" element={<ModulePage module="admin" />} />
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
