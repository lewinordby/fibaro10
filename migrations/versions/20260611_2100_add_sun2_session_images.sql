CREATE TABLE IF NOT EXISTS sun2_tanning_session_images (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sun2_tanning_sessions(id) ON DELETE CASCADE,
    captured_at TIMESTAMP NOT NULL,
    target_at TIMESTAMP NOT NULL,
    delta_seconds DOUBLE PRECISION,
    source_path TEXT,
    source_mtime TIMESTAMP,
    content_type VARCHAR NOT NULL DEFAULT 'image/jpeg',
    image_bytes BYTEA NOT NULL,
    byte_size INTEGER,
    sha256 VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR DEFAULT 'axis_snapshot_backfill',
    CONSTRAINT uq_sun2_session_image_session_id UNIQUE (session_id)
);

CREATE INDEX IF NOT EXISTS ix_sun2_tanning_session_images_session_id
    ON sun2_tanning_session_images (session_id);

CREATE INDEX IF NOT EXISTS ix_sun2_session_images_session_created
    ON sun2_tanning_session_images (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_sun2_session_images_captured
    ON sun2_tanning_session_images (captured_at DESC);

CREATE INDEX IF NOT EXISTS ix_sun2_tanning_session_images_sha256
    ON sun2_tanning_session_images (sha256);
