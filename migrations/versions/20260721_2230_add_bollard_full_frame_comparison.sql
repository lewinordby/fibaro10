ALTER TABLE unifi_protect_bollard_settings
    ALTER COLUMN analysis_interval_seconds SET DEFAULT 300;

ALTER TABLE unifi_protect_bollard_settings
    ALTER COLUMN confirmation_seconds SET DEFAULT 300;

UPDATE unifi_protect_bollard_settings
SET analysis_interval_seconds = 300,
    confirmation_seconds = 300,
    monitoring_enabled = FALSE,
    updated_at = CURRENT_TIMESTAMP
WHERE analysis_interval_seconds <> 300
   OR confirmation_seconds <> 300;

CREATE TABLE IF NOT EXISTS unifi_protect_bollard_camera_monitors (
    console_key VARCHAR NOT NULL,
    camera_id VARCHAR NOT NULL,
    camera_name VARCHAR NOT NULL,
    baseline_path TEXT,
    baseline_captured_at TIMESTAMPTZ,
    latest_path TEXT,
    latest_captured_at TIMESTAMPTZ,
    overlay_path TEXT,
    status VARCHAR NOT NULL DEFAULT 'uncalibrated',
    change_score DOUBLE PRECISION,
    changed_fraction DOUBLE PRECISION,
    largest_change_fraction DOUBLE PRECISION,
    mean_difference DOUBLE PRECISION,
    change_components JSONB NOT NULL DEFAULT '[]'::jsonb,
    alignment JSONB NOT NULL DEFAULT '{}'::jsonb,
    consecutive_abnormal INTEGER NOT NULL DEFAULT 0,
    abnormal_since TIMESTAMPTZ,
    last_checked_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (console_key, camera_id)
);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_bollard_camera_monitors_status
    ON unifi_protect_bollard_camera_monitors (console_key, status, last_checked_at DESC);
