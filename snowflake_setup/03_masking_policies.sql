-- ==========================================================================
-- 03_masking_policies.sql
-- Dynamic Data Masking Policies for PII (GDPR Compliance)
-- ==========================================================================
-- Implements role-aware dynamic masking on PII columns:
--   DATA_ENGINEER   → sees full unmasked values (operational access)
--   DATA_ANALYST_*  → sees masked values (data protection by default)
--
-- Satisfies GDPR Article 25 (data protection by design and by default).
-- ==========================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE ANALYTICS;

-- 1. Email masking policy: j***@gmail.com
CREATE MASKING POLICY IF NOT EXISTS mask_email
AS (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() = 'DATA_ENGINEER' THEN val
        WHEN CURRENT_ROLE() IN ('DATA_ANALYST_UK', 'DATA_ANALYST_EU') THEN
            REGEXP_REPLACE(val, '^([a-zA-Z0-9]).*(@.*)$', '\\1***\\2')
        ELSE '***'
    END;

-- 2. Phone masking policy: +44 *** *** 7890
CREATE MASKING POLICY IF NOT EXISTS mask_phone
AS (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() = 'DATA_ENGINEER' THEN val
        WHEN CURRENT_ROLE() IN ('DATA_ANALYST_UK', 'DATA_ANALYST_EU') THEN
            REGEXP_REPLACE(val, '(\\+\\d{1,3})\\s+\\d{3,}\\s+\\d{3,}\\s+(\\d{4})', '\\1 *** *** \\2')
        ELSE '***'
    END;

-- 3. Full name masking policy: J*** Smith → J***
CREATE MASKING POLICY IF NOT EXISTS mask_full_name
AS (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() = 'DATA_ENGINEER' THEN val
        WHEN CURRENT_ROLE() IN ('DATA_ANALYST_UK', 'DATA_ANALYST_EU') THEN
            REGEXP_REPLACE(val, '^([a-zA-Z]).*', '\\1***')
        ELSE '***'
    END;

-- 4. Apply masking policies to dim_customers columns
ALTER TABLE dim_customers MODIFY COLUMN customer_email SET MASKING POLICY mask_email;
ALTER TABLE dim_customers MODIFY COLUMN customer_phone SET MASKING POLICY mask_phone;
ALTER TABLE dim_customers MODIFY COLUMN customer_full_name SET MASKING POLICY mask_full_name;

-- ==========================================================================
-- Verification queries:
--
--   USE ROLE DATA_ENGINEER;
--   SELECT customer_email, customer_phone, customer_full_name
--   FROM ANALYTICS.MARTS.dim_customers LIMIT 5;
--   -- Result: john.smith@gmail.com | +44 7123 456 7890 | John Smith
--
--   USE ROLE DATA_ANALYST_UK;
--   SELECT customer_email, customer_phone, customer_full_name
--   FROM ANALYTICS.MARTS.dim_customers LIMIT 5;
--   -- Result: j***@gmail.com | +44 *** *** 7890 | J***
-- ==========================================================================
