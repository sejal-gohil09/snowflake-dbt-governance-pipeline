#!/usr/bin/env python3
"""
test_data_quality.py — pytest data quality tests for the governance pipeline.
Validates data loaded into Postgres (Supabase) against business rules.

Run: pytest tests/ -v
"""

import os
import re
import psycopg2
import pytest
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("SUPABASE_DB_URL", "")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_connection():
    if not DB_URL:
        pytest.skip("SUPABASE_DB_URL not set — skipping database tests")
    conn = psycopg2.connect(DB_URL)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def customers(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("SELECT * FROM raw_customers ORDER BY customer_id")
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@pytest.fixture(scope="module")
def orders(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("SELECT * FROM raw_orders ORDER BY order_id")
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@pytest.fixture(scope="module")
def dim_customers(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("SELECT * FROM dim_customers ORDER BY customer_id")
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@pytest.fixture(scope="module")
def fct_orders(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("SELECT * FROM fct_orders ORDER BY order_id")
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Raw customers tests
# ---------------------------------------------------------------------------

class TestRawCustomers:
    def test_customer_ids_unique(self, customers):
        ids = [c["customer_id"] for c in customers]
        assert len(ids) == len(set(ids)), "Duplicate customer_id values found"

    def test_customer_ids_not_null(self, customers):
        assert all(c["customer_id"] is not None for c in customers), "Null customer_id found"

    def test_emails_contain_at_symbol(self, customers):
        for c in customers:
            assert "@" in c["customer_email"], f"Invalid email for {c['customer_id']}: {c['customer_email']}"

    def test_emails_not_null(self, customers):
        assert all(c["customer_email"] for c in customers), "Null customer_email found"

    def test_regions_valid(self, customers):
        valid = {"UK", "EU"}
        for c in customers:
            assert c["region"] in valid, f"Invalid region for {c['customer_id']}: {c['region']}"

    def test_countries_not_null(self, customers):
        assert all(c["country"] for c in customers), "Null country found"

    def test_customer_count_positive(self, customers):
        assert len(customers) > 0, "No customers found in database"


# ---------------------------------------------------------------------------
# Raw orders tests
# ---------------------------------------------------------------------------

class TestRawOrders:
    def test_order_ids_unique(self, orders):
        ids = [o["order_id"] for o in orders]
        assert len(ids) == len(set(ids)), "Duplicate order_id values found"

    def test_order_ids_not_null(self, orders):
        assert all(o["order_id"] is not None for o in orders), "Null order_id found"

    def test_quantities_positive(self, orders):
        for o in orders:
            assert o["quantity"] > 0, f"Non-positive quantity for {o['order_id']}: {o['quantity']}"

    def test_unit_prices_non_negative(self, orders):
        for o in orders:
            assert o["unit_price"] >= 0, f"Negative unit_price for {o['order_id']}: {o['unit_price']}"

    def test_order_regions_valid(self, orders):
        valid = {"UK", "EU"}
        for o in orders:
            assert o["region"] in valid, f"Invalid region for {o['order_id']}: {o['region']}"

    def test_order_dates_not_null(self, orders):
        assert all(o["order_date"] is not None for o in orders), "Null order_date found"

    def test_order_statuses_valid(self, orders):
        valid = {"Pending", "Shipped", "Delivered", "Cancelled", "Refunded"}
        for o in orders:
            assert o["order_status"] in valid, f"Invalid status for {o['order_id']}: {o['order_status']}"

    def test_referential_integrity(self, customers, orders):
        cust_ids = {c["customer_id"] for c in customers}
        for o in orders:
            assert o["customer_id"] in cust_ids, f"Orphan order {o['order_id']}: customer {o['customer_id']} not found"

    def test_order_count_positive(self, orders):
        assert len(orders) > 0, "No orders found in database"


# ---------------------------------------------------------------------------
# dim_customers tests
# ---------------------------------------------------------------------------

class TestDimCustomers:
    def test_surrogate_keys_unique(self, dim_customers):
        keys = [c["customer_key"] for c in dim_customers]
        assert len(keys) == len(set(keys)), "Duplicate customer_key values found"

    def test_natural_keys_unique(self, dim_customers):
        ids = [c["customer_id"] for c in dim_customers]
        assert len(ids) == len(set(ids)), "Duplicate customer_id in dimension"

    def test_ages_in_valid_range(self, dim_customers):
        for c in dim_customers:
            age = c["customer_age"]
            assert 18 <= age <= 100, f"Age out of range for {c['customer_id']}: {age}"

    def test_regions_valid(self, dim_customers):
        valid = {"UK", "EU"}
        for c in dim_customers:
            assert c["region"] in valid, f"Invalid region in dim for {c['customer_id']}: {c['region']}"

    def test_customer_since_not_null(self, dim_customers):
        assert all(c["customer_since"] is not None for c in dim_customers), "Null customer_since found"


# ---------------------------------------------------------------------------
# fct_orders tests
# ---------------------------------------------------------------------------

class TestFctOrders:
    def test_surrogate_keys_unique(self, fct_orders):
        keys = [o["order_key"] for o in fct_orders]
        assert len(keys) == len(set(keys)), "Duplicate order_key values found"

    def test_natural_keys_unique(self, fct_orders):
        ids = [o["order_id"] for o in fct_orders]
        assert len(ids) == len(set(ids)), "Duplicate order_id in fact table"

    def test_customer_key_fk_integrity(self, fct_orders, dim_customers):
        dim_keys = {c["customer_key"] for c in dim_customers}
        for o in fct_orders:
            assert o["customer_key"] in dim_keys, f"FK violation: order_key {o['order_key']} references missing customer_key {o['customer_key']}"

    def test_total_amounts_non_negative(self, fct_orders):
        for o in fct_orders:
            assert o["total_amount"] >= 0, f"Negative total_amount for {o['order_id']}: {o['total_amount']}"

    def test_total_equals_gross_plus_tax(self, fct_orders):
        for o in fct_orders:
            gross = float(o["gross_amount"])
            tax = float(o["tax_amount"])
            total = float(o["total_amount"])
            assert abs(total - (gross + tax)) < 0.03, f"Total mismatch for {o['order_id']}: {gross}+{tax}≠{total}"

    def test_tax_is_20_percent(self, fct_orders):
        for o in fct_orders:
            gross = float(o["gross_amount"])
            tax = float(o["tax_amount"])
            if gross > 0:
                rate = tax / gross
                assert abs(rate - 0.20) < 0.01, f"Tax rate not 20% for {o['order_id']}: {rate:.4f}"

    def test_order_regions_valid(self, fct_orders):
        valid = {"UK", "EU"}
        for o in fct_orders:
            assert o["order_region"] in valid, f"Invalid order_region for {o['order_id']}: {o['order_region']}"
