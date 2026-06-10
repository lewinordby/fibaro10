import ReactECharts from "echarts-for-react";
import { App as AntApp, Button, Card, Form, Input, InputNumber, Space, Table, Tabs, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { saveConfig, type ModuleFilter, type ModuleResponse, type ModuleTable, type VentilationData, type VentilationSettingField } from "../api";

type VentilationPageProps = {
  data: ModuleResponse;
  view: string;
  onReload: () => void;
};

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

function numberText(value: unknown, digits = 1): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: digits }).format(value);
}

function valueText(value: unknown): string {
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

function timeText(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) return date.toLocaleString("nb-NO");
  return value;
}

function minuteFromTime(value: unknown): number | null {
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

function minuteLabel(value: number | string | undefined): string {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return "--:--";
  const minute = Math.max(0, Math.min(1440, Math.round(numeric)));
  const hours = Math.floor(minute / 60);
  const minutes = minute % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function minuteFromEventX(value: number): number {
  return Math.max(0, Math.min(1440, Math.round((value / 1000) * 1440)));
}

type DayChartSample = {
  sample: Record<string, unknown>;
  minute: number;
};

type DayChartTooltipParam = {
  axisValue?: number | string;
  marker?: string;
  seriesName?: string;
  value?: unknown;
};

function chartValue(value: unknown): number | null {
  if (Array.isArray(value) && typeof value[1] === "number") return value[1];
  if (typeof value === "number") return value;
  return null;
}

function formatDayChartTooltip(params: DayChartTooltipParam | DayChartTooltipParam[]): string {
  const items = (Array.isArray(params) ? params : [params]).filter((item) => item.seriesName && item.seriesName !== "__fan_events");
  const first = items[0];
  const firstMinute = Array.isArray(first?.value) && typeof first.value[0] === "number" ? first.value[0] : first?.axisValue;
  const lines = [minuteLabel(firstMinute)];
  items.forEach((item) => {
    const value = chartValue(item.value);
    if (value === null) return;
    lines.push(`${item.marker ?? ""}${item.seriesName}: ${numberText(value)}`);
  });
  return lines.join("<br/>");
}

function stateTag(state: boolean | null | undefined) {
  if (state === true) return <Tag color="green">PÅ</Tag>;
  if (state === false) return <Tag>AV</Tag>;
  return <Tag color="default">-</Tag>;
}

function filterRows(rows: Record<string, unknown>[], columns: string[], query: string) {
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

function VentilationTable({ table, query }: { table: ModuleTable; query: string }) {
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

function Snapshot({ ventilation }: { ventilation: VentilationData }) {
  return (
    <Space direction="vertical" size={12} className="vent-stack">
      <div className="vent-current-row">
        {ventilation.latest.groups.map((group) => (
          <Card className={`work-card vent-zone-card zone-${group.key}`} key={group.key} title={group.title}>
            <div className="vent-zone-grid">
              {group.fields.map((field) => (
                <div className="vent-reading" key={field.key}>
                  <span>{field.label}</span>
                  <strong>{numberText(field.temperature)} C</strong>
                  <small>{field.humidity !== null && field.humidity !== undefined ? `${numberText(field.humidity, 0)}%` : field.detail || "-"}</small>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
      <Card className="work-card vent-state-card">
        <div className="vent-state-head">
          <div>
            <Typography.Text className="eyebrow">Siste ventilasjonssample</Typography.Text>
            <strong>{timeText(ventilation.latest.bucketStart)}</strong>
            <span>{ventilation.latest.mode || "-"}</span>
          </div>
          <div className="vent-weather-line">
            <strong>{ventilation.latest.weather.text || "-"}</strong>
            <span>
              {numberText(ventilation.latest.weather.airTemperature)} C / {numberText(ventilation.latest.weather.relativeHumidity, 0)}% / vind{" "}
              {numberText(ventilation.latest.weather.windSpeed)} m/s
            </span>
          </div>
        </div>
        <div className="vent-fan-strip">
          {ventilation.latest.fans.map((fan) => (
            <span className="vent-fan-pill" key={fan.key}>
              {fan.label}
              {stateTag(fan.state)}
            </span>
          ))}
        </div>
      </Card>
    </Space>
  );
}

function CompactSnapshot({ ventilation }: { ventilation: VentilationData }) {
  const readings = ventilation.latest.groups.flatMap((group) => group.fields.map((field) => ({ ...field, group: group.title })));
  return (
    <Card className="work-card vent-compact-card">
      <div className="vent-compact-main">
        <div className="vent-compact-sample">
          <Typography.Text className="eyebrow">Siste sample</Typography.Text>
          <strong>{timeText(ventilation.latest.bucketStart)}</strong>
          <span>{ventilation.latest.mode || "-"}</span>
        </div>
        <div className="vent-compact-readings">
          {readings.map((field) => (
            <Tooltip key={`${field.group}-${field.key}`} title={field.group}>
              <span className="vent-compact-reading">
                <small>{field.label}</small>
                <strong>{numberText(field.temperature)} C</strong>
                <em>{field.humidity !== null && field.humidity !== undefined ? `${numberText(field.humidity, 0)}%` : field.detail || "-"}</em>
              </span>
            </Tooltip>
          ))}
        </div>
        <div className="vent-compact-weather">
          <strong>{ventilation.latest.weather.text || "-"}</strong>
          <span>
            {numberText(ventilation.latest.weather.airTemperature)} C / {numberText(ventilation.latest.weather.relativeHumidity, 0)}% / vind{" "}
            {numberText(ventilation.latest.weather.windSpeed)} m/s
          </span>
        </div>
      </div>
      <div className="vent-compact-fans">
        {ventilation.latest.fans.map((fan) => (
          <span className="vent-fan-pill" key={fan.key}>
            {fan.label}
            {stateTag(fan.state)}
          </span>
        ))}
      </div>
    </Card>
  );
}

function DayChart({ ventilation, onDayChange }: { ventilation: VentilationData; onDayChange: (day: string) => void }) {
  const day = ventilation.day;
  const defaultKeys = day.series.filter((series) => series.default).map((series) => series.key);
  const defaultVisible = Object.fromEntries(day.series.map((series) => [series.label, defaultKeys.length ? defaultKeys.includes(series.key) : true]));
  const chartSamples: DayChartSample[] = day.samples
    .map((sample) => ({ sample, minute: minuteFromTime(sample.time) }))
    .filter((item): item is DayChartSample => item.minute !== null)
    .sort((left, right) => left.minute - right.minute);
  const fanMarkLines = day.fanEvents
    .map((event) => ({
      name: `${event.time} ${event.fan_short} ${event.action}${event.detail ? ` - ${event.detail}` : ""}`,
      xAxis: minuteFromEventX(event.x),
      lineStyle: {
        color: event.color,
        opacity: event.class === "on" ? 0.58 : 0.42,
        type: "dashed",
        width: 1.2,
      },
      label: {
        show: false,
      },
    }))
    .sort((left, right) => Number(left.xAxis) - Number(right.xAxis));

  const option = {
    tooltip: { trigger: "axis", formatter: formatDayChartTooltip },
    legend: {
      top: 0,
      data: day.series.map((series) => series.label),
      selected: defaultVisible,
    },
    grid: { top: 42, left: 44, right: 20, bottom: 36 },
    xAxis: {
      type: "value",
      min: 0,
      max: 1440,
      interval: 120,
      axisLabel: { formatter: minuteLabel },
      axisPointer: { label: { formatter: (params: { value?: number | string }) => minuteLabel(params.value) } },
    },
    yAxis: { type: "value", name: "C" },
    series: [
      ...day.series.map((series) => ({
        name: series.label,
        type: "line",
        data: chartSamples.map(({ sample, minute }) => [minute, typeof sample[series.key] === "number" ? sample[series.key] : null]),
        smooth: true,
        connectNulls: false,
        showSymbol: false,
        lineStyle: { width: 2, color: series.color },
        itemStyle: { color: series.color },
      })),
      {
        name: "__fan_events",
        type: "line",
        data: chartSamples.map(({ minute }) => [minute, null]),
        silent: false,
        tooltip: { show: false },
        symbol: "none",
        lineStyle: { opacity: 0 },
        markLine: {
          animation: false,
          silent: false,
          symbol: ["none", "none"],
          label: { show: false },
          tooltip: {
            show: true,
            formatter: (params: { name?: string }) => params.name || "Viftehendelse",
          },
          data: fanMarkLines,
        },
      },
    ],
  };

  return (
    <Card className="chart-card vent-day-card" title="Dagslogg temperatur">
      <div className="vent-day-toolbar">
        <Space size={8}>
          <Button size="small" onClick={() => onDayChange(day.prevDay)}>
            Forrige dag
          </Button>
          <Button size="small" onClick={() => onDayChange("")}>
            I dag
          </Button>
          <Button size="small" onClick={() => onDayChange(day.nextDay)}>
            Neste dag
          </Button>
        </Space>
        <Space size={8}>
          <Typography.Text type="secondary">Dato</Typography.Text>
          <Input className="vent-date-input" type="date" value={day.selectedDay} onChange={(event) => onDayChange(event.target.value)} />
        </Space>
      </div>
      <ReactECharts key={day.selectedDay} option={option} style={{ height: 360 }} />
      <div className="vent-fan-lanes">
        {day.fans.map((fan) => {
          const events = day.fanEvents.filter((event) => event.fan_key === fan.key);
          return (
            <div className="vent-fan-lane" key={fan.key}>
              <span>{fan.short || fan.name}</span>
              <div className="vent-fan-track">
                {events.map((event, index) => (
                  <Tooltip key={`${fan.key}-${event.time}-${index}`} title={`${event.time} ${event.fan_short} ${event.action}${event.detail ? ` - ${event.detail}` : ""}`}>
                    <i
                      className={`vent-fan-event ${event.class}`}
                      style={{
                        left: `${event.x / 10}%`,
                        backgroundColor: event.class === "on" ? event.color : "#ffffff",
                        borderColor: event.color,
                      }}
                      aria-label={`${event.time} ${event.fan_short} ${event.action}${event.detail ? ` - ${event.detail}` : ""}`}
                    />
                  </Tooltip>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function WeatherChart({ table }: { table?: ModuleTable }) {
  const rows = useMemo(() => [...(table?.rows ?? [])].reverse(), [table]);
  if (!rows.length) return null;
  const x = rows.map((row) => {
    const value = row.bucket_start;
    if (typeof value !== "string") return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" });
  });
  const option = {
    tooltip: { trigger: "axis" },
    legend: { top: 0 },
    grid: { top: 44, left: 44, right: 22, bottom: 32 },
    xAxis: { type: "category", data: x, axisLabel: { hideOverlap: true } },
    yAxis: { type: "value" },
    series: [
      { name: "Temp", type: "line", data: rows.map((row) => row.air_temperature), showSymbol: false, smooth: true },
      { name: "Fukt", type: "line", data: rows.map((row) => row.relative_humidity), showSymbol: false, smooth: true },
      { name: "Vind", type: "line", data: rows.map((row) => row.wind_speed), showSymbol: false, smooth: true },
      { name: "Skydekke", type: "line", data: rows.map((row) => row.cloud_area_fraction), showSymbol: false, smooth: true },
      { name: "Nedbør", type: "bar", data: rows.map((row) => row.precipitation_next_1h) },
    ],
  };
  return (
    <Card className="chart-card vent-weather-card" title="Yr utvikling">
      <ReactECharts option={option} style={{ height: 330 }} />
    </Card>
  );
}

function FilterBar({ filters }: { filters: ModuleFilter[] }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const filterKey = searchParams.toString();
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    setValues(Object.fromEntries(filters.map((filter) => [filter.key, filter.value === null || filter.value === undefined ? "" : String(filter.value)])));
  }, [filterKey, filters]);

  if (!filters.length) return null;

  function apply() {
    const next = new URLSearchParams(searchParams);
    Object.entries(values).forEach(([key, value]) => {
      const trimmed = value.trim();
      if (trimmed) next.set(key, trimmed);
      else next.delete(key);
    });
    setSearchParams(next);
  }

  function clear() {
    const next = new URLSearchParams(searchParams);
    filters.forEach((filter) => next.delete(filter.key));
    setSearchParams(next);
  }

  return (
    <Card className="work-card module-filter-card">
      <div className="module-filter-grid">
        {filters.map((filter) => (
          <label className="module-filter-field" key={filter.key}>
            <span>{filter.label}</span>
            <Input
              size="small"
              type={filter.type === "datetime" ? "datetime-local" : filter.type}
              value={values[filter.key] ?? ""}
              onChange={(event) => setValues((current) => ({ ...current, [filter.key]: event.target.value }))}
              onPressEnter={apply}
            />
          </label>
        ))}
      </div>
      <Space size={8} className="module-filter-actions">
        <Button size="small" type="primary" onClick={apply}>
          Bruk filtre
        </Button>
        <Button size="small" onClick={clear}>
          Nullstill
        </Button>
      </Space>
    </Card>
  );
}

function settingInput(field: VentilationSettingField) {
  if (field.type === "int" || field.type === "float") return <InputNumber className="edit-number" step={field.type === "float" ? 0.1 : 1} />;
  if (field.type === "time") return <Input type="time" />;
  return <Input />;
}

function SettingsView({ ventilation, onReload }: { ventilation: VentilationData; onReload: () => void }) {
  const settings = ventilation.settings;
  const { message } = AntApp.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (!settings) return;
    const values = Object.fromEntries(settings.groups.flatMap((group) => group.fields.map((field) => [field.key, field.value])));
    form.setFieldsValue(values);
  }, [form, settings]);

  if (!settings) return null;
  const activeSettings = settings;

  async function save() {
    const values = (await form.validateFields()) as Record<string, unknown>;
    setSaving(true);
    try {
      await saveConfig(activeSettings.updateEndpoint, values, reason || "Endret i ventilasjonssiden");
      message.success("Ventilasjonsinnstillinger lagret");
      setReason("");
      onReload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Lagring feilet");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Space direction="vertical" size={14} className="vent-stack">
      <div className="vent-settings-head">
        <Card className="summary-card">
          <span>Versjon</span>
          <strong>{settings.version}</strong>
          <small>Oppdatert {timeText(settings.updatedAt)}</small>
        </Card>
        <Card className="summary-card">
          <span>Endret av</span>
          <strong>{settings.updatedBy || "-"}</strong>
          <small>HC3 henter via config API</small>
        </Card>
      </div>
      <Form form={form} layout="vertical">
        <div className="vent-settings-grid">
          {settings.groups.map((group) => (
            <Card className="work-card vent-setting-card" title={group.title} key={group.title}>
              {group.description ? <Typography.Paragraph type="secondary">{group.description}</Typography.Paragraph> : null}
              {group.fields.map((field) => (
                <Form.Item key={field.key} name={field.key} label={`${field.label}${field.unit ? ` (${field.unit})` : ""}`}>
                  {settingInput(field)}
                </Form.Item>
              ))}
            </Card>
          ))}
        </div>
        <Card className="work-card vent-save-card">
          <Input
            placeholder="Endringsnotat"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <Button type="primary" loading={saving} onClick={save}>
            Lagre innstillinger
          </Button>
        </Card>
      </Form>
      <Card className="work-card" title="Aktive regler">
        <ul className="vent-rule-list">
          {settings.rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </Card>
    </Space>
  );
}

function TableArea({ tables }: { tables: ModuleTable[] }) {
  const [draftQuery, setDraftQuery] = useState("");
  const [query, setQuery] = useState("");
  if (!tables.length) return null;
  return (
    <Card className="table-card module-table-card">
      <div className="table-toolbar">
        <Input.Search
          allowClear
          placeholder="Søk i tabellene"
          value={draftQuery}
          onChange={(event) => {
            setDraftQuery(event.target.value);
            if (!event.target.value) setQuery("");
          }}
          onSearch={(value) => setQuery(value.trim())}
          enterButton="Søk"
        />
      </div>
      <Tabs
        items={tables.map((table) => ({
          key: table.title,
          label: (
            <span>
              {table.title}
              <span className="tab-count">{filterRows(table.rows, table.columns, query).length}</span>
            </span>
          ),
          children: <VentilationTable table={table} query={query} />,
        }))}
      />
    </Card>
  );
}

export default function VentilationPage({ data, view, onReload }: VentilationPageProps) {
  const ventilation = data.ventilation;
  const [searchParams, setSearchParams] = useSearchParams();
  if (!ventilation) return null;

  function setDay(day: string) {
    const next = new URLSearchParams(searchParams);
    if (day) next.set("day", day);
    else next.delete("day");
    setSearchParams(next);
  }

  return (
    <Space direction="vertical" size={16} className="page-stack vent-page">
      {view === "dagslogg" ? <CompactSnapshot ventilation={ventilation} /> : <Snapshot ventilation={ventilation} />}
      {view === "dagslogg" ? <DayChart ventilation={ventilation} onDayChange={setDay} /> : null}
      {view === "yr-logg" ? <WeatherChart table={data.tables[0]} /> : null}
      {view === "innstillinger" ? <SettingsView ventilation={ventilation} onReload={onReload} /> : null}
      {view !== "innstillinger" ? <FilterBar filters={data.filters ?? []} /> : null}
      {view === "hendelser" && ventilation.day.fanEvents.length ? (
        <Card className="work-card" title="Dagens viftehendelser">
          <div className="vent-event-list">
            {ventilation.day.fanEvents.slice(-30).reverse().map((event, index) => (
              <div className={`vent-event-row ${event.class}`} key={`${event.time}-${event.fan_key}-${index}`}>
                <strong>{event.time}</strong>
                <span>{event.fan_name}</span>
                {event.class === "on" ? <Tag color="green">PÅ</Tag> : <Tag>AV</Tag>}
                <small>{event.detail}</small>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
      {view !== "innstillinger" ? <TableArea tables={data.tables} /> : null}
    </Space>
  );
}
