-- Migration: add-unifi-bollard-monitoring
-- Created: 2026-07-21 22:00:00
-- Notes:
--   Local calibration, state and evidence for monitoring the bollards outside
--   the sun studio with three fixed G6 Protect cameras.

CREATE TABLE IF NOT EXISTS unifi_protect_bollard_settings (
    console_key VARCHAR PRIMARY KEY,
    monitoring_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_interval_seconds INTEGER NOT NULL DEFAULT 10
        CHECK (analysis_interval_seconds BETWEEN 5 AND 300),
    confirmation_seconds INTEGER NOT NULL DEFAULT 30
        CHECK (confirmation_seconds BETWEEN 10 AND 1800),
    notification_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS unifi_protect_bollard_regions (
    region_id BIGSERIAL PRIMARY KEY,
    console_key VARCHAR NOT NULL,
    bollard_key VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    camera_id VARCHAR NOT NULL,
    camera_name VARCHAR,
    roi JSONB NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    baseline_path TEXT,
    baseline_captured_at TIMESTAMPTZ,
    match_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.42,
    movement_tolerance_pixels INTEGER NOT NULL DEFAULT 12,
    status VARCHAR NOT NULL DEFAULT 'uncalibrated',
    last_match_score DOUBLE PRECISION,
    last_expected_score DOUBLE PRECISION,
    last_offset_x INTEGER,
    last_offset_y INTEGER,
    consecutive_abnormal INTEGER NOT NULL DEFAULT 0,
    abnormal_since TIMESTAMPTZ,
    last_checked_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (console_key, bollard_key, camera_id)
);

CREATE TABLE IF NOT EXISTS unifi_protect_bollard_incidents (
    incident_id BIGSERIAL PRIMARY KEY,
    console_key VARCHAR NOT NULL,
    bollard_key VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'active',
    severity VARCHAR NOT NULL DEFAULT 'alarm',
    detected_at TIMESTAMPTZ NOT NULL,
    confirmed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ NOT NULL,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR,
    resolved_at TIMESTAMPTZ,
    resolution_reason VARCHAR,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    notification_status VARCHAR NOT NULL DEFAULT 'pending',
    notification_at TIMESTAMPTZ,
    notification_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_bollard_regions_camera
    ON unifi_protect_bollard_regions (console_key, camera_id, enabled);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_bollard_incidents_status
    ON unifi_protect_bollard_incidents (console_key, status, detected_at DESC);
