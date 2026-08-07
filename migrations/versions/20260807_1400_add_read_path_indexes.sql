CREATE INDEX IF NOT EXISTS ix_parkering_normalized_plate_start
    ON parkering (
        (regexp_replace(upper(COALESCE(car_license_number, '')), '[^A-Z0-9]', '', 'g')),
        start_time
    );

CREATE INDEX IF NOT EXISTS ix_kjoretoy_normalized_plate
    ON kjoretoy (
        (regexp_replace(upper(COALESCE(plate, '')), '[^A-Z0-9]', '', 'g'))
    );

CREATE INDEX IF NOT EXISTS ix_kjoretoy_nokkeldata_normalized_plate
    ON kjoretoy_nokkeldata (
        (regexp_replace(upper(COALESCE(plate, '')), '[^A-Z0-9]', '', 'g'))
    );

CREATE INDEX IF NOT EXISTS ix_forecast_snapshots_domain_created
    ON forecast_snapshots (domain, created_at DESC, id DESC);
