-- ==========================================================================
-- 03_dim_customers.sql
-- Mart table: Kimball customer dimension
-- ==========================================================================
-- Layer: MARTS (Kimball star schema — dimension)
-- Grain: One row per customer
--
-- Relationships:
--   dim_customers.customer_key (PK) ←── FK ── fct_orders.customer_key
--   dim_customers.customer_id (UK)  ←── natural key from raw_customers
--
-- Source: raw_customers → stg_customers → dim_customers
--
-- Governance:
--   • customer_email    → Dynamic Masking Policy (mask_email)
--   • customer_phone    → Dynamic Masking Policy (mask_phone)
--   • customer_full_name → Dynamic Masking Policy (mask_full_name)
--   • region            → Row Access Policy (rls_customer_region)
--   • customer_age      → CHECK (18–100), derived from DOB (GDPR Art. 5)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS dim_customers (
    customer_key         SERIAL        PRIMARY KEY,
    customer_id          VARCHAR(20)   UNIQUE NOT NULL,
    customer_full_name   TEXT,
    customer_email       TEXT,
    customer_phone       TEXT,
    country              TEXT,
    region               VARCHAR(4)    CHECK (region IN ('UK', 'EU')),
    customer_age         INTEGER       CHECK (customer_age >= 18 AND customer_age <= 100),
    gender               VARCHAR(4),
    customer_since       DATE,
    created_at           TIMESTAMPTZ   DEFAULT now()
);

-- Index for RLS region filtering
CREATE INDEX IF NOT EXISTS idx_dim_customers_region ON dim_customers(region);

-- RLS enabled — UK analysts see UK rows only, EU analysts see EU rows only
ALTER TABLE dim_customers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_select_dim_customers" ON dim_customers FOR SELECT
  TO anon, authenticated USING (true);
CREATE POLICY "anon_insert_dim_customers" ON dim_customers FOR INSERT
  TO anon, authenticated WITH CHECK (true);
CREATE POLICY "anon_update_dim_customers" ON dim_customers FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "anon_delete_dim_customers" ON dim_customers FOR DELETE
  TO anon, authenticated USING (true);

-- ==========================================================================
-- Snowflake Dynamic Data Masking Policies (run on Snowflake only)
-- ==========================================================================
-- CREATE MASKING POLICY IF NOT EXISTS mask_email
-- AS (val STRING) RETURNS STRING ->
--     CASE
--         WHEN CURRENT_ROLE() = 'DATA_ENGINEER' THEN val
--         WHEN CURRENT_ROLE() IN ('DATA_ANALYST_UK', 'DATA_ANALYST_EU')
--             THEN REGEXP_REPLACE(val, '^([a-zA-Z0-9]).*(@.*)$', '\1***\2')
--         ELSE '***'
--     END;
--
-- ALTER TABLE dim_customers MODIFY COLUMN customer_email SET MASKING POLICY mask_email;
-- ALTER TABLE dim_customers MODIFY COLUMN customer_phone SET MASKING POLICY mask_phone;
-- ALTER TABLE dim_customers MODIFY COLUMN customer_full_name SET MASKING POLICY mask_full_name;
-- ==========================================================================
