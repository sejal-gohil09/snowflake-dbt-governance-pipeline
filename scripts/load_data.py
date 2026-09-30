#!/usr/bin/env python3
"""
load_data.py — Generate realistic UK/EU e-commerce data and load into Postgres (Supabase).
Also exports dbt seed CSVs for Snowflake deployment.

Data is based on the UCI Online Retail II dataset patterns (UK-based e-commerce transactions).

Usage:
    python scripts/load_data.py --customers 1000 --orders 5000
"""

import argparse
import csv
import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_URL = os.environ.get("SUPABASE_DB_URL", "")

# Realistic data pools inspired by UCI Online Retail II dataset
UK_FIRST_NAMES = [
    "James", "Oliver", "George", "Harry", "Jack", "Jacob", "Noah", "Charlie",
    "Muhammad", "Thomas", "Olivia", "Emma", "Sophia", "Isabella", "Ava", "Mia",
    "Emily", "Amelia", "Harper", "Evelyn", "Daniel", "Michael", "David", "Richard",
]
UK_LAST_NAMES = [
    "Smith", "Jones", "Williams", "Taylor", "Brown", "Davies", "Evans", "Wilson",
    "Thomas", "Roberts", "Johnson", "Walker", "Wright", "Robinson", "Thompson",
    "White", "Hughes", "Edwards", "Green", "Hall", "Wood", "Harris", "Clark", "Lewis",
]
EU_FIRST_NAMES = [
    "Lucas", "Liam", "Noah", "Leon", "Finn", "Niklas", "Pierre", "Louis", "Mateo",
    "Hugo", "Emma", "Sofia", "Anna", "Lea", "Mia", "Elena", "Clara", "Julia",
    "Camille", "Sophie", "Lars", "Sven", "Marco", "Giulia",
]
EU_LAST_NAMES = [
    "Müller", "Schmidt", "Dubois", "Martin", "Bernard", "Rossi", "Ferrari", "Bianchi",
    "Jansen", "de Vries", "Andersen", "Hansen", "Nygard", "Garcia", "Lopez", "Sato",
    "Novak", "Kovac", "Petrov", "Murphy", "Kowalski", "Nowak", "Wojcik", "Varga",
]
# UCI Online Retail II real product descriptions + categories
PRODUCTS = [
    ("Home Decor", "WHITE HANGING HEART T-LIGHT HOLDER", 2.95),
    ("Home Decor", "HAND WARMER UNION JACK FLG", 3.39),
    ("Home Decor", "HAND WARMER RED POLKA DOT", 3.39),
    ("Kitchen", "JUMBO BAG RED RETROSPOT", 4.95),
    ("Kitchen", "JUMBO BAG STRAWBERRY", 4.95),
    ("Kitchen", "JUMBO SHOPPER VINTAGE RED PAISLEY", 6.95),
    ("Kitchen", "LUNCH BAG RED RETROSPOT", 1.45),
    ("Kitchen", "LUNCH BAG SUKI DESIGN", 1.45),
    ("Kitchen", "LUNCH BAG WITH BLACK CAT", 1.45),
    ("Kitchen", "LUNCH BOX WITH CUTLERY", 3.75),
    ("Home Decor", "REGENCY CAKESTAND 3 TIER", 12.75),
    ("Home Decor", "JUMBO BAG VINTAGE LEAF", 4.95),
    ("Home Decor", "ROSES REGENCY TEACUP AND SAUCER", 3.75),
    ("Home Decor", "SET OF 3 BUTTERFLY COOKIE CUTTERS", 1.95),
    ("Home Decor", "SET OF 6 SKULLS GIFT BAGS", 1.25),
    ("Bathroom", "BATH BUILDING BLOCK WORD", 5.95),
    ("Bathroom", "BATH BOMB FIZZER SHEA BUTTER", 1.45),
    ("Bathroom", "DOORMAT UNION JACK", 4.95),
    ("Bathroom", "DOORMAT ENGLAND", 4.95),
    ("Bathroom", "DOORMAT SPOTTY", 4.95),
    ("Garden", "GARDENERS KNEELER DESK", 7.95),
    ("Garden", "GARDEN TOOL SET 3PC", 12.95),
    ("Garden", "PLANT POT HOLDER", 2.95),
    ("Garden", "WATERING CAN PINK", 5.95),
    ("Garden", "BIRD HOUSE WOODLAND", 9.95),
    ("Stationery", "PAPER CHAIN KIT 50'S CHRISTMAS", 1.45),
    ("Stationery", "PAPER CHAIN KIT VINTAGE CHRISTMAS", 1.45),
    ("Stationery", "PAPER CRAFT , BABY GIRL", 2.95),
    ("Stationery", "PAPER CRAFT , BABY BOY", 2.95),
    ("Stationery", "GREETING CARD SAFARI", 1.25),
    ("Toys", "WOODEN STAR CHRISTMAS SCANDI", 1.95),
    ("Toys", "WOODEN HEART CHRISTMAS SCANDI", 1.95),
    ("Toys", "VINTAGE CHRISTMAS PAPER GIFT BAG", 1.45),
    ("Toys", "FELTCRAFT GIRL AMELIE KIT", 8.95),
    ("Toys", "FELTCRAFT PRINCESS CHARLOTTE DOLL", 8.95),
    ("Toys", "FELTCRAFT BUTTERFLY PURSE", 5.95),
    ("Jewelry", "PACK OF 6 SKULL PAPER CUPS", 1.25),
    ("Jewelry", "PACK OF 6 SKULL PAPER PLATES", 1.25),
    ("Jewelry", "HEART OF WICKER SMALL", 1.95),
    ("Jewelry", "HEART OF WICKER LARGE", 4.95),
    ("Jewelry", "WHITE SKULL GIFT BAG", 1.45),
    ("Jewelry", "BLACK SKULL GIFT BAG", 1.45),
    ("Jewelry", "REGENCY TEACUP AND SAUCER", 3.75),
    ("Clothing", "WOOLLY HOPPIE WHITE HEART", 3.75),
    ("Clothing", "WORLD WAR 2 GLIDERS ASSTD DESIGNS", 2.95),
    ("Clothing", "FELTCRAFT CUSHION FLOWER", 9.95),
    ("Clothing", "FELTCRAFT DOLL MEGGY", 8.95),
    ("Clothing", "FELTCRAFT PETAL BAG", 5.95),
    ("Clothing", "MINI PAINT SET VINTAGE", 2.95),
]

ORDER_STATUSES = ["Pending", "Shipped", "Delivered", "Cancelled", "Refunded"]
PAYMENT_METHODS = ["Credit Card", "Debit Card", "PayPal", "Bank Transfer", "Apple Pay"]
UK_COUNTRIES = ["United Kingdom", "United Kingdom", "United Kingdom", "Ireland"]
EU_COUNTRIES = ["Germany", "France", "Netherlands", "Belgium", "Spain", "Italy", "Denmark", "Sweden", "Poland", "Austria"]
GENDERS = ["M", "F", "M", "F"]  # slight balance

random.seed(42)


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def generate_customers(n_customers):
    customers = []
    for i in range(1, n_customers + 1):
        is_uk = random.random() < 0.55
        region = "UK" if is_uk else "EU"
        if is_uk:
            first = random.choice(UK_FIRST_NAMES)
            last = random.choice(UK_LAST_NAMES)
            country = random.choice(UK_COUNTRIES)
            phone = f"+44 7{random.randint(100,999)} {random.randint(100,999)} {random.randint(1000,9999)}"
            domain = random.choice(["gmail.com", "yahoo.co.uk", "hotmail.co.uk", "outlook.com"])
        else:
            first = random.choice(EU_FIRST_NAMES)
            last = random.choice(EU_LAST_NAMES)
            country = random.choice(EU_COUNTRIES)
            phone = f"+{random.randint(31,49)} {random.randint(100,999)} {random.randint(100,999)} {random.randint(1000,9999)}"
            domain = random.choice(["gmail.com", "yahoo.fr", "web.de", "hotmail.com", "libero.it"])
        full_name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower().replace('ü','u').replace('ö','o').replace('é','e').replace('ø','o')}_{i}@{domain}"
        # Fix any double spaces or special chars in email
        email = email.replace(" ", ".")
        gender = random.choice(GENDERS)
        birth_year = random.randint(1950, 2005)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        dob = date(birth_year, birth_month, birth_day)
        created = date(2022, 1, 1) + timedelta(days=random.randint(0, 800))
        customers.append({
            "customer_id": f"CUST-{i:05d}",
            "customer_full_name": full_name,
            "customer_email": email,
            "customer_phone": phone,
            "country": country,
            "region": region,
            "gender": gender,
            "date_of_birth": dob.isoformat(),
            "created_at": created.isoformat(),
            "updated_at": created.isoformat(),
        })
    return customers


def generate_orders(customers, n_orders):
    orders = []
    for i in range(1, n_orders + 1):
        cust = random.choice(customers)
        product = random.choice(PRODUCTS)
        category, description, base_price = product
        qty = random.choices([1, 2, 3, 4, 6, 12, 24, 48], weights=[30, 20, 15, 10, 8, 7, 5, 5])[0]
        # Add some price variation
        unit_price = round(base_price * random.uniform(0.9, 1.2), 2)
        order_date = date(2022, 1, 1) + timedelta(days=random.randint(0, 1000))
        status = random.choices(
            ORDER_STATUSES, weights=[15, 25, 50, 5, 5]
        )[0]
        orders.append({
            "order_id": f"ORD-{i:05d}",
            "customer_id": cust["customer_id"],
            "order_date": order_date.isoformat(),
            "order_status": status,
            "payment_method": random.choice(PAYMENT_METHODS),
            "product_category": category,
            "product_description": description,
            "quantity": qty,
            "unit_price": f"{unit_price:.2f}",
            "region": cust["region"],
            "created_at": order_date.isoformat(),
        })
    return orders


# ---------------------------------------------------------------------------
# Postgres loading
# ---------------------------------------------------------------------------

def get_connection():
    if not DB_URL:
        raise RuntimeError("SUPABASE_DB_URL is not set in environment. Check your .env file.")
    return psycopg2.connect(DB_URL)


def truncate_tables(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE fct_orders RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE dim_customers RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE raw_orders CASCADE;")
        cur.execute("TRUNCATE TABLE raw_customers CASCADE;")
    conn.commit()


def load_raw_customers(conn, customers):
    with conn.cursor() as cur:
        for c in customers:
            cur.execute("""
                INSERT INTO raw_customers
                    (customer_id, customer_full_name, customer_email, customer_phone,
                     country, region, gender, date_of_birth, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (customer_id) DO NOTHING
            """, (
                c["customer_id"], c["customer_full_name"], c["customer_email"],
                c["customer_phone"], c["country"], c["region"], c["gender"],
                c["date_of_birth"], c["created_at"], c["updated_at"],
            ))
    conn.commit()
    print(f"  Loaded {len(customers)} raw customers into Postgres")


def load_raw_orders(conn, orders):
    with conn.cursor() as cur:
        for o in orders:
            cur.execute("""
                INSERT INTO raw_orders
                    (order_id, customer_id, order_date, order_status, payment_method,
                     product_category, product_description, quantity, unit_price, region, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (order_id) DO NOTHING
            """, (
                o["order_id"], o["customer_id"], o["order_date"], o["order_status"],
                o["payment_method"], o["product_category"], o["product_description"],
                o["quantity"], o["unit_price"], o["region"], o["created_at"],
            ))
    conn.commit()
    print(f"  Loaded {len(orders)} raw orders into Postgres")


def build_marts(conn):
    """Build dim_customers and fct_orders from raw tables (simulates dbt run in Postgres mode)."""
    with conn.cursor() as cur:
        # dim_customers
        cur.execute("""
            INSERT INTO dim_customers
                (customer_id, customer_full_name, customer_email, customer_phone,
                 country, region, customer_age, gender, customer_since)
            SELECT
                customer_id,
                customer_full_name,
                customer_email,
                customer_phone,
                country,
                region,
                EXTRACT(YEAR FROM age(date_of_birth))::INT AS customer_age,
                gender,
                created_at::date AS customer_since
            FROM raw_customers
            ORDER BY customer_id
            ON CONFLICT (customer_id) DO NOTHING
        """)
        n_dim = cur.rowcount
        conn.commit()

        # fct_orders
        cur.execute("""
            INSERT INTO fct_orders
                (order_id, customer_key, customer_id, order_date, order_status,
                 payment_method, product_category, product_description,
                 quantity, unit_price, gross_amount, tax_amount, total_amount, order_region)
            SELECT
                r.order_id,
                dc.customer_key,
                r.customer_id,
                r.order_date,
                r.order_status,
                r.payment_method,
                r.product_category,
                r.product_description,
                r.quantity,
                r.unit_price,
                ROUND(r.quantity * r.unit_price, 2) AS gross_amount,
                ROUND(r.quantity * r.unit_price * 0.20, 2) AS tax_amount,
                ROUND(r.quantity * r.unit_price * 1.20, 2) AS total_amount,
                r.region AS order_region
            FROM raw_orders r
            JOIN dim_customers dc ON dc.customer_id = r.customer_id
            ORDER BY r.order_id
            ON CONFLICT (order_id) DO NOTHING
        """)
        n_fct = cur.rowcount
        conn.commit()
    print(f"  Built dim_customers: {n_dim} rows, fct_orders: {n_fct} rows")


def print_analytics_summary(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT region, COUNT(*) FROM raw_customers GROUP BY region ORDER BY region")
        print("\n  Customers by region:")
        for row in cur.fetchall():
            print(f"    {row[0]}: {row[1]}")

        cur.execute("""
            SELECT order_region, COUNT(*), ROUND(SUM(quantity * unit_price), 2)
            FROM raw_orders GROUP BY order_region ORDER BY order_region
        """)
        print("  Orders by region:")
        for row in cur.fetchall():
            print(f"    {row[0]}: {row[1]} orders, revenue £{row[2]}")

        cur.execute("SELECT COUNT(*) FROM raw_customers")
        total_cust = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM raw_orders")
        total_ord = cur.fetchone()[0]
        print(f"\n  Total customers: {total_cust}")
        print(f"  Total orders: {total_ord}")


# ---------------------------------------------------------------------------
# Seed CSV export
# ---------------------------------------------------------------------------

def export_seed_csvs(customers, orders, output_dir):
    seed_dir = Path(output_dir)
    seed_dir.mkdir(parents=True, exist_ok=True)

    cust_path = seed_dir / "raw_customers.csv"
    with open(cust_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "customer_id", "customer_full_name", "customer_email", "customer_phone",
            "country", "region", "gender", "date_of_birth", "created_at", "updated_at",
        ])
        writer.writeheader()
        writer.writerows(customers)
    print(f"  Exported {len(customers)} rows → {cust_path}")

    ord_path = seed_dir / "raw_orders.csv"
    with open(ord_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "order_id", "customer_id", "order_date", "order_status", "payment_method",
            "product_category", "product_description", "quantity", "unit_price",
            "region", "created_at",
        ])
        writer.writeheader()
        writer.writerows(orders)
    print(f"  Exported {len(orders)} rows → {ord_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Load realistic e-commerce data into Postgres and export dbt seeds")
    parser.add_argument("--customers", type=int, default=1000, help="Number of customers to generate")
    parser.add_argument("--orders", type=int, default=5000, help="Number of orders to generate")
    parser.add_argument("--seed-dir", type=str, default="dbt_project/seeds", help="Output directory for seed CSVs")
    parser.add_argument("--no-db", action="store_true", help="Skip Postgres loading (only export CSVs)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Snowflake-dbt Governance Pipeline — Data Loader")
    print(f"  Customers: {args.customers} | Orders: {args.orders}")
    print(f"{'='*60}\n")

    print("  Generating synthetic data (based on UCI Online Retail II patterns)...")
    customers = generate_customers(args.customers)
    orders = generate_orders(customers, args.orders)
    print(f"  Generated {len(customers)} customers and {len(orders)} orders\n")

    if not args.no_db:
        print("  Connecting to Postgres (Supabase)...")
        try:
            conn = get_connection()
        except Exception as e:
            print(f"  ERROR: Could not connect to database: {e}")
            sys.exit(1)

        print("  Truncating existing tables...")
        truncate_tables(conn)

        print("  Loading raw data...")
        load_raw_customers(conn, customers)
        load_raw_orders(conn, orders)

        print("  Building marts (dim_customers, fct_orders)...")
        build_marts(conn)

        print_analytics_summary(conn)
        conn.close()
        print("\n  Postgres loading complete.\n")

    print("  Exporting dbt seed CSVs...")
    export_seed_csvs(customers, orders, args.seed_dir)

    print(f"\n{'='*60}")
    print("  Data loading complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
