ALTER TABLE sun2_tanning_session_images
    DROP CONSTRAINT IF EXISTS uq_sun2_session_image_session_id;

ALTER TABLE sun2_tanning_session_images
    ADD COLUMN IF NOT EXISTS offset_seconds INTEGER;

ALTER TABLE sun2_tanning_session_images
    ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE;

UPDATE sun2_tanning_session_images
SET offset_seconds = -5
WHERE offset_seconds IS NULL;

UPDATE sun2_tanning_session_images
SET is_primary = FALSE
WHERE is_primary IS NULL;

ALTER TABLE sun2_tanning_session_images
    ALTER COLUMN offset_seconds SET NOT NULL;

ALTER TABLE sun2_tanning_session_images
    ALTER COLUMN is_primary SET DEFAULT FALSE;

ALTER TABLE sun2_tanning_session_images
    ALTER COLUMN is_primary SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_sun2_session_images_session_offset_unique
    ON sun2_tanning_session_images (session_id, offset_seconds);

CREATE UNIQUE INDEX IF NOT EXISTS ix_sun2_session_images_one_primary
    ON sun2_tanning_session_images (session_id)
    WHERE is_primary;
