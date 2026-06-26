import {
  BarChartOutlined,
  BulbOutlined,
  CalendarOutlined,
  CarOutlined,
  ExperimentOutlined,
  HomeOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MobileOutlined,
  SettingOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Avatar, Button, Dropdown, Layout, Segmented } from "antd";
import type { MenuProps } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { fetchCurrentUser, logoutUser, type AuthUser } from "../api";
import { modulePath, type ModuleView } from "../moduleViews";
import { queryKeys } from "../queryKeys";

const { Header, Sider, Content } = Layout;
const MENU_HIDDEN_STORAGE_KEY = "fibaro10:mainMenuHidden";
const BRAND_ASSET_VERSION = "20260626-shell";

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

type AppShellProps = {
  activeView: string;
  children: ReactNode;
  module: string | null;
  viewItems: ModuleView[];
};

export function AppShell({ activeView, children, module, viewItems }: AppShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuHidden, setMenuHidden] = useState(() => window.localStorage.getItem(MENU_HIDDEN_STORAGE_KEY) === "1");
  const { data: user = null } = useQuery<AuthUser | null>({
    queryKey: queryKeys.auth.currentUser(),
    queryFn: fetchCurrentUser,
    retry: false,
    staleTime: 60_000,
  });
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
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
