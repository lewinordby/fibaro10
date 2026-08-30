"""Existing export definitions preserved during core modularization."""

LIGHT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_key", "device_id", "device_name",
    "mode", "reason", "source", "lux", "value", "state", "extra",
]

LIGHT_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "mode", "source", "lux", "value",
    "light_lyslist", "light_reklame", "light_spot_glass_275", "light_spot_glass_299",
    "light_spot_inngang", "light_parkering", "weather_symbol", "weather_text", "extra",
]

VENT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_key", "device_id", "device_name",
    "mode", "reason", "source", "value", "state", "temp_1etg", "temp_2etg",
    "temp_vip", "temp_ute", "temp_loft", "humidity_1etg", "humidity_2etg",
    "humidity_vip", "humidity_ute", "humidity_yr", "humidity_loft",
    "temp_kjeller", "humidity_kjeller", "temp_passiv", "temp_luftinntak",
    "humidity_passiv", "humidity_luftinntak", "diff_w", "power_w", "energy_kwh",
    "fan_vip", "fan_2etg", "fan_tak", "fan_avfukter", "extra",
]

GENERIC_COLUMNS = [
    "id", "timestamp", "system", "event_type", "action", "device_key", "device_id",
    "device_name", "mode", "reason", "source", "lux", "value", "state", "extra",
]

DOOR_EVENT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_key", "device_id",
    "device_name", "source", "raw_value", "state", "previous_state",
    "battery_level", "extra",
]

VENT_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "mode", "source", "temp_1etg", "temp_2etg",
    "temp_vip", "temp_ute", "temp_ute_netatmo", "temp_yr", "temp_loft",
    "humidity_1etg", "humidity_2etg", "humidity_vip", "humidity_ute",
    "humidity_yr", "humidity_loft", "temp_passiv", "temp_kjeller",
    "humidity_kjeller", "temp_luftinntak", "humidity_passiv",
    "humidity_luftinntak", "temp_min_inne", "temp_avg_inne", "temp_max_inne", "diff_w", "estimated_sunbeds",
    "afterrun_active", "heat_need", "cool_need", "open_time", "pre_cooling",
    "exhaust_time_allowed", "fan_vip", "fan_2etg", "fan_tak", "fan_avfukter", "extra",
]

YR_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "source", "api_updated_at", "last_modified",
    "expires_at", "next_fetch_after", "age_seconds", "forecast_time", "symbol_code",
    "weather_text", "air_temperature", "air_temperature_percentile_10",
    "air_temperature_percentile_90", "relative_humidity", "wind_speed",
    "wind_speed_of_gust", "wind_speed_percentile_10", "wind_speed_percentile_90",
    "wind_from_direction", "cloud_area_fraction", "cloud_area_fraction_high",
    "cloud_area_fraction_medium", "cloud_area_fraction_low", "fog_area_fraction",
    "dew_point_temperature", "air_pressure_at_sea_level", "ultraviolet_index_clear_sky",
    "precipitation_next_1h", "precipitation_next_1h_min", "precipitation_next_1h_max",
    "precipitation_next_6h", "precipitation_next_6h_min", "precipitation_next_6h_max",
    "probability_of_precipitation_next_1h", "probability_of_precipitation_next_6h",
    "probability_of_precipitation_next_12h", "probability_of_thunder_next_1h",
    "air_temperature_min_next_6h", "air_temperature_max_next_6h",
    "symbol_confidence_next_12h", "temp_1h", "temp_3h", "temp_6h", "temp_12h",
    "temp_24h", "symbol_1h", "symbol_3h", "symbol_6h", "symbol_12h",
    "symbol_24h", "temp_min_next_6h", "temp_max_next_6h", "extra", "raw",
]

YR_LOG_TABLE_COLUMNS = [
    "bucket_start", "weather_text", "air_temperature", "relative_humidity",
    "wind_speed", "wind_speed_of_gust", "cloud_area_fraction", "precipitation_next_1h",
]

ROBOROCK_ROBOT_COLUMNS = [
    "id", "duid", "provider", "external_id", "integration_status", "name", "product", "model", "firmware", "protocol_version",
    "serial_number", "local_ip", "cloud_online", "shared", "time_zone_id",
    "last_seen_at", "last_cloud_at", "last_local_at", "last_status_at",
    "last_map_at", "last_error", "capabilities", "extra",
]

ROBOROCK_STATUS_COLUMNS = [
    "id", "robot_duid", "timestamp", "source", "state_code", "state_name",
    "battery", "error_code", "in_cleaning", "in_returning", "clean_time_seconds",
    "clean_area_m2", "fan_power", "water_box_mode", "mop_mode", "dock_type",
    "charge_status", "clean_percent", "local_ip", "rssi", "raw",
]

ROBOROCK_TELEMETRY_COLUMNS = [
    "id", "robot_duid", "timestamp", "source", "state_code", "state_name",
    "battery", "error_code", "in_cleaning", "in_returning", "clean_time_seconds",
    "clean_area_m2", "clean_percent", "fan_power", "water_box_mode", "mop_mode",
    "charge_status", "is_charging", "dock_type", "dock_error_status",
    "dust_collection_status", "auto_dust_collection", "wash_status", "wash_phase",
    "wash_ready", "dry_status", "water_shortage_status", "water_box_status",
    "water_box_carriage_status", "clear_water_status", "clear_water_status_name",
    "dirty_water_status", "dirty_water_status_name", "dust_bag_status",
    "dust_bag_status_name", "clean_fluid_status", "clean_fluid_status_name",
    "water_box_filter_status", "dock_cool_fan_status", "local_ip", "rssi", "dss",
    "rss", "raw",
]

ROBOROCK_TELEMETRY_EVENT_COLUMNS = [
    "id", "robot_duid", "timestamp", "category", "field_name", "title",
    "previous_value", "current_value", "previous_label", "current_label",
    "severity", "raw",
]

ROBOROCK_TELEMETRY_DISPLAY_FIELDS = [
    ("Robot", "state_code", "Status", "state_name"),
    ("Robot", "battery", "Batteri", None),
    ("Robot", "error_code", "Robotfeil", None),
    ("Robot", "in_cleaning", "Rengjøring aktiv", None),
    ("Robot", "in_returning", "Returnerer til dokk", None),
    ("Robot", "clean_percent", "Fremdrift", None),
    ("Robot", "clean_time_seconds", "Rengjøringstid", None),
    ("Robot", "clean_area_m2", "Rengjort areal", None),
    ("Robot", "fan_power", "Sugekraft", None),
    ("Robot", "mop_mode", "Moppemodus", None),
    ("Lading", "is_charging", "Lader nå", None),
    ("Lading", "charge_status", "Ladestatus fra API", None),
    ("Dokk", "dock_type", "Dokktype", None),
    ("Dokk", "dock_error_status", "Dokkfeil", None),
    ("Dokk", "dust_collection_status", "Støvtømming", None),
    ("Dokk", "auto_dust_collection", "Automatisk støvtømming", None),
    ("Dokk", "wash_status", "Moppevask", None),
    ("Dokk", "wash_phase", "Vaskefase", None),
    ("Dokk", "wash_ready", "Klar for vask", None),
    ("Dokk", "dry_status", "Tørking", None),
    ("Dokk", "dock_cool_fan_status", "Dokkens kjølevifte", None),
    ("Vann og beholdere", "clear_water_status", "Rentvann i dokk", "clear_water_status_name"),
    ("Vann og beholdere", "dirty_water_status", "Skittentvann i dokk", "dirty_water_status_name"),
    ("Vann og beholdere", "dust_bag_status", "Støvpose", "dust_bag_status_name"),
    ("Vann og beholdere", "clean_fluid_status", "Rengjøringsmiddel", "clean_fluid_status_name"),
    ("Vann og beholdere", "water_shortage_status", "Vannvarsel", None),
    ("Vann og beholdere", "water_box_status", "Vanntank i robot", None),
    ("Vann og beholdere", "water_box_carriage_status", "Mopp montert", None),
    ("Vann og beholdere", "water_box_filter_status", "Vannfilter", None),
    ("Vann og beholdere", "water_box_mode", "Vannmengde ved vask", None),
    ("Nettverk", "rssi", "WiFi-signal", None),
    ("Nettverk", "local_ip", "Lokal IP", None),
    ("Teknisk", "dss", "DSS-statusord", None),
    ("Teknisk", "rss", "RSS-statusord", None),
]

ROBOROCK_JOB_COLUMNS = [
    "id", "robot_duid", "record_id", "begin_at", "end_at", "duration_seconds",
    "duration_minutes", "area_m2", "cleaned_area_m2", "complete", "error_code",
    "start_type", "clean_type", "finish_reason", "dust_collection_status",
    "avoid_count", "wash_count", "clean_times", "updated_at", "raw",
]

ROBOROCK_SCHEDULE_COLUMNS = [
    "id", "robot_duid", "schedule_id", "cron", "enabled", "repeated", "segments",
    "fan_power", "mop_mode", "water_box_mode", "repeat", "updated_at", "deleted_at", "raw",
]

ROBOROCK_MAP_COLUMNS = [
    "id", "robot_duid", "timestamp", "image_bytes", "raw_bytes", "image_width",
    "image_height", "rooms", "zones", "charger", "vacuum_position", "raw",
]

SUN2_ROOM_COLUMNS = [
    "id", "stat_date", "room_id", "room_key", "room", "source_room_name", "sun2_bed_id", "total_soletid_minutter",
    "totalt_antall_solinger", "solinger_medlemmer", "solinger_ikke_medlemmer",
    "totalt_inntjent_kr", "inntjent_medlemmer_kr", "inntjent_ikke_medlemmer_kr",
    "source", "source_file", "imported_at", "raw",
]

SUN2_IMPORT_COLUMNS = [
    "id", "timestamp", "collector_id", "source", "ok", "stat_date", "source_file",
    "rows_count", "inserted_count", "updated_count", "message", "raw",
]

SUN2_SESSION_COLUMNS = [
    "id", "source_session_id", "started_at", "ended_at", "stat_date", "room_id", "room_key",
    "room", "source_room_name", "sun2_user_id", "sun2_center_id", "sun2_bed_id", "user_name",
    "user_identifier", "customer_type", "gender", "payment_method", "duration_minutes",
    "paid_amount_kr", "status", "source", "source_file", "imported_at", "raw",
]

SUN2_SESSION_IMAGE_COLUMNS = [
    "id", "session_id", "captured_at", "target_at", "offset_seconds", "is_primary", "delta_seconds", "source_path",
    "source_mtime", "content_type", "byte_size", "sha256", "created_at", "source",
]

SUN2_BED_COLUMNS = [
    "id", "room_id", "physical_room_number", "display_room_number", "sun2_center_id",
    "sun2_bed_id", "name", "source_room_name", "bed_model", "bed_model_id",
    "max_minutes", "startup_minutes", "cooldown_minutes", "current_price_per_min",
    "status", "status_code", "lamp_status", "source", "imported_at", "raw",
]

SUN2_MEMBER_COLUMNS = [
    "id", "sun2_user_id", "sun2_center_id", "name", "display_name", "initials", "age",
    "email", "phone", "profile_url", "customer_type", "gender", "birth_date",
    "member_since", "last_seen_at", "status", "balance_kr", "total_spent_kr",
    "visits_count", "source", "source_file", "imported_at", "raw",
]

SUN2_PRODUCT_SALE_COLUMNS = [
    "id", "source_sale_id", "sold_at", "stat_date", "period_start", "period_end",
    "product_name", "product_category", "quantity", "unit_price_kr",
    "amount_inc_vat_kr", "amount_ex_vat_kr", "vat_kr", "payment_method",
    "sun2_user_id", "user_name", "source", "source_file", "imported_at", "raw",
]

SUN2_FINANCE_SETTLEMENT_COLUMNS = [
    "id", "source_payout_id", "payout_label", "period_start", "period_end", "payout_date",
    "member_tanning_count", "member_tanning_inc_vat_kr",
    "unregistered_tanning_count", "unregistered_tanning_inc_vat_kr",
    "tanning_bonus_inc_vat_kr", "tanning_control_inc_vat_kr", "tanning_control_ex_vat_kr",
    "member_product_count", "member_product_inc_vat_kr",
    "unregistered_product_count", "unregistered_product_inc_vat_kr",
    "product_bonus_inc_vat_kr", "product_control_inc_vat_kr", "product_control_ex_vat_kr",
    "transaction_cost_kr", "service_fee_kr", "payout_inc_vat_kr", "vat_kr",
    "source", "source_file", "imported_at", "raw",
]

SUN2_SESSION_IMPORT_COLUMNS = [
    "id", "timestamp", "collector_id", "source", "ok", "source_file",
    "period_first", "period_last", "rows_count", "inserted_count", "updated_count",
    "skipped_count", "message", "raw",
]

ENERGY_HOURLY_COLUMNS = [
    "id", "meter_id", "measured_at", "stat_date", "year", "month", "day", "hour",
    "consumption_kwh", "production_kwh", "status", "is_verified", "is_estimated",
    "is_public_holiday", "use_weekend_prices", "source", "source_file", "imported_at", "raw",
]

ENERGY_IMPORT_COLUMNS = [
    "id", "timestamp", "meter_id", "source", "ok", "source_file", "period_first", "period_last",
    "days_count", "hours_count", "inserted_count", "updated_count", "skipped_count", "total_kwh",
    "estimated_hours_count", "message", "raw",
]

ENERGY_FIBARO_COLUMNS = [
    "id", "timestamp", "bucket_start", "source",
    "inntak_w", "varmepumper_w", "belysning_w", "massasje_w", "annet_w", "avfukter_w",
    "differanse_fibaro_w", "differanse_beregnet_w",
    "inntak_kwh", "varmepumper_kwh", "belysning_kwh", "massasje_kwh", "annet_kwh", "avfukter_kwh",
    "differanse_fibaro_kwh", "differanse_beregnet_kwh",
    "inntak_delta_kwh", "varmepumper_delta_kwh", "belysning_delta_kwh",
    "massasje_delta_kwh", "annet_delta_kwh", "avfukter_delta_kwh", "differanse_fibaro_delta_kwh",
    "differanse_beregnet_delta_kwh",
    "inntak_reset", "varmepumper_reset", "belysning_reset", "massasje_reset",
    "annet_reset", "avfukter_reset", "differanse_fibaro_reset", "extra",
]

AI_QUERY_COLUMNS = [
    "id", "timestamp", "username", "question", "answer", "ok", "error", "tool_calls_count", "raw",
]

AI_DATASETS = {
    "soling_daily": {
        "table": "sun2_room_daily_stats",
        "title": "Soling per rom per dag",
        "description": "SUN2-statistikk med soltid, antall solinger og inntjent beløp per rom og dato.",
        "columns": SUN2_ROOM_COLUMNS,
        "time_column": "stat_date",
    },
    "soling_sessions": {
        "table": "sun2_tanning_sessions",
        "title": "Enkelt-solinger",
        "description": "En rad per soltime/soling hentet fra SUN2 owner, med starttid, rom, bruker, varighet og betalt beløp.",
        "columns": SUN2_SESSION_COLUMNS,
        "time_column": "started_at",
    },
    "soling_beds": {
        "table": "sun2_beds",
        "title": "SUN2 senger og fysisk rom",
        "description": "Fast mapping mellom fysisk rom-id, SUN2 seng-id, SUN2-navn, modell, status og gjeldende innstillinger.",
        "columns": SUN2_BED_COLUMNS,
        "time_column": "imported_at",
    },
    "soling_members": {
        "table": "sun2_members",
        "title": "SUN2 medlemmer",
        "description": "SUN2-brukere/medlemmer med fast SUN2-id og eventuell profilinfo fra medlemssider.",
        "columns": SUN2_MEMBER_COLUMNS,
        "time_column": "imported_at",
    },
    "soling_product_sales": {
        "table": "sun2_product_sales",
        "title": "SUN2 produktsalg",
        "description": "Produktsalg fra SUN2 med salgsdato, produkt, antall og beløp inkl./eks. mva. Brukes til dagsfordeling og oppgjørskontroll.",
        "columns": SUN2_PRODUCT_SALE_COLUMNS,
        "time_column": "sold_at",
    },
    "soling_finance_settlements": {
        "table": "sun2_finance_settlements",
        "title": "SUN2 finansoppgjør",
        "description": "Månedlige finanslinjer fra SUN2 med soling, uregistrerte solinger og kontrollbeløp mot Altera-kreditnota.",
        "columns": SUN2_FINANCE_SETTLEMENT_COLUMNS,
        "time_column": "period_start",
    },
    "energy_hourly": {
        "table": "energy_hourly_consumption",
        "title": "Elvia strømforbruk per time",
        "description": "Importerte Elvia-timesverdier med kWh, måler, dato og status.",
        "columns": ENERGY_HOURLY_COLUMNS,
        "time_column": "measured_at",
    },
    "energy_fibaro": {
        "table": "energy_fibaro_samples",
        "title": "Fibaro strømlogging",
        "description": "30-sekunders logging fra HC3 med realtime effekt, akkumulert kWh som kontrollverdi, beregnet differanse og reset-markering.",
        "columns": ENERGY_FIBARO_COLUMNS,
        "time_column": "bucket_start",
    },
    "light_events": {
        "table": "utelys_events",
        "title": "Lys hendelser",
        "description": "På/av-hendelser for lys, med lux, enhet, årsak og modus.",
        "columns": LIGHT_COLUMNS,
        "time_column": "timestamp",
    },
    "light_samples": {
        "table": "utelys_samples",
        "title": "Lys 5-minutters logging",
        "description": "Regelmessige lys- og lux-prøver med status for alle lysgrupper.",
        "columns": LIGHT_SAMPLE_COLUMNS,
        "time_column": "timestamp",
    },
    "ventilation_events": {
        "table": "ventilasjon_events",
        "title": "Ventilasjon hendelser",
        "description": "Start/stopp-hendelser for vifter med temperaturer, effekt og årsak.",
        "columns": VENT_COLUMNS,
        "time_column": "timestamp",
    },
    "ventilation_samples": {
        "table": "ventilasjon_samples",
        "title": "Ventilasjon 5-minutters logging",
        "description": "Temperaturer, viftestatus, effekt og beregnet driftsmodus.",
        "columns": VENT_SAMPLE_COLUMNS,
        "time_column": "timestamp",
    },
    "yr_forecast": {
        "table": "yr_forecast_samples",
        "title": "Yr værdata",
        "description": "Værvarsel og observasjonsnære verdier hentet fra Yr/MET.",
        "columns": YR_SAMPLE_COLUMNS,
        "time_column": "timestamp",
    },
    "renhold_robots": {
        "table": "roborock_robots",
        "title": "Roborock roboter",
        "description": "Robotmetadata, modell, serienummer, IP, firmware og siste kontakt.",
        "columns": ROBOROCK_ROBOT_COLUMNS,
        "time_column": "last_seen_at",
    },
    "renhold_status": {
        "table": "roborock_status_samples",
        "title": "Roborock status",
        "description": "Statusprøver fra robotene med batteri, tilstand, rengjøring og signal.",
        "columns": ROBOROCK_STATUS_COLUMNS,
        "time_column": "timestamp",
    },
    "renhold_telemetry": {
        "table": "roborock_telemetry_samples",
        "title": "Roborock telemetri",
        "description": "Minuttverdier for robot, lading, dokk, vann, støvpose, vask, tørking og nettverk.",
        "columns": ROBOROCK_TELEMETRY_COLUMNS,
        "time_column": "timestamp",
    },
    "renhold_telemetry_events": {
        "table": "roborock_telemetry_events",
        "title": "Roborock telemetrihendelser",
        "description": "Tilstandsendringer for lading, dokk, vann, støvpose, vask og tørking.",
        "columns": ROBOROCK_TELEMETRY_EVENT_COLUMNS,
        "time_column": "timestamp",
    },
    "renhold_jobs": {
        "table": "roborock_clean_jobs",
        "title": "Roborock jobber",
        "description": "Historiske rengjøringsjobber med tid, areal, varighet og sluttstatus.",
        "columns": ROBOROCK_JOB_COLUMNS,
        "time_column": "begin_at",
    },
    "generic_events": {
        "table": "event_data",
        "title": "Generelle logghendelser",
        "description": "Eldre og generelle loggposter fra HC3 og scripts.",
        "columns": GENERIC_COLUMNS,
        "time_column": "timestamp",
    },
    "door_events": {
        "table": "door_events",
        "title": "Dørhendelser fra HC3",
        "description": "Åpne/lukke-hendelser fra magnetfølere i HC3.",
        "columns": DOOR_EVENT_COLUMNS,
        "time_column": "timestamp",
    },
}
