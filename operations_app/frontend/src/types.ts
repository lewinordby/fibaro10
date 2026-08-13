import type { JsonRecord, ModuleCard } from "@lilletorget/microapp-ui/types";

export type VentilationMeasurement = { key: string; label: string; temperature?: number | null; humidity?: number | null; detail?: string };
export type VentilationMeasurementGroup = { key: string; title: string; fields: VentilationMeasurement[] };
export type VentilationFan = { key: string; label: string; state: boolean | null; detail?: string; statusSource?: string | null; checkedAt?: string | null };
export type VentilationDaySeries = { key: string; label: string; kind?: "temperature" | "humidity"; unit?: string; color: string; default?: boolean };
export type VentilationFanEvent = { fan_key: string; fan_name: string; fan_short: string; color: string; x: number; time: string; action: string; class: "on" | "off"; detail: string };
export type SettingField = { key: string; label: string; type: "time" | "int" | "float" | "bool" | "text"; unit?: string; help?: string; value: string | number | boolean | null };
export type SettingsData = { version: number; updatedAt?: string | null; updatedBy?: string | null; groups: Array<{ title: string; description?: string; fields: SettingField[] }>; rules: string[]; updateEndpoint: string };
export type ControlSettings = SettingsData & { system: string; title: string; subtitle?: string };
export type VentilationData = {
  view: string;
  latest: {
    bucketStart?: string | null;
    mode?: string | null;
    groups: VentilationMeasurementGroup[];
    fans: VentilationFan[];
    weather: { text?: string | null; airTemperature?: number | null; relativeHumidity?: number | null; windSpeed?: number | null; cloudAreaFraction?: number | null };
  };
  day: {
    selectedDay: string;
    selectedDayLabel: string;
    prevDay: string;
    nextDay: string;
    isToday: boolean;
    nowMarker: number | null;
    series: VentilationDaySeries[];
    fans: Array<{ key: string; name: string; short?: string; color?: string; sample_attr?: string }>;
    fanEvents: VentilationFanEvent[];
    samples: JsonRecord[];
  };
  settings?: SettingsData;
};
export type OperationsOverviewResponse = {
  generatedAt: string;
  operatingWindow: { label: string; detail: string; open: boolean };
  cards: Array<ModuleCard & { group?: string }>;
  latestItems: Array<{ label: string; value: string; detail?: string; href?: string }>;
  services: Array<{
    sourceNo?: number;
    jobName?: string;
    label: string;
    status: string;
    detail?: string;
    lastSuccessAt?: string | null;
    nextExpectedAt?: string | null;
  }>;
  lightItems: Array<{ label: string; state: boolean | null; tooltip?: string | null }>;
  fanItems: Array<{
    label: string;
    state: boolean | null;
    tooltip?: string | null;
    statusSource?: string | null;
    checkedAt?: string | null;
  }>;
};
