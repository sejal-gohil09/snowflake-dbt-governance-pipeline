{#
  fct_orders — Kimball orders fact table.
  Grain: one row per order.
  - Surrogate key (order_key) generated via dbt_utils.generate_surrogate_key
  - FK to dim_customers via customer_key (referential integrity enforced by dbt test)
  - Denormalised order_region enables Row-Level Security filtering at the fact level
  - Monetary amounts: gross, tax (20% VAT), total
#}

WITH orders AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        order_status,
        payment_method,
        product_category,
        product_description,
        quantity,
        unit_price,
        gross_amount,
        tax_amount,
        total_amount,
        region AS order_region,
        created_at
    FROM {{ ref('stg_orders') }}
),

dim AS (
    SELECT
        customer_key,
        customer_id,
        region
    FROM {{ ref('dim_customers') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['o.order_id']) }} AS order_key,
    o.order_id,
    d.customer_key,
    o.customer_id,
    o.order_date,
    o.order_status,
    o.payment_method,
    o.product_category,
    o.product_description,
    o.quantity,
    o.unit_price,
    o.gross_amount,
    o.tax_amount,
    o.total_amount,
    -- Denormalised region for RLS filtering without joining to dimension
    o.order_region,
    o.created_at
FROM orders o
INNER JOIN dim d
    ON o.customer_id = d.customer_id
