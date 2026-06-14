WITH ranked_images AS (
    SELECT
        image.id,
        ROW_NUMBER() OVER (
            PARTITION BY image.session_id
            ORDER BY
                CASE WHEN image.offset_seconds = -15 THEN 0 ELSE 1 END,
                ABS(image.offset_seconds + 15),
                image.captured_at ASC NULLS LAST,
                image.id ASC
        ) AS rank
    FROM sun2_tanning_session_images image
    WHERE NOT EXISTS (
        SELECT 1
        FROM sun2_tanning_session_images primary_image
        WHERE primary_image.session_id = image.session_id
          AND primary_image.is_primary
    )
)
UPDATE sun2_tanning_session_images image
SET is_primary = TRUE
FROM ranked_images
WHERE image.id = ranked_images.id
  AND ranked_images.rank = 1;
