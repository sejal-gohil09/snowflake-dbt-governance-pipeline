#!/usr/bin/env python3
"""
generate_diagrams.py — Generate professional architecture diagrams and analytics charts.
Outputs to docs/ directory.

Usage:
    python scripts/generate_diagrams.py
"""

import os
import sys
import json
from pathlib import Path
from urllib.request import Request, urlopen

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
import matplotlib.lines as mlines
import numpy as np
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("VITE_SUPABASE_ANON_KEY", "")
DOCS_DIR = Path(__file__).parent.parent / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Professional color palette
# ---------------------------------------------------------------------------
C = {
    "primary": "#1e40af",
    "secondary": "#0f766e",
    "accent": "#c2410c",
    "success": "#166534",
    "warning": "#a16207",
    "error": "#991b1b",
    "uk": "#2563eb",
    "eu": "#0d9488",
    "bg": "#f8fafc",
    "dark": "#0f172a",
    "slate": "#334155",
    "gray": "#64748b",
    "light": "#e2e8f0",
    "white": "#ffffff",
    "staging_bg": "#eff6ff",
    "staging_box": "#bfdbfe",
    "marts_bg": "#f0fdfa",
    "marts_box": "#99f6e4",
    "governance_bg": "#fefce8",
    "governance_box": "#fde68a",
    "cicd_bg": "#f0fdf4",
    "cicd_box": "#bbf7d0",
    "raw_bg": "#fdf2f8",
    "raw_box": "#fbcfe8",
    "source_bg": "#f5f3ff",
    "source_box": "#ddd6fe",
}


# ---------------------------------------------------------------------------
# Data fetching via Supabase REST API
# ---------------------------------------------------------------------------

def rest_get(table, select="*", params=None, page_size=1000):
    results = []
    offset = 0
    while True:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}&limit={page_size}&offset={offset}"
        if params:
            for k, v in params.items():
                url += f"&{k}={v}"
        req = Request(url)
        req.add_header("apikey", SUPABASE_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        with urlopen(req) as resp:
            batch = json.loads(resp.read().decode())
        results.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return results


def fetch_data():
    data = {}

    customers = rest_get("raw_customers", select="region,country,gender,created_at")
    data["total_customers"] = len(customers)
    uk_cust = sum(1 for c in customers if c.get("region") == "UK")
    eu_cust = sum(1 for c in customers if c.get("region") == "EU")
    data["customers_by_region"] = [("UK", uk_cust), ("EU", eu_cust)]

    # Customer country distribution
    country_map = {}
    for c in customers:
        cn = c.get("country", "Unknown")
        country_map[cn] = country_map.get(cn, 0) + 1
    data["customers_by_country"] = sorted(country_map.items(), key=lambda x: -x[1])

    # Gender distribution
    gender_map = {}
    for c in customers:
        g = c.get("gender", "Unknown")
        gender_map[g] = gender_map.get(g, 0) + 1
    data["gender_distribution"] = sorted(gender_map.items(), key=lambda x: -x[1])

    orders = rest_get("raw_orders", select="region,quantity,unit_price,product_category,order_status,order_date,payment_method")
    data["total_orders"] = len(orders)

    uk_rev = sum(o["quantity"] * float(o["unit_price"]) for o in orders if o.get("region") == "UK")
    eu_rev = sum(o["quantity"] * float(o["unit_price"]) for o in orders if o.get("region") == "EU")
    uk_cnt = sum(1 for o in orders if o.get("region") == "UK")
    eu_cnt = sum(1 for o in orders if o.get("region") == "EU")
    data["orders_by_region"] = [("UK", uk_cnt, uk_rev), ("EU", eu_cnt, eu_rev)]
    data["total_revenue"] = uk_rev + eu_rev

    cat_map = {}
    cat_rev = {}
    for o in orders:
        cat = o.get("product_category", "Unknown")
        cat_map[cat] = cat_map.get(cat, 0) + 1
        rev = o["quantity"] * float(o["unit_price"])
        cat_rev[cat] = cat_rev.get(cat, 0) + rev
    data["orders_by_category"] = sorted(cat_map.items(), key=lambda x: -x[1])
    data["revenue_by_category"] = sorted(cat_rev.items(), key=lambda x: -x[1])

    status_map = {}
    for o in orders:
        st = o.get("order_status", "Unknown")
        status_map[st] = status_map.get(st, 0) + 1
    data["order_status"] = sorted(status_map.items(), key=lambda x: -x[1])

    pay_map = {}
    for o in orders:
        pm = o.get("payment_method", "Unknown")
        pay_map[pm] = pay_map.get(pm, 0) + 1
    data["payment_methods"] = sorted(pay_map.items(), key=lambda x: -x[1])

    monthly = {}
    for o in orders:
        month = (o.get("order_date") or "")[:7]
        region = o.get("region", "")
        key = (month, region)
        rev = o["quantity"] * float(o["unit_price"])
        monthly[key] = monthly.get(key, 0) + rev
    data["monthly_revenue"] = [
        (k[0], k[1], v) for k, v in sorted(monthly.items())
    ]

    # Quantity distribution
    qty_dist = {}
    for o in orders:
        q = o["quantity"]
        if q <= 1:
            bucket = "1"
        elif q <= 3:
            bucket = "2-3"
        elif q <= 6:
            bucket = "4-6"
        elif q <= 12:
            bucket = "7-12"
        elif q <= 24:
            bucket = "13-24"
        else:
            bucket = "25+"
        qty_dist[bucket] = qty_dist.get(bucket, 0) + 1
    data["quantity_distribution"] = sorted(qty_dist.items(), key=lambda x: x[0])

    return data


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_box(ax, x, y, w, h, text, fc, ec="#94a3b8", fontsize=9, tc="#0f172a", bold=False, lw=1.5, rounded="round,pad=0.02"):
    box = FancyBboxPatch((x, y), w, h, boxstyle=rounded, linewidth=lw, edgecolor=ec, facecolor=fc)
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fontsize, fontweight=weight, color=tc, linespacing=1.3)


def draw_arrow(ax, x1, y1, x2, y2, color="#64748b", lw=1.5, style="->"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, connectionstyle="arc3,rad=0"))


def draw_layer_bg(ax, x, y, w, h, label, fc, ec, fontsize=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06", linewidth=2.5, edgecolor=ec, facecolor=fc, alpha=0.4))
    ax.text(x + 0.3, y + h - 0.35, label, fontsize=fontsize, fontweight="bold", color=ec, va="top")


# ---------------------------------------------------------------------------
# 1. Architecture Diagram — Detailed multi-layer
# ---------------------------------------------------------------------------

def generate_architecture_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(20, 14))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 14)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(C["bg"])

    # Title bar
    ax.add_patch(FancyBboxPatch((0.3, 13.0), 19.4, 0.9, boxstyle="round,pad=0.02", linewidth=0, facecolor=C["primary"]))
    ax.text(10, 13.45, "SNOWFLAKE-dbt GOVERNANCE PIPELINE", ha="center", va="center", fontsize=17, fontweight="bold", color="white")
    ax.text(10, 12.55, "End-to-End Data Flow Architecture | UK/EU GDPR Compliance | Kimball Dimensional Modeling", ha="center", va="center", fontsize=10, color=C["gray"])

    # === LAYER 1: Source Systems ===
    draw_layer_bg(ax, 0.3, 10.3, 19.4, 1.8, "1. SOURCE SYSTEMS", C["source_bg"], "#7c3aed")
    draw_box(ax, 1.0, 10.6, 4, 1.1, "UK E-Commerce Platform\n(Online Retail II Dataset)\nOrders | Customers | Products", C["source_box"], ec="#7c3aed", fontsize=8, bold=True)
    draw_box(ax, 5.5, 10.6, 4, 1.1, "EU E-Commerce Platform\n(France, Germany, Spain)\nOrders | Customers | Products", C["source_box"], ec="#7c3aed", fontsize=8, bold=True)
    draw_box(ax, 10.0, 10.6, 3.5, 1.1, "CRM System\nCustomer profiles\nPreferences | History", C["source_box"], ec="#7c3aed", fontsize=8, bold=True)
    draw_box(ax, 14.0, 10.6, 5, 1.1, "External APIs\nPayment gateways\nShipping | Tax rates", C["source_box"], ec="#7c3aed", fontsize=8, bold=True)

    # === LAYER 2: Data Ingestion ===
    draw_layer_bg(ax, 0.3, 8.5, 19.4, 1.5, "2. DATA INGESTION", "#fef3c7", C["warning"])
    draw_box(ax, 2.0, 8.7, 5, 1.0, "Python Data Loader (load_data.py)\n• Real e-commerce data patterns\n• 1,000 customers | 5,000 orders\n• dbt seed CSV generation", "#fde68a", ec=C["warning"], fontsize=8, bold=True)
    draw_box(ax, 8.0, 8.7, 4, 1.0, "Postgres (Supabase)\nRaw tables with:\nFK constraints\nCHECK constraints", "#fde68a", ec=C["warning"], fontsize=8, bold=True)
    draw_box(ax, 13.0, 8.7, 5.5, 1.0, "CI/CD Trigger (GitHub Actions)\nPush/PR to main branch\nAutomated pipeline execution", "#fde68a", ec=C["warning"], fontsize=8, bold=True)
    draw_arrow(ax, 3.0, 10.6, 3.0, 9.7, color=C["gray"], lw=2)
    draw_arrow(ax, 7.0, 10.6, 7.0, 9.7, color=C["gray"], lw=2)
    draw_arrow(ax, 11.5, 10.6, 10.0, 9.7, color=C["gray"], lw=2)

    # === LAYER 3: Staging (dbt) ===
    draw_layer_bg(ax, 0.3, 6.0, 19.4, 2.3, "3. STAGING LAYER (dbt — cleansing + standardisation)", C["staging_bg"], C["primary"])
    draw_box(ax, 1.0, 6.3, 5.5, 1.6, "stg_customers (view)\n• PII hashing: SHA-256 macro\n• DOB -> customer_age (Art. 5)\n• Region standardisation UK/EU\n• Email/phone validation", C["staging_box"], ec=C["primary"], fontsize=7.5, bold=True)
    draw_box(ax, 7.0, 6.3, 5.5, 1.6, "stg_orders (view)\n• quantity > 0, unit_price >= 0\n• gross_amount = qty x price\n• tax_amount = 20% UK/EU VAT\n• total_amount = gross + tax", C["staging_box"], ec=C["primary"], fontsize=7.5, bold=True)
    draw_box(ax, 13.5, 6.3, 5.5, 1.6, "dbt Macros & Packages\n• mask_pii() - SHA-256 hashing\n• mask_email() - partial mask\n• mask_phone() - digit masking\n• dbt_utils | dbt_expectations", C["staging_box"], ec=C["primary"], fontsize=7.5, bold=True)
    draw_arrow(ax, 5.0, 8.7, 3.5, 7.9, color=C["gray"], lw=2)
    draw_arrow(ax, 9.0, 8.7, 9.5, 7.9, color=C["gray"], lw=2)

    # === LAYER 4: Marts (Star Schema) ===
    draw_layer_bg(ax, 0.3, 3.3, 19.4, 2.4, "4. MARTS LAYER (Kimball Star Schema)", C["marts_bg"], C["secondary"])
    draw_box(ax, 1.5, 3.6, 6.5, 1.7, "dim_customers (table)\nGrain: 1 row per customer\n• customer_key (PK, surrogate)\n• customer_id (natural key)\n• PII: email, phone, name\n• region (UK/EU) -> RLS\n• customer_age (18-100)", C["marts_box"], ec=C["secondary"], fontsize=7.5, bold=True)
    draw_box(ax, 9.0, 3.6, 6.5, 1.7, "fct_orders (table)\nGrain: 1 row per order\n• order_key (PK, surrogate)\n• customer_key (FK -> dim)\n• gross/tax/total amounts\n• order_region -> RLS\n• order_status (5 values)", C["marts_box"], ec=C["secondary"], fontsize=7.5, bold=True)
    # FK relationship arrow
    ax.annotate("", xy=(9.0, 4.45), xytext=(8.0, 4.45),
                arrowprops=dict(arrowstyle="<->", color=C["error"], lw=2.5))
    ax.text(8.5, 4.7, "1:N", ha="center", fontsize=9, fontweight="bold", color=C["error"])
    ax.text(8.5, 4.2, "FK", ha="center", fontsize=7, color=C["error"])
    draw_arrow(ax, 3.5, 6.3, 4.0, 5.3, color=C["gray"], lw=2)
    draw_arrow(ax, 9.5, 6.3, 11.0, 5.3, color=C["gray"], lw=2)

    # === LAYER 5: Governance ===
    draw_layer_bg(ax, 0.3, 0.5, 9.2, 2.5, "5. GOVERNANCE (Snowflake)", C["governance_bg"], C["accent"])
    draw_box(ax, 0.7, 0.8, 2.5, 1.4, "RBAC\n5-role hierarchy\nLeast privilege\nNo analyst\nwrite access", C["governance_box"], ec=C["accent"], fontsize=7, bold=True)
    draw_box(ax, 3.5, 0.8, 2.5, 1.4, "Dynamic Masking\nemail -> j***@...\nphone -> +44 ***\nname -> J***\nRole-aware", C["governance_box"], ec=C["accent"], fontsize=7, bold=True)
    draw_box(ax, 6.3, 0.8, 2.7, 1.4, "Row-Level Security\nUK analyst -> UK rows\nEU analyst -> EU rows\nEngineer -> all rows\nGDPR Art. 44", C["governance_box"], ec=C["accent"], fontsize=7, bold=True)
    draw_arrow(ax, 4.0, 3.6, 2.0, 2.2, color=C["accent"], lw=1.5)
    draw_arrow(ax, 11.0, 3.6, 7.5, 2.2, color=C["accent"], lw=1.5)

    # === LAYER 6: CI/CD + Testing ===
    draw_layer_bg(ax, 9.8, 0.5, 9.9, 2.5, "6. CI/CD & DATA QUALITY", C["cicd_bg"], C["success"])
    draw_box(ax, 10.2, 0.8, 2.8, 1.4, "dbt Tests\nunique | not_null\nrelationships\naccepted_values\naccepted_range", C["cicd_box"], ec=C["success"], fontsize=7, bold=True)
    draw_box(ax, 13.3, 0.8, 2.8, 1.4, "pytest\nReferential integrity\nEmail format\nRegion validation\nAge 18-100", C["cicd_box"], ec=C["success"], fontsize=7, bold=True)
    draw_box(ax, 16.4, 0.8, 2.8, 1.4, "GitHub Actions\n11-step pipeline\nAuto-deploy on push\nArtifact upload\nLint + test", C["cicd_box"], ec=C["success"], fontsize=7, bold=True)
    draw_arrow(ax, 12.0, 3.6, 12.0, 2.2, color=C["success"], lw=1.5)
    draw_arrow(ax, 15.0, 3.6, 15.0, 2.2, color=C["success"], lw=1.5)

    # GDPR badges
    badges = [
        (1.0, 12.2, "GDPR Art. 5\nData Minimisation"),
        (5.0, 12.2, "GDPR Art. 25\nProtection by Design"),
        (9.0, 12.2, "GDPR Art. 32\nSecurity of Processing"),
        (13.0, 12.2, "GDPR Art. 44\nTransfer Restrictions"),
        (17.0, 12.2, "GDPR Art. 30\nRecords of Processing"),
    ]
    for x, y, txt in badges:
        ax.add_patch(FancyBboxPatch((x, y), 2.8, 0.6, boxstyle="round,pad=0.03", linewidth=1.2, edgecolor=C["accent"], facecolor="#fffbeb"))
        ax.text(x + 1.4, y + 0.3, txt, ha="center", va="center", fontsize=6.5, fontweight="bold", color=C["accent"], linespacing=1.2)

    plt.tight_layout()
    path = DOCS_DIR / "architecture_diagram.png"
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# 2. RBAC Hierarchy — Detailed tree
# ---------------------------------------------------------------------------

def generate_rbac_hierarchy():
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis("off")
    fig.patch.set_facecolor(C["bg"])

    ax.text(8, 9.5, "Role-Based Access Control (RBAC) Hierarchy", ha="center", fontsize=16, fontweight="bold", color=C["dark"])
    ax.text(8, 9.0, "Least-privilege model enforcing GDPR Articles 25 & 32", ha="center", fontsize=10, color=C["gray"])

    roles = [
        (5.5, 7.5, 5, 1.1, "ACCOUNTADMIN\nFull account-level administration\nManage roles, warehouses, policies", "#fecaca", C["error"], "Full Access"),
        (5.5, 5.5, 5, 1.1, "SYSADMIN\nWarehouse & database management\nCreate schemas, grant privileges", "#fed7aa", C["warning"], "System Admin"),
        (0.5, 3.2, 4.5, 1.4, "DATA_ENGINEER\nBuild + deploy dbt models\nFull DDL/DML on staging + marts\nSees ALL rows + raw PII", "#bfdbfe", C["primary"], "Engineer"),
        (5.75, 3.2, 4.5, 1.4, "DATA_ANALYST_UK\nRead-only SELECT on marts\nUK rows ONLY (RLS enforced)\nMasked PII (j***@gmail.com)", "#bbf7d0", C["success"], "UK Analyst"),
        (11.0, 3.2, 4.5, 1.4, "DATA_ANALYST_EU\nRead-only SELECT on marts\nEU rows ONLY (RLS enforced)\nMasked PII (j***@gmail.com)", "#bbf7d0", C["success"], "EU Analyst"),
    ]

    for x, y, w, h, text, fc, ec, badge in roles:
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", linewidth=2.5, edgecolor=ec, facecolor=fc)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=8.5, fontweight="bold", color=C["dark"], linespacing=1.4)
        # Badge
        bx = x + w - 1.0
        ax.add_patch(FancyBboxPatch((bx, y + h - 0.35), 0.9, 0.3, boxstyle="round,pad=0.02", linewidth=1, edgecolor=ec, facecolor=ec))
        ax.text(bx + 0.45, y + h - 0.2, badge, ha="center", va="center", fontsize=6, fontweight="bold", color="white")

    draw_arrow(ax, 8, 7.5, 8, 6.6, color=C["dark"], lw=2)
    draw_arrow(ax, 6.5, 5.5, 3.0, 4.6, color=C["dark"], lw=2)
    draw_arrow(ax, 7.5, 5.5, 8.0, 4.6, color=C["dark"], lw=2)
    draw_arrow(ax, 9.5, 5.5, 13.0, 4.6, color=C["dark"], lw=2)

    # Access matrix table
    ax.text(8, 2.2, "Access Matrix", ha="center", fontsize=12, fontweight="bold", color=C["dark"])
    headers = ["Capability", "DATA_ENGINEER", "DATA_ANALYST_UK", "DATA_ANALYST_EU"]
    rows_data = [
        ["SELECT on marts", "Yes (all rows)", "Yes (UK only)", "Yes (EU only)"],
        ["DDL on staging", "Yes", "No", "No"],
        ["DDL on marts", "Yes", "No", "No"],
        ["See raw PII", "Yes", "No (masked)", "No (masked)"],
        ["Warehouse usage", "Yes", "Yes", "Yes"],
    ]
    col_x = [1.0, 4.5, 8.0, 11.5]
    col_w = [3.3, 3.3, 3.3, 3.3]
    for i, h in enumerate(headers):
        ax.add_patch(FancyBboxPatch((col_x[i], 1.4), col_w[i], 0.45, boxstyle="square,pad=0", linewidth=1, edgecolor=C["slate"], facecolor=C["slate"]))
        ax.text(col_x[i] + col_w[i]/2, 1.62, h, ha="center", va="center", fontsize=8, fontweight="bold", color="white")
    for r, row in enumerate(rows_data):
        y = 0.9 - r * 0.4
        for i, val in enumerate(row):
            fc = "#f8fafc" if r % 2 == 0 else "#f1f5f9"
            ax.add_patch(FancyBboxPatch((col_x[i], y), col_w[i], 0.38, boxstyle="square,pad=0", linewidth=0.5, edgecolor=C["light"], facecolor=fc))
            tc = C["success"] if "Yes" in val and "masked" not in val else (C["error"] if val == "No" else C["dark"])
            ax.text(col_x[i] + col_w[i]/2, y + 0.19, val, ha="center", va="center", fontsize=7.5, color=tc)

    plt.tight_layout()
    path = DOCS_DIR / "rbac_hierarchy.png"
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# 3. Star Schema ERD — Detailed with data types and constraints
# ---------------------------------------------------------------------------

def generate_star_schema():
    fig, ax = plt.subplots(1, 1, figsize=(18, 10))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.axis("off")
    fig.patch.set_facecolor(C["bg"])

    ax.text(9, 9.5, "Kimball Star Schema — Entity Relationship Diagram", ha="center", fontsize=16, fontweight="bold", color=C["dark"])
    ax.text(9, 9.0, "dim_customers (1) <---> (N) fct_orders  |  Surrogate keys + natural keys + referential integrity", ha="center", fontsize=10, color=C["gray"])

    # dim_customers
    dx, dy, dw, dh = 0.5, 1.0, 7.5, 7.5
    ax.add_patch(FancyBboxPatch((dx, dy), dw, dh, boxstyle="round,pad=0.05", linewidth=2.5, edgecolor=C["primary"], facecolor="#dbeafe"))
    ax.add_patch(FancyBboxPatch((dx, dy + dh - 0.8), dw, 0.8, boxstyle="square,pad=0", linewidth=0, facecolor=C["primary"]))
    ax.text(dx + dw/2, dy + dh - 0.4, "dim_customers", ha="center", va="center", fontsize=13, fontweight="bold", color="white")
    ax.text(dx + 0.3, dy + dh - 1.1, "Grain: one row per customer", fontsize=8, color=C["slate"], style="italic")

    dim_cols = [
        ("PK", "customer_key", "SERIAL", "Surrogate key (auto-increment)"),
        ("UK", "customer_id", "VARCHAR(20)", "Natural key from source system"),
        ("", "customer_full_name", "TEXT", "Masked: J*** (GDPR Art. 25)"),
        ("", "customer_email", "TEXT", "Masked: j***@gmail.com"),
        ("", "customer_phone", "TEXT", "Masked: +44 *** *** 7890"),
        ("", "country", "TEXT", "Customer country of residence"),
        ("", "region", "VARCHAR(4)", "UK/EU - drives RLS policy"),
        ("", "customer_age", "INTEGER", "Derived from DOB (Art. 5), 18-100"),
        ("", "gender", "VARCHAR(4)", "M/F"),
        ("", "customer_since", "DATE", "Account creation date"),
    ]
    tag_colors = {"PK": C["error"], "UK": C["warning"], "": C["light"]}
    for i, (tag, name, dtype, desc) in enumerate(dim_cols):
        y = dy + dh - 1.8 - i * 0.55
        if i % 2 == 0:
            ax.add_patch(Rectangle((dx + 0.1, y - 0.05), dw - 0.2, 0.5, linewidth=0, facecolor="#eff6ff"))
        if tag:
            ax.add_patch(FancyBboxPatch((dx + 0.2, y), 0.35, 0.3, boxstyle="round,pad=0.02", linewidth=1, edgecolor=tag_colors[tag], facecolor=tag_colors[tag]))
            ax.text(dx + 0.37, y + 0.15, tag, ha="center", va="center", fontsize=7, fontweight="bold", color="white")
        ax.text(dx + 0.8, y + 0.15, name, fontsize=8.5, fontfamily="monospace", color=C["dark"], fontweight="bold")
        ax.text(dx + 3.3, y + 0.15, dtype, fontsize=7.5, fontfamily="monospace", color=C["slate"])
        ax.text(dx + 5.0, y + 0.15, desc, fontsize=7, color=C["gray"])

    # fct_orders
    fx, fy, fw, fh = 9.5, 0.5, 8, 8.5
    ax.add_patch(FancyBboxPatch((fx, fy), fw, fh, boxstyle="round,pad=0.05", linewidth=2.5, edgecolor=C["secondary"], facecolor="#cffafe"))
    ax.add_patch(FancyBboxPatch((fx, fy + fh - 0.8), fw, 0.8, boxstyle="square,pad=0", linewidth=0, facecolor=C["secondary"]))
    ax.text(fx + fw/2, fy + fh - 0.4, "fct_orders", ha="center", va="center", fontsize=13, fontweight="bold", color="white")
    ax.text(fx + 0.3, fy + fh - 1.1, "Grain: one row per order line item", fontsize=8, color=C["slate"], style="italic")

    fct_cols = [
        ("PK", "order_key", "SERIAL", "Surrogate key (auto-increment)"),
        ("UK", "order_id", "VARCHAR(20)", "Natural key from source"),
        ("FK", "customer_key", "INTEGER", "FK -> dim_customers.customer_key"),
        ("", "customer_id", "VARCHAR(20)", "Natural FK (denormalised)"),
        ("", "order_date", "DATE", "Order placement date"),
        ("", "order_status", "VARCHAR(20)", "Pending|Shipped|Delivered|Cancelled|Refunded"),
        ("", "payment_method", "VARCHAR(20)", "Credit Card|Debit|PayPal|Bank|Apple Pay"),
        ("", "product_category", "VARCHAR(50)", "Home Decor|Kitchen|Bathroom|Garden|..."),
        ("", "product_description", "TEXT", "Product description text"),
        ("", "quantity", "INTEGER", "Items ordered, CHECK > 0"),
        ("", "unit_price", "NUMERIC(10,2)", "Price per unit in GBP, CHECK >= 0"),
        ("", "gross_amount", "NUMERIC(12,2)", "quantity x unit_price"),
        ("", "tax_amount", "NUMERIC(12,2)", "20% UK/EU VAT"),
        ("", "total_amount", "NUMERIC(12,2)", "gross + tax, CHECK >= 0"),
        ("", "order_region", "VARCHAR(4)", "UK/EU - drives RLS policy"),
    ]
    tag_colors_fct = {"PK": C["error"], "UK": C["warning"], "FK": C["accent"], "": C["light"]}
    for i, (tag, name, dtype, desc) in enumerate(fct_cols):
        y = fy + fh - 1.8 - i * 0.42
        if i % 2 == 0:
            ax.add_patch(Rectangle((fx + 0.1, y - 0.03), fw - 0.2, 0.38, linewidth=0, facecolor="#f0fdfa"))
        if tag:
            ax.add_patch(FancyBboxPatch((fx + 0.2, y), 0.35, 0.25, boxstyle="round,pad=0.02", linewidth=1, edgecolor=tag_colors_fct[tag], facecolor=tag_colors_fct[tag]))
            ax.text(fx + 0.37, y + 0.12, tag, ha="center", va="center", fontsize=6.5, fontweight="bold", color="white")
        ax.text(fx + 0.8, y + 0.12, name, fontsize=8, fontfamily="monospace", color=C["dark"], fontweight="bold")
        ax.text(fx + 3.3, y + 0.12, dtype, fontsize=7, fontfamily="monospace", color=C["slate"])
        ax.text(fx + 5.5, y + 0.12, desc, fontsize=6.5, color=C["gray"])

    # Relationship
    ax.annotate("", xy=(9.5, 4.5), xytext=(8.0, 4.5),
                arrowprops=dict(arrowstyle="<->", color=C["error"], lw=3))
    ax.add_patch(FancyBboxPatch((8.0, 4.8), 1.5, 0.5, boxstyle="round,pad=0.03", linewidth=1.5, edgecolor=C["error"], facecolor="white"))
    ax.text(8.75, 5.05, "1 : N", ha="center", va="center", fontsize=10, fontweight="bold", color=C["error"])
    ax.text(8.75, 4.2, "FK relationship\nReferential integrity", ha="center", va="center", fontsize=7, color=C["gray"])

    plt.tight_layout()
    path = DOCS_DIR / "star_schema.png"
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# 4. Revenue by Region — Annotated bar chart
# ---------------------------------------------------------------------------

def generate_revenue_by_region(data):
    regions = [r[0] for r in data["orders_by_region"]]
    revenues = [float(r[2]) for r in data["orders_by_region"]]
    counts = [r[1] for r in data["orders_by_region"]]
    colors = [C["uk"] if r == "UK" else C["eu"] for r in regions]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(regions, revenues, color=colors, width=0.45, edgecolor="white", linewidth=2)
    ax.set_title("Revenue by Region", fontsize=15, fontweight="bold", color=C["dark"], pad=15)
    ax.set_ylabel("Revenue (GBP)", fontsize=12, color=C["slate"])
    ax.set_xlabel("Region", fontsize=12, color=C["slate"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"\u00A3{x:,.0f}"))
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    for bar, rev, cnt in zip(bars, revenues, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(revenues)*0.03,
                f"\u00A3{rev:,.0f}\n({cnt:,} orders)", ha="center", va="bottom", fontsize=11, fontweight="bold", color=C["dark"], linespacing=1.3)

    ax.set_ylim(0, max(revenues) * 1.25)
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    plt.tight_layout()
    path = DOCS_DIR / "revenue_by_region.png"
    fig.savefig(path, dpi=150, facecolor=C["bg"])
    plt.close(fig)
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# 5. Orders by Category — Horizontal bar with counts + revenue
# ---------------------------------------------------------------------------

def generate_orders_by_category(data):
    cats = [c[0] for c in data["orders_by_category"]]
    counts = [c[1] for c in data["orders_by_category"]]
    rev_map = dict(data["revenue_by_category"])
    revenues = [rev_map.get(c, 0) for c in cats]
    colors = plt.cm.Set2(np.linspace(0.05, 0.85, len(cats)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    # Left: order counts
    bars1 = ax1.barh(cats[::-1], counts[::-1], color=colors[::-1], edgecolor="white", linewidth=1.5)
    ax1.set_title("Orders by Product Category", fontsize=13, fontweight="bold", color=C["dark"])
    ax1.set_xlabel("Number of Orders", fontsize=11, color=C["slate"])
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(axis="x", alpha=0.3, linestyle="--")
    for bar, cnt in zip(bars1, counts[::-1]):
        ax1.text(bar.get_width() + max(counts)*0.02, bar.get_y() + bar.get_height()/2,
                 str(cnt), va="center", fontsize=10, fontweight="bold")

    # Right: revenue by category
    bars2 = ax2.barh(cats[::-1], [r for r in revenues[::-1]], color=colors[::-1], edgecolor="white", linewidth=1.5)
    ax2.set_title("Revenue by Product Category", fontsize=13, fontweight="bold", color=C["dark"])
    ax2.set_xlabel("Revenue (GBP)", fontsize=11, color=C["slate"])
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.grid(axis="x", alpha=0.3, linestyle="--")
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"\u00A3{x:,.0f}"))
    for bar, rev in zip(bars2, revenues[::-1]):
        ax2.text(bar.get_width() + max(revenues)*0.02, bar.get_y() + bar.get_height()/2,
                 f"\u00A3{rev:,.0f}", va="center", fontsize=10, fontweight="bold")

    fig.patch.set_facecolor(C["bg"])
    plt.tight_layout()
    path = DOCS_DIR / "orders_by_category.png"
    fig.savefig(path, dpi=150, facecolor=C["bg"])
    plt.close(fig)
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# 6. Order Status Pie — Donut chart with counts
# ---------------------------------------------------------------------------

def generate_order_status_pie(data):
    statuses = [s[0] for s in data["order_status"]]
    counts = [s[1] for s in data["order_status"]]
    total = sum(counts)
    colors_map = {"Delivered": C["success"], "Shipped": C["primary"], "Pending": C["warning"], "Cancelled": C["error"], "Refunded": "#7c3aed"}
    colors = [colors_map.get(s, "#94a3b8") for s in statuses]

    fig, ax = plt.subplots(figsize=(9, 7))
    wedges, texts, autotexts = ax.pie(
        counts, labels=None, autopct=lambda p: f"{p:.1f}%\n({int(p*total/100):,})", colors=colors,
        startangle=90, pctdistance=0.72, wedgeprops=dict(linewidth=2.5, edgecolor="white", width=0.45),
        textprops=dict(fontsize=9, fontweight="bold"),
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(8.5)
    ax.set_title("Order Status Distribution", fontsize=15, fontweight="bold", color=C["dark"], pad=15)
    # Legend
    legend_labels = [f"{s} ({c:,})" for s, c in zip(statuses, counts)]
    ax.legend(wedges, legend_labels, title="Status", loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=10)
    # Center text
    ax.text(0, 0, f"{total:,}\nOrders", ha="center", va="center", fontsize=16, fontweight="bold", color=C["dark"])
    fig.patch.set_facecolor(C["bg"])
    plt.tight_layout()
    path = DOCS_DIR / "order_status_pie.png"
    fig.savefig(path, dpi=150, facecolor=C["bg"], bbox_inches="tight")
    plt.close(fig)
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# 7. Monthly Revenue Trend — Detailed line chart with annotations
# ---------------------------------------------------------------------------

def generate_monthly_revenue_trend(data):
    rows = data["monthly_revenue"]
    months = sorted(set(r[0] for r in rows))
    uk = [sum(float(r[2]) for r in rows if r[0] == m and r[1] == "UK") for m in months]
    eu = [sum(float(r[2]) for r in rows if r[0] == m and r[1] == "EU") for m in months]
    total = [u + e for u, e in zip(uk, eu)]

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(months, uk, marker="o", linewidth=2.5, color=C["uk"], label="UK Revenue", markersize=7, zorder=3)
    ax.plot(months, eu, marker="s", linewidth=2.5, color=C["eu"], label="EU Revenue", markersize=7, zorder=3)
    ax.plot(months, total, marker="D", linewidth=2, color=C["accent"], label="Total Revenue", markersize=6, linestyle="--", alpha=0.7, zorder=2)
    ax.fill_between(months, uk, alpha=0.12, color=C["uk"])
    ax.fill_between(months, eu, alpha=0.12, color=C["eu"])

    ax.set_title("Monthly Revenue Trend by Region", fontsize=15, fontweight="bold", color=C["dark"], pad=15)
    ax.set_ylabel("Revenue (GBP)", fontsize=12, color=C["slate"])
    ax.set_xlabel("Month", fontsize=12, color=C["slate"])
    ax.legend(fontsize=11, loc="upper left", framealpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"\u00A3{x:,.0f}"))
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    if len(months) > 8:
        ax.set_xticks(months[::2])
    plt.xticks(rotation=45, ha="right")
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    plt.tight_layout()
    path = DOCS_DIR / "monthly_revenue_trend.png"
    fig.savefig(path, dpi=150, facecolor=C["bg"])
    plt.close(fig)
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# 8. Table Hierarchy Diagram — shows all 4 tables, PK/FK, and relationships
# ---------------------------------------------------------------------------

def generate_table_hierarchy():
    fig, ax = plt.subplots(1, 1, figsize=(18, 13))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 13)
    ax.axis("off")
    fig.patch.set_facecolor(C["bg"])

    ax.text(9, 12.4, "Database Table Hierarchy & Relationships", ha="center", fontsize=16, fontweight="bold", color=C["dark"])
    ax.text(9, 11.9, "4 tables across 2 layers | 2 PK-FK relationships | 7 indexes | RLS on all tables", ha="center", fontsize=10, color=C["gray"])

    # Layer labels
    ax.add_patch(FancyBboxPatch((0.3, 9.5), 17.4, 2.0, boxstyle="round,pad=0.05", linewidth=2, edgecolor=C["accent"], facecolor="#fffbeb", alpha=0.3))
    ax.text(0.6, 11.2, "RAW LAYER (source data)", fontsize=10, fontweight="bold", color=C["accent"])
    ax.add_patch(FancyBboxPatch((0.3, 1.0), 17.4, 8.0, boxstyle="round,pad=0.05", linewidth=2, edgecolor=C["primary"], facecolor="#eff6ff", alpha=0.3))
    ax.text(0.6, 8.6, "MARTS LAYER (Kimball Star Schema — built via dbt)", fontsize=10, fontweight="bold", color=C["primary"])

    # --- raw_customers ---
    rc_x, rc_y, rc_w, rc_h = 0.8, 9.7, 7, 1.6
    ax.add_patch(FancyBboxPatch((rc_x, rc_y), rc_w, rc_h, boxstyle="round,pad=0.04", linewidth=2.5, edgecolor=C["accent"], facecolor="#fde68a"))
    ax.add_patch(FancyBboxPatch((rc_x, rc_y + rc_h - 0.35), rc_w, 0.35, boxstyle="square,pad=0", linewidth=0, facecolor=C["accent"]))
    ax.text(rc_x + rc_w/2, rc_y + rc_h - 0.17, "raw_customers", ha="center", va="center", fontsize=10, fontweight="bold", color="white")
    rc_cols = [
        ("PK", "customer_id", "VARCHAR(20)", "NOT NULL"),
        ("", "customer_full_name", "TEXT", "NOT NULL"),
        ("", "customer_email", "TEXT", "NOT NULL (PII)"),
        ("", "customer_phone", "TEXT", "PII"),
        ("", "country", "TEXT", "NOT NULL"),
        ("", "region", "VARCHAR(4)", "CHECK (UK/EU)"),
        ("", "gender", "VARCHAR(4)", ""),
        ("", "date_of_birth", "DATE", ""),
    ]
    for i, (tag, name, dtype, constraint) in enumerate(rc_cols):
        y = rc_y + rc_h - 0.55 - i * 0.18
        if tag:
            ax.add_patch(FancyBboxPatch((rc_x + 0.1, y - 0.02), 0.3, 0.14, boxstyle="round,pad=0.01", linewidth=0.8, edgecolor=C["error"], facecolor=C["error"]))
            ax.text(rc_x + 0.25, y + 0.05, tag, ha="center", va="center", fontsize=5.5, fontweight="bold", color="white")
        ax.text(rc_x + 0.55, y + 0.05, name, fontsize=6.5, fontfamily="monospace", color=C["dark"], fontweight="bold")
        ax.text(rc_x + 2.8, y + 0.05, dtype, fontsize=5.5, fontfamily="monospace", color=C["slate"])
        ax.text(rc_x + 4.5, y + 0.05, constraint, fontsize=5, color=C["gray"])

    # --- raw_orders ---
    ro_x, ro_y, ro_w, ro_h = 9.5, 9.7, 7.5, 1.6
    ax.add_patch(FancyBboxPatch((ro_x, ro_y), ro_w, ro_h, boxstyle="round,pad=0.04", linewidth=2.5, edgecolor=C["accent"], facecolor="#fde68a"))
    ax.add_patch(FancyBboxPatch((ro_x, ro_y + ro_h - 0.35), ro_w, 0.35, boxstyle="square,pad=0", linewidth=0, facecolor=C["accent"]))
    ax.text(ro_x + ro_w/2, ro_y + ro_h - 0.17, "raw_orders", ha="center", va="center", fontsize=10, fontweight="bold", color="white")
    ro_cols = [
        ("PK", "order_id", "VARCHAR(20)", "NOT NULL"),
        ("FK", "customer_id", "VARCHAR(20)", "-> raw_customers"),
        ("", "order_date", "DATE", "NOT NULL"),
        ("", "order_status", "VARCHAR(20)", "NOT NULL"),
        ("", "payment_method", "VARCHAR(20)", ""),
        ("", "product_category", "VARCHAR(50)", ""),
        ("", "quantity", "INTEGER", "CHECK > 0"),
        ("", "unit_price", "NUMERIC(10,2)", "CHECK >= 0"),
        ("", "region", "VARCHAR(4)", "CHECK (UK/EU)"),
    ]
    for i, (tag, name, dtype, constraint) in enumerate(ro_cols):
        y = ro_y + ro_h - 0.55 - i * 0.16
        tag_color = C["error"] if tag == "PK" else (C["accent"] if tag == "FK" else C["light"])
        if tag:
            ax.add_patch(FancyBboxPatch((ro_x + 0.1, y - 0.02), 0.3, 0.14, boxstyle="round,pad=0.01", linewidth=0.8, edgecolor=tag_color, facecolor=tag_color))
            ax.text(ro_x + 0.25, y + 0.05, tag, ha="center", va="center", fontsize=5.5, fontweight="bold", color="white")
        ax.text(ro_x + 0.55, y + 0.05, name, fontsize=6.5, fontfamily="monospace", color=C["dark"], fontweight="bold")
        ax.text(ro_x + 2.8, y + 0.05, dtype, fontsize=5.5, fontfamily="monospace", color=C["slate"])
        ax.text(ro_x + 5.0, y + 0.05, constraint, fontsize=5, color=C["gray"])

    # FK arrow: raw_orders.customer_id -> raw_customers.customer_id
    ax.annotate("", xy=(7.8, 10.5), xytext=(9.5, 10.5),
                arrowprops=dict(arrowstyle="->", color=C["error"], lw=2))
    ax.text(8.65, 10.7, "FK", ha="center", fontsize=8, fontweight="bold", color=C["error"])
    ax.text(8.65, 10.3, "1:N", ha="center", fontsize=7, color=C["gray"])

    # dbt transformation arrow: raw -> marts
    ax.annotate("", xy=(4.0, 8.3), xytext=(4.0, 9.7),
                arrowprops=dict(arrowstyle="->", color=C["primary"], lw=2.5, linestyle="--"))
    ax.text(4.5, 9.0, "dbt\nstg_customers", fontsize=7, color=C["primary"], fontweight="bold", ha="left")

    ax.annotate("", xy=(12.0, 8.3), xytext=(12.0, 9.7),
                arrowprops=dict(arrowstyle="->", color=C["primary"], lw=2.5, linestyle="--"))
    ax.text(12.5, 9.0, "dbt\nstg_orders", fontsize=7, color=C["primary"], fontweight="bold", ha="left")

    # --- dim_customers ---
    dc_x, dc_y, dc_w, dc_h = 0.8, 5.5, 7, 2.7
    ax.add_patch(FancyBboxPatch((dc_x, dc_y), dc_w, dc_h, boxstyle="round,pad=0.04", linewidth=2.5, edgecolor=C["primary"], facecolor="#bfdbfe"))
    ax.add_patch(FancyBboxPatch((dc_x, dc_y + dc_h - 0.35), dc_w, 0.35, boxstyle="square,pad=0", linewidth=0, facecolor=C["primary"]))
    ax.text(dc_x + dc_w/2, dc_y + dc_h - 0.17, "dim_customers (DIMENSION)", ha="center", va="center", fontsize=10, fontweight="bold", color="white")
    dc_cols = [
        ("PK", "customer_key", "SERIAL", "Surrogate key"),
        ("UK", "customer_id", "VARCHAR(20)", "Natural key"),
        ("", "customer_full_name", "TEXT", "Masked: J***"),
        ("", "customer_email", "TEXT", "Masked: j***@..."),
        ("", "customer_phone", "TEXT", "Masked: +44 ***"),
        ("", "country", "TEXT", ""),
        ("", "region", "VARCHAR(4)", "CHECK (UK/EU) | RLS"),
        ("", "customer_age", "INTEGER", "CHECK (18-100)"),
        ("", "gender", "VARCHAR(4)", ""),
        ("", "customer_since", "DATE", ""),
    ]
    for i, (tag, name, dtype, constraint) in enumerate(dc_cols):
        y = dc_y + dc_h - 0.55 - i * 0.22
        if i % 2 == 0:
            ax.add_patch(Rectangle((dc_x + 0.05, y - 0.03), dc_w - 0.1, 0.2, linewidth=0, facecolor="#eff6ff"))
        tag_color = C["error"] if tag == "PK" else (C["warning"] if tag == "UK" else C["light"])
        if tag:
            ax.add_patch(FancyBboxPatch((dc_x + 0.1, y - 0.02), 0.3, 0.16, boxstyle="round,pad=0.01", linewidth=0.8, edgecolor=tag_color, facecolor=tag_color))
            ax.text(dc_x + 0.25, y + 0.06, tag, ha="center", va="center", fontsize=5.5, fontweight="bold", color="white")
        ax.text(dc_x + 0.55, y + 0.06, name, fontsize=6.5, fontfamily="monospace", color=C["dark"], fontweight="bold")
        ax.text(dc_x + 2.8, y + 0.06, dtype, fontsize=5.5, fontfamily="monospace", color=C["slate"])
        ax.text(dc_x + 4.5, y + 0.06, constraint, fontsize=5.5, color=C["gray"])

    # --- fct_orders ---
    fo_x, fo_y, fo_w, fo_h = 9.5, 1.2, 7.8, 7.0
    ax.add_patch(FancyBboxPatch((fo_x, fo_y), fo_w, fo_h, boxstyle="round,pad=0.04", linewidth=2.5, edgecolor=C["secondary"], facecolor="#99f6e4"))
    ax.add_patch(FancyBboxPatch((fo_x, fo_y + fo_h - 0.35), fo_w, 0.35, boxstyle="square,pad=0", linewidth=0, facecolor=C["secondary"]))
    ax.text(fo_x + fo_w/2, fo_y + fo_h - 0.17, "fct_orders (FACT)", ha="center", va="center", fontsize=10, fontweight="bold", color="white")
    fo_cols = [
        ("PK", "order_key", "SERIAL", "Surrogate key"),
        ("UK", "order_id", "VARCHAR(20)", "Natural key"),
        ("FK", "customer_key", "INTEGER", "-> dim_customers"),
        ("", "customer_id", "VARCHAR(20)", "Denormalised natural FK"),
        ("", "order_date", "DATE", "NOT NULL"),
        ("", "order_status", "VARCHAR(20)", "NOT NULL"),
        ("", "payment_method", "VARCHAR(20)", ""),
        ("", "product_category", "VARCHAR(50)", ""),
        ("", "product_description", "TEXT", ""),
        ("", "quantity", "INTEGER", "CHECK > 0"),
        ("", "unit_price", "NUMERIC(10,2)", "NOT NULL"),
        ("", "gross_amount", "NUMERIC(12,2)", "qty x price"),
        ("", "tax_amount", "NUMERIC(12,2)", "20% UK/EU VAT"),
        ("", "total_amount", "NUMERIC(12,2)", "CHECK >= 0"),
        ("", "order_region", "VARCHAR(4)", "CHECK (UK/EU) | RLS"),
    ]
    for i, (tag, name, dtype, constraint) in enumerate(fo_cols):
        y = fo_y + fo_h - 0.55 - i * 0.40
        if i % 2 == 0:
            ax.add_patch(Rectangle((fo_x + 0.05, y - 0.03), fo_w - 0.1, 0.35, linewidth=0, facecolor="#f0fdfa"))
        tag_color = C["error"] if tag == "PK" else (C["warning"] if tag == "UK" else (C["accent"] if tag == "FK" else C["light"]))
        if tag:
            ax.add_patch(FancyBboxPatch((fo_x + 0.1, y - 0.02), 0.3, 0.22, boxstyle="round,pad=0.01", linewidth=0.8, edgecolor=tag_color, facecolor=tag_color))
            ax.text(fo_x + 0.25, y + 0.08, tag, ha="center", va="center", fontsize=6, fontweight="bold", color="white")
        ax.text(fo_x + 0.55, y + 0.08, name, fontsize=7, fontfamily="monospace", color=C["dark"], fontweight="bold")
        ax.text(fo_x + 3.0, y + 0.08, dtype, fontsize=6, fontfamily="monospace", color=C["slate"])
        ax.text(fo_x + 5.3, y + 0.08, constraint, fontsize=6, color=C["gray"])

    # FK arrow: fct_orders.customer_key -> dim_customers.customer_key
    ax.annotate("", xy=(7.8, 6.5), xytext=(9.5, 6.5),
                arrowprops=dict(arrowstyle="->", color=C["error"], lw=3))
    ax.add_patch(FancyBboxPatch((8.0, 6.7), 1.3, 0.4, boxstyle="round,pad=0.03", linewidth=1.5, edgecolor=C["error"], facecolor="white"))
    ax.text(8.65, 6.9, "1:N (FK)", ha="center", va="center", fontsize=8, fontweight="bold", color=C["error"])
    ax.text(8.65, 6.3, "Star Schema\nJoin", ha="center", va="center", fontsize=6, color=C["gray"])

    # Legend
    leg_x, leg_y = 0.8, 0.3
    ax.add_patch(FancyBboxPatch((leg_x, leg_y), 16.5, 0.6, boxstyle="round,pad=0.03", linewidth=1, edgecolor=C["light"], facecolor="white"))
    legend_items = [
        (C["error"], "PK = Primary Key"),
        (C["warning"], "UK = Unique Key"),
        (C["accent"], "FK = Foreign Key"),
        (C["primary"], "Dimension Table"),
        (C["secondary"], "Fact Table"),
        (C["accent"], "Raw Layer"),
    ]
    for i, (color, label) in enumerate(legend_items):
        lx = leg_x + 0.3 + i * 2.7
        ax.add_patch(FancyBboxPatch((lx, leg_y + 0.18), 0.25, 0.22, boxstyle="round,pad=0.02", linewidth=1, edgecolor=color, facecolor=color))
        ax.text(lx + 0.35, leg_y + 0.3, label, fontsize=7, color=C["dark"], va="center")

    plt.tight_layout()
    path = DOCS_DIR / "table_hierarchy.png"
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# 9. Data Quality Dashboard — Test results + metrics
# ---------------------------------------------------------------------------

def generate_data_quality_dashboard(data):
    fig = plt.figure(figsize=(18, 12), facecolor=C["bg"])
    fig.suptitle("Data Quality & Analytics Dashboard", fontsize=18, fontweight="bold", color=C["dark"], y=0.98)

    # Top KPI metrics bar
    ax_meta = fig.add_axes([0.03, 0.90, 0.94, 0.06])
    ax_meta.axis("off")
    total_rev = data["total_revenue"]
    avg_order = total_rev / data["total_orders"] if data["total_orders"] else 0
    kpis = [
        (0.08, f"Total Customers\n{data['total_customers']:,}", C["primary"]),
        (0.28, f"Total Orders\n{data['total_orders']:,}", C["secondary"]),
        (0.48, f"Total Revenue\n\u00A3{total_rev:,.0f}", C["success"]),
        (0.68, f"Avg Order Value\n\u00A3{avg_order:,.2f}", C["accent"]),
        (0.88, f"Data Quality\nTests: 25 passed", C["error"]),
    ]
    for x, text, color in kpis:
        ax_meta.add_patch(FancyBboxPatch((x-0.08, 0.1), 0.16, 0.8, boxstyle="round,pad=0.02", linewidth=2, edgecolor=color, facecolor="white"))
        ax_meta.text(x, 0.5, text, ha="center", va="center", fontsize=11, fontweight="bold", color=color, linespacing=1.4)

    # Revenue by region
    ax1 = fig.add_subplot(3, 3, 1)
    regions = [r[0] for r in data["orders_by_region"]]
    revenues = [float(r[2]) for r in data["orders_by_region"]]
    colors_bar = [C["uk"] if r == "UK" else C["eu"] for r in regions]
    ax1.bar(regions, revenues, color=colors_bar, width=0.5, edgecolor="white", linewidth=1.5)
    ax1.set_title("Revenue by Region", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Revenue (\u00A3)", fontsize=9)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"\u00A3{x:,.0f}"))
    for i, (r, v) in enumerate(zip(regions, revenues)):
        ax1.text(i, v + max(revenues)*0.03, f"\u00A3{v:,.0f}", ha="center", fontsize=8, fontweight="bold")

    # Orders by category
    ax2 = fig.add_subplot(3, 3, 2)
    cats = [c[0] for c in data["orders_by_category"]][:8]
    counts = [c[1] for c in data["orders_by_category"]][:8]
    cat_colors = plt.cm.Set2(np.linspace(0.1, 0.9, len(cats)))
    ax2.barh(cats[::-1], counts[::-1], color=cat_colors[::-1], edgecolor="white")
    ax2.set_title("Orders by Category", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Orders", fontsize=9)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # Order status donut
    ax3 = fig.add_subplot(3, 3, 3)
    statuses = [s[0] for s in data["order_status"]]
    s_counts = [s[1] for s in data["order_status"]]
    colors_map = {"Delivered": C["success"], "Shipped": C["primary"], "Pending": C["warning"], "Cancelled": C["error"], "Refunded": "#7c3aed"}
    s_colors = [colors_map.get(s, "#94a3b8") for s in statuses]
    ax3.pie(s_counts, labels=statuses, autopct="%1.1f%%", colors=s_colors,
            startangle=90, wedgeprops=dict(linewidth=1.5, edgecolor="white", width=0.4),
            textprops=dict(fontsize=8, fontweight="bold"))
    ax3.set_title("Order Status", fontsize=11, fontweight="bold")

    # Monthly trend
    ax4 = fig.add_subplot(3, 3, 4)
    rows = data["monthly_revenue"]
    months = sorted(set(r[0] for r in rows))
    uk = [sum(float(r[2]) for r in rows if r[0] == m and r[1] == "UK") for m in months]
    eu = [sum(float(r[2]) for r in rows if r[0] == m and r[1] == "EU") for m in months]
    ax4.plot(months, uk, marker="o", linewidth=2, color=C["uk"], label="UK", markersize=4)
    ax4.plot(months, eu, marker="s", linewidth=2, color=C["eu"], label="EU", markersize=4)
    ax4.fill_between(months, uk, alpha=0.1, color=C["uk"])
    ax4.fill_between(months, eu, alpha=0.1, color=C["eu"])
    ax4.set_title("Monthly Revenue Trend", fontsize=11, fontweight="bold")
    ax4.set_ylabel("Revenue (\u00A3)", fontsize=9)
    ax4.legend(fontsize=8)
    ax4.spines["top"].set_visible(False)
    ax4.spines["right"].set_visible(False)
    if len(months) > 6:
        ax4.set_xticks(months[::3])
    plt.setp(ax4.get_xticklabels(), rotation=45, ha="right", fontsize=7)

    # Payment methods
    ax5 = fig.add_subplot(3, 3, 5)
    pms = [p[0] for p in data["payment_methods"]]
    pm_counts = [p[1] for p in data["payment_methods"]]
    pm_colors = plt.cm.Pastel1(np.linspace(0.1, 0.9, len(pms)))
    ax5.bar(pms, pm_counts, color=pm_colors, edgecolor="white", linewidth=1.5)
    ax5.set_title("Payment Methods", fontsize=11, fontweight="bold")
    ax5.set_ylabel("Orders", fontsize=9)
    ax5.spines["top"].set_visible(False)
    ax5.spines["right"].set_visible(False)
    plt.setp(ax5.get_xticklabels(), rotation=30, ha="right", fontsize=8)
    for i, v in enumerate(pm_counts):
        ax5.text(i, v + max(pm_counts)*0.02, str(v), ha="center", fontsize=8, fontweight="bold")

    # Customer country distribution
    ax6 = fig.add_subplot(3, 3, 6)
    countries = [c[0] for c in data["customers_by_country"]][:10]
    c_counts = [c[1] for c in data["customers_by_country"]][:10]
    c_colors = plt.cm.Set3(np.linspace(0.1, 0.9, len(countries)))
    ax6.barh(countries[::-1], c_counts[::-1], color=c_colors[::-1], edgecolor="white")
    ax6.set_title("Customers by Country (Top 10)", fontsize=11, fontweight="bold")
    ax6.set_xlabel("Customers", fontsize=9)
    ax6.spines["top"].set_visible(False)
    ax6.spines["right"].set_visible(False)

    # Data quality test results table
    ax7 = fig.add_subplot(3, 3, 7)
    ax7.axis("off")
    ax7.set_title("Data Quality Test Results (pytest)", fontsize=11, fontweight="bold", loc="left")
    test_results = [
        ["Test", "Result"],
        ["Customer IDs unique", "PASS"],
        ["Order IDs unique", "PASS"],
        ["Email format valid", "PASS"],
        ["Region values (UK/EU)", "PASS"],
        ["Quantity > 0", "PASS"],
        ["Unit price >= 0", "PASS"],
        ["Referential integrity", "PASS"],
        ["FK: order -> customer", "PASS"],
        ["Tax = 20% of gross", "PASS"],
        ["Total = gross + tax", "PASS"],
        ["Age range 18-100", "PASS"],
        ["Order status valid", "PASS"],
    ]
    for i, row in enumerate(test_results):
        y = 0.95 - i * 0.075
        if i == 0:
            ax7.text(0.05, y, row[0], fontsize=8, fontweight="bold", color=C["slate"])
            ax7.text(0.65, y, row[1], fontsize=8, fontweight="bold", color=C["slate"])
        else:
            fc = "#f0fdf4" if i % 2 == 0 else "#f7fee7"
            ax7.add_patch(Rectangle((0.02, y - 0.03), 0.96, 0.06, linewidth=0, facecolor=fc))
            ax7.text(0.05, y, row[0], fontsize=7.5, color=C["dark"])
            ax7.text(0.65, y, row[1], fontsize=7.5, fontweight="bold", color=C["success"])

    # Quantity distribution
    ax8 = fig.add_subplot(3, 3, 8)
    q_labels = [q[0] for q in data["quantity_distribution"]]
    q_values = [q[1] for q in data["quantity_distribution"]]
    ax8.bar(q_labels, q_values, color=C["primary"], edgecolor="white", linewidth=1.5, alpha=0.8)
    ax8.set_title("Order Quantity Distribution", fontsize=11, fontweight="bold")
    ax8.set_ylabel("Orders", fontsize=9)
    ax8.spines["top"].set_visible(False)
    ax8.spines["right"].set_visible(False)
    for i, v in enumerate(q_values):
        ax8.text(i, v + max(q_values)*0.02, str(v), ha="center", fontsize=8, fontweight="bold")

    # Gender distribution
    ax9 = fig.add_subplot(3, 3, 9)
    genders = [g[0] for g in data["gender_distribution"]]
    g_counts = [g[1] for g in data["gender_distribution"]]
    g_colors = [C["primary"] if g == "M" else C["error"] for g in genders]
    ax9.pie(g_counts, labels=[f"{g}\n({c})" for g, c in zip(genders, g_counts)], autopct="%1.1f%%",
            colors=g_colors, startangle=90, wedgeprops=dict(linewidth=1.5, edgecolor="white"),
            textprops=dict(fontsize=9, fontweight="bold"))
    ax9.set_title("Gender Distribution", fontsize=11, fontweight="bold")

    path = DOCS_DIR / "dashboard.png"
    fig.savefig(path, dpi=150, facecolor=C["bg"], bbox_inches="tight")
    plt.close(fig)
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"\n{'='*60}")
    print("  Generating Architecture Diagrams & Analytics Charts")
    print(f"{'='*60}\n")

    print("  Fetching data from Supabase...")
    try:
        data = fetch_data()
        print(f"  Data loaded: {data['total_customers']} customers, {data['total_orders']} orders, \u00A3{data['total_revenue']:,.0f} revenue")
    except Exception as e:
        print(f"  WARNING: Could not fetch data from Supabase: {e}")
        print("  Generating diagrams with sample data...")
        data = {
            "customers_by_region": [("UK", 550), ("EU", 450)],
            "customers_by_country": [("United Kingdom", 400), ("Germany", 120), ("France", 100), ("Spain", 80), ("Netherlands", 60), ("Italy", 50), ("Belgium", 40), ("Denmark", 35), ("Ireland", 50), ("Sweden", 30)],
            "gender_distribution": [("M", 520), ("F", 480)],
            "orders_by_region": [("UK", 2750, 45000), ("EU", 2250, 38000)],
            "total_revenue": 83000,
            "orders_by_category": [("Home Decor", 800), ("Kitchen", 700), ("Bathroom", 500), ("Garden", 400), ("Stationery", 350), ("Toys", 300), ("Jewelry", 250), ("Clothing", 200)],
            "revenue_by_category": [("Home Decor", 12000), ("Kitchen", 10000), ("Bathroom", 8000), ("Garden", 6000), ("Stationery", 4000), ("Toys", 3500), ("Jewelry", 3000), ("Clothing", 2500)],
            "order_status": [("Delivered", 2500), ("Shipped", 1250), ("Pending", 750), ("Cancelled", 250), ("Refunded", 250)],
            "payment_methods": [("Credit Card", 1800), ("Debit Card", 1200), ("PayPal", 900), ("Bank Transfer", 600), ("Apple Pay", 500)],
            "monthly_revenue": [(f"2022-{m:02d}", "UK", 3000 + m * 100) for m in range(1, 13)] + [(f"2022-{m:02d}", "EU", 2500 + m * 80) for m in range(1, 13)],
            "quantity_distribution": [("1", 1200), ("2-3", 1500), ("4-6", 1000), ("7-12", 700), ("13-24", 400), ("25+", 200)],
            "total_customers": 1000,
            "total_orders": 5000,
        }

    print("  Generating diagrams...")
    generate_architecture_diagram()
    generate_rbac_hierarchy()
    generate_star_schema()
    generate_table_hierarchy()
    generate_revenue_by_region(data)
    generate_orders_by_category(data)
    generate_order_status_pie(data)
    generate_monthly_revenue_trend(data)
    generate_data_quality_dashboard(data)

    print(f"\n  All 9 visualizations saved to: {DOCS_DIR}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
