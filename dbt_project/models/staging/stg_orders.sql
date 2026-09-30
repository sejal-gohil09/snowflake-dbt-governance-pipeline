{#
  stg_orders — Staging view: standardises transactional order data.
  - Validates quantity > 0 and unit_price >= 0
  - Derives gross_amount, tax_amount (20% UK/EU VAT), and total_amount
  - Standardises order_status and payment_method
#}

WITH raw AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        UPPER(TRIM(order_status)) AS order_status,
        INITCAP(TRIM(payment_method)) AS payment_method,
        product_category,
        product_description,
        quantity,
        unit_price,
        UPPER(TRIM(region)) AS region,
        created_at
    FROM {{ ref('raw_orders') }}
    WHERE quantity > 0
      AND unit_price >= 0
      AND order_date IS NOT NULL
)

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
    -- Monetary calculations
    ROUND(quantity * unit_price, 2) AS gross_amount,
    ROUND(quantity * unit_price * 0.20, 2) AS tax_amount,
    ROUND(quantity * unit_price * 1.20, 2) AS total_amount,
    region,
    created_at
FROM raw
