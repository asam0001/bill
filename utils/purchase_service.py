"""
MediTrack ERP - Purchase & Procurement Management Engine
Authoritative processing of distributor purchases, stock intake, and supplier returns.
Adheres strictly to single source of truth (total_tablets) and Decimal financial safety.
"""

import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Union

from database.db import get_connection
from utils.medicine_service import log_stock_movement
from utils.money import to_decimal, quantize_money, calculate_discount


# ------------------------------------------------------------------------------
# 1. Record Purchase Invoice Transaction
# ------------------------------------------------------------------------------

def record_purchase(
    purchase_invoice_number: str,
    supplier_id: int,
    purchase_date: str,
    due_date: Optional[str],
    payment_status: str,
    total_amount: Union[int, float, str, Decimal],
    discount_percent: Union[int, float, str, Decimal],
    gst_amount: Union[int, float, str, Decimal],
    grand_total: Union[int, float, str, Decimal],
    items: List[Dict[str, Any]],
    paid_amount: Optional[Union[int, float, str, Decimal]] = None,
    cursor: Optional[sqlite3.Cursor] = None
) -> int:
    """
    Records a purchase invoice transaction atomically.
    
    Invariants & Business Rules:
      1. Duplicate Protection: Blocks duplicate invoices for the same supplier.
      2. Expiry Safety: Blocks purchasing stock that is already expired.
      3. Stock Inventory: Quantity added to stock is strictly total_tablets (strips * tablets_per_strip).
      4. Pricing Invariants: Selling Price and Purchase Rate cannot exceed MRP.
      5. Financial Math: Uses Python Decimal and commercial rounding for all money operations.
      6. Ledger Balance: Updates supplier outstanding balance and posts auditable double-entry ledger rows.
      7. Atomic Transaction: Full rollback on any item or constraint failure.
    
    Items list structure:
    [{
        'name': str,
        'manufacturer': str (optional),
        'batch_number': str,
        'expiry_date': str (YYYY-MM-DD),
        'tablets_per_strip': int (> 0),
        'strips_purchased': int/float (optional, if provided converts to quantity),
        'quantity': int (in tablets, i.e. strips * tablets_per_strip),
        'free_strips': int/float (optional, if provided converts to free_quantity),
        'free_quantity': int (optional, in tablets),
        'purchase_price': float/Decimal (per strip),
        'selling_price': float/Decimal (per strip),
        'mrp': float/Decimal (per strip),
        'discount_percent': float/Decimal (optional, default 0.0),
        'gst_percent': float/Decimal (optional, default 12.0)
    }]
    """
    # --- Input Validations ---
    if not items:
        raise ValueError("Purchase invoice must contain at least one item.")

    inv_num_clean = str(purchase_invoice_number).strip() if purchase_invoice_number else ""
    if not inv_num_clean:
        raise ValueError("Purchase Invoice Number cannot be empty.")

    valid_statuses = ("Paid", "Unpaid", "Partial")
    if payment_status not in valid_statuses:
        raise ValueError(f"Invalid payment status '{payment_status}'. Allowed: {', '.join(valid_statuses)}.")

    if not purchase_date:
        purchase_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not due_date:
        # Default due date to purchase date + 30 days
        try:
            p_dt = datetime.strptime(purchase_date[:10], "%Y-%m-%d")
            due_date = (p_dt + timedelta(days=30)).strftime("%Y-%m-%d")
        except Exception:
            due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    # Transaction lifecycle management
    should_close = False
    if cursor is None:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        should_close = True
    else:
        conn = cursor.connection

    try:
        # 1. Verify Supplier Exists
        cursor.execute("SELECT id, name, current_balance FROM suppliers WHERE id = ?;", (supplier_id,))
        supplier_row = cursor.fetchone()
        if not supplier_row:
            raise ValueError(f"Supplier ID {supplier_id} not found in database.")
        supplier_name = supplier_row["name"]

        # 2. Duplicate Purchase Protection (supplier_id + purchase_invoice_number)
        cursor.execute("""
            SELECT id, purchase_date, grand_total 
            FROM purchases 
            WHERE supplier_id = ? AND LOWER(TRIM(purchase_invoice_number)) = LOWER(TRIM(?));
        """, (supplier_id, inv_num_clean))
        duplicate_row = cursor.fetchone()
        if duplicate_row:
            dup_id = duplicate_row["id"]
            dup_date = duplicate_row["purchase_date"]
            dup_total = duplicate_row["grand_total"]
            raise ValueError(
                f"Duplicate Purchase Invoice: Invoice '{inv_num_clean}' has already been recorded "
                f"for supplier '{supplier_name}' on {dup_date} (Purchase ID: #{dup_id}, Total: ₹{dup_total:.2f})."
            )

        # 3. Process & Validate All Line Items
        processed_items = []
        calc_taxable_sum = Decimal("0.00")
        calc_gst_sum = Decimal("0.00")
        calc_grand_sum = Decimal("0.00")
        today = datetime.now().date()

        for idx, item in enumerate(items, start=1):
            med_name = str(item.get("name", "")).strip()
            if not med_name:
                raise ValueError(f"Item #{idx}: Medicine name is required.")

            batch_num = str(item.get("batch_number", "")).strip()
            if not batch_num:
                raise ValueError(f"Item #{idx} ({med_name}): Batch number is required.")

            exp_date = str(item.get("expiry_date", "")).strip()
            if not exp_date:
                raise ValueError(f"Item #{idx} ({med_name}): Expiry date is required.")

            try:
                exp_date_obj = datetime.strptime(exp_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Item #{idx} ({med_name}): Invalid expiry date '{exp_date}'. Format must be YYYY-MM-DD.")

            # Pharmacy Safety: Cannot accept expired stock from distributor
            if exp_date_obj <= today:
                raise ValueError(
                    f"Item #{idx} ({med_name}, Batch '{batch_num}'): Expiry date ({exp_date}) has already passed. "
                    f"Pharmacies are strictly prohibited from procuring expired stock."
                )

            # Tablets per strip
            tps = int(item.get("tablets_per_strip") or 10)
            if tps <= 0:
                raise ValueError(f"Item #{idx} ({med_name}): Tablets per strip must be greater than 0.")

            # Resolve Authoritative Total Tablets (Strips -> Total Tablets)
            # Checks strips_purchased / strips / quantity_in_strips first
            strip_key = next((k for k in ("strips_purchased", "strips", "quantity_in_strips", "strips_qty") if k in item and item[k] is not None), None)
            if strip_key:
                strips_count = to_decimal(item[strip_key])
                if strips_count <= Decimal("0"):
                    raise ValueError(f"Item #{idx} ({med_name}): Strips purchased must be greater than 0.")
                qty_tablets = int(strips_count * Decimal(str(tps)))
            elif "quantity" in item and item["quantity"] is not None:
                qty_tablets = int(item["quantity"])
                if qty_tablets <= 0:
                    raise ValueError(f"Item #{idx} ({med_name}): Quantity must be greater than 0.")
                strips_count = Decimal(str(qty_tablets)) / Decimal(str(tps))
            else:
                raise ValueError(f"Item #{idx} ({med_name}): Quantity or strips purchased must be specified.")

            # Free quantity resolution
            free_strip_key = next((k for k in ("free_strips", "free_strip_qty") if k in item and item[k] is not None), None)
            if free_strip_key:
                free_strips_count = to_decimal(item[free_strip_key])
                free_tablets = max(0, int(free_strips_count * Decimal(str(tps))))
            else:
                free_tablets = max(0, int(item.get("free_quantity") or 0))

            # Financial Fields (Rates per strip)
            p_price = to_decimal(item.get("purchase_price") or 0.0)
            mrp_val = to_decimal(item.get("mrp") or 0.0)
            s_price = to_decimal(item.get("selling_price") if item.get("selling_price") is not None else mrp_val)
            disc_pct = to_decimal(item.get("discount_percent") or 0.0)
            gst_pct = to_decimal(item.get("gst_percent") if item.get("gst_percent") is not None else 12.0)

            if p_price < Decimal("0.00"):
                raise ValueError(f"Item #{idx} ({med_name}): Purchase price cannot be negative.")
            if s_price < Decimal("0.00"):
                raise ValueError(f"Item #{idx} ({med_name}): Selling price cannot be negative.")
            if mrp_val < Decimal("0.00"):
                raise ValueError(f"Item #{idx} ({med_name}): MRP cannot be negative.")

            # Invariant: Selling price cannot exceed MRP
            if mrp_val > Decimal("0.00") and s_price > mrp_val:
                raise ValueError(f"Item #{idx} ({med_name}): Selling price (₹{s_price}) cannot exceed MRP (₹{mrp_val}).")

            # Invariant: Purchase rate should not exceed MRP
            if mrp_val > Decimal("0.00") and p_price > mrp_val:
                raise ValueError(f"Item #{idx} ({med_name}): Purchase rate (₹{p_price}) cannot exceed MRP (₹{mrp_val}).")

            # Line item math using Decimal
            gross_item = quantize_money(strips_count * p_price)
            item_discount = calculate_discount(gross_item, disc_pct)
            item_taxable = gross_item - item_discount
            item_gst = quantize_money(item_taxable * (gst_pct / Decimal("100.0")))
            item_total = item_taxable + item_gst

            calc_taxable_sum += item_taxable
            calc_gst_sum += item_gst
            calc_grand_sum += item_total

            processed_items.append({
                "name": med_name,
                "manufacturer": str(item.get("manufacturer") or "").strip(),
                "batch_number": batch_num,
                "expiry_date": exp_date,
                "tablets_per_strip": tps,
                "quantity": qty_tablets,
                "free_quantity": free_tablets,
                "added_quantity": qty_tablets + free_tablets,
                "purchase_price": p_price,
                "selling_price": s_price,
                "mrp": mrp_val,
                "discount_percent": disc_pct,
                "gst_percent": gst_pct,
                "item_total": item_total
            })

        # Final Invoice Header Figures (using Decimal)
        final_taxable = quantize_money(total_amount if total_amount is not None else calc_taxable_sum)
        final_gst = quantize_money(gst_amount if gst_amount is not None else calc_gst_sum)
        final_grand = quantize_money(grand_total if grand_total is not None else calc_grand_sum)
        final_disc_pct = to_decimal(discount_percent or 0.0)

        # 4. Insert Purchase Header
        cursor.execute("""
            INSERT INTO purchases (
                purchase_invoice_number, supplier_id, purchase_date, due_date,
                payment_status, total_amount, discount_percent, gst_amount, grand_total
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            inv_num_clean, supplier_id, purchase_date, due_date,
            payment_status, float(final_taxable), float(final_disc_pct), float(final_gst), float(final_grand)
        ))
        purchase_id = cursor.lastrowid

        # 5. Insert Line Items, Update Inventory Batches & Log Stock Movements
        for p_item in processed_items:
            med_name = p_item["name"]
            batch_num = p_item["batch_number"]
            exp_date = p_item["expiry_date"]
            tps = p_item["tablets_per_strip"]
            qty = p_item["quantity"]
            free_qty = p_item["free_quantity"]
            added_qty = p_item["added_quantity"]
            p_price = p_item["purchase_price"]
            s_price = p_item["selling_price"]
            mrp_val = p_item["mrp"]
            disc_pct = p_item["discount_percent"]
            gst_pct = p_item["gst_percent"]
            item_total = p_item["item_total"]

            # 5a. Verify or Insert Medicine Master
            cursor.execute("SELECT id FROM medicines WHERE LOWER(TRIM(name)) = LOWER(TRIM(?));", (med_name,))
            med_row = cursor.fetchone()
            if med_row:
                medicine_id = med_row["id"]
            else:
                cursor.execute("""
                    INSERT INTO medicines (name, manufacturer, gst_rate, reorder_level, status)
                    VALUES (?, ?, ?, 20, 'Active');
                """, (med_name, p_item["manufacturer"], float(gst_pct)))
                medicine_id = cursor.lastrowid

            # 5b. Update existing batch or insert new batch
            cursor.execute("""
                SELECT id, quantity, free_quantity 
                FROM medicine_batches 
                WHERE medicine_id = ? AND LOWER(TRIM(batch_number)) = LOWER(TRIM(?));
            """, (medicine_id, batch_num))
            batch_row = cursor.fetchone()

            if batch_row:
                batch_id = batch_row["id"]
                # Atomically increment stock quantity in total_tablets
                cursor.execute("""
                    UPDATE medicine_batches SET
                        expiry_date = ?,
                        purchase_price = ?,
                        selling_price = ?,
                        mrp = ?,
                        tablets_per_strip = ?,
                        quantity = quantity + ?,
                        free_quantity = COALESCE(free_quantity, 0) + ?,
                        discount = ?,
                        gst = ?,
                        supplier_id = ?,
                        purchase_invoice = ?,
                        purchase_date = ?
                    WHERE id = ?;
                """, (
                    exp_date, float(p_price), float(s_price), float(mrp_val),
                    tps, added_qty, free_qty, float(disc_pct), float(gst_pct),
                    supplier_id, inv_num_clean, purchase_date, batch_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO medicine_batches (
                        batch_number, medicine_id, expiry_date, purchase_price, selling_price, mrp,
                        tablets_per_strip, quantity, free_quantity, discount, gst, supplier_id,
                        purchase_invoice, purchase_date, low_stock_threshold
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 20);
                """, (
                    batch_num, medicine_id, exp_date, float(p_price), float(s_price), float(mrp_val),
                    tps, added_qty, free_qty, float(disc_pct), float(gst_pct),
                    supplier_id, inv_num_clean, purchase_date
                ))

            # 5c. Insert Item Detail Record
            cursor.execute("""
                INSERT INTO purchase_items (
                    purchase_id, medicine_id, batch_number, expiry_date, quantity,
                    free_quantity, purchase_price, mrp, discount_percent, gst_percent, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                purchase_id, medicine_id, batch_num, exp_date, qty,
                free_qty, float(p_price), float(mrp_val), float(disc_pct), float(gst_pct), float(item_total)
            ))

            # 5d. Log Immutable Stock Movement
            log_stock_movement(
                cursor=cursor,
                medicine_id=medicine_id,
                batch_number=batch_num,
                type_name="PURCHASE",
                quantity=added_qty,
                reference_id=inv_num_clean,
                description=f"Procured via Purchase #{inv_num_clean} (+{qty} purchased, +{free_qty} free tablets)"
            )

        # 6. Supplier Outstanding Balance & Ledger Updates
        supp_balance = to_decimal(supplier_row["current_balance"])

        if payment_status == "Paid":
            settled_amount = final_grand
        elif payment_status == "Unpaid":
            settled_amount = Decimal("0.00")
        else:  # "Partial"
            settled_amount = quantize_money(paid_amount if paid_amount is not None else Decimal("0.00"))

        new_supp_balance = supp_balance + final_grand - settled_amount

        cursor.execute("UPDATE suppliers SET current_balance = ? WHERE id = ?;", (float(new_supp_balance), supplier_id))

        # 6a. Record the purchase credit in ledger
        temp_balance = supp_balance + final_grand
        cursor.execute("""
            INSERT INTO supplier_ledger (
                supplier_id, date, type, reference_id, debit, credit, balance, description
            ) VALUES (?, ?, 'PURCHASE', ?, 0.0, ?, ?, ?);
        """, (
            supplier_id, purchase_date, inv_num_clean, float(final_grand),
            float(temp_balance), f"Invoice #{inv_num_clean} purchase entry"
        ))

        # 6b. Record settlement debit if paid/partial immediately
        if settled_amount > Decimal("0.00"):
            cursor.execute("""
                INSERT INTO supplier_ledger (
                    supplier_id, date, type, reference_id, debit, credit, balance, description
                ) VALUES (?, ?, 'PAYMENT', ?, ?, 0.0, ?, ?);
            """, (
                supplier_id, purchase_date, inv_num_clean, float(settled_amount),
                float(new_supp_balance), f"Immediate settlement for invoice #{inv_num_clean} ({payment_status})"
            ))

        if should_close:
            conn.commit()

        return purchase_id

    except Exception:
        if should_close:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if should_close:
            conn.close()


# ------------------------------------------------------------------------------
# 2. Purchase Returns Management (Section 21)
# ------------------------------------------------------------------------------

def record_purchase_return(
    supplier_id: int,
    return_date: str,
    total_refund: Union[int, float, str, Decimal],
    reference_invoice: str,
    returned_items: List[Dict[str, Any]],
    reason: str = "Return to supplier",
    cursor: Optional[sqlite3.Cursor] = None
) -> int:
    """
    Registers a debit return note to a supplier for returned stock.
    Atomically:
      1. Validates sufficient stock in medicine_batches.
      2. Deducts quantity from batches.
      3. Records negative stock movement.
      4. Decreases supplier current balance (less owed to supplier).
      5. Records RETURN debit entry in supplier_ledger.
    """
    if not returned_items:
        raise ValueError("Supplier return item list is empty.")

    ref_clean = str(reference_invoice).strip() if reference_invoice else "N/A"
    if not return_date:
        return_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    should_close = False
    if cursor is None:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        should_close = True
    else:
        conn = cursor.connection

    try:
        # 1. Verify Supplier Exists
        cursor.execute("SELECT id, name, current_balance FROM suppliers WHERE id = ?;", (supplier_id,))
        supplier_row = cursor.fetchone()
        if not supplier_row:
            raise ValueError(f"Supplier ID {supplier_id} not found.")

        # 2. Insert Return Header Placeholder
        refund_dec = quantize_money(total_refund)
        cursor.execute("""
            INSERT INTO purchase_returns (supplier_id, return_date, total_refund, reference_invoice, reason)
            VALUES (?, ?, ?, ?, ?);
        """, (supplier_id, return_date, float(refund_dec), ref_clean, reason))
        return_id = cursor.lastrowid

        # 3. Process Each Returned Item
        calculated_total = Decimal("0.00")

        for idx, item in enumerate(returned_items, start=1):
            med_id = int(item["medicine_id"])
            batch_num = str(item["batch_number"]).strip()

            # Find target batch
            cursor.execute("""
                SELECT id, quantity, tablets_per_strip, purchase_price, gst
                FROM medicine_batches 
                WHERE medicine_id = ? AND LOWER(TRIM(batch_number)) = LOWER(TRIM(?));
            """, (med_id, batch_num))
            batch = cursor.fetchone()
            if not batch:
                raise ValueError(f"Item #{idx}: Batch '{batch_num}' not found in stock for medicine ID {med_id}.")

            tps = int(batch["tablets_per_strip"] or 10)

            # Determine tablets to return
            strip_key = next((k for k in ("strips_returned", "strips", "strips_qty") if k in item and item[k] is not None), None)
            if strip_key:
                ret_qty = int(to_decimal(item[strip_key]) * Decimal(str(tps)))
            else:
                ret_qty = int(item.get("quantity") or 0)

            if ret_qty <= 0:
                raise ValueError(f"Item #{idx} (Batch '{batch_num}'): Return quantity must be greater than 0.")

            # Concurrency double-check on stock availability
            if batch["quantity"] < ret_qty:
                raise ValueError(
                    f"Insufficient stock for batch '{batch_num}'. "
                    f"Available: {batch['quantity']} tablets, return requested: {ret_qty} tablets."
                )

            # Atomically decrement stock
            cursor.execute("""
                UPDATE medicine_batches 
                SET quantity = quantity - ? 
                WHERE id = ? AND quantity >= ?;
            """, (ret_qty, batch["id"], ret_qty))
            if cursor.rowcount == 0:
                raise ValueError(f"Stock conflict on batch '{batch_num}'. Please retry operation.")

            # Compute financial return value
            rate = to_decimal(item.get("purchase_price", batch["purchase_price"]))
            gst = to_decimal(item.get("gst_percent", batch["gst"]))

            strips_val = Decimal(str(ret_qty)) / Decimal(str(tps))
            item_taxable = quantize_money(strips_val * rate)
            item_gst = quantize_money(item_taxable * (gst / Decimal("100.0")))
            item_total = item_taxable + item_gst
            calculated_total += item_total

            # Record Return Line Item
            cursor.execute("""
                INSERT INTO purchase_return_items (
                    purchase_return_id, medicine_id, batch_number, quantity, purchase_price, gst_percent, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (return_id, med_id, batch_num, ret_qty, float(rate), float(gst), float(item_total)))

            # Log negative stock movement
            log_stock_movement(
                cursor=cursor,
                medicine_id=med_id,
                batch_number=batch_num,
                type_name="PURCHASE_RETURN",
                quantity=-ret_qty,
                reference_id=f"RET-{return_id}",
                description=f"Purchase return to supplier against invoice #{ref_clean}"
            )

        # Final refund figure
        final_refund = refund_dec if refund_dec > Decimal("0.00") else calculated_total
        cursor.execute("UPDATE purchase_returns SET total_refund = ? WHERE id = ?;", (float(final_refund), return_id))

        # 4. Reduce Supplier Outstanding Balance & Post to Ledger
        supp_balance = to_decimal(supplier_row["current_balance"])
        new_supp_balance = supp_balance - final_refund
        cursor.execute("UPDATE suppliers SET current_balance = ? WHERE id = ?;", (float(new_supp_balance), supplier_id))

        cursor.execute("""
            INSERT INTO supplier_ledger (
                supplier_id, date, type, reference_id, debit, credit, balance, description
            ) VALUES (?, ?, 'RETURN', ?, ?, 0.0, ?, ?);
        """, (
            supplier_id, return_date, f"RET-{return_id}", float(final_refund),
            float(new_supp_balance), f"Debit return note reference RET-{return_id} (Invoice Ref: {ref_clean})"
        ))

        if should_close:
            conn.commit()

        return return_id

    except Exception:
        if should_close:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if should_close:
            conn.close()


# ------------------------------------------------------------------------------
# 3. Read & Query Helpers
# ------------------------------------------------------------------------------

def get_all_purchases() -> List[Dict[str, Any]]:
    """Retrieves all purchase invoices ordered by latest purchase date."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, s.name as supplier_name, s.phone as supplier_phone, s.gst_number as supplier_gst
        FROM purchases p
        JOIN suppliers s ON p.supplier_id = s.id
        ORDER BY p.purchase_date DESC, p.id DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_purchase_by_id(purchase_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single purchase invoice header by ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, s.name as supplier_name, s.phone as supplier_phone, 
               s.address as supplier_address, s.gst_number as supplier_gst
        FROM purchases p
        JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.id = ?;
    """, (purchase_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_purchase_by_invoice(purchase_invoice_number: str, supplier_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Looks up a purchase invoice by invoice number and optional supplier ID."""
    if not purchase_invoice_number:
        return None
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if supplier_id is not None:
        cursor.execute("""
            SELECT p.*, s.name as supplier_name 
            FROM purchases p
            JOIN suppliers s ON p.supplier_id = s.id
            WHERE LOWER(TRIM(p.purchase_invoice_number)) = LOWER(TRIM(?)) AND p.supplier_id = ?;
        """, (purchase_invoice_number, supplier_id))
    else:
        cursor.execute("""
            SELECT p.*, s.name as supplier_name 
            FROM purchases p
            JOIN suppliers s ON p.supplier_id = s.id
            WHERE LOWER(TRIM(p.purchase_invoice_number)) = LOWER(TRIM(?));
        """, (purchase_invoice_number,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_purchase_items(purchase_id: int) -> List[Dict[str, Any]]:
    """Retrieves line items for a given purchase invoice ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pi.*, m.name as medicine_name, m.manufacturer, m.generic_name
        FROM purchase_items pi
        JOIN medicines m ON pi.medicine_id = m.id
        WHERE pi.purchase_id = ?
        ORDER BY pi.id ASC;
    """, (purchase_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_purchase_returns() -> List[Dict[str, Any]]:
    """Retrieves all purchase returns ordered by date."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.*, s.name as supplier_name
        FROM purchase_returns pr
        JOIN suppliers s ON pr.supplier_id = s.id
        ORDER BY pr.return_date DESC, pr.id DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_purchase_return_by_id(return_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single purchase return record by ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.*, s.name as supplier_name, s.phone as supplier_phone, s.gst_number as supplier_gst
        FROM purchase_returns pr
        JOIN suppliers s ON pr.supplier_id = s.id
        WHERE pr.id = ?;
    """, (return_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_purchase_return_items(return_id: int) -> List[Dict[str, Any]]:
    """Retrieves all items belonging to a purchase return."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pri.*, m.name as medicine_name, m.manufacturer
        FROM purchase_return_items pri
        JOIN medicines m ON pri.medicine_id = m.id
        WHERE pri.purchase_return_id = ?
        ORDER BY pri.id ASC;
    """, (return_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
