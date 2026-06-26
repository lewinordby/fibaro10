import {
  BarChartOutlined,
  BulbOutlined,
  CalendarOutlined,
  CarOutlined,
  ExperimentOutlined,
  MobileOutlined,
  SettingOutlined,
  ToolOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import type { ReactNode } from "react";
import { modulePath } from "./moduleViews";

export type MainNavigationModule = {
  module: string;
  icon: ReactNode;
  label: string;
  color: string;
};

const mainModules: MainNavigationModule[] = [
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

export const mainModuleGroups = [
  { label: "Økonomi", modules: mainModules.slice(0, 3) },
  { label: "Bygg og drift", modules: mainModules.slice(3, 7) },
  { label: "System", modules: mainModules.slice(7) },
];

export function selectedMainModuleKey(pathname: string): string {
  const menuModule = mainModules.find((item) => pathname.startsWith(`/${item.module}`));
  return menuModule ? modulePath(menuModule.module) : "";
}
