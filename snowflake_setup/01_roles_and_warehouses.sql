-- ==========================================================================
-- 01_roles_and_warehouses.sql
-- Role-Based Access Control (RBAC) Architecture Setup
-- ==========================================================================
-- Creates a least-privilege role hierarchy for the analytics platform:
--   ACCOUNTADMIN → SYSADMIN → DATA_ENGINEER
--                              ├─ DATA_ANALYST_UK (read-only, UK rows)
--                              └─ DATA_ANALYST_EU (read-only, EU rows)
--
-- Run as ACCOUNTADMIN in Snowsight or via snowsql.
-- ==========================================================================

USE ROLE ACCOUNTADMIN;

-- 1. Create custom roles
CREATE ROLE IF NOT EXISTS DATA_ENGINEER;
CREATE ROLE IF NOT EXISTS DATA_ANALYST_UK;
CREATE ROLE IF NOT EXISTS DATA_ANALYST_EU;

-- 2. Establish role hierarchy (grant child roles to parent roles)
GRANT ROLE DATA_ENGINEER TO ROLE SYSADMIN;
GRANT ROLE DATA_ANALYST_UK TO ROLE DATA_ENGINEER;
GRANT ROLE DATA_ANALYST_EU TO ROLE DATA_ENGINEER;

-- 3. Create databases and schemas
CREATE DATABASE IF NOT EXISTS ANALYTICS;
CREATE SCHEMA IF NOT EXISTS ANALYTICS.STAGING;
CREATE SCHEMA IF NOT EXISTS ANALYTICS.MARTS;

-- 4. Create a dedicated warehouse (if COMPUTE_WH is not sufficient)
CREATE WAREHOUSE IF NOT EXISTS ANALYTICS_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

-- 5. Grant warehouse usage
GRANT USAGE ON WAREHOUSE ANALYTICS_WH TO ROLE DATA_ENGINEER;
GRANT USAGE ON WAREHOUSE ANALYTICS_WH TO ROLE DATA_ANALYST_UK;
GRANT USAGE ON WAREHOUSE ANALYTICS_WH TO ROLE DATA_ANALYST_EU;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE DATA_ENGINEER;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE DATA_ANALYST_UK;

-- 6. Grant database/schema access
GRANT USAGE ON DATABASE ANALYTICS TO ROLE DATA_ENGINEER;
GRANT USAGE ON DATABASE ANALYTICS TO ROLE DATA_ANALYST_UK;
GRANT USAGE ON DATABASE ANALYTICS TO ROLE DATA_ANALYST_EU;

GRANT ALL PRIVILEGES ON SCHEMA ANALYTICS.STAGING TO ROLE DATA_ENGINEER;
GRANT ALL PRIVILEGES ON SCHEMA ANALYTICS.MARTS TO ROLE DATA_ENGINEER;

-- Analysts get read-only access to marts only (not staging)
GRANT USAGE ON SCHEMA ANALYTICS.MARTS TO ROLE DATA_ANALYST_UK;
GRANT USAGE ON SCHEMA ANALYTICS.MARTS TO ROLE DATA_ANALYST_EU;

-- Grant SELECT on all current and future mart tables
GRANT SELECT ON ALL TABLES IN SCHEMA ANALYTICS.MARTS TO ROLE DATA_ANALYST_UK;
GRANT SELECT ON ALL TABLES IN SCHEMA ANALYTICS.MARTS TO ROLE DATA_ANALYST_EU;

GRANT SELECT ON FUTURE TABLES IN SCHEMA ANALYTICS.MARTS TO ROLE DATA_ANALYST_UK;
GRANT SELECT ON FUTURE TABLES IN SCHEMA ANALYTICS.MARTS TO ROLE DATA_ANALYST_EU;

-- 7. Create users (example — replace passwords in production)
CREATE USER IF NOT EXISTS eng_pipeline
    PASSWORD = 'EngineSecurePass2024!'
    DEFAULT_ROLE = DATA_ENGINEER
    DEFAULT_WAREHOUSE = ANALYTICS_WH;

CREATE USER IF NOT EXISTS analyst_uk
    PASSWORD = 'UKAnalystPass2024!'
    DEFAULT_ROLE = DATA_ANALYST_UK
    DEFAULT_WAREHOUSE = ANALYTICS_WH;

CREATE USER IF NOT EXISTS analyst_eu
    PASSWORD = 'EUAnalystPass2024!'
    DEFAULT_ROLE = DATA_ANALYST_EU
    DEFAULT_WAREHOUSE = ANALYTICS_WH;

-- 8. Assign roles to users
GRANT ROLE DATA_ENGINEER TO USER eng_pipeline;
GRANT ROLE DATA_ANALYST_UK TO USER analyst_uk;
GRANT ROLE DATA_ANALYST_EU TO USER analyst_eu;

-- ==========================================================================
-- Summary:
--   DATA_ENGINEER   → Full DDL/DML on staging + marts, all regions
--   DATA_ANALYST_UK → SELECT on marts only, UK rows only (enforced by RLS)
--   DATA_ANALYST_EU → SELECT on marts only, EU rows only (enforced by RLS)
--   No analyst has access to raw/staging — least privilege enforced.
-- ==========================================================================
