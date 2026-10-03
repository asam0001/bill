import sqlite3
from datetime import datetime
from decimal import Decimal
from database.db import get_connection
from utils.money import (
    to_decimal, quantize_money, calculate_tablet_price,
    calculate_line_item, calculate_tax, calculate_discount
)
from utils.medicine_service import (
    log_stock_movement, is_batch_expired, authorize_expired_sale_override
)

# ==============================================================================
# MediTrack Sales & Billing Engine (Section 4, 13, 14, 16, 18, 20, 21)
# Enforces:
#  - Authoritative tablet deductions
#  - Decimal monetary accuracy with commercial rounding
#  - Strict expired stock blocking with audited administrative overrides
#  - Atomic double-check inventory commits with automatic rollbacks
#  - Return tracking preventing over-returns beyond original billed quantities
# ==============================================================================

def generate_next_bill_number() -> str:
    """
    Generates the next sequential invoice number based on shop settings.
    E.g. MT-2026-000001
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM settings WHERE key='bill_prefix';")
    p_row = cursor.fetchone()
    prefix = p_row["value"] if p_row else "MT-2026-"

    cursor.execute("SELECT value FROM settings WHERE key='starting_bill_number';")
    s_row = cursor.fetchone()
    start_num = int(s_row["value"]) if s_row else 1

    cursor.execute("SELECT bill_number FROM bills WHERE bill_number LIKE ? ORDER BY bill_number DESC LIMIT 1;", (f"{prefix}%",))
    last_row = cursor.fetchone()

    if last_row:
        last_bill = last_row["bill_number"]
        suffix = last_bill[len(prefix):]
        try:
            next_num = int(suffix) + 1
        except ValueError:
            next_num = start_num
    else:
        next_num = start_num

    conn.close()
    return f"{prefix}{str(next_num).zfill(6)}"


def record_sale(
    customer_id: int,
    customer_name: str,
    customer_phone: str,
    payment_mode: str,
    cart_items: list,
    discount_percent: float = 0.0,
    allow_expired_override: bool = False,
    override_user: str = "Admin",
    override_reason: str = ""
) -> str:
    """
    Executes an atomic retail pharmacy sale.
    
    cart_items structure:
    [
        {
            'medicine_id': int,
            'batch_number': str,
            'quantity': int  # Authoritative quantity in tablets
        },
        ...
    ]
    """
    if not cart_items:
        raise ValueError("Cart cannot be empty for checkout.")
    
    dec_discount_pct = to_decimal(discount_percent)
    if dec_discount_pct < Decimal("0.0") or dec_discount_pct > Decimal("100.0"):
        raise ValueError("Discount percentage must be between 0.0% and 100.0%.")

    bill_number = generate_next_bill_number()

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Verify customer if specified
        cust_row = None
        if customer_id:
            cursor.execute("SELECT id, name, outstanding_balance, credit_limit FROM customers WHERE id = ?;", (customer_id,))
            cust_row = cursor.fetchone()
            if not cust_row:
                raise ValueError("Specified customer not found.")

        bill_items_to_save = []
        total_gross = Decimal("0.00")
        total_discount = Decimal("0.00")
        total_profit = Decimal("0.00")
        total_gst = Decimal("0.00")

        # 2. Validate items, check stock, enforce expiry, compute Decimal lines
        for item in cart_items:
            med_id = item["medicine_id"]
            batch_num = str(item["batch_number"]).strip()
            qty = int(item["quantity"])

            if qty <= 0:
                raise ValueError(f"Quantity must be greater than zero (received {qty}).")

            # Fetch medicine master
            cursor.execute("SELECT id, name FROM medicines WHERE id = ? AND status = 'Active';", (med_id,))
            med = cursor.fetchone()
            if not med:
                raise ValueError(f"Medicine ID {med_id} not found or inactive.")

            # Fetch batch details
            cursor.execute("""
                SELECT id, quantity, purchase_price, selling_price, mrp, gst, tablets_per_strip, expiry_date
                FROM medicine_batches 
                WHERE medicine_id = ? AND batch_number = ?;
            """, (med_id, batch_num))
            batch = cursor.fetchone()
            if not batch:
                raise ValueError(f"Batch '{batch_num}' not found for medicine '{med['name']}'.")

            # Expiry Safety Enforcement (Section 8 & 15)
            if is_batch_expired(batch["expiry_date"]):
                if not allow_expired_override:
                    raise ValueError(
                        f"Cannot dispense expired medicine '{med['name']}' "
                        f"(Batch: {batch_num}, Expired: {batch['expiry_date']}). "
                        f"An authorized administrative override is required."
                    )
                # Record explicit audit log for authorized override
                reason_clean = override_reason.strip() or f"POS checkout override for bill #{bill_number}"
                authorize_expired_sale_override(med_id, batch_num, override_user or "Admin", reason_clean, cursor=cursor)

            # Stock check
            available_qty = batch["quantity"]
            if available_qty < qty:
                raise ValueError(
                    f"Insufficient stock for {med['name']} (Batch: {batch_num}). "
                    f"Available: {available_qty} tablets. Requested: {qty} tablets."
                )

            # Unit calculations via centralized money module
            tps = batch["tablets_per_strip"]
            p_tablet = calculate_tablet_price(batch["purchase_price"], tps)
            s_tablet = calculate_tablet_price(batch["selling_price"], tps)

            line_calc = calculate_line_item(
                quantity_tablets=qty,
                price_per_tablet=s_tablet,
                discount_percent=dec_discount_pct,
                cost_per_tablet=p_tablet,
                gst_percent=batch["gst"]
            )

            total_gross += line_calc["gross"]
            total_discount += line_calc["discount_amount"]
            total_profit += line_calc["profit"]
            total_gst += line_calc["tax_amount"]

            bill_items_to_save.append({
                "medicine_id": med_id,
                "medicine_name": med["name"],
                "batch": batch_num,
                "quantity": qty,
                "price_per_tablet": line_calc["float_gross"] / qty if qty > 0 else 0.0,
                "discount_percent": float(dec_discount_pct),
                "subtotal": line_calc["float_subtotal"],
                "profit": line_calc["float_profit"],
                "gst_percent": float(batch["gst"]),
                "batch_id": batch["id"],
                "current_stock": available_qty,
                "new_stock": available_qty - qty
            })

        grand_total = total_gross - total_discount
        half_gst = (total_gst / Decimal("2.0")).quantize(Decimal("0.01"))
        cgst_amount = float(half_gst)
        sgst_amount = float(total_gst - half_gst)

        # Credit Limit validation for unpaid sales
        if payment_mode == "Unpaid" and cust_row:
            projected_balance = Decimal(str(cust_row["outstanding_balance"])) + grand_total
            credit_limit = Decimal(str(cust_row["credit_limit"]))
            if credit_limit > Decimal("0.0") and projected_balance > credit_limit:
                raise ValueError(
                    f"Credit limit exceeded for customer '{cust_row['name']}'. "
                    f"Limit: ₹{credit_limit:,.2f}, Current Balance: ₹{cust_row['outstanding_balance']:,.2f}, "
                    f"Projected: ₹{projected_balance:,.2f}."
                )

        # 3. Insert Bill Header
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO bills (
                bill_number, date, customer_id, customer_name, customer_phone, payment_mode, 
                total_amount, discount, discount_amount, grand_total, total_profit, 
                sgst, cgst, igst, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'Active');
        """, (
            bill_number, date_str, customer_id, (customer_name or "").strip(), (customer_phone or "").strip(), payment_mode,
            float(total_gross), float(dec_discount_pct), float(total_discount), float(grand_total), float(total_profit),
            sgst_amount, cgst_amount
        ))

        # 4. Save Line Items & Deduct Stock with Concurrency Check
        for item in bill_items_to_save:
            cursor.execute("""
                INSERT INTO bill_items (
                    bill_number, medicine_id, medicine_name, batch, quantity, 
                    price_per_tablet, discount_percent, subtotal, profit, gst_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                bill_number, item["medicine_id"], item["medicine_name"], item["batch"], item["quantity"],
                item["price_per_tablet"], item["discount_percent"], item["subtotal"], item["profit"], item["gst_percent"]
            ))

            # Concurrency-safe atomic stock deduction
            cursor.execute("""
                UPDATE medicine_batches 
                SET quantity = quantity - ? 
                WHERE id = ? AND quantity >= ?;
            """, (item["quantity"], item["batch_id"], item["quantity"]))

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Concurrent stock conflict on '{item['medicine_name']}' (Batch: {item['batch']}). "
                    f"Available stock changed during transaction. Sale aborted."
                )

            # Log movement
            log_stock_movement(
                cursor, item["medicine_id"], item["batch"], "SALE",
                -item["quantity"], bill_number, f"POS retail invoice sale #{bill_number}"
            )

        # 5. Handle Customer outstanding balance for Credit sales
        if payment_mode == "Unpaid" and customer_id:
            new_cust_balance = float(Decimal(str(cust_row["outstanding_balance"])) + grand_total)
            cursor.execute("UPDATE customers SET outstanding_balance = ? WHERE id = ?;", (new_cust_balance, customer_id))
            
            cursor.execute("""
                INSERT INTO customer_ledger (
                    customer_id, date, type, reference_id, debit, credit, balance, description
                ) VALUES (?, ?, 'SALE', ?, ?, 0.0, ?, ?);
            """, (
                customer_id, date_str, bill_number, float(grand_total), new_cust_balance,
                f"Credit invoice #{bill_number} retail billing"
            ))

        cursor.execute("COMMIT;")
        return bill_number

    except Exception as ex:
        cursor.execute("ROLLBACK;")
        raise ex
    finally:
        conn.close()


def get_all_bills(limit: int = 500):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills ORDER BY date DESC LIMIT ?;", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_bill_by_number(bill_number: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE bill_number = ?;", (bill_number,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_bill_items(bill_number: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bill_items WHERE bill_number = ?;", (bill_number,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_unpaid_bills():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE payment_mode = 'Unpaid' AND status = 'Active' ORDER BY date DESC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def pay_unpaid_bill(bill_number: str, payment_mode: str):
    """
    Clears an outstanding unpaid/credit bill with Cash, UPI, or Card.
    Synchronously updates customer credit balance and customer ledger.
    """
    if payment_mode not in ("Cash", "UPI", "Card"):
        raise ValueError(f"Invalid settlement payment mode '{payment_mode}'. Must be Cash, UPI, or Card.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")

        cursor.execute("SELECT customer_id, grand_total FROM bills WHERE bill_number = ? AND payment_mode = 'Unpaid';", (bill_number,))
        bill = cursor.fetchone()
        if not bill:
            raise ValueError(f"Unpaid invoice #{bill_number} not found or already settled.")

        cursor.execute("UPDATE bills SET payment_mode = ? WHERE bill_number = ?;", (payment_mode, bill_number))

        cust_id = bill["customer_id"]
        amount_dec = to_decimal(bill["grand_total"])

        if cust_id:
            cursor.execute("SELECT outstanding_balance FROM customers WHERE id = ?;", (cust_id,))
            cust = cursor.fetchone()
            if cust:
                new_bal = float(max(Decimal("0.00"), to_decimal(cust["outstanding_balance"]) - amount_dec))
                cursor.execute("UPDATE customers SET outstanding_balance = ? WHERE id = ?;", (new_bal, cust_id))

                date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO customer_ledger (
                        customer_id, date, type, reference_id, debit, credit, balance, description
                    ) VALUES (?, ?, 'PAYMENT', ?, 0.0, ?, ?, ?);
                """, (
                    cust_id, date_str, bill_number, float(amount_dec), new_bal,
                    f"Payment settled via {payment_mode} for invoice #{bill_number}"
                ))

        cursor.execute("COMMIT;")
    except Exception as ex:
        cursor.execute("ROLLBACK;")
        raise ex
    finally:
        conn.close()


def get_total_unpaid_amount() -> float:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(grand_total) FROM bills WHERE payment_mode = 'Unpaid' AND status = 'Active';")
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if (row and row[0] is not None) else 0.0


# ------------------------------------------------------------------------------
# Sales Returns & Cancellation Engine (Section 20 & 21)
# ------------------------------------------------------------------------------

def record_sales_return(bill_number: str, returned_items: list, refund_mode: str = "Cash", reason: str = "Customer Return"):
    """
    Executes a formal sales return.
    Strictly validates that returned quantity does not exceed originally billed quantity
    minus any previously processed returns.
    
    returned_items:
    [
        {'medicine_id': int, 'batch_number': str, 'quantity': int, 'price_per_tablet': float, 'gst_percent': float}
    ]
    """
    if not returned_items:
        raise ValueError("Return items list cannot be empty.")

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Verify original bill exists
        cursor.execute("SELECT customer_id, grand_total, payment_mode FROM bills WHERE bill_number = ?;", (bill_number,))
        bill_row = cursor.fetchone()
        if not bill_row:
            raise ValueError(f"Invoice #{bill_number} not found.")

        total_refund_dec = Decimal("0.00")

        # 2. Validate line quantities against billed quantity and past returns
        for item in returned_items:
            med_id = item["medicine_id"]
            batch_num = item["batch_number"].strip()
            ret_qty = int(item["quantity"])

            if ret_qty <= 0:
                raise ValueError("Return quantity must be greater than zero.")

            # Check original billed quantity
            cursor.execute("""
                SELECT quantity, price_per_tablet FROM bill_items 
                WHERE bill_number = ? AND medicine_id = ? AND batch = ?;
            """, (bill_number, med_id, batch_num))
            bi_row = cursor.fetchone()
            if not bi_row:
                raise ValueError(f"Medicine batch '{batch_num}' was not part of original invoice #{bill_number}.")

            billed_qty = bi_row["quantity"]

            # Query previously returned quantities for this item
            cursor.execute("""
                SELECT COALESCE(SUM(sri.quantity), 0) as already_returned
                FROM sales_return_items sri
                JOIN sales_returns sr ON sri.sales_return_id = sr.id
                WHERE sr.bill_number = ? AND sri.medicine_id = ? AND sri.batch = ?;
            """, (bill_number, med_id, batch_num))
            past_row = cursor.fetchone()
            already_returned = past_row["already_returned"] if past_row else 0
            max_returnable = billed_qty - already_returned

            if ret_qty > max_returnable:
                raise ValueError(
                    f"Return quantity ({ret_qty}) exceeds returnable quantity ({max_returnable}) "
                    f"for Batch '{batch_num}'. Originally Billed: {billed_qty}, Already Returned: {already_returned}."
                )

            rate_dec = to_decimal(item.get("price_per_tablet", bi_row["price_per_tablet"]))
            item_refund = quantize_money(Decimal(str(ret_qty)) * rate_dec)
            total_refund_dec += item_refund

        # 3. Create sales_returns record
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO sales_returns (bill_number, return_date, total_refund, refund_mode, reason)
            VALUES (?, ?, ?, ?, ?);
        """, (bill_number, date_str, float(total_refund_dec), refund_mode, reason.strip()))
        sales_return_id = cursor.lastrowid

        # 4. Insert items & restore stock
        for item in returned_items:
            med_id = item["medicine_id"]
            batch_num = item["batch_number"].strip()
            ret_qty = int(item["quantity"])
            rate_float = float(to_decimal(item.get("price_per_tablet", 0.0)))
            gst_float = float(to_decimal(item.get("gst_percent", 12.0)))
            item_refund_float = float(quantize_money(Decimal(str(ret_qty)) * to_decimal(rate_float)))

            cursor.execute("""
                INSERT INTO sales_return_items (
                    sales_return_id, medicine_id, batch, quantity, price_per_tablet, gst_percent, total_refund
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (sales_return_id, med_id, batch_num, ret_qty, rate_float, gst_float, item_refund_float))

            # Atomically restore stock into batch
            cursor.execute("""
                UPDATE medicine_batches 
                SET quantity = quantity + ? 
                WHERE medicine_id = ? AND batch_number = ?;
            """, (ret_qty, med_id, batch_num))

            # Log stock movement
            log_stock_movement(
                cursor, med_id, batch_num, "SALES_RETURN", ret_qty,
                f"SRET-{sales_return_id}", f"Sales return ref invoice #{bill_number} (Reason: {reason})"
            )

        # 5. Customer ledger adjustment for credit return
        cust_id = bill_row["customer_id"]
        if bill_row["payment_mode"] == "Unpaid" and cust_id:
            cursor.execute("SELECT outstanding_balance FROM customers WHERE id = ?;", (cust_id,))
            cust = cursor.fetchone()
            if cust:
                new_bal = float(max(Decimal("0.00"), to_decimal(cust["outstanding_balance"]) - total_refund_dec))
                cursor.execute("UPDATE customers SET outstanding_balance = ? WHERE id = ?;", (new_bal, cust_id))

                cursor.execute("""
                    INSERT INTO customer_ledger (
                        customer_id, date, type, reference_id, debit, credit, balance, description
                    ) VALUES (?, ?, 'RETURN', ?, 0.0, ?, ?, ?);
                """, (
                    cust_id, date_str, f"SRET-{sales_return_id}", float(total_refund_dec), new_bal,
                    f"Credit adjustment for sales return #{sales_return_id} (Invoice #{bill_number})"
                ))

        cursor.execute("COMMIT;")
        return sales_return_id

    except Exception as ex:
        cursor.execute("ROLLBACK;")
        raise ex
    finally:
        conn.close()


# ------------------------------------------------------------------------------
# Reports & Dashboard Helpers
# ------------------------------------------------------------------------------

def get_report_sales_data(filter_type: str):
    from datetime import timedelta
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    days_map = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}
    days = days_map.get(filter_type, 7)

    date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT * FROM bills WHERE date >= ? AND status = 'Active' ORDER BY date ASC;", (date_limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_report_top_sold(filter_type: str, limit: int = 10):
    from datetime import timedelta
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    days_map = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}
    days = days_map.get(filter_type, 7)

    date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        SELECT bi.medicine_name, bi.batch, SUM(bi.quantity) as total_sold
        FROM bill_items bi
        JOIN bills b ON bi.bill_number = b.bill_number
        WHERE b.date >= ? AND b.status = 'Active'
        GROUP BY bi.medicine_name, bi.batch
        ORDER BY total_sold DESC
        LIMIT ?;
    """, (date_limit, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_report_top_profitable(filter_type: str, limit: int = 10):
    from datetime import timedelta
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    days_map = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}
    days = days_map.get(filter_type, 7)

    date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        SELECT bi.medicine_name, bi.batch, SUM(bi.profit) as total_profit
        FROM bill_items bi
        JOIN bills b ON bi.bill_number = b.bill_number
        WHERE b.date >= ? AND b.status = 'Active'
        GROUP BY bi.medicine_name, bi.batch
        ORDER BY total_profit DESC
        LIMIT ?;
    """, (date_limit, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
