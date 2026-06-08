import { App as AntApp, Button, Card, Input, Segmented, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useState } from "react";
import type { ReactNode } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { fetchModule, runModuleAction, type ModuleAction, type ModuleCard, type ModuleTable } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useAsyncData } from "../hooks";
import { defaultModuleView, moduleLabel, modulePath, MODULE_VIEWS } from "../moduleViews";

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
    plate: "Reg.nr",
    navn: "Navn",
    omrade: "Område",
    parking_area: "Område",
    fee_inc_vat: "Beløp",
    paid_amount_kr: "Beløp",
    paid_total: "Sum betalt",
    paid: "Betalt",
    first_seen: "Først sett",
    last_seen: "Sist sett",
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
    totalt_antall_solinger: "Solinger",
    totalt_inntjent_kr: "Omsetning",
    solinger_medlemmer: "Medlemmer",
    solinger_ikke_medlemmer: "Ikke medlemmer",
    period_type: "Periode",
    period_start: "Fra",
    period_end: "Til",
    forecast_sessions: "Prognose økter",
    forecast_paid: "Prognose kr",
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

function moduleColumns(table: ModuleTable): ColumnsType<Record<string, unknown>> {
  return table.columns.map((column) => ({
    title: labelize(column),
    dataIndex: column,
    key: column,
    align: numericColumn(column) ? "right" : undefined,
    ellipsis: true,
    sorter: (left, right) => compareValues(left[column], right[column]),
    render: (value: unknown) => {
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
}

function filterRows(rows: Record<string, unknown>[], columns: string[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return rows;
  return rows.filter((row) =>
    columns.some((column) => displayValue(row[column]).toLowerCase().includes(normalized)),
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

function ModuleTablePane({ table, query }: { table: ModuleTable; query: string }) {
  const filteredRows = filterRows(table.rows, table.columns, query);
  return (
    <Space direction="vertical" size={8} className="table-pane">
      <Typography.Text type="secondary">
        {countText(filteredRows.length, table.rows.length, query)}
      </Typography.Text>
      <Table
        rowKey={(row, index) => tableRowKey(row, table.title, index)}
        size="small"
        columns={moduleColumns(table)}
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
  const navigate = useNavigate();
  const { message, modal } = AntApp.useApp();
  const [query, setQuery] = useState("");
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const view = params.view ?? defaultModuleView(module);
  const viewItems = MODULE_VIEWS[module] ?? [];
  const isKnownView = !viewItems.length || viewItems.some((item) => item.key === view);
  const safeView = isKnownView ? view : defaultModuleView(module);
  const activeView = viewItems.find((item) => item.key === safeView);
  const { data, loading, error } = useAsyncData(() => fetchModule(module, safeView), [module, safeView, reloadToken]);

  if (!isKnownView) return <Navigate to={modulePath(module)} replace />;

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
  const displayTitle = activeView && viewItems.length > 1 ? `${moduleLabel(module)} · ${activeView.label}` : data.title;

  return (
    <Space direction="vertical" size={18} className="page-stack">
      <section className="section-head module-head">
        <div>
          <Typography.Text className="eyebrow">Desktop v2</Typography.Text>
          <Typography.Title level={1}>{displayTitle}</Typography.Title>
          <Typography.Paragraph>{data.subtitle}</Typography.Paragraph>
        </div>
        {viewItems.length > 1 ? (
          <Segmented
            className="module-view-switcher"
            value={view}
            options={viewItems.map((item) => ({ label: item.label, value: item.key }))}
            onChange={(next) => navigate(modulePath(module, String(next)))}
          />
        ) : null}
      </section>

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

      <Card className="table-card module-table-card">
        <div className="table-toolbar">
          <Input.Search
            allowClear
            placeholder="Søk i tabellene"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <Tabs
          items={data.tables.map((table) => ({
            key: table.title,
            label: tabLabel(table, query),
            children: <ModuleTablePane table={table} query={query} />,
          }))}
        />
      </Card>
    </Space>
  );
}
