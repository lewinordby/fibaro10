import { AimOutlined, CalendarOutlined, LeftOutlined, RightOutlined } from "@ant-design/icons";
import { App as AntApp, Button, Card, Checkbox, Form, Input, InputNumber, Modal, Select, Space, Spin, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { lazy, Suspense, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import {
  fetchModule,
  fetchSunSessionImageBrowser,
  runModuleAction,
  selectSunSessionImage,
  setSunSessionPrimaryImage,
  submitModuleEdit,
  type JsonRecord,
  type ModuleAction,
  type ModuleDayNavigation,
  type ModuleEditConfig,
  type ModuleEditField,
  type ModuleRow,
  type ModuleTable,
  type SunSessionImageBrowser,
  type SunSessionSavedImage,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useAsyncData } from "../hooks";
import { defaultModuleView, modulePath, MODULE_VIEWS } from "../moduleViews";
import { appPath } from "../navigation";
import { ModuleFilterBar } from "./module/ModuleFilterBar";
import { ModuleMetric } from "./module/ModuleMetric";
import { ParkingTimelinePanel } from "./module/ParkingTimelinePanel";
import { SunTimelinePanel } from "./module/SunTimelinePanel";

const EnergyElviaPage = lazy(() => import("./EnergyElviaPage"));
const EnergySunbedsPage = lazy(() => import("./EnergySunbedsPage"));
const ModuleChartPanel = lazy(() => import("./module/ModuleChartPanel"));
const VentilationPage = lazy(() => import("./VentilationPage"));

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
    vehicle_share: "Andel biler %",
    parking_share: "Andel parkeringer %",
    sun_paid: "Soling kr",
    parking_paid: "Parkering kr",
    total_paid: "Sum kr",
    sun_count: "Solinger",
    parking_count: "Parkeringer",
    total_count: "Antall totalt",
    first_seen: "Først sett",
    last_seen: "Sist sett",
    svv_status: "SVV",
    sun2_id: "SUN2-ID",
    parking_time_min: "Min",
    parkering_count: "Parkeringer",
    previous_parking_count: "Parkeringer før",
    previous_paid_total: "Betalt før",
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
    actual_parkeringer: "Faktisk parkeringer",
    forecast_parkeringer: "Prognose parkeringer",
    delta_parkeringer: "Avvik parkeringer",
    actual_paid: "Faktisk kr",
    forecast_paid: "Prognose kr",
    delta_paid: "Avvik kr",
    actual_hours: "Faktisk timer",
    forecast_hours: "Prognose timer",
    actual_minutes: "Faktisk min",
    remaining_days: "Dager igjen",
    actual_vehicles: "Faktiske biler",
    forecast_vehicles: "Prognose biler",
    tempo: "Tempo %",
    period_label: "Periode",
    period_done: "Avsluttet",
    period_type: "Periode",
    period_start: "Fra",
    period_end: "Til",
    provider: "Leverandør",
    sender: "Avsender",
    email_date: "E-postdato",
    email_subject: "Emne",
    attachment_filename: "Vedlegg",
    attachment_content_type: "Filtype",
    attachment_size: "Bytes",
    attachment_sha256: "SHA-256",
    average_paid: "Snitt kr",
    flowbird_source_count: "Flowbird parkeringer",
    flowbird_source_paid_ex_vat: "Flowbird eks. mva",
    gross_coin_card_ex_vat: "Brutto mynt/kort eks. mva",
    flowbird_source_diff_ex_vat: "Avvik Flowbird",
    easypark_source_count: "EasyPark parkeringer",
    easypark_source_paid_ex_vat: "EasyPark eks. mva Fibaro10",
    easypark_source_diff_ex_vat: "Avvik EasyPark kilde",
    other_source_count: "Andre kilder",
    easypark_ex_vat: "EasyPark eks. mva",
    easypark_inc_vat_estimate: "EasyPark inkl. mva",
    easypark_diff_inc_vat: "Avvik EasyPark",
    payout_inc_vat: "Til utbetaling",
    parser_confidence: "Tolkesikkerhet",
    forecast_minutes: "Prognose min",
    actual_sessions_at_save: "Faktiske økter",
    actual_paid_at_save: "Faktisk kr",
    circuit_no: "Kurs",
    description: "Beskrivelse",
    applications: "Applikasjoner",
    request: "Bestilling",
    headline: "Leveranseoverskrift",
    work_duration: "Tidsbruk",
    credits_used: "Kreditter",
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
    source_no: "Nr",
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
    severity: "Alvor",
    domain: "Fagområde",
    item: "Gjelder",
    problem: "Problem",
    detail: "Detalj",
    metric: "Målepunkt",
    target: "Mål",
    coverage_percent: "Dekning %",
    missing_count: "Mangler",
    sample_count: "Samples",
    factor: "Faktor",
    correlation: "Korrelasjon",
    strength: "Styrke",
    direction: "Retning",
    sample_days: "Dager",
    is_weekend: "Helg",
    weekday: "Ukedag",
    avg_inntak_w: "Snitt inntak W",
    avg_diff_w: "Snitt diff W",
    weather_samples: "Værsamples",
    energy_samples: "Energisamples",
    recommended_action: "Anbefalt handling",
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
  return /(_w|_kr|_kwh|_min|_m2|_count|_share|count|paid|fee|vat|payout|diff|confidence|duration|minutes|hour|age|battery|rssi|lux|temp|humidity|wind|cloud|precipitation|breaker|power|energy)$/i.test(
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
  onEdit?: (edit: ModuleEditConfig, row: ModuleRow, create?: boolean) => void,
): ColumnsType<ModuleRow> {
  const columns: ColumnsType<ModuleRow> = table.columns.map((column) => ({
    title: labelize(column),
    dataIndex: column,
    key: column,
    align: numericColumn(column) ? "right" : undefined,
    ellipsis: true,
    sorter: (left, right) => compareValues(left[column], right[column]),
    render: (value: unknown, row) => {
      if ((column === "plate" || column === "car_license_number") && typeof value === "string" && typeof row.path === "string") {
        const internalPath = appPath(row.path);
        if (internalPath) return <Link to={internalPath}>{displayValue(value)}</Link>;
      }
      if (["build", "headline", "title"].includes(column) && typeof row.path === "string") {
        const internalPath = appPath(row.path);
        if (internalPath) return <Link to={internalPath}>{displayValue(value)}</Link>;
      }
      if (["period_label", "attachment_filename", "email_subject"].includes(column) && typeof row.path === "string") {
        const internalPath = appPath(row.path);
        if (internalPath) return <Link to={internalPath}>{displayValue(value)}</Link>;
      }
      if (column === "owner_warning" && value) {
        return <Tag color="gold">{displayValue(value)}</Tag>;
      }
      if (column === "parser_confidence" && typeof value === "number") {
        const percent = Math.round(value * 100);
        const color = percent >= 90 ? "green" : percent >= 70 ? "gold" : "volcano";
        return <Tag color={color}>{percent} %</Tag>;
      }
      if (column === "severity" && typeof value === "string") {
        const normalized = value.toLowerCase();
        const color =
          normalized.includes("kritisk") ? "red" : normalized.includes("høy") ? "volcano" : normalized.includes("medium") ? "gold" : "blue";
        return <Tag color={color}>{displayValue(value)}</Tag>;
      }
      if (typeof value === "string" && (column === "path" || /^https?:\/\//i.test(value) || value.startsWith("/"))) {
        return <LinkValue value={value} />;
      }
      if (typeof value === "boolean") {
        return <Tag color={value ? "green" : "default"}>{displayValue(value)}</Tag>;
      }
      if (column === "status" && typeof value === "string") {
        const normalized = value.toLowerCase();
        const color =
          normalized.includes("ongoing") || normalized.includes("ok") || normalized.includes("tolket")
            ? "green"
            : normalized.includes("kontroll")
              ? "gold"
              : "default";
        return <Tag color={color}>{displayValue(value)}</Tag>;
      }
      if (["description", "applications", "request"].includes(column)) {
        const text = displayValue(value);
        return <Typography.Text title={text}>{text}</Typography.Text>;
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
      render: (_value, row) => {
        const edit = table.edit as ModuleEditConfig;
        if (edit.kind === "access-key" && row.is_master === true) {
          return <Typography.Text type="secondary">Låst</Typography.Text>;
        }
        return (
          <Button size="small" onClick={() => onEdit(edit, row)}>
            Rediger
          </Button>
        );
      },
    });
  }
  return columns;
}

function filterRows(rows: ModuleRow[], columns: string[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return rows;
  const exactQuery =
    normalized.length >= 2 && normalized[0] === normalized[normalized.length - 1] && ["\"", "'"].includes(normalized[0])
      ? normalized.slice(1, -1).trim()
      : "";
  const exactPattern = exactQuery
    ? new RegExp(`(^|[^\\p{L}\\p{N}_])${exactQuery.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}($|[^\\p{L}\\p{N}_])`, "iu")
    : null;
  const compactQuery = normalized.replace(/[^a-z0-9æøå]/gi, "");
  return rows.filter((row) =>
    columns.some((column) => {
      const value = displayValue(row[column]).toLowerCase();
      if (exactPattern) {
        const compactExact = exactQuery.replace(/[^a-z0-9æøå]/gi, "");
        return exactPattern.test(value) || (compactExact.length > 1 && value.replace(/[^a-z0-9æøå]/gi, "") === compactExact);
      }
      return value.includes(normalized) || (compactQuery.length > 1 && value.replace(/[^a-z0-9æøå]/gi, "").includes(compactQuery));
    }),
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

function editInitialValues(edit: ModuleEditConfig, row: ModuleRow, create: boolean) {
  const fields = create ? edit.createFields ?? edit.fields : edit.fields;
  const values: JsonRecord = {};
  for (const field of fields) {
    values[field.key] = field.type === "boolean" ? Boolean(row[field.key]) : row[field.key] ?? undefined;
  }
  return values;
}

function tableRowKey(row: ModuleRow, tableTitle: string, index?: number) {
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

function ModuleDayNavigationBar({
  navigation,
  onDayChange,
}: {
  navigation: ModuleDayNavigation;
  onDayChange: (day: string) => void;
}) {
  return (
    <Card className="work-card module-day-nav-card">
      <div className="module-day-nav-title">
        <Typography.Text type="secondary">Dato</Typography.Text>
        <Typography.Text strong>{navigation.selectedDayLabel}</Typography.Text>
      </div>
      <Space.Compact className="module-day-nav-actions">
        <Button size="small" icon={<LeftOutlined />} onClick={() => onDayChange(navigation.prevDay)}>
          Forrige dag
        </Button>
        <Button size="small" icon={<AimOutlined />} onClick={() => onDayChange("")}>
          I dag
        </Button>
        <Button size="small" icon={<RightOutlined />} onClick={() => onDayChange(navigation.nextDay)}>
          Neste dag
        </Button>
        <Input
          aria-label="Dato"
          className="module-day-nav-date"
          prefix={<CalendarOutlined />}
          size="small"
          type="date"
          value={navigation.selectedDay}
          onChange={(event) => onDayChange(event.target.value)}
        />
      </Space.Compact>
    </Card>
  );
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
  if (module === "parkering" && view === "kjoretoy") return "Søk etter reg.nr, bil, eier, område. Bruk \"nordby\" for eksakt ord.";
  return "Søk i tabellene";
}

function ModuleTablePane({
  table,
  query,
  onEdit,
}: {
  table: ModuleTable;
  query: string;
  onEdit?: (edit: ModuleEditConfig, row: ModuleRow, create?: boolean) => void;
}) {
  const columns = useMemo(() => moduleColumns(table, onEdit), [onEdit, table]);
  const filteredRows = useMemo(() => filterRows(table.rows, table.columns, query), [query, table.columns, table.rows]);
  const tableRows = useMemo(
    () =>
      filteredRows.map((row, index) => ({
        ...row,
        __rowKey: tableRowKey(row, table.title, index),
      })),
    [filteredRows, table.title],
  );
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
        rowKey="__rowKey"
        size="small"
        columns={columns}
        dataSource={tableRows}
        pagination={{ pageSize: 25, showSizeChanger: true }}
        scroll={{ x: "max-content" }}
        locale={{
          emptyText: query.trim() ? "Ingen treff for søket" : "Ingen rader å vise",
        }}
      />
    </Space>
  );
}

function rowString(row: ModuleRow, key: string): string {
  const value = row[key];
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function sessionImageUrl(row: ModuleRow): string {
  const url = rowString(row, "image_url");
  if (!url) return "";
  const version = rowString(row, "image_captured_at") || rowString(row, "id");
  return version ? `${url}?v=${encodeURIComponent(version)}` : url;
}

function rowSavedImages(row: ModuleRow): SunSessionSavedImage[] {
  return Array.isArray(row.session_images) ? (row.session_images as SunSessionSavedImage[]) : [];
}

function SunSessionDetails({ row, onImageChanged }: { row: ModuleRow; onImageChanged: () => void }) {
  const { message } = AntApp.useApp();
  const imageUrl = sessionImageUrl(row);
  const hasImage = row.has_image === true && Boolean(imageUrl);
  const sessionId = Number(row.id);
  const canBrowseImages = Number.isFinite(sessionId) && sessionId > 0;
  const [browserOpen, setBrowserOpen] = useState(false);
  const [browserLoading, setBrowserLoading] = useState(false);
  const [savingImage, setSavingImage] = useState(false);
  const [settingPrimaryImageId, setSettingPrimaryImageId] = useState<number | null>(null);
  const [browser, setBrowser] = useState<SunSessionImageBrowser | null>(null);
  const [selectedInlineImageId, setSelectedInlineImageId] = useState<number | null>(null);
  const inlineImages = rowSavedImages(row);
  const defaultInlineIndex = Math.max(0, inlineImages.findIndex((image) => image.isPrimary));
  const selectedInlineIndex = inlineImages.findIndex((image) => image.id === selectedInlineImageId);
  const activeInlineIndex = selectedInlineIndex >= 0 ? selectedInlineIndex : defaultInlineIndex;
  const activeInlineImage = inlineImages[activeInlineIndex] ?? null;
  const fields: Array<[string, unknown]> = [
    ["Start", row.started_at],
    ["Slutt", row.ended_at],
    ["Rom", row.room_label || row.room || row.room_id],
    ["Varighet", row.duration_minutes ? `${displayValue(row.duration_minutes)} min` : ""],
    ["Betalt", row.paid_amount_kr ? `${displayValue(row.paid_amount_kr)} kr` : ""],
    ["Bruker", row.user_name || row.sun2_user_id],
    ["Betaling", row.payment_method],
    ["Kundetype", row.customer_type],
    ["Status", row.status],
    ["Bildetid", row.image_captured_at],
    ["Bilder", row.image_count ? `${displayValue(row.image_count)} lagret` : ""],
    ["Avvik", row.image_delta_seconds !== null && row.image_delta_seconds !== undefined ? `${displayValue(row.image_delta_seconds)} sek` : ""],
  ];

  async function openBrowser(snapshotId?: string | null) {
    if (!canBrowseImages) {
      message.error("Mangler intern soltime-ID.");
      return;
    }
    setBrowserOpen(true);
    setBrowserLoading(true);
    try {
      const nextBrowser = await fetchSunSessionImageBrowser(sessionId, snapshotId);
      setBrowser(nextBrowser);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke hente bildearkivet");
    } finally {
      setBrowserLoading(false);
    }
  }

  async function useCurrentImage() {
    if (!canBrowseImages || !browser?.current) return;
    setSavingImage(true);
    try {
      await selectSunSessionImage(sessionId, browser.current.id);
      message.success("Bildet er byttet");
      const nextBrowser = await fetchSunSessionImageBrowser(sessionId, browser.current.id);
      setBrowser(nextBrowser);
      onImageChanged();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke bytte bilde");
    } finally {
      setSavingImage(false);
    }
  }

  async function setInlineImageAsPrimary(image: SunSessionSavedImage) {
    if (!canBrowseImages || image.isPrimary || settingPrimaryImageId) return;
    setSettingPrimaryImageId(image.id);
    try {
      await setSunSessionPrimaryImage(sessionId, image.id);
      message.success("Hovedbildet er oppdatert");
      setSelectedInlineImageId(image.id);
      onImageChanged();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke sette hovedbilde");
    } finally {
      setSettingPrimaryImageId(null);
    }
  }

  function moveInlineImage(delta: number) {
    if (!inlineImages.length) return;
    const nextIndex = (activeInlineIndex + delta + inlineImages.length) % inlineImages.length;
    setSelectedInlineImageId(inlineImages[nextIndex].id);
  }

  const modalFooter = [
    <Button key="older" disabled={browserLoading || !browser?.canPrevious} onClick={() => openBrowser(browser?.previousSnapshotId)}>
      Arkiv eldre
    </Button>,
    <Button key="newer" disabled={browserLoading || !browser?.canNext} onClick={() => openBrowser(browser?.nextSnapshotId)}>
      Arkiv nyere
    </Button>,
    <Button
      key="ok"
      type="primary"
      loading={savingImage}
      disabled={browserLoading || !browser?.current || browser.current.isLinked}
      onClick={useCurrentImage}
    >
      {browser?.current?.isLinked ? "Allerede valgt" : "Bruk dette bildet"}
    </Button>,
  ];

  return (
    <div className="sun-session-detail">
      <div className="sun-session-fields">
        {fields.map(([label, value]) => (
          <div className="sun-session-field" key={label}>
            <span>{label}</span>
            <strong>{displayValue(value)}</strong>
          </div>
        ))}
      </div>
      <div className="sun-session-image-panel">
        {activeInlineImage ? (
          <div className="sun-session-inline-browser">
            <img
              src={`${activeInlineImage.imageUrl}?v=${encodeURIComponent(activeInlineImage.id)}`}
              alt={`Lagret Axis-bilde ${activeInlineImage.label}`}
              loading="lazy"
            />
            <div className="sun-session-inline-meta">
              <strong>{activeInlineIndex + 1} av {inlineImages.length}</strong>
              <span>{activeInlineImage.offsetLabel} - {activeInlineImage.label}</span>
              {activeInlineImage.isPrimary ? <Tag color="gold">Hovedbilde</Tag> : null}
            </div>
            <div className="sun-session-inline-controls">
              <Button size="small" disabled={inlineImages.length < 2} onClick={() => moveInlineImage(-1)}>
                Forrige
              </Button>
              <Button size="small" disabled={inlineImages.length < 2} onClick={() => moveInlineImage(1)}>
                Neste
              </Button>
              <Button
                size="small"
                type={activeInlineImage.isPrimary ? "default" : "primary"}
                loading={settingPrimaryImageId === activeInlineImage.id}
                disabled={activeInlineImage.isPrimary || Boolean(settingPrimaryImageId)}
                onClick={() => setInlineImageAsPrimary(activeInlineImage)}
              >
                {activeInlineImage.isPrimary ? "Hovedbilde" : "Sett som hovedbilde"}
              </Button>
              <Button size="small" onClick={() => openBrowser(activeInlineImage.snapshotId || null)} disabled={!canBrowseImages}>
                Bildearkiv
              </Button>
            </div>
          </div>
        ) : hasImage ? (
          <div className="sun-session-inline-browser">
            <img src={imageUrl} alt={`Axis-bilde for soltime ${displayValue(row.started_at)}`} loading="lazy" />
            <div className="sun-session-inline-controls">
              <Button size="small" onClick={() => openBrowser()} disabled={!canBrowseImages}>
                Bildearkiv
              </Button>
            </div>
          </div>
        ) : (
          <div className="sun-session-empty-image">
            <Typography.Text type="secondary">Ingen koblet bilde for denne soltimen.</Typography.Text>
            <Button size="small" onClick={() => openBrowser()} disabled={!canBrowseImages}>
              Bildearkiv
            </Button>
          </div>
        )}
      </div>
      <Modal
        title="Bildearkiv for soltime"
        open={browserOpen}
        width={980}
        className="sun-image-browser-modal"
        onCancel={() => setBrowserOpen(false)}
        footer={modalFooter}
      >
        <div className="sun-image-browser">
          {browserLoading ? (
            <div className="sun-image-browser-loading">
              <Spin />
            </div>
          ) : browser?.current ? (
            <>
              <div className="sun-image-browser-meta">
                <div>
                  <span>Arkivbilde</span>
                  <strong>{browser.current.label}</strong>
                </div>
                <div>
                  <span>Beregnet bildetid</span>
                  <strong>{browser.targetLabel || "-"}</strong>
                </div>
                <div>
                  <span>Avvik</span>
                  <strong>{browser.current.deltaSeconds !== null && browser.current.deltaSeconds !== undefined ? `${displayValue(browser.current.deltaSeconds)} sek` : "-"}</strong>
                </div>
                <div>
                  <span>Status</span>
                  <strong>{browser.current.isLinked ? "Lagret på posten" : "Kan velges"}</strong>
                </div>
              </div>
              <img
                className="sun-image-browser-image"
                src={`${browser.current.imageUrl}?v=${encodeURIComponent(browser.current.id)}`}
                alt={`Axis-bilde ${browser.current.label}`}
              />
            </>
          ) : (
            <div className="sun-image-browser-empty">
              <Typography.Text type="secondary">Ingen Axis-bilder finnes i arkivet.</Typography.Text>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}

function SunSessionsPanel({
  table,
  query,
  draftQuery,
  onSearch,
  onClear,
  onDraftChange,
  onImageChanged,
}: {
  table?: ModuleTable;
  query: string;
  draftQuery: string;
  onSearch: (value?: string) => void;
  onClear: () => void;
  onDraftChange: (value: string) => void;
  onImageChanged: () => void;
}) {
  const rows = table ? filterRows(table.rows, table.columns, query) : [];
  return (
    <Card className="table-card sun-sessions-card">
      <div className="table-toolbar">
        <Input.Search
          allowClear
          placeholder="Søk i viste soltimer"
          value={draftQuery}
          onChange={(event) => {
            const nextValue = event.target.value;
            onDraftChange(nextValue);
            if (!nextValue) onClear();
          }}
          onSearch={onSearch}
          enterButton="Søk"
        />
      </div>
      <div className="sun-session-list-head">
        <Typography.Text type="secondary">{countText(rows.length, table?.rows.length ?? 0, query)}</Typography.Text>
      </div>
      <div className="sun-session-list">
        {rows.length ? (
          rows.map((row, index) => {
            const key = tableRowKey(row, table?.title ?? "Enkeltimer", index);
            const hasImage = row.has_image === true;
            const imageCount = Number(row.image_count || 0);
            return (
              <details className="sun-session-item" key={key}>
                <summary className="sun-session-summary">
                  <div className="sun-session-main">
                    <Typography.Text strong>{displayValue(row.started_at)}</Typography.Text>
                    <span>{displayValue(row.room_label || row.room || row.room_id)}</span>
                    <span>{displayValue(row.user_name || row.sun2_user_id)}</span>
                  </div>
                  <div className="sun-session-tags">
                    <Tag>{row.duration_minutes ? `${displayValue(row.duration_minutes)} min` : "Tid -"}</Tag>
                    <Tag>{row.paid_amount_kr ? `${displayValue(row.paid_amount_kr)} kr` : "Kr -"}</Tag>
                    <Tag color={hasImage ? "green" : "default"}>{hasImage ? `${imageCount || 1} bilder` : "Ingen bilde"}</Tag>
                  </div>
                </summary>
                <SunSessionDetails row={row} onImageChanged={onImageChanged} />
              </details>
            );
          })
        ) : (
          <div className="sun-session-empty">
            <Typography.Text type="secondary">{query.trim() ? "Ingen treff for søket" : "Ingen soltimer å vise"}</Typography.Text>
          </div>
        )}
      </div>
    </Card>
  );
}

export default function ModulePage({ module }: { module: string }) {
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { message, modal } = AntApp.useApp();
  const [form] = Form.useForm();
  const [query, setQuery] = useState("");
  const [draftQuery, setDraftQuery] = useState("");
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [editState, setEditState] = useState<{ edit: ModuleEditConfig; row: ModuleRow; create: boolean } | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const view = params.view ?? defaultModuleView(module);
  const viewItems = MODULE_VIEWS[module] ?? [];
  const isKnownView = !viewItems.length || viewItems.some((item) => item.key === view);
  const safeView = isKnownView ? view : defaultModuleView(module);
  const serverQuery = module === "parkering" && safeView === "kjoretoy" ? query : "";
  const filterKey = searchParams.toString();
  const timelineDay =
    (module === "soling" && safeView === "dagslinje") ||
    (module === "parkering" && safeView === "dagslinje") ||
    (module === "ventilasjon" && safeView === "dagslogg")
      ? searchParams.get("day") ?? ""
      : "";
  const { data, loading, error } = useAsyncData(
    () => fetchModule(module, safeView, serverQuery, timelineDay || undefined, searchParams),
    [module, safeView, serverQuery, timelineDay, filterKey, reloadToken],
  );

  if (!isKnownView) return <Navigate to={modulePath(module)} replace />;

  function runSearch(value = draftQuery) {
    setQuery(value.trim());
  }

  function clearSearch() {
    setDraftQuery("");
    setQuery("");
  }

  function setTimelineDay(day: string) {
    const nextParams = new URLSearchParams(searchParams);
    if (day) nextParams.set("day", day);
    else nextParams.delete("day");
    setSearchParams(nextParams);
  }

  function applyModuleFilters(values: Record<string, string>) {
    const nextParams = new URLSearchParams(searchParams);
    Object.entries(values).forEach(([key, value]) => {
      const trimmed = value.trim();
      if (trimmed) nextParams.set(key, trimmed);
      else nextParams.delete(key);
    });
    setSearchParams(nextParams);
  }

  function clearModuleFilters(keys: string[]) {
    const nextParams = new URLSearchParams(searchParams);
    keys.forEach((key) => nextParams.delete(key));
    setSearchParams(nextParams);
  }

  function openEdit(edit: ModuleEditConfig, row: ModuleRow, create = false) {
    form.resetFields();
    form.setFieldsValue(editInitialValues(edit, row, create));
    setEditState({ edit, row, create });
  }

  async function saveEdit() {
    if (!editState || savingEdit) return;
    const values = (await form.validateFields()) as JsonRecord;
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
  if (module === "ventilasjon" && data.ventilation) {
    return (
      <Suspense fallback={<LoadingBlock />}>
        <VentilationPage data={data} view={safeView} onReload={() => setReloadToken((value) => value + 1)} />
      </Suspense>
    );
  }
  if (module === "energi" && safeView === "elvia" && data.energyElvia) {
    return (
      <Suspense fallback={<LoadingBlock />}>
        <EnergyElviaPage data={data} onReload={() => setReloadToken((value) => value + 1)} />
      </Suspense>
    );
  }
  if (module === "energi" && safeView === "forbruk-per-seng" && data.energySunbeds) {
    return (
      <Suspense fallback={<LoadingBlock />}>
        <Space direction="vertical" size={14} className="page-stack">
          {data.filters?.length ? (
            <ModuleFilterBar
              filters={data.filters}
              key={`${module}-${safeView}-${filterKey}`}
              onApply={applyModuleFilters}
              onClear={clearModuleFilters}
            />
          ) : null}
          <EnergySunbedsPage data={data} />
        </Space>
      </Suspense>
    );
  }
  const hideModuleChrome = Boolean(data.parkingTimeline);
  const isSunSessionsView = module === "soling" && safeView === "enkeltimer";

  return (
    <Space direction="vertical" size={18} className="page-stack">
      {data.actions?.length && !hideModuleChrome ? (
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

      {data.dayNavigation && !hideModuleChrome ? (
        <ModuleDayNavigationBar navigation={data.dayNavigation} onDayChange={setTimelineDay} />
      ) : null}

      {data.filters?.length ? (
        <ModuleFilterBar
          filters={data.filters}
          key={`${module}-${safeView}-${filterKey}`}
          onApply={applyModuleFilters}
          onClear={clearModuleFilters}
        />
      ) : null}

      {isSunSessionsView ? (
        <SunSessionsPanel
          table={data.tables[0]}
          query={query}
          draftQuery={draftQuery}
          onSearch={runSearch}
          onClear={clearSearch}
          onDraftChange={setDraftQuery}
          onImageChanged={() => setReloadToken((value) => value + 1)}
        />
      ) : (
        <>
      {data.cards.length && !hideModuleChrome ? (
        <div className="metric-grid primary-grid">
          {data.cards.map((card) => (
            <ModuleMetric card={card} key={card.title} module={module} view={safeView} />
          ))}
        </div>
      ) : null}

      {data.sunTimeline ? (
        <SunTimelinePanel timeline={data.sunTimeline} onDayChange={setTimelineDay} />
      ) : data.parkingTimeline ? (
        <ParkingTimelinePanel timeline={data.parkingTimeline} onDayChange={setTimelineDay} />
      ) : (
        <>
          {data.charts?.map((chart) => <ModuleChartPanel chart={chart} key={chart.title} onDayChange={setTimelineDay} />)}

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
        </>
      )}
        </>
      )}

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
