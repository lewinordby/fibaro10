-- Migration: add-unifi-protect-events
-- Created: 2026-07-21 10:45:00
-- Notes:
--   Camera inventory and deduplicated events from the official local Protect WebSocket.

CREATE TABLE IF NOT EXISTS unifi_protect_cameras (
    console_key VARCHAR NOT NULL,
    camera_id VARCHAR NOT NULL,
    name VARCHAR,
    model_key VARCHAR,
    mac VARCHAR,
    state VARCHAR,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    raw JSONB NOT NULL,
    PRIMARY KEY (console_key, camera_id)
);

CREATE TABLE IF NOT EXISTS unifi_protect_events (
    console_key VARCHAR NOT NULL,
    source_event_id VARCHAR NOT NULL,
    message_type VARCHAR NOT NULL,
    event_type VARCHAR,
    model_key VARCHAR,
    camera_id VARCHAR,
    camera_name VARCHAR,
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    score DOUBLE PRECISION,
    first_received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_count INTEGER NOT NULL DEFAULT 1,
    raw JSONB NOT NULL,
    PRIMARY KEY (console_key, source_event_id)
);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_start
    ON unifi_protect_events (start_at DESC);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_camera_start
    ON unifi_protect_events (console_key, camera_id, start_at DESC);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_type_start
    ON unifi_protect_events (event_type, start_at DESC);
