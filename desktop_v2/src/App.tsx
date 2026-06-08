import {
  AlertOutlined,
  AreaChartOutlined,
  BulbOutlined,
  CalendarOutlined,
  CarOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  HomeOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Space, Typography } from "antd";
import type { MenuProps } from "antd";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import OverviewPage from "./pages/OverviewPage";
import RevenueMonthPage from "./pages/RevenueMonthPage";
import OperationsPage from "./pages/OperationsPage";

const { Header, Sider, Content } = Layout;

const menuItems: MenuProps["items"] = [
  { key: "/oversikt", icon: <DashboardOutlined />, label: "Oversikt" },
  { key: "/omsetning", icon: <AreaChartOutlined />, label: "Omsetning" },
  { key: "/drift", icon: <DatabaseOutlined />, label: "Drift" },
  { type: "divider" },
  { key: "legacy:/status/dashboard", icon: <HomeOutlined />, label: "Dagens status" },
  { key: "legacy:/parkering/oversikt", icon: <CarOutlined />, label: "Parkering" },
  { key: "legacy:/soling/dagslinje", icon: <CalendarOutlined />, label: "Soling" },
  { key: "legacy:/energi/status", icon: <ThunderboltOutlined />, label: "Energi" },
  { key: "legacy:/lys/dagslogg-lux", icon: <BulbOutlined />, label: "Lys" },
  { key: "legacy:/ventilasjon/dagslogg-temp", icon: <ExperimentOutlined />, label: "Ventilasjon" },
];

function selectedKey(pathname: string): string {
  if (pathname.startsWith("/omsetning")) return "/omsetning";
  if (pathname.startsWith("/drift")) return "/drift";
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
            if (key.startsWith("legacy:")) {
              window.location.href = key.replace("legacy:", "");
              return;
            }
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
            <Button icon={<AlertOutlined />} href="/status/datakilder">
              Datakilder
            </Button>
            <Button type="primary" href="/status/dashboard">
              Gammel revisjon
            </Button>
          </Space>
        </Header>
        <Content className="app-content">
          <Routes>
            <Route index element={<Navigate to="/oversikt" replace />} />
            <Route path="/oversikt" element={<OverviewPage />} />
            <Route path="/omsetning" element={<RevenueMonthPage />} />
            <Route path="/drift" element={<OperationsPage />} />
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
