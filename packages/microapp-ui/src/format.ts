export function nok(value: number, digits = 0) {
  return new Intl.NumberFormat("nb-NO", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number.isFinite(value) ? value : 0);
}

export function signedNok(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 kr";
  return `${value > 0 ? "+" : "-"}${nok(Math.abs(value))} kr`;
}

export function percentDelta(current: number, previous: number) {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) return "-";
  const value = ((current - previous) / previous) * 100;
  return `${value > 0 ? "+" : ""}${value.toFixed(0)}%`;
}

export function shortDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("nb-NO", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function valueLabel(key: string) {
  const labels: Record<string, string> = {
    id: "ID",
    name: "Navn",
    title: "Navn",
    headline: "Overskrift",
    description: "Forklaring",
    detail: "Detaljer",
    message: "Siste resultat",
    count: "Antall",
    total: "Totalt",
    value: "Verdi",
    key: "Nøkkel",
    source: "Kilde",
    source_no: "Nr.",
    category: "Område",
    date: "Dato",
    period_label: "Periode",
    period_start: "Fra",
    period_end: "Til",
    status: "Status",
    status_text: "Statusforklaring",
    active: "Aktiv",
    enabled: "Aktivert",
    ok: "OK",
    success: "Vellykket",
    error: "Feil",
    age: "Sist oppdatert",
    timestamp: "Tidspunkt",
    updated_at: "Oppdatert",
    last_success_at: "Sist vellykket",
    last_failed_at: "Sist feilet",
    next_expected_at: "Neste forventet",
    last_seen_at: "Sist sett",
    last_run_at: "Sist kjørt",
    performed_at: "Tidspunkt",
    performed_by: "Registrert av",
    site_visit: "Besøk",
    site_visit_id: "Besøks-ID",
    target_type: "Gjelder",
    target_name: "Objekt",
    action_type: "Aktivitet",
    priority: "Prioritet",
    severity: "Alvorlighetsgrad",
    domain: "Område",
    item: "Kontrollpunkt",
    problem: "Problem",
    recommended_action: "Anbefalt tiltak",
    assessment: "Vurdering",
    summary: "Utført arbeid / observasjon",
    tags: "Emneord",
    duration: "Varighet",
    duration_minutes: "Varighet",
    follow_up_needed: "Må følges opp",
    follow_up_text: "Oppfølgingsnotat",
    started_at: "Kom",
    ended_at: "Dro",
    tasks_count: "Oppgaver",
    last_synced_at: "Sist synket",
    confidence: "Sikkerhet",
    enter_source: "Kilde inn",
    leave_source: "Kilde ut",
    source_visit_id: "Kilde-ID",
    notes: "Notat",
    tag: "Emneord",
    start_time: "Start",
    end_time: "Slutt",
    end_delta_min: "Avvik",
    car_license_number: "Reg.nr",
    plate: "Reg.nr",
    vehicle_title: "Kjøretøy",
    navn: "Eier",
    omrade: "Område",
    fee_inc_vat: "Beløp",
    parking_time_min: "Tid",
    previous_parking_count: "P før",
    previous_paid_total: "B før",
    parkering_count: "Parkeringer",
    paid_total: "Betalt totalt",
    parking_paid: "Parkering",
    parking_count: "Parkeringer",
    total_paid: "Sum omsetning",
    total_count: "Antall totalt",
    sun_paid: "Soling",
    sun_count: "Solinger",
    vehicles: "Kjøretøy",
    vehicle_share: "Andel kjøretøy",
    parkeringer: "Parkeringer",
    parking_share: "Andel parkeringer",
    days_count: "Dager",
    period: "Periode",
    week_label: "Uke",
    date_range: "Datoer",
    week_start: "Uke fra",
    sessions: "Parkeringer",
    paid: "Beløp",
    minutes: "Minutter",
    avg_paid_per_session: "Snittbeløp",
    avg_minutes_per_session: "Snitttid",
    duration_coverage_pct: "Tidsdekning",
    last_seen: "Sist sett",
    first_seen: "Først sett",
    path: "Detaljer",
    attachment_filename: "Fil",
    imported_at: "Importert",
    payout_inc_vat: "Utbetalt",
    actual_parkeringer: "Faktisk antall",
    forecast_parkeringer: "Prognose antall",
    delta_parkeringer: "Avvik antall",
    actual_paid: "Faktisk beløp",
    forecast_paid: "Prognose beløp",
    delta_paid: "Avvik beløp",
    actual_minutes: "Faktisk tid",
    forecast_minutes: "Prognose tid",
    actual_vehicles: "Faktiske kjøretøy",
    forecast_vehicles: "Prognose kjøretøy",
    remaining_days: "Dager igjen",
    period_type: "Periodetype",
    created_at: "Opprettet",
    parser_confidence: "Tolkingssikkerhet",
    email_date: "E-post mottatt",
    easypark_inc_vat_estimate: "EasyPark inkl. mva",
    flowbird_source_count: "Flowbird antall",
    flowbird_source_paid_ex_vat: "Flowbird grunnlag",
    easypark_source_count: "EasyPark antall",
    easypark_source_paid_ex_vat: "EasyPark grunnlag",
    other_source_count: "Andre antall",
    average_paid: "Snittbeløp",
    easypark_ex_vat: "EasyPark eks. mva",
    gross_coin_card_ex_vat: "Mynt/kort eks. mva",
    flowbird_source_diff_ex_vat: "Flowbird-avvik",
    easypark_source_diff_ex_vat: "EasyPark-avvik",
  };
  return labels[key] || key.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

export function displayCell(key: string, value: unknown) {
  if (value == null || value === "") return "-";
  if (typeof value === "boolean") return value ? "Ja" : "Nei";
  if (typeof value === "number") {
    if (key.includes("paid") || key.includes("amount") || key.includes("revenue") || key.includes("fee") || key.includes("payout") || key.includes("ex_vat") || key.includes("average_paid") || key === "total") return `${nok(value)} kr`;
    if (key.includes("percent") || key.endsWith("_pct") || key.includes("confidence")) return `${nok(value, 1)} %`;
    if (key.includes("minutes") || key.endsWith("_min")) return `${nok(value, Number.isInteger(value) ? 0 : 1)} min`;
    return nok(value, Number.isInteger(value) ? 0 : 1);
  }
  if (typeof value === "string" && ((key.endsWith("_time") || key.endsWith("_at") || key.endsWith("_seen") || key === "email_date") || /^\d{4}-\d{2}-\d{2}(?:T|$)/.test(value))) {
    const date = new Date(value);
    if (!Number.isNaN(date.getTime())) return value.length === 10
      ? date.toLocaleDateString("nb-NO", { day: "2-digit", month: "2-digit", year: "numeric" })
      : date.toLocaleString("nb-NO", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  if (key === "status" && typeof value === "string") {
    const labels: Record<string, string> = { ok: "OK", error: "Feil", failed: "Feilet", running: "Kjører", warning: "Varsel" };
    return labels[value.trim().toLowerCase()] || value;
  }
  return String(value);
}
