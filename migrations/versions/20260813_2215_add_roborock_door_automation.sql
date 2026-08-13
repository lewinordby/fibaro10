CREATE TABLE IF NOT EXISTS roborock_door_automations (
    id SERIAL PRIMARY KEY,
    robot_duid VARCHAR NOT NULL UNIQUE,
    door_device_id INTEGER NOT NULL DEFAULT 541,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    opening_threshold INTEGER NOT NULL DEFAULT 10,
    quiet_minutes INTEGER NOT NULL DEFAULT 60,
    zone_numbers JSON NOT NULL DEFAULT '[]',
    profile_id INTEGER NOT NULL REFERENCES roborock_cleaning_profiles(id),
    counter_reset_at TIMESTAMP,
    last_attempt_at TIMESTAMP,
    last_started_at TIMESTAMP,
    last_request_id VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'disabled',
    last_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_roborock_door_automations_robot
ON roborock_door_automations (robot_duid);

CREATE INDEX IF NOT EXISTS ix_roborock_door_automations_enabled
ON roborock_door_automations (enabled);

CREATE INDEX IF NOT EXISTS ix_roborock_door_automations_status
ON roborock_door_automations (status);
