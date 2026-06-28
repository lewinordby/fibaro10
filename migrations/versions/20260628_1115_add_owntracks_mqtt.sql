CREATE TABLE IF NOT EXISTS owntracks_devices (
    id SERIAL PRIMARY KEY,
    topic VARCHAR NOT NULL UNIQUE,
    username VARCHAR,
    device VARCHAR,
    tracker_id VARCHAR,
    last_seen_at TIMESTAMP,
    last_received_at TIMESTAMP,
    last_message_type VARCHAR,
    last_event VARCHAR,
    last_lat DOUBLE PRECISION,
    last_lon DOUBLE PRECISION,
    last_accuracy_m DOUBLE PRECISION,
    last_battery_percent INTEGER,
    last_connection VARCHAR,
    last_regions JSON,
    last_raw JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS owntracks_locations (
    id SERIAL PRIMARY KEY,
    topic VARCHAR NOT NULL,
    username VARCHAR,
    device VARCHAR,
    tracker_id VARCHAR,
    message_type VARCHAR,
    event VARCHAR,
    timestamp TIMESTAMP,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    accuracy_m DOUBLE PRECISION,
    battery_percent INTEGER,
    connection VARCHAR,
    velocity_kmh DOUBLE PRECISION,
    altitude_m DOUBLE PRECISION,
    regions JSON,
    raw JSON
);

CREATE INDEX IF NOT EXISTS ix_owntracks_devices_topic ON owntracks_devices (topic);
CREATE INDEX IF NOT EXISTS ix_owntracks_devices_seen ON owntracks_devices (last_seen_at DESC);
CREATE INDEX IF NOT EXISTS ix_owntracks_locations_topic_time ON owntracks_locations (topic, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_owntracks_locations_received ON owntracks_locations (received_at DESC);
