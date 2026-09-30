-- ==========================================================================
-- 05_sample_analytics_queries.sql
-- Analytical queries demonstrating the star schema and table relationships
-- ==========================================================================
-- These queries show how the 4 tables connect and how analysts interact
-- with the Kimball star schema. Run these after loading data and building marts.
-- ==========================================================================

-- ---------------------------------------------------------------------------
-- Query 1: Total revenue by region (UK vs EU)
-- Uses: fct_orders (fact) — no dimension join needed (denormalised region)
-- ---------------------------------------------------------------------------
SELECT
    order_region,
    COUNT(*)                          AS total_orders,
    SUM(quantity)                     AS total_items_sold,
    SUM(gross_amount)                 AS gross_revenue,
    SUM(tax_amount)                   AS tax_collected,
    SUM(total_amount)                 AS total_revenue,
    ROUND(AVG(total_amount), 2)       AS avg_order_value
FROM fct_orders
GROUP BY order_region
ORDER BY order_region;

-- ---------------------------------------------------------------------------
-- Query 2: Revenue by product category and region
-- Uses: fct_orders (fact) — denormalised region enables RLS filtering
-- ---------------------------------------------------------------------------
SELECT
    product_category,
    order_region,
    COUNT(*)                          AS order_count,
    SUM(quantity)                     AS items_sold,
    SUM(total_amount)                 AS revenue,
    ROUND(AVG(total_amount), 2)       AS avg_order_value
FROM fct_orders
GROUP BY product_category, order_region
ORDER BY revenue DESC;

-- ---------------------------------------------------------------------------
-- Query 3: Customer spend analysis (star schema join)
-- Uses: fct_orders (fact) JOIN dim_customers (dimension)
-- Relationship: fct_orders.customer_key = dim_customers.customer_key
-- ---------------------------------------------------------------------------
SELECT
    dc.country,
    dc.region,
    COUNT(DISTINCT dc.customer_id)    AS unique_customers,
    COUNT(fo.order_id)                AS total_orders,
    SUM(fo.total_amount)              AS total_spend,
    ROUND(AVG(fo.total_amount), 2)    AS avg_spend_per_order,
    MAX(fo.total_amount)              AS largest_order
FROM dim_customers dc
INNER JOIN fct_orders fo ON dc.customer_key = fo.customer_key
GROUP BY dc.country, dc.region
ORDER BY total_spend DESC;

-- ---------------------------------------------------------------------------
-- Query 4: Monthly revenue trend by region
-- Uses: fct_orders (fact)
-- ---------------------------------------------------------------------------
SELECT
    TO_CHAR(order_date, 'YYYY-MM')    AS month,
    order_region,
    COUNT(*)                          AS orders,
    SUM(total_amount)                 AS revenue
FROM fct_orders
GROUP BY TO_CHAR(order_date, 'YYYY-MM'), order_region
ORDER BY month, order_region;

-- ---------------------------------------------------------------------------
-- Query 5: Order status distribution
-- Uses: fct_orders (fact)
-- ---------------------------------------------------------------------------
SELECT
    order_status,
    COUNT(*)                          AS order_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_total,
    SUM(total_amount)                 AS revenue
FROM fct_orders
GROUP BY order_status
ORDER BY order_count DESC;

-- ---------------------------------------------------------------------------
-- Query 6: Top 10 customers by total spend (star schema join)
-- Uses: dim_customers (dimension) JOIN fct_orders (fact)
-- Note: In production, PII columns are masked for analysts (j***@gmail.com)
-- ---------------------------------------------------------------------------
SELECT
    dc.customer_id,
    dc.customer_full_name,
    dc.country,
    dc.region,
    dc.customer_age,
    COUNT(fo.order_id)                AS total_orders,
    SUM(fo.total_amount)              AS total_spend,
    ROUND(AVG(fo.total_amount), 2)    AS avg_order_value,
    MAX(fo.order_date)                AS last_order_date
FROM dim_customers dc
INNER JOIN fct_orders fo ON dc.customer_key = fo.customer_key
GROUP BY dc.customer_id, dc.customer_full_name, dc.country, dc.region, dc.customer_age
ORDER BY total_spend DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- Query 7: Data quality check — orphan orders (should return 0 rows)
-- Verifies referential integrity between fact and dimension
-- ---------------------------------------------------------------------------
SELECT fo.order_id, fo.customer_id, fo.customer_key
FROM fct_orders fo
LEFT JOIN dim_customers dc ON fo.customer_key = dc.customer_key
WHERE dc.customer_key IS NULL;

-- ---------------------------------------------------------------------------
-- Query 8: Table hierarchy summary — row counts across all 4 tables
-- Shows the pipeline flow: raw → staging → marts
-- ---------------------------------------------------------------------------
SELECT 'raw_customers'  AS table_name, COUNT(*) AS row_count FROM raw_customers
UNION ALL
SELECT 'raw_orders',                   COUNT(*)             FROM raw_orders
UNION ALL
SELECT 'dim_customers (mart)',         COUNT(*)             FROM dim_customers
UNION ALL
SELECT 'fct_orders (mart)',            COUNT(*)             FROM fct_orders
ORDER BY table_name;
