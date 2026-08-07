CREATE TABLE IF NOT EXISTS operational_incident_reviews (
    id SERIAL PRIMARY KEY,
    incident_key VARCHAR NOT NULL UNIQUE,
    status VARCHAR NOT NULL DEFAULT 'acknowledged',
    note TEXT NULL,
    reviewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_operational_incident_reviews_incident_key
    ON operational_incident_reviews (incident_key);
CREATE INDEX IF NOT EXISTS ix_operational_incident_reviews_status
    ON operational_incident_reviews (status);
CREATE INDEX IF NOT EXISTS ix_operational_incident_reviews_reviewed_at
    ON operational_incident_reviews (reviewed_at);
