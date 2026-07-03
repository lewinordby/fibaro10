import {
  BarChartOutlined,
  BulbOutlined,
  CalendarOutlined,
  CarOutlined,
  CarryOutOutlined,
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
  { module: "koble", icon: <ToolOutlined /> },
  { module: "energi", icon: <ThunderboltOutlined /> },
  { module: "ventilasjon", icon: <ExperimentOutlined /> },
  { module: "lys", icon: <BulbOutlined /> },
  { module: "vedlikehold", icon: <CarryOutOutlined /> },
  { module: "ideer", icon: <BulbOutlined /> },
  { module: "renhold", icon: <ToolOutlined /> },
  { module: "mobil", icon: <MobileOutlined /> },
  { module: "admin", icon: <SettingOutlined /> },
];

const mainModules: MainNavigationModule[] = mainModuleIcons.map((item) => ({
  ...item,
  label: moduleNavigationLabel(item.module),
  color: moduleColor(item.module),
}));

const mainModulesByKey = new Map(mainModules.map((item) => [item.module, item]));
const modulesForGroup = (modules: string[]) =>
  modules.map((module) => mainModulesByKey.get(module)).filter(Boolean) as MainNavigationModule[];

export const mainModuleGroups = [
  { label: "", modules: modulesForGroup(["status"]) },
  { label: "Økonomi", modules: modulesForGroup(["omsetning", "parkering", "soling", "koble"]) },
  { label: "Bygg og drift", modules: modulesForGroup(["energi", "ventilasjon", "lys", "renhold", "vedlikehold"]) },
  { label: "System", modules: modulesForGroup(["ideer", "mobil", "admin"]) },
];

export function selectedMainModuleKey(pathname: string): string {
  const menuModule = mainModules.find((item) => pathname.startsWith(`/${item.module}`));
  return menuModule ? modulePath(menuModule.module) : "";
}
