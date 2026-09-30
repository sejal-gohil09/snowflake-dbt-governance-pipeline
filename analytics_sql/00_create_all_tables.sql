-- ==========================================================================
-- 00_create_all_tables.sql
-- Master script: creates all 4 tables in dependency order with relationships
-- ==========================================================================
-- Run this script to create the complete database schema in one pass.
-- Tables are created in dependency order:
--   1. raw_customers  (no dependencies)
--   2. raw_orders     (FK → raw_customers)
--   3. dim_customers  (built from raw_customers via dbt)
--   4. fct_orders     (FK → dim_customers, built from raw_orders via dbt)
--
-- Table Hierarchy:
--
--   raw_customers (PK: customer_id)
--       │
--       ├── FK: raw_orders.customer_id → raw_customers.customer_id
--       │
--       │   raw_orders (PK: order_id)
--       │
--       ▼ (dbt transformation: stg_customers → dim_customers)
--   dim_customers (PK: customer_key, UK: customer_id)
--       │
--       ├── FK: fct_orders.customer_key → dim_customers.customer_key
--       │
--       │   fct_orders (PK: order_key, UK: order_id)
--       │
--       ▼
--   Kimball Star Schema: dim_customers (1) ←──→ (N) fct_orders
--
-- Indexes created:
--   idx_customers_region          ON raw_customers(region)
--   idx_orders_customer_id        ON raw_orders(customer_id)
--   idx_orders_region             ON raw_orders(region)
--   idx_dim_customers_region      ON dim_customers(region)
--   idx_fct_orders_customer_key   ON fct_orders(customer_key)
--   idx_fct_orders_order_region   ON fct_orders(order_region)
--   idx_fct_orders_order_date     ON fct_orders(order_date)
--
-- RLS enabled on all 4 tables with anon + authenticated CRUD policies.
-- ==========================================================================

-- Step 1: Raw layer — source data landing zone
\i analytics_sql/01_raw_customers.sql
\i analytics_sql/02_raw_orders.sql

-- Step 2: Mart layer — Kimball star schema
\i analytics_sql/03_dim_customers.sql
\i analytics_sql/04_fct_orders.sql

-- Step 3: Verify table creation
SELECT 'raw_customers'  AS table_name, COUNT(*) AS row_count FROM raw_customers
UNION ALL
SELECT 'raw_orders',                   COUNT(*)             FROM raw_orders
UNION ALL
SELECT 'dim_customers',                COUNT(*)             FROM dim_customers
UNION ALL
SELECT 'fct_orders',                   COUNT(*)             FROM fct_orders
ORDER BY table_name;
