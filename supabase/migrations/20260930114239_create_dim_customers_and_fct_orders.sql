/*
# Create dbt mart tables: dim_customers and fct_orders

1. New Tables
   - `dim_customers`: Kimball customer dimension — one row per customer
     - customer_key SERIAL PRIMARY KEY (surrogate key)
     - customer_id VARCHAR(20) UNIQUE NOT NULL (natural key)
     - customer_full_name TEXT
     - customer_email TEXT (masked at application layer; stored hashed via dbt macro in Snowflake)
     - customer_phone TEXT
     - country TEXT
     - region VARCHAR(4) CHECK (UK/EU)
     - customer_age INTEGER CHECK (18-100)
     - gender VARCHAR(4)
     - customer_since DATE
     - created_at TIMESTAMPTZ DEFAULT now()
   - `fct_orders`: Kimball orders fact table — one row per order
     - order_key SERIAL PRIMARY KEY (surrogate key)
     - order_id VARCHAR(20) UNIQUE NOT NULL (natural key)
     - customer_key INTEGER REFERENCES dim_customers(customer_key)
     - customer_id VARCHAR(20) NOT NULL
     - order_date DATE NOT NULL
     - order_status VARCHAR(20) NOT NULL
     - payment_method VARCHAR(20)
     - product_category VARCHAR(50)
     - product_description TEXT
     - quantity INTEGER NOT NULL CHECK > 0
     - unit_price NUMERIC(10,2) NOT NULL
     - gross_amount NUMERIC(12,2) NOT NULL
     - tax_amount NUMERIC(12,2) NOT NULL
     - total_amount NUMERIC(12,2) NOT NULL CHECK >= 0
     - order_region VARCHAR(4) NOT NULL CHECK (UK/EU)
     - created_at TIMESTAMPTZ DEFAULT now()

2. Security
   - RLS enabled on both mart tables.
   - No-auth analytics pipeline: policies allow anon + authenticated CRUD.

3. Notes
   - These tables are populated by the dbt run step (or by load_data.py for standalone Postgres mode).
   - Foreign key from fct_orders.customer_key -> dim_customers.customer_key enforces referential integrity.
   - Indexes on region columns for RLS-style filtering performance.
*/

CREATE TABLE IF NOT EXISTS dim_customers (
    customer_key SERIAL PRIMARY KEY,
    customer_id VARCHAR(20) UNIQUE NOT NULL,
    customer_full_name TEXT,
    customer_email TEXT,
    customer_phone TEXT,
    country TEXT,
    region VARCHAR(4) CHECK (region IN ('UK', 'EU')),
    customer_age INTEGER CHECK (customer_age >= 18 AND customer_age <= 100),
    gender VARCHAR(4),
    customer_since DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fct_orders (
    order_key SERIAL PRIMARY KEY,
    order_id VARCHAR(20) UNIQUE NOT NULL,
    customer_key INTEGER REFERENCES dim_customers(customer_key) ON DELETE CASCADE,
    customer_id VARCHAR(20) NOT NULL,
    order_date DATE NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    payment_method VARCHAR(20),
    product_category VARCHAR(50),
    product_description TEXT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL,
    gross_amount NUMERIC(12,2) NOT NULL,
    tax_amount NUMERIC(12,2) NOT NULL,
    total_amount NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    order_region VARCHAR(4) NOT NULL CHECK (order_region IN ('UK', 'EU')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dim_customers_region ON dim_customers(region);
CREATE INDEX IF NOT EXISTS idx_fct_orders_customer_key ON fct_orders(customer_key);
CREATE INDEX IF NOT EXISTS idx_fct_orders_order_region ON fct_orders(order_region);
CREATE INDEX IF NOT EXISTS idx_fct_orders_order_date ON fct_orders(order_date);

ALTER TABLE dim_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE fct_orders ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_dim_customers" ON dim_customers;
CREATE POLICY "anon_select_dim_customers" ON dim_customers FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_dim_customers" ON dim_customers;
CREATE POLICY "anon_insert_dim_customers" ON dim_customers FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_dim_customers" ON dim_customers;
CREATE POLICY "anon_update_dim_customers" ON dim_customers FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_dim_customers" ON dim_customers;
CREATE POLICY "anon_delete_dim_customers" ON dim_customers FOR DELETE
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_select_fct_orders" ON fct_orders;
CREATE POLICY "anon_select_fct_orders" ON fct_orders FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_fct_orders" ON fct_orders;
CREATE POLICY "anon_insert_fct_orders" ON fct_orders FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_fct_orders" ON fct_orders;
CREATE POLICY "anon_update_fct_orders" ON fct_orders FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_fct_orders" ON fct_orders;
CREATE POLICY "anon_delete_fct_orders" ON fct_orders FOR DELETE
  TO anon, authenticated USING (true);