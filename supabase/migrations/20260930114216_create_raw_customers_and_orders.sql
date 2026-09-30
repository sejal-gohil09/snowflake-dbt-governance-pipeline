/*
# Create raw_customers and raw_orders tables for e-commerce governance pipeline

1. New Tables
   - `raw_customers`: Source customer data with PII (email, phone, name) across UK/EU regions
     - customer_id VARCHAR(20) PRIMARY KEY
     - customer_full_name TEXT NOT NULL
     - customer_email TEXT NOT NULL
     - customer_phone TEXT
     - country TEXT NOT NULL
     - region VARCHAR(4) NOT NULL CHECK (UK/EU)
     - gender VARCHAR(4)
     - date_of_birth DATE
     - created_at TIMESTAMPTZ DEFAULT now()
     - updated_at TIMESTAMPTZ DEFAULT now()
   - `raw_orders`: Transactional order data linked to customers
     - order_id VARCHAR(20) PRIMARY KEY
     - customer_id VARCHAR(20) FK -> raw_customers
     - order_date DATE NOT NULL
     - order_status VARCHAR(20) NOT NULL
     - payment_method VARCHAR(20)
     - product_category VARCHAR(50)
     - product_description TEXT
     - quantity INTEGER NOT NULL CHECK > 0
     - unit_price NUMERIC(10,2) NOT NULL
     - region VARCHAR(4) NOT NULL CHECK (UK/EU)
     - created_at TIMESTAMPTZ DEFAULT now()

2. Security
   - RLS enabled on both tables.
   - No-auth data pipeline project: policies allow anon + authenticated CRUD (data is intentionally shared for analytics).

3. Notes
   - These tables hold source-system data loaded by scripts/load_data.py.
   - The dbt layer (staging + marts) transforms this into a Kimball star schema.
   - Indexes added on customer_id (orders FK) and region for query performance.
*/

CREATE TABLE IF NOT EXISTS raw_customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    customer_full_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_phone TEXT,
    country TEXT NOT NULL,
    region VARCHAR(4) NOT NULL CHECK (region IN ('UK', 'EU')),
    gender VARCHAR(4),
    date_of_birth DATE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_orders (
    order_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES raw_customers(customer_id) ON DELETE CASCADE,
    order_date DATE NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    payment_method VARCHAR(20),
    product_category VARCHAR(50),
    product_description TEXT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    region VARCHAR(4) NOT NULL CHECK (region IN ('UK', 'EU')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON raw_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_region ON raw_orders(region);
CREATE INDEX IF NOT EXISTS idx_customers_region ON raw_customers(region);

ALTER TABLE raw_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_orders ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_raw_customers" ON raw_customers;
CREATE POLICY "anon_select_raw_customers" ON raw_customers FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_raw_customers" ON raw_customers;
CREATE POLICY "anon_insert_raw_customers" ON raw_customers FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_raw_customers" ON raw_customers;
CREATE POLICY "anon_update_raw_customers" ON raw_customers FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_raw_customers" ON raw_customers;
CREATE POLICY "anon_delete_raw_customers" ON raw_customers FOR DELETE
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_select_raw_orders" ON raw_orders;
CREATE POLICY "anon_select_raw_orders" ON raw_orders FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_raw_orders" ON raw_orders;
CREATE POLICY "anon_insert_raw_orders" ON raw_orders FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_raw_orders" ON raw_orders;
CREATE POLICY "anon_update_raw_orders" ON raw_orders FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_raw_orders" ON raw_orders;
CREATE POLICY "anon_delete_raw_orders" ON raw_orders FOR DELETE
  TO anon, authenticated USING (true);