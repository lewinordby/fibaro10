CREATE TABLE IF NOT EXISTS roborock_schedule_snapshots (
    id SERIAL PRIMARY KEY,
    robot_duid VARCHAR NOT NULL,
    captured_at TIMESTAMP NOT NULL,
    source VARCHAR,
    fingerprint VARCHAR NOT NULL,
    schedules JSON NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS ix_roborock_schedule_snapshots_robot_duid
ON roborock_schedule_snapshots (robot_duid);

CREATE INDEX IF NOT EXISTS ix_roborock_schedule_snapshots_captured_at
ON roborock_schedule_snapshots (captured_at);

CREATE INDEX IF NOT EXISTS ix_roborock_schedule_snapshots_history
ON roborock_schedule_snapshots (robot_duid, captured_at DESC);
