-- Migration: add-unifi-plate-validations
-- Created: 2026-07-21 17:00:00
-- Notes:
--   Protect Ledger-owned Nordic plate validation cache and audit trail.

CREATE TABLE IF NOT EXISTS unifi_protect_plate_validations (
    console_key VARCHAR NOT NULL,
    plate TEXT NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    is_valid BOOLEAN,
    likely_misread BOOLEAN NOT NULL DEFAULT FALSE,
    country_code VARCHAR,
    source VARCHAR,
    vehicle_label TEXT,
    local_match BOOLEAN NOT NULL DEFAULT FALSE,
    sources JSONB NOT NULL DEFAULT '{}'::jsonb,
    error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    checked_at TIMESTAMPTZ,
    next_check_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (console_key, plate)
);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_plate_validations_due
    ON unifi_protect_plate_validations (console_key, next_check_at, status);

CREATE INDEX IF NOT EXISTS ix_unifi_protect_plate_validations_status
    ON unifi_protect_plate_validations (console_key, status, last_seen_at DESC);
