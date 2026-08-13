CREATE TABLE IF NOT EXISTS roborock_command_runs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR NOT NULL UNIQUE,
    robot_duid VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    requested_at TIMESTAMP,
    finished_at TIMESTAMP,
    requested_by VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'running',
    message TEXT,
    before_state JSON,
    after_state JSON,
    result JSON
);

CREATE INDEX IF NOT EXISTS ix_roborock_command_runs_request_id
ON roborock_command_runs (request_id);

CREATE INDEX IF NOT EXISTS ix_roborock_command_runs_robot_duid
ON roborock_command_runs (robot_duid);

CREATE INDEX IF NOT EXISTS ix_roborock_command_runs_action
ON roborock_command_runs (action);

CREATE INDEX IF NOT EXISTS ix_roborock_command_runs_requested_at
ON roborock_command_runs (requested_at DESC);

CREATE INDEX IF NOT EXISTS ix_roborock_command_runs_status
ON roborock_command_runs (status);

CREATE INDEX IF NOT EXISTS ix_roborock_command_runs_robot_requested
ON roborock_command_runs (robot_duid, requested_at DESC);
