import os
import sys
from datetime import datetime, timedelta

# Setup paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db, get_connection
from utils.supplier_service import add_supplier, get_all_suppliers
from utils.customer_service import add_customer, get_all_customers
from utils.purchase_service import record_purchase
from utils.sales_service import record_sale, get_bill_by_number, get_bill_items, get_unpaid_bills, pay_unpaid_bill, get_total_unpaid_amount
from utils.medicine_service import get_medicine_by_id, get_all_medicines
from utils.backup_service import backup_database, restore_database

def run_tests():
    print("==================================================")
    print("  Starting Medical Shop System Automated Tests    ")
    print("==================================================")
    
    # 1. Initialize clean test DB
    # We will backup and clean database during test to not corrupt active shop DB
    db_file = "medical_shop.db"
    db_backup_temp = "medical_shop_temp_test_backup.db"
    if os.path.exists(db_file):
        if os.path.exists(db_backup_temp):
            os.remove(db_backup_temp)
        os.rename(db_file, db_backup_temp)
        print("[Setup] Backed up active DB to a temporary test file.")
        
    try:
        init_db()
        print("[PASS] Database initialized successfully.")
        
        # 2. Add Supplier
        supplier_name = "Apex Pharmaceuticals"
        sup_id = add_supplier(name=supplier_name, phone="9876543210", email="apex@pharma.com", address="Industrial Zone, Delhi")
        print(f"[PASS] Supplier added with ID: {sup_id}")
        
        # 3. Test Purchase (10 strips, 15 tablets per strip)
        # Purchase price = ₹18 per strip, Selling = ₹25, MRP = ₹32
        med_name = "Paracetamol 650"
        med_batch = "PRC-901"
        expiry_date = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d") # 120 days from now (not expired)
        
        # Record multi-item invoice
        record_purchase(
            purchase_invoice_number="TEST-INV-1",
            supplier_id=sup_id,
            purchase_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            due_date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            payment_status="Unpaid",
            total_amount=180.0, # 10 strips * Rs 18
            discount_percent=0.0,
            gst_amount=21.6, # 12% GST of 180
            grand_total=201.6,
            items=[{
                'name': med_name,
                'manufacturer': "Apex Labs",
                'batch_number': med_batch,
                'expiry_date': expiry_date,
                'quantity': 150, # 10 strips * 15 tabs
                'free_quantity': 0,
                'purchase_price': 18.0,
                'selling_price': 25.0,
                'mrp': 32.0,
                'discount_percent': 0.0,
                'gst_percent': 12.0,
                'tablets_per_strip': 15
            }]
        )
        
        all_meds = get_all_medicines()
        assert len(all_meds) == 1, "Expected 1 medicine batch in stock."
        med = all_meds[0]
        med_id = med['id'] # medicine_batches.id
        
        assert med['total_tablets'] == 150, f"Expected 150 tablets, got {med['total_tablets']}"
        assert med['strips'] == 10, f"Expected 10 strips, got {med['strips']}"
        assert med['loose_tablets'] == 0, f"Expected 0 loose, got {med['loose_tablets']}"
        print("[PASS] Purchase registered. Stock matches expected (150 tablets, 10 strips).")
        
        # 4. Test Sale (5 tablets)
        cart = [{'medicine_id': med['medicine_id'], 'batch_number': med['batch'], 'quantity': 5}]
        # Discount = 10%
        bill_num = record_sale(
            customer_id=None,
            customer_name="John Doe",
            customer_phone="9988776655",
            payment_mode="Cash",
            cart_items=cart,
            discount_percent=10.0
        )
        
        # Verify Stock Deductions
        med = get_medicine_by_id(med_id)
        # Original 150 - 5 sold = 145 tablets
        # 145 / 15 = 9 strips, 10 loose tablets
        assert med['total_tablets'] == 145, f"Expected 145 tablets, got {med['total_tablets']}"
        assert med['strips'] == 9, f"Expected 9 strips, got {med['strips']}"
        assert med['loose_tablets'] == 10, f"Expected 10 loose tablets, got {med['loose_tablets']}"
        print("[PASS] Sale of 5 tablets processed. Stock successfully reduced to 145 tablets (9 strips + 10 loose).")
        
        # 5. Verify Billing Math Calculations (10% discount, purchase price ₹18/15=₹1.20, selling ₹25/15=₹1.6667)
        bill = get_bill_by_number(bill_num)
        bill_items = get_bill_items(bill_num)
        
        item = bill_items[0]
        price_per_tablet = 25.0 / 15.0
        purchase_price_per_tablet = 18.0 / 15.0
        
        # Gross = 5 * 1.666666... = 8.3333333333
        gross = 5 * price_per_tablet
        expected_discount = gross * 10.0 / 100.0
        expected_subtotal = gross - expected_discount
        expected_cost = 5 * purchase_price_per_tablet
        expected_profit = expected_subtotal - expected_cost
        
        # Delta assertions for float precision
        assert abs(bill['total_amount'] - gross) < 0.01, f"Expected gross {gross}, got {bill['total_amount']}"
        assert abs(bill['discount_amount'] - expected_discount) < 0.01, f"Expected discount {expected_discount}, got {bill['discount_amount']}"
        assert abs(bill['grand_total'] - expected_subtotal) < 0.01, f"Expected grand total {expected_subtotal}, got {bill['grand_total']}"
        assert abs(bill['total_profit'] - expected_profit) < 0.01, f"Expected profit {expected_profit}, got {bill['total_profit']}"
        print(f"[PASS] Billing calculations correct: Subtotal = Rs. {bill['total_amount']:.2f}, Discount = Rs. {bill['discount_amount']:.2f}, Grand Total = Rs. {bill['grand_total']:.2f}, Profit = Rs. {bill['total_profit']:.2f}")
        
        # 6. Test Sale over Stock Limits (should fail)
        try:
            cart_over = [{'medicine_id': med['medicine_id'], 'batch_number': med['batch'], 'quantity': 200}]
            record_sale(None, "Failing Sale", "999", "UPI", cart_over, 0.0)
            print("[FAIL] Billed quantity over stock should have raised ValueError!")
            assert False, "Quantity over stock boundary was not caught."
        except ValueError as e:
            print(f"[PASS] Correctly rejected sale exceeding stock: '{str(e)}'")
            
        # 6b. Test Unpaid/Credit sales tracking and clearing
        cust_id = add_customer(name="Jane Credit", phone="9876543210")
        
        unpaid_cart = [{'medicine_id': med['medicine_id'], 'batch_number': med['batch'], 'quantity': 10}]
        unpaid_bill_num = record_sale(
            customer_id=cust_id,
            customer_name="Jane Credit",
            customer_phone="9876543210",
            payment_mode="Unpaid",
            cart_items=unpaid_cart,
            discount_percent=0.0
        )
        
        # Verify it's returned in unpaid list
        unpaid_bills = get_unpaid_bills()
        assert any(b['bill_number'] == unpaid_bill_num for b in unpaid_bills), "Expected unpaid bill to be returned in get_unpaid_bills()"
        
        # Verify total unpaid amount matches
        total_unpaid = get_total_unpaid_amount()
        unpaid_bill = get_bill_by_number(unpaid_bill_num)
        assert abs(total_unpaid - unpaid_bill['grand_total']) < 0.01, f"Expected unpaid total {unpaid_bill['grand_total']}, got {total_unpaid}"
        
        # Pay the bill
        pay_unpaid_bill(unpaid_bill_num, "UPI")
        
        # Verify it is no longer unpaid
        unpaid_bills_post = get_unpaid_bills()
        assert not any(b['bill_number'] == unpaid_bill_num for b in unpaid_bills_post), "Expected cleared bill to not be returned in get_unpaid_bills()"
        
        bill_post = get_bill_by_number(unpaid_bill_num)
        assert bill_post['payment_mode'] == "UPI", f"Expected payment mode 'UPI', got {bill_post['payment_mode']}"
        
        total_unpaid_post = get_total_unpaid_amount()
        assert total_unpaid_post == 0.0, f"Expected total unpaid to be 0.0, got {total_unpaid_post}"
        print("[PASS] Unpaid sales tracking and clearing tests successfully verified.")
        
        # 7. Backup and Restore database
        # Create a backup
        backup_path = backup_database()
        backup_filename = os.path.basename(backup_path)
        print(f"[PASS] Database backup created at: {backup_filename}")
        
        # Make a change after backup
        add_supplier("Supplier After Backup", "000", "after@backup.com", "Nowhere")
        all_sups_before = get_all_suppliers()
        assert len(all_sups_before) == 2, "Expected 2 suppliers after adding one."
        
        # Restore backup
        restore_database(backup_filename)
        all_sups_after = get_all_suppliers()
        assert len(all_sups_after) == 1, f"Expected database to restore back to 1 supplier, found {len(all_sups_after)}"
        print("[PASS] Database restored successfully. Changes made after backup were rolled back.")
        
        # Clean up test backups
        if os.path.exists(backup_path):
            os.remove(backup_path)
            
        print("\n==================================================")
        print("    ALL AUTOMATED TEST CASES PASSED SUCCESSFULLY  ")
        print("==================================================")
        
    finally:
        # Clean up database file to restore original state
        if os.path.exists(db_file):
            os.remove(db_file)
        if os.path.exists(db_backup_temp):
            os.rename(db_backup_temp, db_file)
            print("[Clean] Restored active DB from temporary backup.")

if __name__ == "__main__":
    run_tests()
