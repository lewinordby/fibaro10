-- Migration: add-unifi-event-policy-ui
-- Created: 2026-07-21 12:30:00
-- Notes:
--   Storage policy catalog, audit trail, detection metadata and filesystem snapshot metadata.

ALTER TABLE unifi_protect_cameras
    ADD COLUMN IF NOT EXISTS store_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE unifi_protect_cameras
    ADD COLUMN IF NOT EXISTS smart_detect_types TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE unifi_protect_cameras
    ADD COLUMN IF NOT EXISTS smart_detect_audio_types TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE unifi_protect_cameras
    ADD COLUMN IF NOT EXISTS observed_event_count BIGINT NOT NULL DEFAULT 0;
ALTER TABLE unifi_protect_cameras
    ADD COLUMN IF NOT EXISTS last_event_at TIMESTAMPTZ;
ALTER TABLE unifi_protect_cameras
    ADD COLUMN IF NOT EXISTS config_updated_at TIMESTAMPTZ;

ALTER TABLE unifi_protect_events
    ADD COLUMN IF NOT EXISTS smart_detect_types TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE unifi_protect_events
    ADD COLUMN IF NOT EXISTS duration_ms BIGINT;
ALTER TABLE unifi_protect_events
    ADD COLUMN IF NOT EXISTS snapshot_status VARCHAR NOT NULL DEFAULT 'not_requested';
ALTER TABLE unifi_protect_events
    ADD COLUMN IF NOT EXISTS snapshot_path TEXT;
ALTER TABLE unifi_protect_events
    ADD COLUMN IF NOT EXISTS snapshot_content_type VARCHAR;
ALTER TABLE unifi_protect_events
    ADD COLUMN IF NOT EXISTS snapshot_size_bytes BIGINT;
ALTER TABLE unifi_protect_events
    ADD COLUMN IF NOT EXISTS snapshot_captured_at TIMESTAMPTZ;
ALTER TABLE unifi_protect_events
    ADD COLUMN IF NOT EXISTS snapshot_error TEXT;
ALTER TABLE unifi_protect_events
    ADD COLUMN IF NOT EXISTS snapshot_attempt_count INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS unifi_protect_settings (
    console_key VARCHAR PRIMARY KEY,
    default_store_new_event_types BOOLEAN NOT NULL DEFAULT TRUE,
    retention_days INTEGER NOT NULL DEFAULT 365 CHECK (retention_days BETWEEN 1 AND 3650),
    catalog_sample_limit_bytes INTEGER NOT NULL DEFAULT 65536
        CHECK (catalog_sample_limit_bytes BETWEEN 1024 AND 1048576),
    snapshots_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    snapshot_high_quality BOOLEAN NOT NULL DEFAULT FALSE,
    snapshot_max_bytes INTEGER NOT NULL DEFAULT 12582912
        CHECK (snapshot_max_bytes BETWEEN 65536 AND 52428800),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE unifi_protect_settings
    ADD COLUMN IF NOT EXISTS snapshots_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE unifi_protect_settings
    ADD COLUMN IF NOT EXISTS snapshot_high_quality BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE unifi_protect_settings
    ADD COLUMN IF NOT EXISTS snapshot_max_bytes INTEGER NOT NULL DEFAULT 12582912;

CREATE TABLE IF NOT EXISTS unifi_protect_event_type_config (
    console_key VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    category VARCHAR NOT NULL DEFAULT 'Annet',
    description TEXT,
    store_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_observed BOOLEAN NOT NULL DEFAULT FALSE,
    observed_count BIGINT NOT NULL DEFAULT 0,
    stored_count BIGINT NOT NULL DEFAULT 0,
    ignored_count BIGINT NOT NULL DEFAULT 0,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    last_sample JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (console_key, event_type)
);

CREATE TABLE IF NOT EXISTS unifi_protect_detection_type_config (
    console_key VARCHAR NOT NULL,
    detection_type VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    category VARCHAR NOT NULL DEFAULT 'Annet',
    description TEXT,
    store_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    supported_camera_count INTEGER NOT NULL DEFAULT 0,
    is_observed BOOLEAN NOT NULL DEFAULT FALSE,
    observed_count BIGINT NOT NULL DEFAULT 0,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (console_key, detection_type)
);

CREATE TABLE IF NOT EXISTS unifi_protect_config_history (
    id BIGSERIAL PRIMARY KEY,
    console_key VARCHAR NOT NULL,
    target_kind VARCHAR NOT NULL,
    target_key VARCHAR NOT NULL,
    old_value JSONB,
    new_value JSONB NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_detection_types
    ON unifi_protect_events USING GIN (smart_detect_types);
CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_received
    ON unifi_protect_events (last_received_at DESC);
CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_snapshot_status
    ON unifi_protect_events (console_key, snapshot_status);
CREATE INDEX IF NOT EXISTS ix_unifi_protect_config_history_changed
    ON unifi_protect_config_history (console_key, changed_at DESC);
