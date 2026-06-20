-- ============================================================================
-- Target (CONFORMED) layer schema
-- ----------------------------------------------------------------------------
-- Clean, typed, deduplicated tables with constraints and referential
-- integrity. This is the "single source of truth" that downstream consumers
-- (BI, analytics, the modernized cloud platform) read from.
-- ============================================================================

DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_customers;
DROP TABLE IF EXISTS dim_products;

CREATE TABLE dim_customers (
    customer_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id    TEXT NOT NULL UNIQUE,
    first_name     TEXT,
    last_name      TEXT,
    email          TEXT,
    phone          TEXT,
    country        TEXT,             -- standardized ISO-style country name
    signup_date    TEXT,             -- ISO 8601 (YYYY-MM-DD)
    segment        TEXT,             -- Enterprise | SMB | Consumer
    credit_limit   REAL,
    _loaded_at     TEXT
);

CREATE TABLE dim_products (
    product_key    INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id     TEXT NOT NULL UNIQUE,
    product_name   TEXT,
    category       TEXT,
    unit_price     REAL,
    currency       TEXT,             -- ISO 4217 (USD, EUR, GBP)
    active         INTEGER,          -- 1 = active, 0 = inactive
    launch_date    TEXT,
    _loaded_at     TEXT
);

CREATE TABLE fact_orders (
    order_key      INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id       TEXT NOT NULL,
    customer_id    TEXT NOT NULL,
    product_id     TEXT NOT NULL,
    order_date     TEXT,             -- ISO 8601
    quantity       INTEGER,
    unit_price     REAL,
    discount_pct   REAL,
    gross_amount   REAL,             -- quantity * unit_price
    net_amount     REAL,             -- gross_amount * (1 - discount_pct/100)
    status         TEXT,             -- standardized status code
    _loaded_at     TEXT
    -- NOTE: referential integrity is intentionally NOT enforced as a hard FK
    -- constraint here. In a migration you must be able to LAND orphan records
    -- in order to detect, report, and remediate them (rules O-FK-01/02) rather
    -- than have the load silently fail. The orphan check in the reconciliation
    -- report is the control that surfaces these.
);

-- ----------------------------------------------------------------------------
-- Operational control / audit tables
-- ----------------------------------------------------------------------------

DROP TABLE IF EXISTS exceptions;
CREATE TABLE exceptions (
    exception_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT,
    entity         TEXT,             -- customers | products | orders
    natural_key    TEXT,             -- source business key of the bad record
    source_row     INTEGER,
    rule_id        TEXT,             -- references validation_rules.csv
    severity       TEXT,             -- ERROR | WARN
    field          TEXT,
    bad_value      TEXT,
    message        TEXT,
    detected_at    TEXT
);

DROP TABLE IF EXISTS run_log;
CREATE TABLE run_log (
    run_id         TEXT,
    step           TEXT,
    entity         TEXT,
    metric         TEXT,
    value          REAL,
    logged_at      TEXT
);
