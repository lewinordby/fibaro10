-- Migration: add-unifi-recognition-snapshots
-- Created: 2026-07-21 20:30:00
-- Notes:
--   Store a dedicated, timestamped camera image for every Protect recognition.
--   Historical event snapshots are intentionally not reused as OCR evidence.

ALTER TABLE unifi_protect_recognitions
    ADD COLUMN IF NOT EXISTS snapshot_status VARCHAR NOT NULL DEFAULT 'not_requested';
ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_path TEXT;
ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_content_type VARCHAR;
ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_size_bytes BIGINT;
ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_captured_at TIMESTAMPTZ;
ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_target_at TIMESTAMPTZ;
ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_time_offset_ms INTEGER;
ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_source VARCHAR;
ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_camera_id VARCHAR;
ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_error TEXT;
ALTER TABLE unifi_protect_recognitions
    ADD COLUMN IF NOT EXISTS snapshot_attempt_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS ix_unifi_protect_recognitions_snapshot_status
    ON unifi_protect_recognitions (console_key, snapshot_status, occurred_at DESC);

