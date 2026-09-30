-- ==========================================================================
-- 02_row_level_security.sql
-- Regional Row-Level Security (RLS) Policies
-- ==========================================================================
-- Ensures UK analysts see only UK rows and EU analysts see only EU rows.
-- Satisfies GDPR Article 44 (cross-border data transfer restrictions).
--
-- Snowflake Row Access Policies evaluate at query time based on
-- CURRENT_ROLE() and CURRENT_REGION().
-- ==========================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE ANALYTICS;

-- 1. Create row access policy for dim_customers
CREATE ROW ACCESS POLICY IF NOT EXISTS rls_customer_region
AS (region_val VARCHAR) RETURNS BOOLEAN ->
    CASE
        WHEN CURRENT_ROLE() = 'DATA_ENGINEER' THEN TRUE
        WHEN CURRENT_ROLE() = 'DATA_ANALYST_UK' AND region_val = 'UK' THEN TRUE
        WHEN CURRENT_ROLE() = 'DATA_ANALYST_EU' AND region_val = 'EU' THEN TRUE
        ELSE FALSE
    END;

-- 2. Create row access policy for fct_orders
CREATE ROW ACCESS POLICY IF NOT EXISTS rls_order_region
AS (order_region_val VARCHAR) RETURNS BOOLEAN ->
    CASE
        WHEN CURRENT_ROLE() = 'DATA_ENGINEER' THEN TRUE
        WHEN CURRENT_ROLE() = 'DATA_ANALYST_UK' AND order_region_val = 'UK' THEN TRUE
        WHEN CURRENT_ROLE() = 'DATA_ANALYST_EU' AND order_region_val = 'EU' THEN TRUE
        ELSE FALSE
    END;

-- 3. Apply RLS policies to mart tables
ALTER ROW ACCESS POLICY rls_customer_region ON dim_customers;
ALTER TABLE dim_customers ADD ROW ACCESS POLICY rls_customer_region
    ON (region);

ALTER ROW ACCESS POLICY rls_order_region ON fct_orders;
ALTER TABLE fct_orders ADD ROW ACCESS POLICY rls_order_region
    ON (order_region);

-- 4. Grant schema-level access (the policies must be owned by a role with manage rights)
GRANT APPLY ON ROW ACCESS POLICY rls_customer_region TO ROLE DATA_ENGINEER;
GRANT APPLY ON ROW ACCESS POLICY rls_order_region TO ROLE DATA_ENGINEER;

-- ==========================================================================
-- Verification queries (run as each role to confirm RLS):
--
--   USE ROLE DATA_ANALYST_UK;
--   SELECT COUNT(*) FROM ANALYTICS.MARTS.dim_customers;  -- should show UK count only
--   SELECT DISTINCT region FROM ANALYTICS.MARTS.dim_customers;  -- should show only 'UK'
--
--   USE ROLE DATA_ANALYST_EU;
--   SELECT COUNT(*) FROM ANALYTICS.MARTS.dim_customers;  -- should show EU count only
--   SELECT DISTINCT region FROM ANALYTICS.MARTS.dim_customers;  -- should show only 'EU'
--
--   USE ROLE DATA_ENGINEER;
--   SELECT COUNT(*) FROM ANALYTICS.MARTS.dim_customers;  -- should show ALL rows
--   SELECT DISTINCT region FROM ANALYTICS.MARTS.dim_customers;  -- should show UK + EU
-- ==========================================================================
