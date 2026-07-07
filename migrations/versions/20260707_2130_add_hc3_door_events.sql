-- Migration: add-hc3-door-events
-- Created: 2026-07-07 21:30:00
-- Notes:
--   Dedicated log table for HC3 magnet/contact sensor open/close events.

CREATE TABLE IF NOT EXISTS door_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR DEFAULT 'door_change',
    action VARCHAR NOT NULL,
    device_key VARCHAR,
    device_id INTEGER,
    device_name VARCHAR,
    source TEXT,
    raw_value VARCHAR,
    state BOOLEAN,
    previous_state BOOLEAN,
    battery_level DOUBLE PRECISION,
    extra JSON
);

CREATE INDEX IF NOT EXISTS ix_door_events_timestamp
    ON door_events (timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_door_events_device_timestamp
    ON door_events (device_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_door_events_action_timestamp
    ON door_events (action, timestamp DESC);
