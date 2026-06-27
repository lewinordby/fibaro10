import { Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";

import type { ModuleTable, VentilationData } from "../../api";
const LABELS: Record<string, string> = {
  time: "Tid",
  bucket_start: "Tid",
  timestamp: "Tid",
  mode: "Modus",
  temp_1etg: "1.etg",
  temp_2etg: "2.etg",
  temp_vip: "VIP",
  temp_ute: "Ute styring",
  temp_ute_netatmo: "Netatmo ute",
  temp_yr: "Yr temp",
  temp_loft: "Loft",
  temp_luftinntak: "Innluft",
  temp_passiv: "Passiv innluft",
  temp_kjeller: "Kjeller",
  humidity_1etg: "Fukt 1.etg",
  humidity_2etg: "Fukt 2.etg",
  humidity_vip: "Fukt VIP",
  humidity_ute: "Fukt ute",
  humidity_yr: "Fukt Yr",
  humidity_loft: "Fukt loft",
  humidity_luftinntak: "Fukt innluft",
  humidity_passiv: "Fukt passiv",
  humidity_kjeller: "Fukt kjeller",
  fan_vip: "VIP",
  fan_2etg: "2.etg",
  fan_tak: "Tak",
  fan_avfukter: "Avfukter",
  weather_text: "Vær",
  air_temperature: "Lufttemp",
  relative_humidity: "Fukt",
  wind_speed: "Vind",
  wind_speed_of_gust: "Vindkast",
  cloud_area_fraction: "Skydekke",
  precipitation_next_1h: "Nedbør 1t",
  action: "Handling",
  device_name: "Enhet",
  reason: "Årsak",
  state: "Status",
  rule: "Regel",
  description: "Beskrivelse",
  group: "Gruppe",
  label: "Navn",
  value: "Verdi",
  unit: "Enhet",
  help: "Forklaring",
  changed_at: "Endret",
  changed_by: "Endret av",
  version: "Versjon",
};

function label(column: string): string {
  return LABELS[column] ?? column.replaceAll("_", " ");
}

export function numberText(value: unknown, digits = 1): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: digits }).format(value);
}

export function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "PÅ" : "AV";
  if (typeof value === "number") return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 2 }).format(value);
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}T/.test(text)) {
    const date = new Date(text);
    if (!Number.isNaN(date.getTime())) return date.toLocaleString("nb-NO");
  }
  return text;
}

export function timeText(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) return date.toLocaleString("nb-NO");
  return value;
}

export function minuteFromTime(value: unknown): number | null {
  if (typeof value !== "string") return null;
  const match = value.match(/^(\d{1,2}):(\d{2})/);
  if (!match) return null;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes) || minutes > 59) return null;
  if (hours === 24 && minutes === 0) return 1440;
  if (hours < 0 || hours > 23) return null;
  return hours * 60 + minutes;
}

export function minuteLabel(value: number | string | undefined): string {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return "--:--";
  const minute = Math.max(0, Math.min(1440, Math.round(numeric)));
  const hours = Math.floor(minute / 60);
  const minutes = minute % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

export function minuteFromEventX(value: number): number {
  return Math.max(0, Math.min(1440, Math.round((value / 1000) * 1440)));
}

export function percentFromEventX(value: number): number {
  return Math.max(0, Math.min(100, value / 10));
}

export type DayChartSample = {
  sample: Record<string, unknown>;
  minute: number;
};

export type DayChartTooltipParam = {
  axisValue?: number | string;
  marker?: string;
  seriesName?: string;
  value?: unknown;
};

export type VentChartFocus = "temperature" | "humidity";
type VentFanEvent = VentilationData["day"]["fanEvents"][number];

export type VentFanRunSegment = {
  left: number;
  width: number;
  color: string;
  title: string;
};

function booleanSampleValue(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return Number.isFinite(value) ? value !== 0 : null;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "on", "paa", "p\u00e5"].includes(normalized)) return true;
    if (["0", "false", "off", "av"].includes(normalized)) return false;
  }
  return null;
}

export function fanSampleRunSegments(
  samples: Record<string, unknown>[],
  sampleAttr: string | undefined,
  color: string,
  label: string,
  endPercent: number,
): VentFanRunSegment[] {
  if (!sampleAttr) return [];
  const sorted = samples
    .map((sample) => ({ minute: minuteFromTime(sample.time), state: booleanSampleValue(sample[sampleAttr]) }))
    .filter((item): item is { minute: number; state: boolean } => item.minute !== null && item.state !== null)
    .sort((left, right) => left.minute - right.minute);

  const segments: VentFanRunSegment[] = [];
  let activeStart: number | null = null;
  for (const sample of sorted) {
    const percent = Math.max(0, Math.min(100, (sample.minute / 1440) * 100));
    if (sample.state) {
      if (activeStart === null) activeStart = percent;
      continue;
    }
    if (activeStart === null) continue;
    if (percent > activeStart) {
      segments.push({
        left: activeStart,
        width: percent - activeStart,
        color,
        title: `${minuteLabel(Math.round((activeStart / 100) * 1440))}-${minuteLabel(sample.minute)} ${label} aktiv`,
      });
    }
    activeStart = null;
  }

  if (activeStart !== null) {
    const right = Math.max(activeStart, Math.min(100, endPercent));
    if (right > activeStart) {
      segments.push({
        left: activeStart,
        width: right - activeStart,
        color,
        title: `${minuteLabel(Math.round((activeStart / 100) * 1440))}-${minuteLabel(Math.round((right / 100) * 1440))} ${label} aktiv`,
      });
    }
  }

  return segments;
}

export function fanRunSegments(events: VentFanEvent[], endPercent: number): VentFanRunSegment[] {
  const sorted = [...events].sort((left, right) => left.x - right.x);
  const segments: VentFanRunSegment[] = [];
  let activeStart: VentFanEvent | null = null;

  for (const event of sorted) {
    if (event.class === "on") {
      if (!activeStart) activeStart = event;
      continue;
    }

    if (!activeStart) continue;
    const left = percentFromEventX(activeStart.x);
    const right = percentFromEventX(event.x);
    if (right > left) {
      segments.push({
        left,
        width: right - left,
        color: activeStart.color || event.color,
        title: `${activeStart.time}-${event.time} ${event.fan_short} aktiv`,
      });
    }
    activeStart = null;
  }

  if (activeStart) {
    const left = percentFromEventX(activeStart.x);
    const right = Math.max(left, Math.min(100, endPercent));
    if (right > left) {
      segments.push({
        left,
        width: right - left,
        color: activeStart.color,
        title: `${activeStart.time}-${minuteLabel(Math.round((right / 100) * 1440))} ${activeStart.fan_short} aktiv`,
      });
    }
  }

  return segments;
}

export function chartFocusFromSearch(value: string | null): VentChartFocus {
  return value === "humidity" ? "humidity" : "temperature";
}

export function seriesFocus(series: { key: string; kind?: string }): VentChartFocus {
  if (series.kind === "humidity" || series.key.startsWith("humidity_")) return "humidity";
  return "temperature";
}

function chartValue(value: unknown): number | null {
  if (Array.isArray(value) && typeof value[1] === "number") return value[1];
  if (typeof value === "number") return value;
  return null;
}

export function formatDayChartTooltip(params: DayChartTooltipParam | DayChartTooltipParam[], unit: string): string {
  const items = (Array.isArray(params) ? params : [params]).filter((item) => item.seriesName && item.seriesName !== "__fan_events");
  const first = items[0];
  const firstMinute = Array.isArray(first?.value) && typeof first.value[0] === "number" ? first.value[0] : first?.axisValue;
  const lines = [minuteLabel(firstMinute)];
  items.forEach((item) => {
    const value = chartValue(item.value);
    if (value === null) return;
    lines.push(`${item.marker ?? ""}${item.seriesName}: ${numberText(value)}${unit}`);
  });
  return lines.join("<br/>");
}

export function stateTag(state: boolean | null | undefined) {
  if (state === true) return <Tag color="green">PÅ</Tag>;
  if (state === false) return <Tag>AV</Tag>;
  return <Tag color="default">-</Tag>;
}

export function filterRows(rows: Record<string, unknown>[], columns: string[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return rows;
  return rows.filter((row) => columns.some((column) => valueText(row[column]).toLowerCase().includes(normalized)));
}

function tableColumns(table: ModuleTable): ColumnsType<Record<string, unknown>> {
  return table.columns.map((column) => ({
    title: label(column),
    dataIndex: column,
    key: column,
    ellipsis: true,
    align: /(temp|humidity|wind|cloud|precipitation|count|value)$/i.test(column) ? "right" : undefined,
    render: (value: unknown) => (typeof value === "boolean" ? stateTag(value) : valueText(value)),
  }));
}

export function VentilationTable({ table, query }: { table: ModuleTable; query: string }) {
  const rows = filterRows(table.rows, table.columns, query);
  return (
    <Table
      rowKey={(row, index) => `${table.title}-${row.id ?? row.time ?? row.bucket_start ?? row.timestamp ?? index}`}
      size="small"
      columns={tableColumns(table)}
      dataSource={rows}
      pagination={{ pageSize: 25, showSizeChanger: true }}
      scroll={{ x: "max-content" }}
    />
  );
}
