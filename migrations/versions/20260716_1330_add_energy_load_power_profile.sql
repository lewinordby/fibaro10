ALTER TABLE energy_loads
    ADD COLUMN IF NOT EXISTS power_profile VARCHAR,
    ADD COLUMN IF NOT EXISTS min_power_w DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS max_power_w DOUBLE PRECISION;

UPDATE energy_loads
SET power_profile = CASE
    WHEN expected_power_w IS NOT NULL THEN 'fixed'
    ELSE 'unknown'
END
WHERE power_profile IS NULL OR power_profile = '';

CREATE INDEX IF NOT EXISTS ix_energy_loads_power_profile
    ON energy_loads (power_profile);
