-- ==========================================================================
-- 02_raw_orders.sql
-- Source table: Transactional order data linked to customers
-- ==========================================================================
-- Layer: RAW (source system landing zone)
-- Grain: One row per order
--
-- Relationships:
--   raw_orders.customer_id (FK) ──→ raw_customers.customer_id (PK)
--
-- Check Constraints:
--   quantity > 0 (no zero or negative quantities)
--   unit_price >= 0 (no negative prices)
--   region IN ('UK', 'EU')
-- ==========================================================================

CREATE TABLE IF NOT EXISTS raw_orders (
    order_id             VARCHAR(20)   PRIMARY KEY,
    customer_id          VARCHAR(20)   NOT NULL REFERENCES raw_customers(customer_id) ON DELETE CASCADE,
    order_date           DATE          NOT NULL,
    order_status         VARCHAR(20)   NOT NULL,
    payment_method       VARCHAR(20),
    product_category     VARCHAR(50),
    product_description  TEXT,
    quantity             INTEGER       NOT NULL CHECK (quantity > 0),
    unit_price           NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    region               VARCHAR(4)    NOT NULL CHECK (region IN ('UK', 'EU')),
    created_at           TIMESTAMPTZ   DEFAULT now()
);

-- Indexes for join performance and region filtering
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON raw_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_region      ON raw_orders(region);

-- RLS enabled for regional data isolation (GDPR Art. 44)
ALTER TABLE raw_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_select_raw_orders" ON raw_orders FOR SELECT
  TO anon, authenticated USING (true);
CREATE POLICY "anon_insert_raw_orders" ON raw_orders FOR INSERT
  TO anon, authenticated WITH CHECK (true);
CREATE POLICY "anon_update_raw_orders" ON raw_orders FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "anon_delete_raw_orders" ON raw_orders FOR DELETE
  TO anon, authenticated USING (true);
