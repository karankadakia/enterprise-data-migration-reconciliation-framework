-- ============================================================================
-- Staging (RAW) layer schema
-- ----------------------------------------------------------------------------
-- The staging layer mirrors the source files as-is. Every column is TEXT so
-- that dirty / malformed values load without error and can be profiled and
-- cleansed downstream. This is the classic "land raw, transform later" (ELT)
-- pattern used in enterprise data migrations and cloud platforms.
-- ============================================================================

DROP TABLE IF EXISTS stg_customers;
CREATE TABLE stg_customers (
    customer_id   TEXT,
    first_name    TEXT,
    last_name     TEXT,
    email         TEXT,
    phone         TEXT,
    country       TEXT,
    signup_date   TEXT,
    segment       TEXT,
    credit_limit  TEXT,
    _source_file  TEXT,
    _source_row   INTEGER,
    _loaded_at    TEXT
);

DROP TABLE IF EXISTS stg_products;
CREATE TABLE stg_products (
    product_id    TEXT,
    product_name  TEXT,
    category      TEXT,
    unit_price    TEXT,
    currency      TEXT,
    active        TEXT,
    launch_date   TEXT,
    _source_file  TEXT,
    _source_row   INTEGER,
    _loaded_at    TEXT
);

DROP TABLE IF EXISTS stg_orders;
CREATE TABLE stg_orders (
    order_id      TEXT,
    customer_id   TEXT,
    product_id    TEXT,
    order_date    TEXT,
    quantity      TEXT,
    unit_price    TEXT,
    discount_pct  TEXT,
    status        TEXT,
    _source_file  TEXT,
    _source_row   INTEGER,
    _loaded_at    TEXT
);
