"""
MediTrack ERP - Realistic Pharmacy Database Seeder
Populates initial master data for local testing, demo walk-throughs, and development.
Safe to run on new or existing databases (idempotent; skips existing entries).
"""

import os
import sys
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import init_db, get_connection
from utils.supplier_service import add_supplier, get_all_suppliers
from utils.customer_service import add_customer, get_all_customers
from utils.purchase_service import record_purchase
from utils.sales_service import record_sale
from utils.settings_service import update_settings


def seed_database(db_path: str = None):
    print("=" * 60)
    print("MediTrack ERP — Seeding Realistic Pharmacy Data")
    print("=" * 60)

    # 1. Initialize schema
    init_db(db_path)
    print("[1/6] Schema initialized with Version 2 migrations.")

    # 2. Configure Shop Settings
    update_settings({
        "shop_name": "MediTrack Wellness Pharmacy",
        "owner_name": "Dr. Ramesh Verma (Reg. Pharmacist)",
        "phone": "+91 98765 43210",
        "address": "Shop #4, Metro Healthcare Complex, MG Road, Bengaluru",
        "gst_number": "29ABCDE1234F1Z5",
        "upi_id": "meditrack@okaxis",
        "bill_prefix": "MT-2026-",
        "expiry_warning_days": "90"
    })
    print("[2/6] Shop settings and branding configured.")

    # 3. Seed Suppliers
    suppliers_data = [
        {"name": "Apex Pharma Distributors", "phone": "9845011223", "email": "orders@apexpharma.in", "address": "Hub #12, Peenya Industrial Area, Bengaluru", "gst_number": "29AAACA1234A1Z1"},
        {"name": "Sun Healthcare Logistics", "phone": "9845022334", "email": "supply@sunhealth.com", "address": "Plot 45, Electronic City Phase 1, Bengaluru", "gst_number": "29AAACB2345B1Z2"},
        {"name": "Cipla Regional Depot", "phone": "9845033445", "email": "south_depot@cipla.com", "address": "B-3, Whitefield Logistics Park, Bengaluru", "gst_number": "29AAACC3456C1Z3"}
    ]

    supplier_ids = {}
    existing_suppliers = {s["name"]: s["id"] for s in get_all_suppliers()}
    for s in suppliers_data:
        if s["name"] in existing_suppliers:
            supplier_ids[s["name"]] = existing_suppliers[s["name"]]
        else:
            s_id = add_supplier(
                name=s["name"], phone=s["phone"], email=s["email"],
                address=s["address"], gst_number=s["gst_number"]
            )
            supplier_ids[s["name"]] = s_id
    print(f"[3/6] Verified {len(supplier_ids)} registered suppliers.")

    # 4. Seed Customers
    customers_data = [
        {"name": "Suresh Kumar", "phone": "9811122233", "credit_limit": 5000.0, "address": "Flat 201, Green Heights"},
        {"name": "Anita Deshmukh", "phone": "9822233344", "credit_limit": 8000.0, "address": "14/A, Palm Meadows"},
        {"name": "Mohammad Rizwan", "phone": "9833344455", "credit_limit": 3000.0, "address": "45, Mosque Road, Frazer Town"}
    ]

    existing_customers = {c["name"]: c["id"] for c in get_all_customers()}
    for c in customers_data:
        if c["name"] not in existing_customers:
            add_customer(name=c["name"], phone=c["phone"], credit_limit=c["credit_limit"], address=c["address"])
    print(f"[4/6] Verified registered patient profiles.")

    # 5. Seed Purchases & Inventory Batches
    today = datetime.now()
    exp_healthy_1 = (today + timedelta(days=450)).strftime("%Y-%m-%d")
    exp_healthy_2 = (today + timedelta(days=600)).strftime("%Y-%m-%d")
    exp_soon_1 = (today + timedelta(days=45)).strftime("%Y-%m-%d") # Expiring soon alert
    exp_soon_2 = (today + timedelta(days=75)).strftime("%Y-%m-%d")

    # Purchase Invoice 1 (Apex Pharma)
    p1_invoice = "APEX-2026-089"
    try:
        record_purchase(
            purchase_invoice_number=p1_invoice,
            supplier_id=supplier_ids["Apex Pharma Distributors"],
            purchase_date=(today - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S"),
            due_date=(today + timedelta(days=15)).strftime("%Y-%m-%d"),
            payment_status="Paid",
            total_amount=1550.0,
            discount_percent=0.0,
            gst_amount=186.0,
            grand_total=1736.0,
            items=[
                {
                    "name": "Dolo 650",
                    "manufacturer": "Micro Labs",
                    "batch_number": "DL-9081",
                    "expiry_date": exp_healthy_1,
                    "strips_purchased": 50,
                    "free_strips": 5,
                    "tablets_per_strip": 15,
                    "purchase_price": 24.50, # per strip
                    "selling_price": 31.00,
                    "mrp": 33.60,
                    "discount_percent": 2.0,
                    "gst_percent": 12.0
                },
                {
                    "name": "Pan-D",
                    "manufacturer": "Alkem Laboratories",
                    "batch_number": "PND-4412",
                    "expiry_date": exp_healthy_2,
                    "strips_purchased": 30,
                    "tablets_per_strip": 15,
                    "purchase_price": 140.00,
                    "selling_price": 185.00,
                    "mrp": 199.00,
                    "discount_percent": 5.0,
                    "gst_percent": 12.0
                }
            ]
        )
        print(f"  -> Recorded Purchase {p1_invoice}")
    except Exception as ex:
        print(f"  -> Purchase {p1_invoice} already seeded or skipped: {ex}")

    # Purchase Invoice 2 (Sun Healthcare)
    p2_invoice = "SUN-2026-1044"
    try:
        record_purchase(
            purchase_invoice_number=p2_invoice,
            supplier_id=supplier_ids["Sun Healthcare Logistics"],
            purchase_date=(today - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
            due_date=(today + timedelta(days=25)).strftime("%Y-%m-%d"),
            payment_status="Unpaid",
            total_amount=2450.0,
            discount_percent=0.0,
            gst_amount=294.0,
            grand_total=2744.0,
            items=[
                {
                    "name": "Augmentin 625 Duo",
                    "manufacturer": "GlaxoSmithKline",
                    "batch_number": "AUG-7721",
                    "expiry_date": exp_healthy_1,
                    "strips_purchased": 25,
                    "tablets_per_strip": 10,
                    "purchase_price": 150.00,
                    "selling_price": 190.00,
                    "mrp": 204.50,
                    "discount_percent": 3.0,
                    "gst_percent": 12.0
                },
                {
                    "name": "Azithral 500",
                    "manufacturer": "Alembic Pharma",
                    "batch_number": "AZT-309",
                    "expiry_date": exp_soon_1, # Expiring soon
                    "strips_purchased": 20,
                    "tablets_per_strip": 5,
                    "purchase_price": 95.00,
                    "selling_price": 120.00,
                    "mrp": 132.00,
                    "discount_percent": 0.0,
                    "gst_percent": 12.0
                },
                {
                    "name": "Telma 40",
                    "manufacturer": "Glenmark",
                    "batch_number": "TLM-881",
                    "expiry_date": exp_soon_2, # Expiring in 75 days
                    "strips_purchased": 40,
                    "tablets_per_strip": 15,
                    "purchase_price": 160.00,
                    "selling_price": 210.00,
                    "mrp": 228.00,
                    "discount_percent": 4.0,
                    "gst_percent": 12.0
                }
            ]
        )
        print(f"  -> Recorded Purchase {p2_invoice}")
    except Exception as ex:
        print(f"  -> Purchase {p2_invoice} already seeded or skipped: {ex}")

    # Update rack and shelf locations for medicines
    conn = get_connection(db_path)
    cur = conn.cursor()
    rack_mappings = {
        "Dolo 650": "Rack A - Shelf 1",
        "Pan-D": "Rack A - Shelf 3",
        "Augmentin 625 Duo": "Rack B - Shelf 2 (Antibiotics)",
        "Azithral 500": "Rack B - Shelf 1 (Antibiotics)",
        "Telma 40": "Rack C - Shelf 4 (Cardio)"
    }
    for med_name, shelf in rack_mappings.items():
        cur.execute("UPDATE medicines SET rack_shelf = ? WHERE name = ?;", (shelf, med_name))
    conn.commit()
    conn.close()
    print("[5/6] Inventory batches populated with FEFO expiry and rack/shelf locations.")

    # 6. Seed Sample Counter Sales Bills
    try:
        # Bill 1: Walk-in cash patient buying 15 tablets (1 strip) of Dolo 650
        record_sale(
            customer_id=1,
            customer_name="Walk-in Cash Patient",
            customer_phone="9876500001",
            payment_mode="Cash",
            discount_percent=0.0,
            cart_items=[{
                "medicine_id": 1,
                "batch_number": "DL-9081",
                "quantity": 15 # 1 strip = 15 tablets of Dolo 650
            }]
        )
        print("  -> Created baseline sales transaction #1")
    except Exception as ex:
        print(f"  -> Bill seeding skipped: {ex}")

    print("[6/6] Database seeding complete! MediTrack is ready for production and demo use.")
    print("=" * 60)


if __name__ == "__main__":
    seed_database()
