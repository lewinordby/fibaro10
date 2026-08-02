-- Migration: add-unifi-recognitions-api
-- Created: 2026-07-21 15:00:00
-- Notes:
--   Local Alarm Manager webhook ingestion, identity/plate recognition and cursor API indexes.

CREATE TABLE IF NOT EXISTS unifi_protect_alarm_webhooks (
    console_key VARCHAR NOT NULL,
    webhook_id VARCHAR NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    occurred_at TIMESTAMPTZ,
    alarm_name VARCHAR,
    source_event_id VARCHAR,
    source_device VARCHAR,
    recognition_count INTEGER NOT NULL DEFAULT 0,
    processing_status VARCHAR NOT NULL DEFAULT 'received',
    raw JSONB NOT NULL,
    PRIMARY KEY (console_key, webhook_id)
);

CREATE TABLE IF NOT EXISTS unifi_protect_recognitions (
    recognition_id BIGSERIAL PRIMARY KEY,
    console_key VARCHAR NOT NULL,
    webhook_id VARCHAR NOT NULL,
    trigger_index INTEGER NOT NULL,
    kind VARCHAR NOT NULL CHECK (kind IN ('license_plate', 'face', 'person_of_interest')),
    value TEXT,
    normalized_value TEXT,
    is_known BOOLEAN,
    trigger_key VARCHAR,
    camera_id VARCHAR,
    camera_name VARCHAR,
    source_device VARCHAR,
    source_event_id VARCHAR,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    correlation_status VARCHAR NOT NULL DEFAULT 'unmatched',
    raw JSONB NOT NULL,
    UNIQUE (console_key, webhook_id, trigger_index)
);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_cursor
    ON unifi_protect_events (
        console_key,
        (COALESCE(start_at, last_received_at)) DESC,
        source_event_id DESC
    );

CREATE INDEX IF NOT EXISTS ix_unifi_protect_recognitions_cursor
    ON unifi_protect_recognitions (console_key, occurred_at DESC, recognition_id DESC);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_recognitions_value
    ON unifi_protect_recognitions (console_key, kind, normalized_value, occurred_at DESC);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_recognitions_camera
    ON unifi_protect_recognitions (console_key, camera_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_alarm_webhooks_received
    ON unifi_protect_alarm_webhooks (console_key, received_at DESC);
