CREATE TABLE IF NOT EXISTS sun2_finance_settlements (
    id SERIAL PRIMARY KEY,
    source_payout_id VARCHAR NOT NULL,
    payout_label VARCHAR,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    payout_date DATE,
    member_tanning_count INTEGER,
    member_tanning_inc_vat_kr DOUBLE PRECISION,
    unregistered_tanning_count INTEGER,
    unregistered_tanning_inc_vat_kr DOUBLE PRECISION,
    tanning_bonus_inc_vat_kr DOUBLE PRECISION,
    tanning_control_inc_vat_kr DOUBLE PRECISION,
    tanning_control_ex_vat_kr DOUBLE PRECISION,
    member_product_count INTEGER,
    member_product_inc_vat_kr DOUBLE PRECISION,
    unregistered_product_count INTEGER,
    unregistered_product_inc_vat_kr DOUBLE PRECISION,
    product_bonus_inc_vat_kr DOUBLE PRECISION,
    product_control_inc_vat_kr DOUBLE PRECISION,
    product_control_ex_vat_kr DOUBLE PRECISION,
    transaction_cost_kr DOUBLE PRECISION,
    service_fee_kr DOUBLE PRECISION,
    payout_inc_vat_kr DOUBLE PRECISION,
    vat_kr DOUBLE PRECISION,
    source VARCHAR,
    source_file VARCHAR,
    imported_at TIMESTAMP,
    raw JSON,
    CONSTRAINT uq_sun2_finance_settlement_source_id UNIQUE (source, source_payout_id)
);

CREATE INDEX IF NOT EXISTS ix_sun2_finance_period
    ON sun2_finance_settlements (period_start, period_end);

CREATE INDEX IF NOT EXISTS ix_sun2_finance_imported
    ON sun2_finance_settlements (imported_at DESC);
