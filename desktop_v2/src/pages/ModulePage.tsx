import ReactECharts from "echarts-for-react";
import { App as AntApp, Button, Card, Checkbox, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useState } from "react";
import type { ReactNode } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import {
  fetchModule,
  runModuleAction,
  submitModuleEdit,
  type ModuleAction,
  type ModuleCard,
  type ModuleChart,
  type ModuleEditConfig,
  type ModuleEditField,
  type ModuleTable,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useAsyncData } from "../hooks";
import { defaultModuleView, modulePath, MODULE_VIEWS } from "../moduleViews";
import { appPath } from "../navigation";

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Ja" : "Nei";
  if (typeof value === "number") {
    return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 2 }).format(value);
  }
  if (typeof value === "object") return JSON.stringify(value);
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}T/.test(text)) {
    const date = new Date(text);
    if (!Number.isNaN(date.getTime())) return date.toLocaleString("nb-NO");
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    const date = new Date(`${text}T00:00:00`);
    if (!Number.isNaN(date.getTime())) return date.toLocaleDateString("nb-NO");
  }
  return text;
}

function labelize(column: string): string {
  const labels: Record<string, string> = {
    bucket_start: "Tid",
    timestamp: "Tid",
    created_at: "Opprettet",
    start_time: "Start",
    started_at: "Start",
    begin_at: "Start",
    end_time: "Slutt",
    ended_at: "Slutt",
    end_at: "Slutt",
    car_license_number: "Reg.nr",
    owner_warning: "Eier-sjekk",
    plate: "Reg.nr",
    vehicle_title: "Kjøretøy",
    current_ownership_at: "Sist eierskifte",
    navn: "Navn",
    omrade: "Område",
    parking_area: "Område",
    fee_inc_vat: "Beløp",
    paid_amount_kr: "Beløp",
    paid_total: "Sum betalt",
    paid: "Betalt",
    first_seen: "Først sett",
    last_seen: "Sist sett",
    svv_status: "SVV",
    sun2_id: "SUN2-ID",
    parking_time_min: "Min",
    parkering_count: "Parkeringer",
    duration_minutes: "Min",
    room: "Rom",
    user_name: "Bruker",
    payment_method: "Betaling",
    customer_type: "Kundetype",
    physical_room_number: "Rom",
    room_id: "Rom-ID",
    bed_model: "Sengemodell",
    current_price_per_min: "Kr/min",
    max_minutes: "Maks min",
    lamp_status: "Lampe",
    imported_at: "Importert",
    last_seen_at: "Sist sett",
    visits_count: "Besøk",
    total_spent_kr: "Total kjøp",
    balance_kr: "Saldo",
    stat_date: "Dato",
    total_soletid_minutter: "Soltid min",
    total_soletid_timer: "Soltid timer",
    totalt_antall_solinger: "Solinger",
    totalt_inntjent_kr: "Omsetning",
    solinger_medlemmer: "Medlemmer",
    solinger_ikke_medlemmer: "Ikke medlemmer",
    rows_count: "Rader",
    inserted_count: "Nye",
    updated_count: "Oppdatert",
    skipped_count: "Hoppet over",
    sessions_count: "Solinger",
    rooms_count: "Rom",
    days_count: "Dager",
    duration_hours: "Timer",
    room_label: "Rom",
    hour_label: "Time",
    last_session_at: "Sist soling",
    session_name: "Navn i økt",
    actual_sessions: "Faktisk solinger",
    forecast_sessions: "Prognose solinger",
    delta_sessions: "Avvik solinger",
    actual_paid: "Faktisk kr",
    forecast_paid: "Prognose kr",
    delta_paid: "Avvik kr",
    actual_hours: "Faktisk timer",
    forecast_hours: "Prognose timer",
    remaining_days: "Dager igjen",
    tempo: "Tempo %",
    period_label: "Periode",
    period_done: "Avsluttet",
    period_type: "Periode",
    period_start: "Fra",
    period_end: "Til",
    forecast_minutes: "Prognose min",
    actual_sessions_at_save: "Faktiske økter",
    actual_paid_at_save: "Faktisk kr",
    circuit_no: "Kurs",
    description: "Beskrivelse",
    breaker: "Sikring",
    breaker_type: "Type",
    is_sunbed: "Solseng",
    note: "Notat",
    name: "Navn",
    load_type: "Lasttype",
    area: "Område",
    expected_power_w: "Forventet W",
    fibaro_device_id: "HC3-enhet",
    fibaro_meter_id: "HC3-måler",
    active: "Aktiv",
    inntak_w: "Inntak W",
    varmepumper_w: "Varmepumper W",
    belysning_w: "Belysning W",
    massasje_w: "Massasje W",
    annet_w: "Annet W",
    avfukter_w: "Avfukter W",
    differanse_beregnet_w: "Diff W",
    measured_at: "Målt",
    hour: "Time",
    consumption_kwh: "kWh",
    is_estimated: "Estimert",
    source: "Kilde",
    source_system: "Kilde",
    user_interface: "Grensesnitt",
    subtype: "Type",
    period_first: "Fra",
    period_last: "Til",
    hours_count: "Timer",
    total_kwh: "kWh total",
    ok: "OK",
    message: "Melding",
    temp_avg_inne: "Inne",
    temp_ute: "Ute",
    temp_loft: "Loft",
    temp_luftinntak: "Innluft",
    temp_kjeller: "Kjeller",
    humidity_1etg: "Fukt 1. etg",
    humidity_2etg: "Fukt 2. etg",
    humidity_vip: "Fukt VIP",
    humidity_kjeller: "Fukt kjeller",
    fan_vip: "VIP-vifte",
    fan_2etg: "2. etg vifte",
    fan_tak: "Takvifte",
    fan_avfukter: "Avfukter",
    weather_text: "Vær",
    air_temperature: "Lufttemp",
    relative_humidity: "Fukt ute",
    wind_speed: "Vind",
    wind_speed_of_gust: "Vindkast",
    cloud_area_fraction: "Skydekke",
    precipitation_next_1h: "Nedbør 1t",
    action: "Handling",
    device_name: "Enhet",
    mode: "Modus",
    reason: "Årsak",
    state: "Status",
    lux: "Lux",
    light_lyslist: "Lyslist",
    light_reklame: "Reklame",
    light_spot_glass_275: "Spot 275",
    light_spot_glass_299: "Spot 299",
    light_spot_inngang: "Inngang",
    light_parkering: "Parkering",
    cloud_online: "Online",
    local_ip: "IP",
    battery: "Batteri",
    last_error: "Siste feil",
    cleaned_area_m2: "Areal m²",
    complete: "Ferdig",
    error_code: "Feilkode",
    finish_reason: "Avslutning",
    robot_duid: "Robot",
    state_name: "Status",
    clean_area_m2: "Areal m²",
    rssi: "RSSI",
    title: "Tittel",
    category: "Kategori",
    status: "Status",
    status_text: "Status",
    age: "Alder",
    last_success_at: "Sist OK",
    build: "Build",
    date: "Dato",
    username: "Bruker",
    question: "Spørsmål",
    error: "Feil",
    tool: "Verktøy",
    path: "Lenke",
    count: "Antall",
    key: "Nøkkel",
    value: "Verdi",
    group: "Gruppe",
    label: "Navn",
    unit: "Enhet",
    help: "Forklaring",
    rule: "Regel",
    version: "Versjon",
    updated_at: "Oppdatert",
    updated_by: "Endret av",
    config_key: "Konfig",
    changed_at: "Endret",
    changed_by: "Endret av",
    is_master: "Master",
    key_prefix: "Nøkkelprefix",
    uses_count: "Brukt",
    method: "Metode",
    success: "OK",
  };
  return labels[column] ?? column.replaceAll("_", " ");
}

function sortableValue(value: unknown): number | string {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "boolean") return value ? 1 : 0;
  if (typeof value === "number") return Number.isFinite(value) ? value : "";
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) {
    const time = new Date(text).getTime();
    if (!Number.isNaN(time)) return time;
  }
  const numeric = Number(text.replace(",", "."));
  if (Number.isFinite(numeric) && text.trim() !== "") return numeric;
  return text.toLocaleLowerCase("nb-NO");
}

function compareValues(left: unknown, right: unknown): number {
  const a = sortableValue(left);
  const b = sortableValue(right);
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "nb-NO", { numeric: true, sensitivity: "base" });
}

function numericColumn(column: string): boolean {
  return /(_w|_kr|_kwh|_min|_m2|_count|count|paid|fee|duration|minutes|hour|age|battery|rssi|lux|temp|humidity|wind|cloud|precipitation|breaker|power|energy)$/i.test(
    column,
  );
}

function LinkValue({ value }: { value: string }) {
  const internalPath = appPath(value);
  if (internalPath) return <Link to={internalPath}>{value}</Link>;
  if (value.startsWith("/") || /^https?:\/\//i.test(value)) return <a href={value}>{value}</a>;
  return displayValue(value);
}

function moduleColumns(
  table: ModuleTable,
  onEdit?: (edit: ModuleEditConfig, row: Record<string, unknown>, create?: boolean) => void,
): ColumnsType<Record<string, unknown>> {
  const columns: ColumnsType<Record<string, unknown>> = table.columns.map((column) => ({
    title: labelize(column),
    dataIndex: column,
    key: column,
    align: numericColumn(column) ? "right" : undefined,
    ellipsis: true,
    sorter: (left, right) => compareValues(left[column], right[column]),
    render: (value: unknown, row) => {
      if (column === "plate" && typeof value === "string" && typeof row.path === "string") {
        const internalPath = appPath(row.path);
        if (internalPath) return <Link to={internalPath}>{displayValue(value)}</Link>;
      }
      if (column === "owner_warning" && value) {
        return <Tag color="gold">{displayValue(value)}</Tag>;
      }
      if (typeof value === "string" && (column === "path" || /^https?:\/\//i.test(value) || value.startsWith("/"))) {
        return <LinkValue value={value} />;
      }
      if (typeof value === "boolean") {
        return <Tag color={value ? "green" : "default"}>{displayValue(value)}</Tag>;
      }
      if (column === "status" && typeof value === "string") {
        const normalized = value.toLowerCase();
        const color = normalized.includes("ongoing") || normalized.includes("ok") ? "green" : "default";
        return <Tag color={color}>{displayValue(value)}</Tag>;
      }
      return displayValue(value);
    },
  }));
  if (table.edit && onEdit) {
    columns.push({
      title: "",
      key: "__edit",
      fixed: "right",
      width: 92,
      render: (_value, row) => (
        <Button size="small" onClick={() => onEdit(table.edit as ModuleEditConfig, row)}>
          Rediger
        </Button>
      ),
    });
  }
  return columns;
}

function filterRows(rows: Record<string, unknown>[], columns: string[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return rows;
  const compactQuery = normalized.replace(/[^a-z0-9æøå]/gi, "");
  return rows.filter((row) =>
    columns.some((column) => {
      const value = displayValue(row[column]).toLowerCase();
      return value.includes(normalized) || (compactQuery.length > 1 && value.replace(/[^a-z0-9æøå]/gi, "").includes(compactQuery));
    }),
  );
}

function ModuleMetric({ card }: { card: ModuleCard }) {
  return (
    <Card className={`metric-card module-metric tone-${card.tone ?? "status"}`}>
      <Typography.Text className="metric-title">{card.title}</Typography.Text>
      <div className="metric-value-row">
        <span className="metric-value">{card.value}</span>
        {card.unit ? <span className="metric-unit">{card.unit}</span> : null}
      </div>
      <div className="metric-detail">{card.detail || "\u00a0"}</div>
    </Card>
  );
}

function ModuleChartPanel({ chart }: { chart: ModuleChart }) {
  const option = {
    tooltip: { trigger: "axis" },
    legend: { top: 0 },
    grid: { top: 46, left: 46, right: 24, bottom: chart.x.length > 80 ? 58 : 34 },
    dataZoom:
      chart.x.length > 80
        ? [
            { type: "inside", start: Math.max(0, 100 - Math.round((80 / chart.x.length) * 100)), end: 100 },
            { type: "slider", height: 18, bottom: 12 },
          ]
        : undefined,
    xAxis: {
      type: "category",
      data: chart.x,
      boundaryGap: chart.type === "bar",
      axisLabel: { hideOverlap: true },
    },
    yAxis: { type: "value" },
    series: chart.series.map((series) => ({
      name: series.name,
      type: series.type ?? chart.type ?? "line",
      data: series.data,
      smooth: (series.type ?? chart.type ?? "line") === "line",
      connectNulls: false,
      showSymbol: false,
      itemStyle: series.color ? { color: series.color } : undefined,
      lineStyle: series.color ? { color: series.color, width: 2 } : undefined,
      areaStyle: chart.series.length === 1 && (series.type ?? chart.type ?? "line") === "line" ? { opacity: 0.08 } : undefined,
    })),
  };

  return (
    <Card className="chart-card module-chart-card" title={chart.title}>
      {chart.subtitle ? <Typography.Text type="secondary">{chart.subtitle}</Typography.Text> : null}
      <ReactECharts option={option} style={{ height: chart.height ?? 330 }} />
    </Card>
  );
}

function fieldInput(field: ModuleEditField) {
  if (field.type === "textarea") return <Input.TextArea rows={3} />;
  if (field.type === "number") return <InputNumber className="edit-number" />;
  if (field.type === "boolean") return <Checkbox>{field.label}</Checkbox>;
  if (field.type === "select") return <Select options={field.options} />;
  if (field.type === "password") return <Input.Password autoComplete="new-password" />;
  return <Input />;
}

function editInitialValues(edit: ModuleEditConfig, row: Record<string, unknown>, create: boolean) {
  const fields = create ? edit.createFields ?? edit.fields : edit.fields;
  const values: Record<string, unknown> = {};
  for (const field of fields) {
    values[field.key] = field.type === "boolean" ? Boolean(row[field.key]) : row[field.key] ?? undefined;
  }
  return values;
}

function tableRowKey(row: Record<string, unknown>, tableTitle: string, index?: number) {
  const stableValue =
    row.id ??
    row.plate ??
    row.sun2_user_id ??
    row.room_id ??
    row.duid ??
    row.robot_duid ??
    row.record_id ??
    row.bucket_start ??
    row.timestamp ??
    row.started_at ??
    row.start_time;
  return `${tableTitle}-${stableValue ?? index ?? 0}`;
}

function countText(filteredCount: number, totalCount: number, query: string): string {
  if (query.trim() && filteredCount !== totalCount) return `Viser ${filteredCount} av ${totalCount} rader`;
  return `${totalCount} rader`;
}

function tabLabel(table: ModuleTable, query: string): ReactNode {
  const filteredCount = filterRows(table.rows, table.columns, query).length;
  return (
    <span>
      {table.title}
      <span className="tab-count">{query.trim() ? `${filteredCount}/${table.rows.length}` : table.rows.length}</span>
    </span>
  );
}

function tableSearchPlaceholder(module: string, view: string): string {
  if (module === "parkering" && view === "kjoretoy") return "Søk etter reg.nr, bil, eier, område";
  return "Søk i tabellene";
}

function ModuleTablePane({
  table,
  query,
  onEdit,
}: {
  table: ModuleTable;
  query: string;
  onEdit?: (edit: ModuleEditConfig, row: Record<string, unknown>, create?: boolean) => void;
}) {
  const filteredRows = filterRows(table.rows, table.columns, query);
  return (
    <Space direction="vertical" size={8} className="table-pane">
      <div className="table-pane-head">
        <Typography.Text type="secondary">
          {countText(filteredRows.length, table.rows.length, query)}
        </Typography.Text>
        {table.edit?.createEndpoint && onEdit ? (
          <Button type="primary" size="small" onClick={() => onEdit(table.edit as ModuleEditConfig, {}, true)}>
            Ny
          </Button>
        ) : null}
      </div>
      <Table
        rowKey={(row, index) => tableRowKey(row, table.title, index)}
        size="small"
        columns={moduleColumns(table, onEdit)}
        dataSource={filteredRows}
        pagination={{ pageSize: 25, showSizeChanger: true }}
        scroll={{ x: "max-content" }}
        locale={{
          emptyText: query.trim() ? "Ingen treff for søket" : "Ingen rader å vise",
        }}
      />
    </Space>
  );
}

export default function ModulePage({ module }: { module: string }) {
  const params = useParams();
  const { message, modal } = AntApp.useApp();
  const [form] = Form.useForm();
  const [query, setQuery] = useState("");
  const [draftQuery, setDraftQuery] = useState("");
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [editState, setEditState] = useState<{ edit: ModuleEditConfig; row: Record<string, unknown>; create: boolean } | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const view = params.view ?? defaultModuleView(module);
  const viewItems = MODULE_VIEWS[module] ?? [];
  const isKnownView = !viewItems.length || viewItems.some((item) => item.key === view);
  const safeView = isKnownView ? view : defaultModuleView(module);
  const serverQuery = module === "parkering" && safeView === "kjoretoy" ? query : "";
  const { data, loading, error } = useAsyncData(
    () => fetchModule(module, safeView, serverQuery),
    [module, safeView, serverQuery, reloadToken],
  );

  if (!isKnownView) return <Navigate to={modulePath(module)} replace />;

  function runSearch(value = draftQuery) {
    setQuery(value.trim());
  }

  function clearSearch() {
    setDraftQuery("");
    setQuery("");
  }

  function openEdit(edit: ModuleEditConfig, row: Record<string, unknown>, create = false) {
    form.resetFields();
    form.setFieldsValue(editInitialValues(edit, row, create));
    setEditState({ edit, row, create });
  }

  async function saveEdit() {
    if (!editState || savingEdit) return;
    const values = await form.validateFields();
    setSavingEdit(true);
    try {
      const result = await submitModuleEdit(editState.edit, editState.row, values, editState.create);
      message.success(String(result.message || "Lagret"));
      setEditState(null);
      setReloadToken((value) => value + 1);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Lagring feilet");
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleAction(action: ModuleAction) {
    if (runningAction) return;
    const runAction = async () => {
      setRunningAction(action.key);
      try {
        const result = await runModuleAction(action);
        message.success(String(result.message || "Handling utført"));
        setReloadToken((value) => value + 1);
      } catch (err) {
        message.error(err instanceof Error ? err.message : "Handling feilet");
      } finally {
        setRunningAction(null);
      }
    };

    if (action.confirm) {
      modal.confirm({
        title: action.label,
        content: action.confirm,
        okText: "Kjør",
        cancelText: "Avbryt",
        onOk: runAction,
      });
      return;
    }
    await runAction();
  }

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={18} className="page-stack">
      {data.actions?.length ? (
        <Card className="work-card module-actions">
          <Space>
            {data.actions.map((action) => (
              <Button
                key={action.key}
                type={action.tone === "primary" ? "primary" : "default"}
                loading={runningAction === action.key}
                disabled={Boolean(runningAction && runningAction !== action.key)}
                onClick={() => handleAction(action)}
              >
                {action.label}
              </Button>
            ))}
          </Space>
        </Card>
      ) : null}

      <div className="metric-grid primary-grid">
        {data.cards.map((card) => (
          <ModuleMetric card={card} key={card.title} />
        ))}
      </div>

      {data.charts?.map((chart) => <ModuleChartPanel chart={chart} key={chart.title} />)}

      <Card className="table-card module-table-card">
        <div className="table-toolbar">
          <Input.Search
            allowClear
            placeholder={tableSearchPlaceholder(module, safeView)}
            value={draftQuery}
            onChange={(event) => {
              const nextValue = event.target.value;
              setDraftQuery(nextValue);
              if (!nextValue) clearSearch();
            }}
            onSearch={runSearch}
            enterButton="Søk"
          />
        </div>
        <Tabs
          items={data.tables.map((table) => ({
            key: table.title,
            label: tabLabel(table, query),
            children: <ModuleTablePane table={table} query={query} onEdit={openEdit} />,
          }))}
        />
      </Card>

      <Modal
        title={
          editState
            ? `${editState.create ? "Ny" : "Rediger"} ${editState.edit.title.toLowerCase()}`
            : "Rediger"
        }
        open={Boolean(editState)}
        okText="Lagre"
        cancelText="Avbryt"
        confirmLoading={savingEdit}
        onOk={saveEdit}
        onCancel={() => setEditState(null)}
        destroyOnHidden
      >
        {editState ? (
          <Form form={form} layout="vertical" className="edit-form">
            {(editState.create ? editState.edit.createFields ?? editState.edit.fields : editState.edit.fields).map((field) => (
              <Form.Item
                key={field.key}
                name={field.key}
                label={field.type === "boolean" ? undefined : field.label}
                valuePropName={field.type === "boolean" ? "checked" : "value"}
                rules={field.required ? [{ required: true, message: `${field.label} må fylles ut` }] : undefined}
              >
                {fieldInput(field)}
              </Form.Item>
            ))}
          </Form>
        ) : null}
      </Modal>
    </Space>
  );
}
