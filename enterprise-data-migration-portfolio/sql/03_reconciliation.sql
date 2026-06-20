-- ============================================================================
-- Reconciliation queries
-- ----------------------------------------------------------------------------
-- These queries support row-count and financial reconciliation between the
-- staging (source-of-record) and target (conformed) layers. They are run by
-- src/06_reconcile.py but are kept here as documented, reusable SQL assets.
-- ============================================================================

-- Row counts by layer for each entity ---------------------------------------
-- Customers
SELECT 'customers' AS entity,
       (SELECT COUNT(*) FROM stg_customers) AS staging_rows,
       (SELECT COUNT(*) FROM dim_customers) AS target_rows;

-- Products
SELECT 'products' AS entity,
       (SELECT COUNT(*) FROM stg_products) AS staging_rows,
       (SELECT COUNT(*) FROM dim_products) AS target_rows;

-- Orders
SELECT 'orders' AS entity,
       (SELECT COUNT(*) FROM stg_orders) AS staging_rows,
       (SELECT COUNT(*) FROM fact_orders) AS target_rows;

-- Financial control total: net revenue of completed orders in target --------
SELECT ROUND(SUM(net_amount), 2) AS target_completed_net_revenue
FROM   fact_orders
WHERE  status = 'COMPLETED';

-- Orphan check: target orders whose customer is missing from dim_customers --
-- (should return zero rows after a clean run)
SELECT o.order_id, o.customer_id
FROM   fact_orders o
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id
WHERE  c.customer_id IS NULL;
