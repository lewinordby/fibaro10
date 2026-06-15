CREATE TABLE IF NOT EXISTS sun2_product_sales (
    id SERIAL PRIMARY KEY,
    source_sale_id VARCHAR NOT NULL,
    sold_at TIMESTAMP,
    stat_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,
    product_name VARCHAR,
    product_category VARCHAR,
    quantity DOUBLE PRECISION,
    unit_price_kr DOUBLE PRECISION,
    amount_inc_vat_kr DOUBLE PRECISION,
    amount_ex_vat_kr DOUBLE PRECISION,
    vat_kr DOUBLE PRECISION,
    payment_method VARCHAR,
    sun2_user_id VARCHAR,
    user_name VARCHAR,
    source VARCHAR,
    source_file VARCHAR,
    imported_at TIMESTAMP,
    raw JSON,
    CONSTRAINT uq_sun2_product_sale_source_id UNIQUE (source, source_sale_id)
);

CREATE INDEX IF NOT EXISTS ix_sun2_product_sales_stat
    ON sun2_product_sales (stat_date, sold_at DESC);

CREATE INDEX IF NOT EXISTS ix_sun2_product_sales_period
    ON sun2_product_sales (period_start, period_end);

CREATE INDEX IF NOT EXISTS ix_sun2_product_sales_product
    ON sun2_product_sales (product_name, stat_date);
