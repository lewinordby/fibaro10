CREATE TABLE IF NOT EXISTS asset_registry_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    category VARCHAR NOT NULL DEFAULT 'Annet',
    location VARCHAR NULL,
    manufacturer VARCHAR NULL,
    model VARCHAR NULL,
    serial_no VARCHAR NULL,
    hc3_device_id INTEGER NULL,
    owner_app VARCHAR NULL,
    status VARCHAR NOT NULL DEFAULT 'I drift',
    installed_at DATE NULL,
    warranty_until DATE NULL,
    service_interval_days INTEGER NULL,
    last_service_at DATE NULL,
    notes TEXT NULL,
    extra JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_asset_registry_items_name ON asset_registry_items (name);
CREATE INDEX IF NOT EXISTS ix_asset_registry_items_category ON asset_registry_items (category);
CREATE INDEX IF NOT EXISTS ix_asset_registry_items_location ON asset_registry_items (location);
CREATE INDEX IF NOT EXISTS ix_asset_registry_items_serial_no ON asset_registry_items (serial_no);
CREATE INDEX IF NOT EXISTS ix_asset_registry_items_hc3_device_id ON asset_registry_items (hc3_device_id);
CREATE INDEX IF NOT EXISTS ix_asset_registry_items_owner_app ON asset_registry_items (owner_app);
CREATE INDEX IF NOT EXISTS ix_asset_registry_items_status ON asset_registry_items (status);
CREATE INDEX IF NOT EXISTS ix_asset_registry_items_warranty_until ON asset_registry_items (warranty_until);
CREATE INDEX IF NOT EXISTS ix_asset_registry_items_updated_at ON asset_registry_items (updated_at);

CREATE TABLE IF NOT EXISTS automation_workbench_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    domain VARCHAR NOT NULL DEFAULT 'Drift',
    description TEXT NULL,
    trigger_type VARCHAR NOT NULL DEFAULT 'Hendelse',
    trigger_config JSON NULL,
    conditions JSON NULL,
    actions JSON NULL,
    mode VARCHAR NOT NULL DEFAULT 'Utkast',
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    cooldown_minutes INTEGER NOT NULL DEFAULT 0,
    last_evaluated_at TIMESTAMP NULL,
    last_triggered_at TIMESTAMP NULL,
    last_result TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_automation_workbench_rules_name ON automation_workbench_rules (name);
CREATE INDEX IF NOT EXISTS ix_automation_workbench_rules_domain ON automation_workbench_rules (domain);
CREATE INDEX IF NOT EXISTS ix_automation_workbench_rules_trigger_type ON automation_workbench_rules (trigger_type);
CREATE INDEX IF NOT EXISTS ix_automation_workbench_rules_mode ON automation_workbench_rules (mode);
CREATE INDEX IF NOT EXISTS ix_automation_workbench_rules_enabled ON automation_workbench_rules (enabled);
CREATE INDEX IF NOT EXISTS ix_automation_workbench_rules_updated_at ON automation_workbench_rules (updated_at);
