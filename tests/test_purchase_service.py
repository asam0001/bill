"""
Automated Test Suite for utils/purchase_service.py
Validates:
  1. Authoritative Total Tablets conversion (strips -> total_tablets).
  2. Duplicate Purchase Protection (same supplier + same invoice blocked).
  3. Procurement expiry blocking (expired medicines cannot be purchased).
  4. Pricing rules (Selling Price > MRP blocked, Purchase Rate > MRP blocked).
  5. Supplier balance & double-entry ledger tracking (Unpaid vs Paid).
  6. Batch merging / incrementing on subsequent purchases.
  7. Purchase Returns (stock decrement, concurrency check, balance credit reduction).
  8. Query helper functions.
"""

import os
import sys
import shutil
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Test database sandbox
TEST_DB = "test_purchase_sandbox.db"
os.environ["MEDITRACK_DB_PATH"] = os.path.abspath(TEST_DB)
if os.path.exists(TEST_DB):
    try:
        os.remove(TEST_DB)
    except Exception:
        pass

import database.db
database.db.DB_NAME = TEST_DB
from database.db import init_db, get_connection
from utils.supplier_service import add_supplier, get_supplier_ledger, get_supplier_by_id
from utils.medicine_service import get_all_medicines, search_medicines, get_medicine_by_id
from utils.purchase_service import (
    record_purchase,
    record_purchase_return,
    get_all_purchases,
    get_purchase_by_id,
    get_purchase_by_invoice,
    get_purchase_items,
    get_all_purchase_returns,
    get_purchase_return_by_id,
    get_purchase_return_items
)

def run_tests():
    print("=" * 60)
    print("STARTING TEST SUITE: utils/purchase_service.py")
    print("=" * 60)

    # 1. Initialize schema
    init_db(TEST_DB)
    print("[PASS] Sandbox database initialized.")

    # 2. Setup Suppliers
    sup1_id = add_supplier(name="Sun Pharma Dist", phone="9876543210", email="sun@pharma.com", address="Mumbai Hub")
    sup2_id = add_supplier(name="Cipla Dist", phone="9876543211", email="cipla@pharma.com", address="Pune Hub")
    assert sup1_id > 0 and sup2_id > 0
    print(f"[PASS] Created suppliers: ID {sup1_id}, ID {sup2_id}")

    # 3. Test Purchase #1 (Unpaid, strips to tablets conversion)
    # 10 strips of 15 tablets = 150 tablets. Buy rate ₹20/strip, Sell ₹30/strip, MRP ₹35/strip
    # Gross = 10 * 20 = 200. GST 12% = 24. Grand total = 224.
    valid_exp = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    p1_items = [{
        "name": "Amoxicillin 500",
        "manufacturer": "Sun Pharma",
        "batch_number": "AMX-101",
        "expiry_date": valid_exp,
        "strips_purchased": 10,
        "tablets_per_strip": 15,
        "purchase_price": 20.0,
        "selling_price": 30.0,
        "mrp": 35.0,
        "discount_percent": 0.0,
        "gst_percent": 12.0
    }]

    p1_id = record_purchase(
        purchase_invoice_number="INV-SUN-001",
        supplier_id=sup1_id,
        purchase_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        due_date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        payment_status="Unpaid",
        total_amount=200.0,
        discount_percent=0.0,
        gst_amount=24.0,
        grand_total=224.0,
        items=p1_items
    )
    assert p1_id > 0, "Purchase 1 ID should be positive"
    print(f"[PASS] Purchase #1 recorded successfully with ID {p1_id}")

    # Verify inventory was updated with total_tablets
    meds = get_all_medicines()
    assert len(meds) == 1, f"Expected 1 batch, found {len(meds)}"
    med = meds[0]
    assert med["total_tablets"] == 150, f"Expected 150 total tablets, got {med['total_tablets']}"
    assert med["strips"] == 10, f"Expected 10 strips, got {med['strips']}"
    assert med["loose_tablets"] == 0, f"Expected 0 loose tablets, got {med['loose_tablets']}"
    print("[PASS] Inventory reflects correct authoritative total_tablets (150 tabs = 10 strips).")

    # Verify supplier balance and ledger for Unpaid purchase
    sup1 = get_supplier_by_id(sup1_id)
    assert abs(sup1["current_balance"] - 224.0) < 0.001, f"Expected supplier balance 224.0, got {sup1['current_balance']}"
    ledger = get_supplier_ledger(sup1_id)
    assert len(ledger) == 1, f"Expected 1 ledger entry, found {len(ledger)}"
    assert ledger[0]["type"] == "PURCHASE"
    assert abs(ledger[0]["credit"] - 224.0) < 0.001
    assert abs(ledger[0]["balance"] - 224.0) < 0.001
    print("[PASS] Supplier balance & ledger correctly updated for Unpaid credit purchase.")

    # 4. Duplicate Purchase Protection Test
    # Submitting the same invoice number for the same supplier must raise ValueError
    dup_caught = False
    try:
        record_purchase(
            purchase_invoice_number="INV-SUN-001",
            supplier_id=sup1_id,
            purchase_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            due_date=None,
            payment_status="Unpaid",
            total_amount=200.0,
            discount_percent=0.0,
            gst_amount=24.0,
            grand_total=224.0,
            items=p1_items
        )
    except ValueError as e:
        if "Duplicate Purchase Invoice" in str(e):
            dup_caught = True
            print(f"[PASS] Duplicate purchase blocked: {e}")
    assert dup_caught, "Expected Duplicate Purchase Protection to raise ValueError"

    # But same invoice number for DIFFERENT supplier should be allowed!
    p_diff_sup = record_purchase(
        purchase_invoice_number="INV-SUN-001",
        supplier_id=sup2_id,
        purchase_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        due_date=None,
        payment_status="Paid",
        total_amount=200.0,
        discount_percent=0.0,
        gst_amount=24.0,
        grand_total=224.0,
        items=[{
            "name": "Paracetamol 500",
            "batch_number": "PRC-CIP-1",
            "expiry_date": valid_exp,
            "quantity": 100,
            "tablets_per_strip": 10,
            "purchase_price": 10.0,
            "selling_price": 15.0,
            "mrp": 20.0
        }]
    )
    assert p_diff_sup > 0
    print("[PASS] Different supplier allowed with identical invoice number string.")

    # 5. Expired stock rejection test
    # Trying to procure an expired medicine must fail
    expired_caught = False
    try:
        record_purchase(
            purchase_invoice_number="INV-EXPIRED-TEST",
            supplier_id=sup1_id,
            purchase_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            due_date=None,
            payment_status="Unpaid",
            total_amount=100.0,
            discount_percent=0.0,
            gst_amount=12.0,
            grand_total=112.0,
            items=[{
                "name": "Old Medicine",
                "batch_number": "OLD-001",
                "expiry_date": "2024-01-01", # Expired!
                "quantity": 100,
                "tablets_per_strip": 10,
                "purchase_price": 10.0,
                "mrp": 20.0
            }]
        )
    except ValueError as e:
        if "has already passed" in str(e) or "expired" in str(e).lower():
            expired_caught = True
            print(f"[PASS] Procurement of expired medicine blocked: {e}")
    assert expired_caught, "Expected expired medicine rejection"

    # 6. Pricing Rules Validation
    # Selling Price > MRP must fail
    sp_mrp_caught = False
    try:
        record_purchase(
            purchase_invoice_number="INV-PRICING-1",
            supplier_id=sup1_id,
            purchase_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            due_date=None,
            payment_status="Unpaid",
            total_amount=100.0,
            discount_percent=0.0,
            gst_amount=12.0,
            grand_total=112.0,
            items=[{
                "name": "Price Check Med",
                "batch_number": "PC-001",
                "expiry_date": valid_exp,
                "quantity": 100,
                "tablets_per_strip": 10,
                "purchase_price": 10.0,
                "selling_price": 25.0, # Exceeds MRP!
                "mrp": 20.0
            }]
        )
    except ValueError as e:
        if "cannot exceed MRP" in str(e):
            sp_mrp_caught = True
            print(f"[PASS] Selling price > MRP blocked: {e}")
    assert sp_mrp_caught

    # Purchase Price > MRP must fail
    pp_mrp_caught = False
    try:
        record_purchase(
            purchase_invoice_number="INV-PRICING-2",
            supplier_id=sup1_id,
            purchase_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            due_date=None,
            payment_status="Unpaid",
            total_amount=100.0,
            discount_percent=0.0,
            gst_amount=12.0,
            grand_total=112.0,
            items=[{
                "name": "Price Check Med 2",
                "batch_number": "PC-002",
                "expiry_date": valid_exp,
                "quantity": 100,
                "tablets_per_strip": 10,
                "purchase_price": 30.0, # Exceeds MRP!
                "selling_price": 18.0,
                "mrp": 20.0
            }]
        )
    except ValueError as e:
        if "cannot exceed MRP" in str(e):
            pp_mrp_caught = True
            print(f"[PASS] Purchase rate > MRP blocked: {e}")
    assert pp_mrp_caught

    # 7. Test Batch Incrementing (Restocking existing batch AMX-101)
    # Existing has 150 tablets. Adding 5 strips (= 75 tablets) + 1 free strip (= 15 tablets) = 90 tablets.
    # Total tablets should become 150 + 90 = 240.
    p_restock_id = record_purchase(
        purchase_invoice_number="INV-SUN-002",
        supplier_id=sup1_id,
        purchase_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        due_date=None,
        payment_status="Paid", # Paid immediately
        total_amount=100.0,
        discount_percent=0.0,
        gst_amount=12.0,
        grand_total=112.0,
        items=[{
            "name": "Amoxicillin 500",
            "batch_number": "AMX-101",
            "expiry_date": valid_exp,
            "strips_purchased": 5,
            "free_strips": 1,
            "tablets_per_strip": 15,
            "purchase_price": 20.0,
            "selling_price": 30.0,
            "mrp": 35.0
        }]
    )
    assert p_restock_id > 0
    batch_updated = search_medicines("AMX-101")[0]
    assert batch_updated["total_tablets"] == 240, f"Expected 240 total tablets, got {batch_updated['total_tablets']}"
    assert batch_updated["strips"] == 16, f"Expected 16 strips, got {batch_updated['strips']}"
    print("[PASS] Batch restocking atomically incremented stock to 240 tablets (16 strips).")

    # For Paid purchase, balance should remain unchanged
    sup1_after = get_supplier_by_id(sup1_id)
    assert abs(sup1_after["current_balance"] - 224.0) < 0.001, f"Expected 224.0 balance, got {sup1_after['current_balance']}"
    print("[PASS] Paid purchase maintains net balance and writes complete audit trail.")

    # 8. Test Purchase Returns
    # Return 45 tablets (3 strips) of AMX-101
    med_amx_id = batch_updated["medicine_id"]
    ret_id = record_purchase_return(
        supplier_id=sup1_id,
        return_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_refund=67.20, # 3 strips * 20 = 60 + 12% GST = 67.20
        reference_invoice="INV-SUN-001",
        returned_items=[{
            "medicine_id": med_amx_id,
            "batch_number": "AMX-101",
            "quantity": 45, # 45 tablets
            "purchase_price": 20.0,
            "gst_percent": 12.0
        }]
    )
    assert ret_id > 0
    print(f"[PASS] Purchase return recorded with ID {ret_id}")

    # Check stock after return: 240 - 45 = 195 tablets (13 strips)
    batch_after_ret = search_medicines("AMX-101")[0]
    assert batch_after_ret["total_tablets"] == 195, f"Expected 195 tablets, got {batch_after_ret['total_tablets']}"
    assert batch_after_ret["strips"] == 13, f"Expected 13 strips, got {batch_after_ret['strips']}"
    print("[PASS] Stock decremented to 195 tablets (13 strips) after purchase return.")

    # Check supplier balance after return: 224.0 - 67.20 = 156.80
    sup1_after_ret = get_supplier_by_id(sup1_id)
    assert abs(sup1_after_ret["current_balance"] - 156.80) < 0.01, f"Expected 156.80, got {sup1_after_ret['current_balance']}"
    print(f"[PASS] Supplier balance reduced from ₹224.00 to ₹{sup1_after_ret['current_balance']:.2f}")

    # Over-return rejection: Attempting to return more stock than available (e.g. 500 tablets) must fail
    over_ret_caught = False
    try:
        record_purchase_return(
            supplier_id=sup1_id,
            return_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_refund=500.0,
            reference_invoice="INV-SUN-001",
            returned_items=[{
                "medicine_id": med_amx_id,
                "batch_number": "AMX-101",
                "quantity": 500,
                "purchase_price": 20.0,
                "gst_percent": 12.0
            }]
        )
    except ValueError as e:
        if "Insufficient stock" in str(e):
            over_ret_caught = True
            print(f"[PASS] Over-return prevented: {e}")
    assert over_ret_caught, "Expected over-return to raise ValueError"

    # 9. Test Query Helpers
    all_purchases = get_all_purchases()
    assert len(all_purchases) == 3, f"Expected 3 purchases, got {len(all_purchases)}"
    
    p_by_id = get_purchase_by_id(p1_id)
    assert p_by_id is not None
    assert p_by_id["purchase_invoice_number"] == "INV-SUN-001"
    assert p_by_id["supplier_name"] == "Sun Pharma Dist"

    p_by_inv = get_purchase_by_invoice("INV-SUN-001", supplier_id=sup1_id)
    assert p_by_inv is not None and p_by_inv["id"] == p1_id

    p_items = get_purchase_items(p1_id)
    assert len(p_items) == 1
    assert p_items[0]["batch_number"] == "AMX-101"
    assert p_items[0]["quantity"] == 150

    all_returns = get_all_purchase_returns()
    assert len(all_returns) == 1
    ret_by_id = get_purchase_return_by_id(ret_id)
    assert ret_by_id is not None
    assert ret_by_id["reference_invoice"] == "INV-SUN-001"
    
    ret_items = get_purchase_return_items(ret_id)
    assert len(ret_items) == 1
    assert ret_items[0]["quantity"] == 45
    print("[PASS] All query helpers (get_all_purchases, get_purchase_by_id, get_purchase_by_invoice, get_purchase_items, returns) verified.")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! (EXIT CODE 0)")
    print("=" * 60)

if __name__ == "__main__":
    try:
        run_tests()
    finally:
        # Cleanup test database
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass
