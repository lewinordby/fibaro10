"""Existing schema bootstrap preserved during core modularization."""

STARTUP_COLUMNS = {
    "utelys_events": [
        ("device_key", "VARCHAR"),
    ],
    "ventilasjon_events": [
        ("device_key", "VARCHAR"),
        ("humidity_1etg", "DOUBLE PRECISION"),
        ("humidity_2etg", "DOUBLE PRECISION"),
        ("humidity_vip", "DOUBLE PRECISION"),
        ("humidity_ute", "DOUBLE PRECISION"),
        ("humidity_yr", "DOUBLE PRECISION"),
        ("humidity_loft", "DOUBLE PRECISION"),
        ("temp_kjeller", "DOUBLE PRECISION"),
        ("humidity_kjeller", "DOUBLE PRECISION"),
        ("humidity_passiv", "DOUBLE PRECISION"),
        ("humidity_luftinntak", "DOUBLE PRECISION"),
        ("fan_avfukter", "BOOLEAN"),
    ],
    "event_data": [
        ("device_key", "VARCHAR"),
    ],
    "door_events": [
        ("event_type", "VARCHAR DEFAULT 'door_change'"),
        ("action", "VARCHAR"),
        ("device_key", "VARCHAR"),
        ("device_id", "INTEGER"),
        ("device_name", "VARCHAR"),
        ("source", "TEXT"),
        ("raw_value", "VARCHAR"),
        ("state", "BOOLEAN"),
        ("previous_state", "BOOLEAN"),
        ("battery_level", "DOUBLE PRECISION"),
        ("extra", "JSON"),
    ],
    "roborock_door_automations": [
        ("minimum_interval_minutes", "INTEGER NOT NULL DEFAULT 60"),
    ],
    "utelys_samples": [
        ("light_spot_glass_275", "BOOLEAN"),
        ("light_spot_glass_299", "BOOLEAN"),
        ("weather_symbol", "VARCHAR"),
        ("weather_text", "VARCHAR"),
    ],
    "ventilasjon_samples": [
        ("temp_ute_netatmo", "DOUBLE PRECISION"),
        ("temp_yr", "DOUBLE PRECISION"),
        ("humidity_1etg", "DOUBLE PRECISION"),
        ("humidity_2etg", "DOUBLE PRECISION"),
        ("humidity_vip", "DOUBLE PRECISION"),
        ("humidity_ute", "DOUBLE PRECISION"),
        ("humidity_yr", "DOUBLE PRECISION"),
        ("humidity_loft", "DOUBLE PRECISION"),
        ("temp_kjeller", "DOUBLE PRECISION"),
        ("humidity_kjeller", "DOUBLE PRECISION"),
        ("humidity_passiv", "DOUBLE PRECISION"),
        ("humidity_luftinntak", "DOUBLE PRECISION"),
        ("temp_min_inne", "DOUBLE PRECISION"),
        ("temp_avg_inne", "DOUBLE PRECISION"),
        ("temp_max_inne", "DOUBLE PRECISION"),
        ("estimated_sunbeds", "INTEGER"),
        ("afterrun_active", "BOOLEAN"),
        ("heat_need", "BOOLEAN"),
        ("cool_need", "BOOLEAN"),
        ("open_time", "BOOLEAN"),
        ("pre_cooling", "BOOLEAN"),
        ("exhaust_time_allowed", "BOOLEAN"),
        ("fan_avfukter", "BOOLEAN"),
    ],
    "access_keys": [
        ("key_plaintext", "VARCHAR"),
        ("role", "VARCHAR"),
        ("last_notified_at", "TIMESTAMP"),
    ],
    "site_visits": [
        ("source", "VARCHAR DEFAULT 'owntracks'"),
        ("source_visit_id", "VARCHAR"),
        ("location_key", "VARCHAR DEFAULT 'lilletorget'"),
        ("location_name", "VARCHAR DEFAULT 'Lilletorget'"),
        ("topic", "VARCHAR"),
        ("username", "VARCHAR"),
        ("device", "VARCHAR"),
        ("started_at", "TIMESTAMP"),
        ("ended_at", "TIMESTAMP"),
        ("duration_seconds", "INTEGER"),
        ("status", "VARCHAR DEFAULT 'open'"),
        ("confidence", "DOUBLE PRECISION"),
        ("enter_source", "VARCHAR"),
        ("leave_source", "VARCHAR"),
        ("notes", "TEXT"),
        ("raw", "JSON"),
        ("last_synced_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ],
    "maintenance_log_entries": [
        ("site_visit_id", "INTEGER"),
        ("target_type", "VARCHAR"),
        ("room_id", "VARCHAR"),
        ("target_name", "VARCHAR"),
        ("action_type", "VARCHAR"),
        ("priority", "VARCHAR"),
    ],
    "parking_sun_link_job_state": [
        ("enabled", "BOOLEAN DEFAULT FALSE"),
        ("generation", "INTEGER DEFAULT 1"),
        ("min_matches", "INTEGER DEFAULT 2"),
        ("max_minutes", "INTEGER DEFAULT 3"),
        ("recent_days", "INTEGER DEFAULT 0"),
        ("idle_sleep_seconds", "INTEGER DEFAULT 20"),
        ("status", "VARCHAR DEFAULT 'stoppet'"),
        ("status_text", "TEXT"),
        ("processed_count", "INTEGER DEFAULT 0"),
        ("matched_count", "INTEGER DEFAULT 0"),
        ("candidate_count", "INTEGER DEFAULT 0"),
        ("strong_candidate_count", "INTEGER DEFAULT 0"),
        ("checked_plate_count", "INTEGER DEFAULT 0"),
        ("last_processed_parking_id", "BIGINT"),
        ("last_processed_plate", "TEXT"),
        ("last_processed_at", "TIMESTAMP"),
        ("last_worker_seen_at", "TIMESTAMP"),
        ("last_started_at", "TIMESTAMP"),
        ("last_finished_at", "TIMESTAMP"),
        ("last_error", "TEXT"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("raw", "JSON"),
    ],
    "parking_sun_link_processed": [
        ("generation", "INTEGER"),
        ("parking_record_id", "BIGINT"),
        ("plate", "TEXT"),
        ("parking_start_at", "TIMESTAMP"),
        ("matches_found", "INTEGER DEFAULT 0"),
        ("checked_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ],
    "parking_sun_link_matches": [
        ("generation", "INTEGER"),
        ("plate", "TEXT"),
        ("sun2_id", "TEXT"),
        ("parking_record_id", "BIGINT"),
        ("parking_id", "BIGINT"),
        ("source_system", "TEXT"),
        ("parking_start_at", "TIMESTAMP"),
        ("sun_session_id", "INTEGER"),
        ("source_session_id", "VARCHAR"),
        ("sun_started_at", "TIMESTAMP"),
        ("room_id", "VARCHAR"),
        ("room", "VARCHAR"),
        ("user_name", "VARCHAR"),
        ("duration_minutes", "DOUBLE PRECISION"),
        ("paid_amount_kr", "DOUBLE PRECISION"),
        ("fee_inc_vat", "DOUBLE PRECISION"),
        ("delta_minutes", "DOUBLE PRECISION"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ],
    "parking_sun_link_candidates": [
        ("generation", "INTEGER"),
        ("plate", "TEXT"),
        ("sun2_id", "TEXT"),
        ("status", "VARCHAR DEFAULT 'Avventer'"),
        ("confidence", "DOUBLE PRECISION DEFAULT 0"),
        ("matches_count", "INTEGER DEFAULT 0"),
        ("parking_match_count", "INTEGER DEFAULT 0"),
        ("match_days_count", "INTEGER DEFAULT 0"),
        ("plate_candidate_count", "INTEGER DEFAULT 1"),
        ("sun2_candidate_count", "INTEGER DEFAULT 1"),
        ("competitor_matches_count", "INTEGER DEFAULT 0"),
        ("assessment", "TEXT"),
        ("first_match_at", "TIMESTAMP"),
        ("last_match_at", "TIMESTAMP"),
        ("avg_delta_minutes", "DOUBLE PRECISION"),
        ("navn", "TEXT"),
        ("omrade", "TEXT"),
        ("user_name", "VARCHAR"),
        ("parking_count", "BIGINT"),
        ("paid_total", "DOUBLE PRECISION"),
        ("matched_paid_total", "DOUBLE PRECISION"),
        ("note", "TEXT"),
        ("confirmed_at", "TIMESTAMP"),
        ("confirmed_by", "VARCHAR"),
        ("rejected_at", "TIMESTAMP"),
        ("rejected_by", "VARCHAR"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ],
    "yr_forecast_samples": [
        ("api_updated_at", "TIMESTAMP"),
        ("last_modified", "TIMESTAMP"),
        ("expires_at", "TIMESTAMP"),
        ("next_fetch_after", "TIMESTAMP"),
        ("age_seconds", "INTEGER"),
        ("wind_speed_of_gust", "DOUBLE PRECISION"),
        ("probability_of_precipitation_next_1h", "DOUBLE PRECISION"),
        ("probability_of_precipitation_next_6h", "DOUBLE PRECISION"),
        ("air_temperature_percentile_10", "DOUBLE PRECISION"),
        ("air_temperature_percentile_90", "DOUBLE PRECISION"),
        ("wind_speed_percentile_10", "DOUBLE PRECISION"),
        ("wind_speed_percentile_90", "DOUBLE PRECISION"),
        ("cloud_area_fraction_high", "DOUBLE PRECISION"),
        ("cloud_area_fraction_medium", "DOUBLE PRECISION"),
        ("cloud_area_fraction_low", "DOUBLE PRECISION"),
        ("ultraviolet_index_clear_sky", "DOUBLE PRECISION"),
        ("precipitation_next_1h_min", "DOUBLE PRECISION"),
        ("precipitation_next_1h_max", "DOUBLE PRECISION"),
        ("precipitation_next_6h_min", "DOUBLE PRECISION"),
        ("precipitation_next_6h_max", "DOUBLE PRECISION"),
        ("probability_of_precipitation_next_12h", "DOUBLE PRECISION"),
        ("probability_of_thunder_next_1h", "DOUBLE PRECISION"),
        ("air_temperature_min_next_6h", "DOUBLE PRECISION"),
        ("air_temperature_max_next_6h", "DOUBLE PRECISION"),
        ("symbol_confidence_next_12h", "VARCHAR"),
        ("raw", "JSON"),
    ],
    "roborock_robots": [
        ("serial_number", "VARCHAR"),
        ("last_map_at", "TIMESTAMP"),
        ("provider", "VARCHAR DEFAULT 'roborock'"),
        ("external_id", "VARCHAR"),
        ("integration_status", "VARCHAR DEFAULT 'active'"),
    ],
    "roborock_schedules": [
        ("deleted_at", "TIMESTAMP"),
    ],
    "kjoretoy": [
        ("navn", "TEXT"),
        ("omrade", "TEXT"),
        ("omrade_kilde", "TEXT"),
        ("omrade_oppdatert", "TIMESTAMP"),
        ("sun2_id", "TEXT"),
        ("notat", "TEXT"),
        ("car_info_fetched_at", "TIMESTAMP"),
        ("car_info_status", "INTEGER"),
        ("car_info_error", "TEXT"),
        ("car_info_url", "TEXT"),
        ("car_info_data", "JSON"),
    ],
    "sun2_room_daily_stats": [
        ("room_id", "VARCHAR"),
        ("room_key", "VARCHAR"),
        ("source_room_name", "VARCHAR"),
        ("sun2_bed_id", "VARCHAR"),
    ],
    "sun2_tanning_sessions": [
        ("room_id", "VARCHAR"),
        ("sun2_user_id", "VARCHAR"),
        ("sun2_center_id", "VARCHAR"),
        ("sun2_bed_id", "VARCHAR"),
        ("gender", "VARCHAR"),
        ("payment_method", "VARCHAR"),
    ],
    "sun2_tanning_session_images": [
        ("offset_seconds", "INTEGER"),
        ("is_primary", "BOOLEAN DEFAULT FALSE"),
    ],
    "sun2_members": [
        ("sun2_center_id", "VARCHAR"),
        ("name", "VARCHAR"),
        ("display_name", "VARCHAR"),
        ("initials", "VARCHAR"),
        ("age", "INTEGER"),
        ("email", "VARCHAR"),
        ("phone", "VARCHAR"),
        ("profile_url", "TEXT"),
        ("customer_type", "VARCHAR"),
        ("gender", "VARCHAR"),
        ("birth_date", "DATE"),
        ("member_since", "DATE"),
        ("last_seen_at", "TIMESTAMP"),
        ("status", "VARCHAR"),
        ("balance_kr", "DOUBLE PRECISION"),
        ("total_spent_kr", "DOUBLE PRECISION"),
        ("visits_count", "INTEGER"),
        ("source", "VARCHAR"),
        ("source_file", "VARCHAR"),
        ("imported_at", "TIMESTAMP"),
        ("raw", "JSON"),
    ],
    "energy_fibaro_samples": [
        ("differanse_beregnet_w", "DOUBLE PRECISION"),
        ("differanse_beregnet_kwh", "DOUBLE PRECISION"),
        ("differanse_beregnet_delta_kwh", "DOUBLE PRECISION"),
        ("inntak_reset", "BOOLEAN"),
        ("varmepumper_reset", "BOOLEAN"),
        ("belysning_reset", "BOOLEAN"),
        ("massasje_reset", "BOOLEAN"),
        ("annet_reset", "BOOLEAN"),
        ("avfukter_w", "DOUBLE PRECISION"),
        ("avfukter_kwh", "DOUBLE PRECISION"),
        ("avfukter_delta_kwh", "DOUBLE PRECISION"),
        ("avfukter_reset", "BOOLEAN"),
        ("differanse_fibaro_reset", "BOOLEAN"),
    ],
    "energy_circuits": [
        ("is_sunbed", "BOOLEAN"),
    ],
    "energy_loads": [
        ("energy_node_id", "INTEGER"),
        ("power_profile", "VARCHAR"),
        ("min_power_w", "DOUBLE PRECISION"),
        ("max_power_w", "DOUBLE PRECISION"),
    ],
    "energy_nodes": [
        ("parent_node_id", "INTEGER"),
        ("node_type", "VARCHAR"),
        ("manufacturer", "VARCHAR"),
        ("model", "VARCHAR"),
        ("device_type", "VARCHAR"),
        ("hc3_device_id", "INTEGER"),
        ("hc3_power_device_id", "INTEGER"),
        ("hc3_energy_device_id", "INTEGER"),
        ("hc3_switch_device_id", "INTEGER"),
        ("aggregate_group_key", "VARCHAR"),
        ("endpoint_key", "VARCHAR"),
        ("has_meter", "BOOLEAN"),
        ("has_switch", "BOOLEAN"),
    ],
}

PERFORMANCE_INDEXES = [
    (
        "ix_access_logs_retention",
        "CREATE INDEX IF NOT EXISTS ix_access_logs_retention "
        "ON access_logs (success, timestamp)",
    ),
    (
        "ix_import_job_runs_retention",
        "CREATE INDEX IF NOT EXISTS ix_import_job_runs_retention "
        "ON import_job_runs (ok, finished_at)",
    ),
    (
        "ix_notification_outbox_retention",
        "CREATE INDEX IF NOT EXISTS ix_notification_outbox_retention "
        "ON notification_outbox (status, sent_at)",
    ),
    (
        "ix_auth_sessions_retention",
        "CREATE INDEX IF NOT EXISTS ix_auth_sessions_retention "
        "ON auth_sessions (expires_at, revoked_at)",
    ),
    (
        "ix_energy_loads_power_profile",
        "CREATE INDEX IF NOT EXISTS ix_energy_loads_power_profile "
        "ON energy_loads (power_profile)",
    ),
    (
        "ix_energy_loads_energy_node_id",
        "CREATE INDEX IF NOT EXISTS ix_energy_loads_energy_node_id "
        "ON energy_loads (energy_node_id)",
    ),
    (
        "ix_energy_nodes_circuit_power",
        "CREATE INDEX IF NOT EXISTS ix_energy_nodes_circuit_power "
        "ON energy_nodes (circuit_no, hc3_power_device_id)",
    ),
    (
        "ix_energy_nodes_parent",
        "CREATE INDEX IF NOT EXISTS ix_energy_nodes_parent "
        "ON energy_nodes (parent_node_id)",
    ),
    (
        "ix_energy_nodes_hc3",
        "CREATE INDEX IF NOT EXISTS ix_energy_nodes_hc3 "
        "ON energy_nodes (hc3_device_id, hc3_power_device_id, hc3_switch_device_id)",
    ),
    (
        "ix_energy_nodes_energy",
        "CREATE INDEX IF NOT EXISTS ix_energy_nodes_energy "
        "ON energy_nodes (hc3_energy_device_id)",
    ),
    (
        "ix_energy_nodes_aggregate_group",
        "CREATE INDEX IF NOT EXISTS ix_energy_nodes_aggregate_group "
        "ON energy_nodes (aggregate_group_key, circuit_no)",
    ),
    (
        "ix_sun2_sessions_stat_started",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_stat_started "
        "ON sun2_tanning_sessions (stat_date, started_at DESC)",
    ),
    (
        "ix_sun2_sessions_room_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_room_stat "
        "ON sun2_tanning_sessions (room_id, stat_date)",
    ),
    (
        "ix_sun2_sessions_user_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_user_stat "
        "ON sun2_tanning_sessions (sun2_user_id, stat_date)",
    ),
    (
        "ix_sun2_sessions_payment_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_payment_stat "
        "ON sun2_tanning_sessions (payment_method, stat_date)",
    ),
    (
        "ix_sun2_sessions_status_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_status_stat "
        "ON sun2_tanning_sessions (status, stat_date)",
    ),
    (
        "ix_sun2_sessions_customer_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_customer_stat "
        "ON sun2_tanning_sessions (customer_type, stat_date)",
    ),
    (
        "ix_sun2_session_images_session_created",
        "CREATE INDEX IF NOT EXISTS ix_sun2_session_images_session_created "
        "ON sun2_tanning_session_images (session_id, created_at DESC)",
    ),
    (
        "ix_sun2_session_images_captured",
        "CREATE INDEX IF NOT EXISTS ix_sun2_session_images_captured "
        "ON sun2_tanning_session_images (captured_at DESC)",
    ),
    (
        "ix_sun2_session_images_session_offset_unique",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_sun2_session_images_session_offset_unique "
        "ON sun2_tanning_session_images (session_id, offset_seconds)",
    ),
    (
        "ix_sun2_session_images_one_primary",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_sun2_session_images_one_primary "
        "ON sun2_tanning_session_images (session_id) WHERE is_primary",
    ),
    (
        "ix_sun2_members_name",
        "CREATE INDEX IF NOT EXISTS ix_sun2_members_name "
        "ON sun2_members (name)",
    ),
    (
        "ix_sun2_members_display_name",
        "CREATE INDEX IF NOT EXISTS ix_sun2_members_display_name "
        "ON sun2_members (display_name)",
    ),
    (
        "ix_sun2_members_status_type",
        "CREATE INDEX IF NOT EXISTS ix_sun2_members_status_type "
        "ON sun2_members (status, customer_type)",
    ),
    (
        "ix_sun2_product_sales_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_product_sales_stat "
        "ON sun2_product_sales (stat_date, sold_at DESC)",
    ),
    (
        "ix_sun2_product_sales_period",
        "CREATE INDEX IF NOT EXISTS ix_sun2_product_sales_period "
        "ON sun2_product_sales (period_start, period_end)",
    ),
    (
        "ix_sun2_product_sales_product",
        "CREATE INDEX IF NOT EXISTS ix_sun2_product_sales_product "
        "ON sun2_product_sales (product_name, stat_date)",
    ),
    (
        "ix_sun2_finance_period",
        "CREATE INDEX IF NOT EXISTS ix_sun2_finance_period "
        "ON sun2_finance_settlements (period_start, period_end)",
    ),
    (
        "ix_sun2_finance_imported",
        "CREATE INDEX IF NOT EXISTS ix_sun2_finance_imported "
        "ON sun2_finance_settlements (imported_at DESC)",
    ),
    (
        "ix_sun2_room_daily_date_room",
        "CREATE INDEX IF NOT EXISTS ix_sun2_room_daily_date_room "
        "ON sun2_room_daily_stats (stat_date, room_id)",
    ),
    (
        "ix_energy_hourly_year_month",
        "CREATE INDEX IF NOT EXISTS ix_energy_hourly_year_month "
        "ON energy_hourly_consumption (year, month)",
    ),
    (
        "ix_energy_hourly_date_meter",
        "CREATE INDEX IF NOT EXISTS ix_energy_hourly_date_meter "
        "ON energy_hourly_consumption (stat_date, meter_id)",
    ),
    (
        "ix_energy_fibaro_bucket",
        "CREATE INDEX IF NOT EXISTS ix_energy_fibaro_bucket "
        "ON energy_fibaro_samples (bucket_start DESC)",
    ),
    (
        "ix_energy_fibaro_timestamp",
        "CREATE INDEX IF NOT EXISTS ix_energy_fibaro_timestamp "
        "ON energy_fibaro_samples (timestamp DESC)",
    ),
    (
        "ix_vent_samples_bucket_mode",
        "CREATE INDEX IF NOT EXISTS ix_vent_samples_bucket_mode "
        "ON ventilasjon_samples (bucket_start, mode)",
    ),
    (
        "ix_light_samples_bucket_mode",
        "CREATE INDEX IF NOT EXISTS ix_light_samples_bucket_mode "
        "ON utelys_samples (bucket_start, mode)",
    ),
    (
        "ix_door_events_device_timestamp",
        "CREATE INDEX IF NOT EXISTS ix_door_events_device_timestamp "
        "ON door_events (device_id, timestamp DESC)",
    ),
    (
        "ix_door_events_action_timestamp",
        "CREATE INDEX IF NOT EXISTS ix_door_events_action_timestamp "
        "ON door_events (action, timestamp DESC)",
    ),
    (
        "ix_import_runs_job_finished",
        "CREATE INDEX IF NOT EXISTS ix_import_runs_job_finished "
        "ON import_job_runs (job_name, finished_at DESC)",
    ),
    (
        "ix_roborock_telemetry_robot_timestamp",
        "CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_robot_timestamp "
        "ON roborock_telemetry_samples (robot_duid, timestamp DESC)",
    ),
    (
        "ix_roborock_telemetry_events_robot_timestamp",
        "CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_events_robot_timestamp "
        "ON roborock_telemetry_events (robot_duid, timestamp DESC)",
    ),
    (
        "ix_roborock_probes_robot_command_timestamp",
        "CREATE INDEX IF NOT EXISTS ix_roborock_probes_robot_command_timestamp "
        "ON roborock_probe_results (robot_duid, command, timestamp DESC)",
    ),
    (
        "ix_roborock_schedules_current",
        "CREATE INDEX IF NOT EXISTS ix_roborock_schedules_current "
        "ON roborock_schedules (robot_duid, deleted_at, enabled)",
    ),
    (
        "ix_roborock_schedule_snapshots_history",
        "CREATE INDEX IF NOT EXISTS ix_roborock_schedule_snapshots_history "
        "ON roborock_schedule_snapshots (robot_duid, captured_at DESC)",
    ),
    (
        "ix_parkering_plate_start",
        "CREATE INDEX IF NOT EXISTS ix_parkering_plate_start "
        "ON parkering (upper(car_license_number), start_time DESC)",
    ),
    (
        "ix_parkering_compact_plate_start",
        "CREATE INDEX IF NOT EXISTS ix_parkering_compact_plate_start "
        "ON parkering (upper(replace(car_license_number, ' ', '')), start_time DESC)",
    ),
    (
        "ix_parkering_start_status",
        "CREATE INDEX IF NOT EXISTS ix_parkering_start_status "
        "ON parkering (start_time DESC, status)",
    ),
    (
        "ix_kjoretoy_last_seen_plate",
        "CREATE INDEX IF NOT EXISTS ix_kjoretoy_last_seen_plate "
        "ON kjoretoy (last_seen DESC, plate)",
    ),
    (
        "ix_kjoretoy_merke_modell",
        "CREATE INDEX IF NOT EXISTS ix_kjoretoy_merke_modell "
        "ON kjoretoy_nokkeldata (merke, modell)",
    ),
    (
        "ix_kjoretoy_sun2_id",
        "CREATE INDEX IF NOT EXISTS ix_kjoretoy_sun2_id "
        "ON kjoretoy (sun2_id)",
    ),
    (
        "ux_parking_sun_link_processed_generation_parking",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_parking_sun_link_processed_generation_parking "
        "ON parking_sun_link_processed (generation, parking_record_id)",
    ),
    (
        "ux_parking_sun_link_match_pair",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_parking_sun_link_match_pair "
        "ON parking_sun_link_matches (generation, parking_record_id, sun_session_id)",
    ),
    (
        "ux_parking_sun_link_candidate_pair",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_parking_sun_link_candidate_pair "
        "ON parking_sun_link_candidates (generation, plate, sun2_id)",
    ),
    (
        "ix_parking_sun_link_candidates_list",
        "CREATE INDEX IF NOT EXISTS ix_parking_sun_link_candidates_list "
        "ON parking_sun_link_candidates (generation, status, confidence DESC, matches_count DESC, last_match_at DESC)",
    ),
    (
        "ix_parking_sun_link_matches_list",
        "CREATE INDEX IF NOT EXISTS ix_parking_sun_link_matches_list "
        "ON parking_sun_link_matches (generation, parking_start_at DESC, sun_started_at DESC)",
    ),
    (
        "ix_parking_sun_link_processed_checked",
        "CREATE INDEX IF NOT EXISTS ix_parking_sun_link_processed_checked "
        "ON parking_sun_link_processed (generation, checked_at DESC)",
    ),
    (
        "ux_site_visits_source_visit",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_site_visits_source_visit "
        "ON site_visits (source, source_visit_id)",
    ),
    (
        "ix_site_visits_location_started",
        "CREATE INDEX IF NOT EXISTS ix_site_visits_location_started "
        "ON site_visits (location_key, started_at DESC)",
    ),
    (
        "ix_site_visits_status_started",
        "CREATE INDEX IF NOT EXISTS ix_site_visits_status_started "
        "ON site_visits (status, started_at DESC)",
    ),
    (
        "ix_maintenance_log_entries_site_visit_id",
        "CREATE INDEX IF NOT EXISTS ix_maintenance_log_entries_site_visit_id "
        "ON maintenance_log_entries (site_visit_id)",
    ),
]
