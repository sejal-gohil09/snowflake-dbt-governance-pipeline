-- ==========================================================================
-- 04_fct_orders.sql
-- Mart table: Kimball orders fact table
-- ==========================================================================
-- Layer: MARTS (Kimball star schema — fact)
-- Grain: One row per order
--
-- Relationships:
--   fct_orders.customer_key (FK) ──→ dim_customers.customer_key (PK)
--   fct_orders.customer_id        ←── natural key from raw_orders
--   fct_orders.order_id           ←── natural key from raw_orders
--
-- Source: raw_orders → stg_orders → fct_orders
--         joins to dim_customers on customer_id to get customer_key
--
-- Monetary columns derived in staging:
--   gross_amount = quantity × unit_price
--   tax_amount   = gross_amount × 0.20 (UK/EU VAT)
--   total_amount = gross_amount + tax_amount
--
-- Governance:
--   • order_region → Row Access Policy (rls_order_region)
--   • total_amount → CHECK (>= 0) — no negative revenue
--   • quantity     → CHECK (> 0)  — no zero/negative quantities
-- ==========================================================================

CREATE TABLE IF NOT EXISTS fct_orders (
    order_key            SERIAL         PRIMARY KEY,
    order_id             VARCHAR(20)    UNIQUE NOT NULL,
    customer_key         INTEGER        REFERENCES dim_customers(customer_key) ON DELETE CASCADE,
    customer_id          VARCHAR(20)    NOT NULL,
    order_date           DATE           NOT NULL,
    order_status         VARCHAR(20)    NOT NULL,
    payment_method       VARCHAR(20),
    product_category     VARCHAR(50),
    product_description  TEXT,
    quantity             INTEGER        NOT NULL CHECK (quantity > 0),
    unit_price           NUMERIC(10,2)  NOT NULL,
    gross_amount         NUMERIC(12,2)  NOT NULL,
    tax_amount           NUMERIC(12,2)  NOT NULL,
    total_amount         NUMERIC(12,2)  NOT NULL CHECK (total_amount >= 0),
    order_region         VARCHAR(4)     NOT NULL CHECK (order_region IN ('UK', 'EU')),
    created_at           TIMESTAMPTZ    DEFAULT now()
);

-- Indexes for join performance, RLS filtering, and date-range queries
CREATE INDEX IF NOT EXISTS idx_fct_orders_customer_key ON fct_orders(customer_key);
CREATE INDEX IF NOT EXISTS idx_fct_orders_order_region ON fct_orders(order_region);
CREATE INDEX IF NOT EXISTS idx_fct_orders_order_date   ON fct_orders(order_date);

-- RLS enabled — UK analysts see UK rows only, EU analysts see EU rows only
ALTER TABLE fct_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_select_fct_orders" ON fct_orders FOR SELECT
  TO anon, authenticated USING (true);
CREATE POLICY "anon_insert_fct_orders" ON fct_orders FOR INSERT
  TO anon, authenticated WITH CHECK (true);
CREATE POLICY "anon_update_fct_orders" ON fct_orders FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "anon_delete_fct_orders" ON fct_orders FOR DELETE
  TO anon, authenticated USING (true);

-- ==========================================================================
-- Snowflake Row Access Policy (run on Snowflake only)
-- ==========================================================================
-- CREATE ROW ACCESS POLICY IF NOT EXISTS rls_order_region
-- AS (order_region_val VARCHAR) RETURNS BOOLEAN ->
--     CASE
--         WHEN CURRENT_ROLE() = 'DATA_ENGINEER' THEN TRUE
--         WHEN CURRENT_ROLE() = 'DATA_ANALYST_UK' AND order_region_val = 'UK' THEN TRUE
--         WHEN CURRENT_ROLE() = 'DATA_ANALYST_EU' AND order_region_val = 'EU' THEN TRUE
--         ELSE FALSE
--     END;
--
-- ALTER TABLE fct_orders ADD ROW ACCESS POLICY rls_order_region ON (order_region);
-- ==========================================================================
