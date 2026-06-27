import {
  BarChartOutlined,
  BulbOutlined,
  CalendarOutlined,
  CarOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  MobileOutlined,
  SettingOutlined,
  ToolOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import type { ReactNode } from "react";
import { moduleColor, moduleNavigationLabel, modulePath } from "./moduleViews";

export type MainNavigationModule = {
  module: string;
  icon: ReactNode;
  label: string;
  color: string;
};

const mainModuleIcons: Array<Pick<MainNavigationModule, "module" | "icon">> = [
  { module: "status", icon: <DashboardOutlined /> },
  { module: "omsetning", icon: <BarChartOutlined /> },
  { module: "parkering", icon: <CarOutlined /> },
  { module: "soling", icon: <CalendarOutlined /> },
  { module: "energi", icon: <ThunderboltOutlined /> },
  { module: "ventilasjon", icon: <ExperimentOutlined /> },
  { module: "lys", icon: <BulbOutlined /> },
  { module: "renhold", icon: <ToolOutlined /> },
  { module: "mobil", icon: <MobileOutlined /> },
  { module: "admin", icon: <SettingOutlined /> },
];

const mainModules: MainNavigationModule[] = mainModuleIcons.map((item) => ({
  ...item,
  label: moduleNavigationLabel(item.module),
  color: moduleColor(item.module),
}));

export const mainModuleGroups = [
  { label: "", modules: mainModules.slice(0, 1) },
  { label: "Økonomi", modules: mainModules.slice(1, 4) },
  { label: "Bygg og drift", modules: mainModules.slice(4, 8) },
  { label: "System", modules: mainModules.slice(8) },
];

export function selectedMainModuleKey(pathname: string): string {
  const menuModule = mainModules.find((item) => pathname.startsWith(`/${item.module}`));
  return menuModule ? modulePath(menuModule.module) : "";
}
