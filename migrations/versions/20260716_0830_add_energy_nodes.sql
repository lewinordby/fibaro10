CREATE TABLE IF NOT EXISTS energy_nodes (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    circuit_no INTEGER,
    parent_node_id INTEGER,
    node_type VARCHAR,
    manufacturer VARCHAR,
    model VARCHAR,
    device_type VARCHAR,
    hc3_device_id INTEGER,
    hc3_power_device_id INTEGER,
    hc3_switch_device_id INTEGER,
    endpoint_key VARCHAR,
    has_meter BOOLEAN,
    has_switch BOOLEAN,
    area VARCHAR,
    active BOOLEAN DEFAULT TRUE,
    note TEXT,
    source VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_energy_node_parent FOREIGN KEY (parent_node_id) REFERENCES energy_nodes(id) ON DELETE SET NULL,
    CONSTRAINT uq_energy_node_circuit_power_endpoint UNIQUE (circuit_no, hc3_power_device_id, endpoint_key)
);

ALTER TABLE energy_loads ADD COLUMN IF NOT EXISTS energy_node_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_energy_load_energy_node'
    ) THEN
        ALTER TABLE energy_loads
            ADD CONSTRAINT fk_energy_load_energy_node
            FOREIGN KEY (energy_node_id) REFERENCES energy_nodes(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_energy_nodes_circuit_power ON energy_nodes (circuit_no, hc3_power_device_id);
CREATE INDEX IF NOT EXISTS ix_energy_nodes_parent ON energy_nodes (parent_node_id);
CREATE INDEX IF NOT EXISTS ix_energy_nodes_hc3 ON energy_nodes (hc3_device_id, hc3_power_device_id, hc3_switch_device_id);
CREATE INDEX IF NOT EXISTS ix_energy_loads_energy_node_id ON energy_loads (energy_node_id);
