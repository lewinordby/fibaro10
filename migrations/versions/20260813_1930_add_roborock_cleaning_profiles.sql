CREATE TABLE IF NOT EXISTS roborock_cleaning_profiles (
    id SERIAL PRIMARY KEY,
    slug VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    description TEXT,
    cleaning_type VARCHAR NOT NULL,
    fan_power INTEGER NOT NULL,
    water_box_mode INTEGER NOT NULL,
    mop_mode INTEGER NOT NULL,
    repeat INTEGER NOT NULL DEFAULT 1,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    builtin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_roborock_cleaning_profiles_slug
ON roborock_cleaning_profiles (slug);

CREATE INDEX IF NOT EXISTS ix_roborock_cleaning_profiles_name
ON roborock_cleaning_profiles (name);

CREATE INDEX IF NOT EXISTS ix_roborock_cleaning_profiles_type
ON roborock_cleaning_profiles (cleaning_type);

CREATE INDEX IF NOT EXISTS ix_roborock_cleaning_profiles_active
ON roborock_cleaning_profiles (active);

CREATE INDEX IF NOT EXISTS ix_roborock_cleaning_profiles_updated_at
ON roborock_cleaning_profiles (updated_at DESC);
