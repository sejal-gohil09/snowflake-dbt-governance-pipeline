{#
  dim_customers — Kimball customer dimension table.
  Grain: one row per customer.
  - Surrogate key (customer_key) generated via dbt_utils.generate_surrogate_key
  - PII columns included for governance demonstration (masked at Snowflake layer)
  - Region column enables Row-Level Security filtering
  - customer_age derived from DOB (data minimisation)
#}

WITH stg AS (
    SELECT
        customer_id,
        customer_full_name,
        customer_email_raw AS customer_email,
        customer_phone_raw AS customer_phone,
        country,
        region,
        gender,
        customer_age,
        date_of_birth,
        created_at,
        updated_at
    FROM {{ ref('stg_customers') }}
    WHERE customer_id IS NOT NULL
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['customer_id']) }} AS customer_key,
    customer_id,
    customer_full_name,
    customer_email,
    customer_phone,
    country,
    region,
    gender,
    customer_age,
    date_of_birth,
    created_at::date AS customer_since,
    updated_at
FROM stg
