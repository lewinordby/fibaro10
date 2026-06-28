import { VideoCameraOutlined } from "@ant-design/icons";
import { Button, Checkbox, Input, InputNumber, Select, Space, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link } from "react-router-dom";

import type { JsonRecord, ModuleEditConfig, ModuleEditField, ModuleRow, ModuleTable } from "../../api";
import { appPath } from "../../navigation";
export function displayValue(value: unknown): string {
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
    vehicle_owner: "Eier",
    vehicle_make: "Bilmerke",
    vehicle_type: "Type",
    vehicle_color: "Farge",
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
    sun_paid: "Sum sol",
    parking_paid: "Sum parkering",
    total_paid: "Sum kr",
    sun_count: "Antall sol",
    parking_count: "Antall parkering",
    total_count: "Antall totalt",
    first_seen: "Først sett",
    parking_system_ex_vat: "Parkering Fibaro10",
    parking_settlement_ex_vat: "Oppgjør parkering",
    parking_diff_ex_vat: "Avvik parkering",
    parking_control_status: "Status parkering",
    sun_system_ex_vat: "Soling Fibaro10",
    sun_settlement_ex_vat: "Oppgjør soling",
    sun_diff_ex_vat: "Avvik soling",
    sun_control_status: "Status soling",
    system_total_ex_vat: "Sum Fibaro10",
    settlement_total_ex_vat: "Sum oppgjør",
    total_diff_ex_vat: "Avvik sum",
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
    product_name: "Produkt",
    product_category: "Kategori",
    quantity: "Antall",
    unit_price_kr: "Pris",
    amount_inc_vat_kr: "Inkl. mva",
    amount_ex_vat_kr: "Eks. mva",
    vat_kr: "Mva",
    sales_count: "Salgslinjer",
    average_sale_inc_vat_kr: "Snitt inkl. mva",
    source_scope: "Grunnlag",
    control_basis: "Kontroll",
    physical_room_number: "Rom",
    room_id: "Rom-ID",
    bed_model: "Sengemodell",
    current_price_per_min: "Kr/min",
    max_minutes: "Maks min",
    lamp_status: "Lampe",
    imported_at: "Importert",
    last_seen_at: "Sist sett",
    visits_count: "Besøk",
    total_spent_kr: "Totalt kjøp",
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
    hc3_kwh: "HC3 kWh",
    elvia_kwh: "Elvia kWh",
    diff_kwh: "Avvik kWh",
    diff_percent: "Avvik %",
    hc3_samples: "HC3 samples",
    hc3_delta_samples: "HC3 delta",
    elvia_status: "Elvia-status",
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
    key_prefix: "Nøkkelprefiks",
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
  return /(_w|_kr|_kwh|_min|_m2|_count|_share|count|quantity|paid|fee|vat|payout|diff|confidence|duration|minutes|hour|age|battery|rssi|lux|temp|humidity|wind|cloud|precipitation|breaker|power|energy)$/i.test(
    column,
  );
}

function LinkValue({ value }: { value: string }) {
  const internalPath = appPath(value);
  if (internalPath) return <Link to={internalPath}>{value}</Link>;
  if (value.startsWith("/") || /^https?:\/\//i.test(value)) return <a href={value}>{value}</a>;
  return displayValue(value);
}

function renderTimeWithVideo(value: unknown, row: ModuleRow, urlKey: string, tooltip: string) {
  const href = row[urlKey];
  if (typeof href !== "string" || !href) return displayValue(value);
  return (
    <Space size={4} wrap={false}>
      <span>{displayValue(value)}</span>
      <Tooltip title={tooltip}>
        <Button
          aria-label={tooltip}
          href={href}
          icon={<VideoCameraOutlined />}
          rel="noreferrer"
          size="small"
          target="_blank"
          type="text"
        />
      </Tooltip>
    </Space>
  );
}

export function moduleColumns(
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
      if (column === "start_time" && typeof row.unifi_start_url === "string") {
        return renderTimeWithVideo(value, row, "unifi_start_url", "Åpne start i UniFi Protect");
      }
      if (column === "end_time" && typeof row.unifi_end_url === "string") {
        return renderTimeWithVideo(value, row, "unifi_end_url", "Åpne slutt i UniFi Protect");
      }
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
      if (column.endsWith("_control_status") && typeof value === "string") {
        const normalized = value.toLowerCase();
        const color = normalized.includes("ok") ? "green" : normalized.includes("avvik") ? "volcano" : "gold";
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

export function filterRows(rows: ModuleRow[], columns: string[], query: string) {
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

export function fieldInput(field: ModuleEditField) {
  if (field.type === "textarea") return <Input.TextArea rows={3} />;
  if (field.type === "number") return <InputNumber className="edit-number" />;
  if (field.type === "boolean") return <Checkbox>{field.label}</Checkbox>;
  if (field.type === "select") return <Select options={field.options} />;
  if (field.type === "password") return <Input.Password autoComplete="new-password" />;
  return <Input />;
}

export function editInitialValues(edit: ModuleEditConfig, row: ModuleRow, create: boolean) {
  const fields = create ? edit.createFields ?? edit.fields : edit.fields;
  const values: JsonRecord = {};
  for (const field of fields) {
    values[field.key] = field.type === "boolean" ? Boolean(row[field.key]) : row[field.key] ?? undefined;
  }
  return values;
}

export function tableRowKey(row: ModuleRow, tableTitle: string, index?: number) {
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

export function countText(filteredCount: number, totalCount: number, query: string): string {
  if (query.trim() && filteredCount !== totalCount) return `Viser ${filteredCount} av ${totalCount} rader`;
  return `${totalCount} rader`;
}
