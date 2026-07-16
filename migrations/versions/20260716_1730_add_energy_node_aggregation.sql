ALTER TABLE energy_nodes
    ADD COLUMN IF NOT EXISTS hc3_energy_device_id INTEGER,
    ADD COLUMN IF NOT EXISTS aggregate_group_key VARCHAR;

-- Kurs 6: realtime 530, akkumulert 529, samlet under Annet.
UPDATE energy_nodes
SET hc3_energy_device_id = COALESCE(hc3_energy_device_id, 529),
    aggregate_group_key = COALESCE(aggregate_group_key, 'other'),
    updated_at = CURRENT_TIMESTAMP
WHERE hc3_power_device_id = 530;

-- Kurs 29 hadde tidligere akkumulert energimåler 398 registrert som wattkilde.
UPDATE energy_nodes
SET hc3_power_device_id = 399,
    hc3_energy_device_id = COALESCE(hc3_energy_device_id, 398),
    aggregate_group_key = COALESCE(aggregate_group_key, 'massage'),
    updated_at = CURRENT_TIMESTAMP
WHERE circuit_no = 29
  AND hc3_power_device_id = 398;

UPDATE energy_nodes
SET hc3_switch_device_id = NULL,
    has_switch = FALSE,
    name = REPLACE(name, 'HC3 398', 'HC3 399'),
    updated_at = CURRENT_TIMESTAMP
WHERE circuit_no = 29
  AND hc3_power_device_id = 399
  AND hc3_switch_device_id = 84;

UPDATE energy_nodes
SET aggregate_group_key = COALESCE(aggregate_group_key, CASE
        WHEN hc3_power_device_id IN (226, 230, 234) THEN 'heat_pumps'
        WHEN hc3_power_device_id IN (201, 208, 213, 275, 280, 286, 287, 292, 293, 299, 303, 207, 298, 143, 186, 424, 425, 440) THEN 'lighting'
        WHEN hc3_power_device_id IN (309, 314, 319, 324, 399) THEN 'massage'
        WHEN hc3_power_device_id IN (269, 247, 368, 373, 378, 405, 406, 160, 449, 530) THEN 'other'
        ELSE NULL
    END),
    hc3_energy_device_id = COALESCE(hc3_energy_device_id, CASE hc3_power_device_id
        WHEN 309 THEN 308 WHEN 314 THEN 313 WHEN 319 THEN 318 WHEN 324 THEN 323 WHEN 399 THEN 398
        WHEN 368 THEN 367 WHEN 373 THEN 372 WHEN 378 THEN 377 WHEN 530 THEN 529
        ELSE hc3_power_device_id
    END),
    updated_at = CURRENT_TIMESTAMP
WHERE (aggregate_group_key IS NULL OR hc3_energy_device_id IS NULL)
  AND hc3_power_device_id IN (
      226, 230, 234, 201, 208, 213, 275, 280, 286, 287, 292, 293, 299, 303, 207, 298, 143, 186, 424, 425, 440,
      309, 314, 319, 324, 399, 269, 247, 368, 373, 378, 405, 406, 160, 449, 530
  );

UPDATE energy_loads
SET fibaro_meter_id = 399,
    updated_at = CURRENT_TIMESTAMP
WHERE circuit_no = 29
  AND fibaro_meter_id = 398;

CREATE INDEX IF NOT EXISTS ix_energy_nodes_energy
    ON energy_nodes (hc3_energy_device_id);

CREATE INDEX IF NOT EXISTS ix_energy_nodes_aggregate_group
    ON energy_nodes (aggregate_group_key, circuit_no);
