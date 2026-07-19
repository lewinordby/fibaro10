-- Migration: add-alarm-events
-- Created: 2026-07-19 22:00:00
-- Notes:
--   Persistent audit trail for alarms, notifications, resolution and review.

CREATE TABLE IF NOT EXISTS alarm_events (
    id SERIAL PRIMARY KEY,
    event_key VARCHAR NOT NULL UNIQUE,
    domain VARCHAR NOT NULL DEFAULT 'doors',
    alarm_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'active',
    severity VARCHAR NOT NULL DEFAULT 'alert',
    outcome VARCHAR NOT NULL DEFAULT 'unreviewed',
    title VARCHAR NOT NULL,
    detail TEXT,
    device_key VARCHAR,
    device_id INTEGER,
    room_id VARCHAR,
    display_room_number INTEGER,
    physical_room_number INTEGER,
    sun2_bed_id VARCHAR,
    source_session_id VARCHAR,
    door_changed_at TIMESTAMP,
    expected_exit_at TIMESTAMP,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_reason VARCHAR,
    notification_status VARCHAR NOT NULL DEFAULT 'pending',
    notification_count INTEGER NOT NULL DEFAULT 0,
    first_notification_at TIMESTAMP,
    last_notification_at TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR,
    review_note TEXT,
    source VARCHAR NOT NULL DEFAULT 'sunroom_door_monitor',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    raw JSON
);

CREATE INDEX IF NOT EXISTS ix_alarm_events_detected
    ON alarm_events (detected_at DESC);

CREATE INDEX IF NOT EXISTS ix_alarm_events_domain_status
    ON alarm_events (domain, status, detected_at DESC);

CREATE INDEX IF NOT EXISTS ix_alarm_events_room
    ON alarm_events (room_id, detected_at DESC);

CREATE INDEX IF NOT EXISTS ix_alarm_events_notification
    ON alarm_events (notification_status, last_notification_at DESC);
