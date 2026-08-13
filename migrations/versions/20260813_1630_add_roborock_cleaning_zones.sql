CREATE TABLE IF NOT EXISTS cleaning_zones (
    id SERIAL PRIMARY KEY,
    zone_number INTEGER NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_cleaning_zones_zone_number
ON cleaning_zones (zone_number);

CREATE INDEX IF NOT EXISTS ix_cleaning_zones_updated_at
ON cleaning_zones (updated_at DESC);

CREATE TABLE IF NOT EXISTS roborock_cleaning_zone_mappings (
    id SERIAL PRIMARY KEY,
    robot_duid VARCHAR NOT NULL,
    zone_id INTEGER NOT NULL REFERENCES cleaning_zones(id),
    segment_id VARCHAR NOT NULL,
    source_schedule_id VARCHAR,
    source_cron VARCHAR,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    imported_by VARCHAR,
    CONSTRAINT uq_roborock_cleaning_zone_robot_zone UNIQUE (robot_duid, zone_id),
    CONSTRAINT uq_roborock_cleaning_zone_robot_segment UNIQUE (robot_duid, segment_id)
);

CREATE INDEX IF NOT EXISTS ix_roborock_cleaning_zone_mappings_robot_duid
ON roborock_cleaning_zone_mappings (robot_duid);

CREATE INDEX IF NOT EXISTS ix_roborock_cleaning_zone_mappings_zone_id
ON roborock_cleaning_zone_mappings (zone_id);

CREATE INDEX IF NOT EXISTS ix_roborock_cleaning_zone_mappings_imported_at
ON roborock_cleaning_zone_mappings (imported_at DESC);
