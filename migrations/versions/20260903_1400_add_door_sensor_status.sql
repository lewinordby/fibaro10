CREATE TABLE IF NOT EXISTS door_sensor_status (
    device_id INTEGER PRIMARY KEY,
    device_key VARCHAR NULL,
    device_name VARCHAR NULL,
    state BOOLEAN NULL,
    raw_value VARCHAR NULL,
    battery_level DOUBLE PRECISION NULL,
    hc3_dead BOOLEAN NULL,
    hc3_enabled BOOLEAN NULL,
    observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_changed_at TIMESTAMP NULL,
    last_change_event_id INTEGER NULL,
    source VARCHAR NULL,
    extra JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_door_sensor_status_device_key ON door_sensor_status (device_key);
CREATE INDEX IF NOT EXISTS ix_door_sensor_status_state ON door_sensor_status (state);
CREATE INDEX IF NOT EXISTS ix_door_sensor_status_observed_at ON door_sensor_status (observed_at);
CREATE INDEX IF NOT EXISTS ix_door_sensor_status_last_changed_at ON door_sensor_status (last_changed_at);
CREATE INDEX IF NOT EXISTS ix_door_sensor_status_source ON door_sensor_status (source);
CREATE INDEX IF NOT EXISTS ix_door_sensor_status_created_at ON door_sensor_status (created_at);
CREATE INDEX IF NOT EXISTS ix_door_sensor_status_updated_at ON door_sensor_status (updated_at);

WITH ordered_events AS (
    SELECT
        id,
        timestamp,
        device_id,
        device_key,
        device_name,
        state,
        raw_value,
        battery_level,
        source,
        LAG(state) OVER (PARTITION BY device_id ORDER BY timestamp, id) AS prior_state
    FROM door_events
    WHERE device_id IS NOT NULL AND state IS NOT NULL
),
latest_events AS (
    SELECT DISTINCT ON (device_id) *
    FROM ordered_events
    ORDER BY device_id, timestamp DESC, id DESC
),
latest_changes AS (
    SELECT DISTINCT ON (device_id) *
    FROM ordered_events
    WHERE prior_state IS NULL OR prior_state IS DISTINCT FROM state
    ORDER BY device_id, timestamp DESC, id DESC
)
INSERT INTO door_sensor_status (
    device_id,
    device_key,
    device_name,
    state,
    raw_value,
    battery_level,
    observed_at,
    last_changed_at,
    last_change_event_id,
    source,
    extra,
    created_at,
    updated_at
)
SELECT
    current_event.device_id,
    current_event.device_key,
    current_event.device_name,
    current_event.state,
    current_event.raw_value,
    current_event.battery_level,
    current_event.timestamp,
    change_event.timestamp,
    change_event.id,
    current_event.source,
    '{"backfilled": true}'::json,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM latest_events AS current_event
LEFT JOIN latest_changes AS change_event ON change_event.device_id = current_event.device_id
ON CONFLICT (device_id) DO NOTHING;
