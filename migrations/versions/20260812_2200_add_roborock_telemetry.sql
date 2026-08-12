CREATE TABLE IF NOT EXISTS roborock_telemetry_samples (
    id SERIAL PRIMARY KEY,
    robot_duid VARCHAR NOT NULL,
    timestamp TIMESTAMP,
    source VARCHAR,
    state_code INTEGER,
    state_name VARCHAR,
    battery INTEGER,
    error_code INTEGER,
    in_cleaning BOOLEAN,
    in_returning BOOLEAN,
    clean_time_seconds INTEGER,
    clean_area_m2 DOUBLE PRECISION,
    clean_percent INTEGER,
    fan_power INTEGER,
    water_box_mode INTEGER,
    mop_mode INTEGER,
    charge_status INTEGER,
    is_charging BOOLEAN,
    dock_type INTEGER,
    dock_error_status INTEGER,
    dust_collection_status INTEGER,
    auto_dust_collection BOOLEAN,
    wash_status INTEGER,
    wash_phase INTEGER,
    wash_ready BOOLEAN,
    dry_status INTEGER,
    water_shortage_status INTEGER,
    water_box_status INTEGER,
    water_box_carriage_status INTEGER,
    clear_water_status INTEGER,
    clear_water_status_name VARCHAR,
    dirty_water_status INTEGER,
    dirty_water_status_name VARCHAR,
    dust_bag_status INTEGER,
    dust_bag_status_name VARCHAR,
    clean_fluid_status INTEGER,
    clean_fluid_status_name VARCHAR,
    water_box_filter_status INTEGER,
    dock_cool_fan_status INTEGER,
    local_ip VARCHAR,
    rssi INTEGER,
    dss INTEGER,
    rss INTEGER,
    raw JSON
);

CREATE TABLE IF NOT EXISTS roborock_telemetry_events (
    id SERIAL PRIMARY KEY,
    robot_duid VARCHAR NOT NULL,
    timestamp TIMESTAMP,
    category VARCHAR,
    field_name VARCHAR NOT NULL,
    title VARCHAR,
    previous_value VARCHAR,
    current_value VARCHAR,
    previous_label VARCHAR,
    current_label VARCHAR,
    severity VARCHAR,
    raw JSON
);

CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_samples_robot_duid
ON roborock_telemetry_samples (robot_duid);

CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_samples_timestamp
ON roborock_telemetry_samples (timestamp);

CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_robot_timestamp
ON roborock_telemetry_samples (robot_duid, timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_events_robot_duid
ON roborock_telemetry_events (robot_duid);

CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_events_timestamp
ON roborock_telemetry_events (timestamp);

CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_events_category
ON roborock_telemetry_events (category);

CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_events_field_name
ON roborock_telemetry_events (field_name);

CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_events_severity
ON roborock_telemetry_events (severity);

CREATE INDEX IF NOT EXISTS ix_roborock_telemetry_events_robot_timestamp
ON roborock_telemetry_events (robot_duid, timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_roborock_probes_robot_command_timestamp
ON roborock_probe_results (robot_duid, command, timestamp DESC);
