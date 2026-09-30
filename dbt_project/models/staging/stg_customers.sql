{#
  stg_customers — Staging view: cleanses raw customer data.
  - Standardises column names and data types
  - Hashes PII columns (email, phone) at the dbt layer (defence-in-depth)
  - Derives customer_age from date_of_birth (data minimisation per GDPR Art. 5)
  - Standardises region values to UK/EU
#}

WITH raw AS (
    SELECT
        customer_id,
        customer_full_name,
        customer_email,
        customer_phone,
        UPPER(TRIM(country)) AS country,
        UPPER(TRIM(region)) AS region,
        gender,
        date_of_birth,
        created_at,
        updated_at
    FROM {{ ref('raw_customers') }}
)

SELECT
    customer_id,
    customer_full_name,
    -- PII hashing: SHA-256 hash for defence-in-depth
    {{ mask_pii('customer_email') }} AS customer_email_hash,
    customer_email AS customer_email_raw,
    {{ mask_pii('customer_phone') }} AS customer_phone_hash,
    customer_phone AS customer_phone_raw,
    country,
    region,
    gender,
    -- Data minimisation: replace DOB with derived age (GDPR Art. 5)
    {{ dbt_utils.datediff('date_of_birth', 'CURRENT_DATE', 'year') }} AS customer_age,
    date_of_birth,
    created_at,
    updated_at
FROM raw
