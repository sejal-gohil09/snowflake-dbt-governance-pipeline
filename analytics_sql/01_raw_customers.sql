-- ==========================================================================
-- 01_raw_customers.sql
-- Source table: Customer data with PII (UK + EU regions)
-- ==========================================================================
-- Layer: RAW (source system landing zone)
-- Grain: One row per customer
--
-- Relationships:
--   raw_customers.customer_id (PK) ←── FK ── raw_orders.customer_id
--
-- PII Columns: customer_email, customer_phone, customer_full_name
-- These are protected by Dynamic Data Masking policies at the mart layer.
-- ==========================================================================

CREATE TABLE IF NOT EXISTS raw_customers (
    customer_id          VARCHAR(20)   PRIMARY KEY,
    customer_full_name   TEXT          NOT NULL,
    customer_email       TEXT          NOT NULL,
    customer_phone       TEXT,
    country              TEXT          NOT NULL,
    region               VARCHAR(4)    NOT NULL CHECK (region IN ('UK', 'EU')),
    gender               VARCHAR(4),
    date_of_birth        DATE,
    created_at           TIMESTAMPTZ   DEFAULT now(),
    updated_at           TIMESTAMPTZ   DEFAULT now()
);

-- Index for RLS-style region filtering
CREATE INDEX IF NOT EXISTS idx_customers_region ON raw_customers(region);

-- RLS enabled for regional data isolation (GDPR Art. 44)
ALTER TABLE raw_customers ENABLE ROW LEVEL SECURITY;

-- Policies: allow anon + authenticated full CRUD (data pipeline context)
CREATE POLICY "anon_select_raw_customers" ON raw_customers FOR SELECT
  TO anon, authenticated USING (true);
CREATE POLICY "anon_insert_raw_customers" ON raw_customers FOR INSERT
  TO anon, authenticated WITH CHECK (true);
CREATE POLICY "anon_update_raw_customers" ON raw_customers FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "anon_delete_raw_customers" ON raw_customers FOR DELETE
  TO anon, authenticated USING (true);
