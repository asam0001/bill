import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from database.db import get_connection

# ==============================================================================
# MediTrack Inventory & Stock Control Service
# Authoritative Unit: total_tablets (Strips & Loose are derived)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Authoritative Unit Calculations (Section 5 & 6)
# ------------------------------------------------------------------------------

def calculate_strips_details(total_tablets: int, tablets_per_strip: int):
    """
    Computes full strips and loose tablets strictly from authoritative total_tablets.
    Formula:
        full_strips = total_tablets // tablets_per_strip
        loose_tablets = total_tablets % tablets_per_strip
    """
    if tablets_per_strip <= 0:
        return 0, max(0, int(total_tablets))
    total = max(0, int(total_tablets))
    strips = total // tablets_per_strip
    loose = total % tablets_per_strip
    return strips, loose


def get_formatted_stock_string(total_tablets: int, tablets_per_strip: int) -> str:
    """Human-readable stock display string (e.g. '12 strips + 4 tab')."""
    strips, loose = calculate_strips_details(total_tablets, tablets_per_strip)
    if strips == 0 and loose == 0:
        return "0 strips (Out of stock)"
    if loose == 0:
        return f"{strips} strip{'s' if strips != 1 else ''}"
    if strips == 0:
        return f"{loose} tab{'s' if loose != 1 else ''}"
    return f"{strips} strip{'s' if strips != 1 else ''} + {loose} tab{'s' if loose != 1 else ''}"


def convert_units_to_tablets(quantity: int, unit: str, tablets_per_strip: int) -> int:
    """
    Converts user input quantity into authoritative total_tablets based on unit.
    Units supported: 'Tablet', 'Tab', 'Strip', 'Strips'.
    """
    qty = max(0, int(quantity))
    unit_norm = str(unit).strip().capitalize()
    if unit_norm in ("Strip", "Strips"):
        return qty * max(1, int(tablets_per_strip))
    return qty


def calculate_tablet_prices(purchase_price_per_strip: float, selling_price_per_strip: float, tablets_per_strip: int):
    """
    Calculates per-tablet purchase and selling prices using Decimal precision.
    Guarantees no floating point drift during single-tablet billing.
    """
    t_count = Decimal(str(max(1, int(tablets_per_strip))))
    p_strip = Decimal(str(purchase_price_per_strip))
    s_strip = Decimal(str(selling_price_per_strip))

    p_tablet = (p_strip / t_count).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    s_tablet = (s_strip / t_count).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    return float(p_tablet), float(s_tablet)


# ------------------------------------------------------------------------------
# 2. Stock Health & Expiry Classification (Section 8, 9, 42)
# ------------------------------------------------------------------------------

def get_batch_status(expiry_date_str: str, total_tablets: int, threshold: int = 20, expiry_warning_days: int = 90, today=None):
    """
    Evaluates batch status against expiry and threshold rules.
    Returns: (STATUS_CODE, STATUS_DISPLAY_LABEL)
    """
    if today is None:
        today = datetime.now().date()
    elif isinstance(today, str):
        today = datetime.strptime(today, "%Y-%m-%d").date()

    if total_tablets <= 0:
        return "OUT_OF_STOCK", "⚫ Out of Stock"

    try:
        exp_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return "UNKNOWN", "❓ Invalid Expiry"

    if exp_date < today:
        return "EXPIRED", "🔴 Expired"
    elif exp_date <= today + timedelta(days=expiry_warning_days):
        return "EXPIRING_SOON", "🟠 Expiring Soon"
    elif total_tablets <= threshold:
        return "LOW_STOCK", "🟡 Low Stock"
    else:
        return "HEALTHY", "🟢 In Stock"


def is_batch_expired(expiry_date_str: str, today_str: str = None) -> bool:
    """Checks whether an expiry date string is strictly in the past."""
    if today_str is None:
        today = datetime.now().date()
    else:
        today = datetime.strptime(today_str, "%Y-%m-%d").date()
    try:
        exp_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
        return exp_date < today
    except Exception:
        return False


def _format_batch_row(row):
    """
    Standardizes a database batch row into a fully populated, UI-ready dict.
    Provides explicit unit counts, tablet prices, and stock health tags.
    """
    med = dict(row)
    med["batch"] = med.get("batch_number", "")
    med["total_tablets"] = med.get("quantity", 0)

    # Threshold priority: batch threshold -> medicine reorder_level -> 20
    threshold = med.get("low_stock_threshold") or med.get("reorder_level") or 20
    med["threshold"] = threshold
    med["reorder_level"] = threshold

    t_strip = med.get("tablets_per_strip") or 10
    med["tablets_per_strip"] = t_strip

    # Derived display quantities
    strips, loose = calculate_strips_details(med["quantity"], t_strip)
    med["strips"] = strips
    med["loose_tablets"] = loose
    med["stock_string"] = get_formatted_stock_string(med["quantity"], t_strip)

    # Unit prices
    p_strip = med.get("purchase_price", 0.0)
    s_strip = med.get("selling_price", 0.0)
    med["purchase_price_per_strip"] = p_strip
    med["selling_price_per_strip"] = s_strip

    p_tab, s_tab = calculate_tablet_prices(p_strip, s_strip, t_strip)
    med["purchase_price_per_tablet"] = p_tab
    med["selling_price_per_tablet"] = s_tab

    # Stock Health Status
    status_code, status_label = get_batch_status(med.get("expiry_date", ""), med["quantity"], threshold)
    med["stock_status"] = status_code
    med["status_label"] = status_label
    med["is_expired"] = (status_code == "EXPIRED")
    med["is_expiring_soon"] = (status_code == "EXPIRING_SOON")
    med["is_low_stock"] = (status_code == "LOW_STOCK" or med["quantity"] <= threshold)
    med["is_out_of_stock"] = (med["quantity"] <= 0)

    return med


# ------------------------------------------------------------------------------
# 3. Medicine Master CRUD (Section 7)
# ------------------------------------------------------------------------------

def add_medicine_master(name, manufacturer="", generic_name="", brand="", category="", dosage_form="Tablet", 
                        strength="", pack_size="10", unit="Strip", hsn_code="", gst_rate=12.0, 
                        prescription_required=0, reorder_level=20, minimum_stock=10, maximum_stock=500, 
                        rack_shelf="", status="Active"):
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Medicine Name cannot be empty.")
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO medicines (
                name, manufacturer, generic_name, brand, category, dosage_form, 
                strength, pack_size, unit, hsn_code, gst_rate, prescription_required, 
                reorder_level, minimum_stock, maximum_stock, rack_shelf, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            clean_name, manufacturer.strip(), generic_name.strip(), brand.strip(), category.strip(), dosage_form,
            strength.strip(), pack_size.strip(), unit.strip(), hsn_code.strip(), gst_rate, prescription_required,
            reorder_level, minimum_stock, maximum_stock, rack_shelf.strip(), status
        ))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"Medicine master with name '{clean_name}' already exists.")
    finally:
        conn.close()


def update_medicine_master(medicine_id, name, manufacturer="", generic_name="", brand="", category="", 
                           dosage_form="Tablet", strength="", pack_size="10", unit="Strip", hsn_code="", 
                           gst_rate=12.0, prescription_required=0, reorder_level=20, minimum_stock=10, 
                           maximum_stock=500, rack_shelf="", status="Active"):
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Medicine Name cannot be empty.")
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE medicines SET 
                name=?, manufacturer=?, generic_name=?, brand=?, category=?, dosage_form=?, 
                strength=?, pack_size=?, unit=?, hsn_code=?, gst_rate=?, prescription_required=?, 
                reorder_level=?, minimum_stock=?, maximum_stock=?, rack_shelf=?, status=?
            WHERE id=?;
        """, (
            clean_name, manufacturer.strip(), generic_name.strip(), brand.strip(), category.strip(), dosage_form,
            strength.strip(), pack_size.strip(), unit.strip(), hsn_code.strip(), gst_rate, prescription_required,
            reorder_level, minimum_stock, maximum_stock, rack_shelf.strip(), status, medicine_id
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"Medicine master with name '{clean_name}' already exists.")
    finally:
        conn.close()


def delete_medicine_master(medicine_id):
    """Soft-deletes a medicine master by setting status to Inactive."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE medicines SET status='Inactive' WHERE id=?;", (medicine_id,))
    conn.commit()
    conn.close()


def get_all_medicines_master(include_inactive: bool = False):
    conn = get_connection()
    cursor = conn.cursor()
    if include_inactive:
        cursor.execute("SELECT * FROM medicines ORDER BY name ASC;")
    else:
        cursor.execute("SELECT * FROM medicines WHERE status='Active' ORDER BY name ASC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ------------------------------------------------------------------------------
# 4. Medicine Batches CRUD (Section 7 & 8)
# ------------------------------------------------------------------------------

def add_medicine_batch(batch_number, medicine_id, expiry_date, purchase_price, selling_price, mrp, 
                       tablets_per_strip, quantity, free_quantity=0, discount=0.0, gst=12.0, 
                       supplier_id=None, purchase_invoice=None, purchase_date=None, low_stock_threshold=20):
    clean_batch = batch_number.strip()
    clean_expiry = expiry_date.strip()
    if not clean_batch or not clean_expiry:
        raise ValueError("Batch number and Expiry date cannot be empty.")
    try:
        datetime.strptime(clean_expiry, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Expiry date must be in YYYY-MM-DD format.")
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO medicine_batches (
                batch_number, medicine_id, expiry_date, purchase_price, selling_price, mrp, 
                tablets_per_strip, quantity, free_quantity, discount, gst, supplier_id, 
                purchase_invoice, purchase_date, low_stock_threshold
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            clean_batch, medicine_id, clean_expiry, purchase_price, selling_price, mrp,
            max(1, int(tablets_per_strip)), max(0, int(quantity)), free_quantity, discount, gst, supplier_id,
            purchase_invoice, purchase_date, low_stock_threshold
        ))
        batch_id = cursor.lastrowid
        
        # Log stock movement
        total_in = max(0, int(quantity)) + max(0, int(free_quantity))
        log_stock_movement(cursor, medicine_id, clean_batch, 'PURCHASE', total_in, purchase_invoice or 'OP-STOCK', "Initial batch stock entry")
        
        conn.commit()
        return batch_id
    except sqlite3.IntegrityError:
        raise ValueError(f"Batch '{clean_batch}' already exists for this medicine.")
    finally:
        conn.close()


def update_medicine_batch(batch_id, batch_number, expiry_date, purchase_price, selling_price, mrp, 
                          tablets_per_strip, quantity, free_quantity=0, discount=0.0, gst=12.0, 
                          supplier_id=None, purchase_invoice=None, purchase_date=None, low_stock_threshold=20):
    clean_batch = batch_number.strip()
    clean_expiry = expiry_date.strip()
    if not clean_batch or not clean_expiry:
        raise ValueError("Batch number and Expiry date cannot be empty.")
    try:
        datetime.strptime(clean_expiry, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Expiry date must be in YYYY-MM-DD format.")
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Fetch current record to audit stock adjustments
        cursor.execute("SELECT medicine_id, quantity, batch_number FROM medicine_batches WHERE id=?;", (batch_id,))
        old_row = cursor.fetchone()
        
        cursor.execute("""
            UPDATE medicine_batches SET 
                batch_number=?, expiry_date=?, purchase_price=?, selling_price=?, mrp=?, 
                tablets_per_strip=?, quantity=?, free_quantity=?, discount=?, gst=?, 
                supplier_id=?, purchase_invoice=?, purchase_date=?, low_stock_threshold=?
            WHERE id=?;
        """, (
            clean_batch, clean_expiry, purchase_price, selling_price, mrp,
            max(1, int(tablets_per_strip)), max(0, int(quantity)), free_quantity, discount, gst, supplier_id,
            purchase_invoice, purchase_date, low_stock_threshold, batch_id
        ))
        
        if old_row:
            diff = max(0, int(quantity)) - old_row['quantity']
            if diff != 0:
                log_stock_movement(cursor, old_row['medicine_id'], clean_batch, 'ADJUSTMENT', diff, 'SYS-EDIT', "Batch details edit adjustment")
                
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"Batch '{clean_batch}' already exists for this medicine.")
    finally:
        conn.close()


def delete_medicine_batch(batch_id):
    """Deletes a batch if safe."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medicine_batches WHERE id=?;", (batch_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------------------
# 5. Formal Stock Adjustment System (Section 40)
# ------------------------------------------------------------------------------

def adjust_stock(batch_id: int, new_quantity: int, reason: str, notes: str = "", user: str = "Admin"):
    """
    Formally records an inventory adjustment with indelible audit trail.
    Supported reasons: 'damaged', 'expired', 'missing', 'count_correction', 'supplier_return', 'opening_balance', 'other'
    """
    valid_reasons = ('damaged', 'expired', 'missing', 'count_correction', 'supplier_return', 'opening_balance', 'other')
    if reason not in valid_reasons:
        raise ValueError(f"Invalid adjustment reason '{reason}'. Allowed: {valid_reasons}")
    if new_quantity < 0:
        raise ValueError("Stock quantity cannot be adjusted below zero.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, medicine_id, batch_number, quantity FROM medicine_batches WHERE id=?;", (batch_id,))
        batch = cursor.fetchone()
        if not batch:
            raise ValueError(f"Batch with ID {batch_id} not found.")

        old_quantity = batch["quantity"]
        change = new_quantity - old_quantity

        if change == 0:
            return

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Update batch quantity
        cursor.execute("UPDATE medicine_batches SET quantity=? WHERE id=?;", (new_quantity, batch_id))

        # 2. Insert into stock_adjustments table
        cursor.execute("""
            INSERT INTO stock_adjustments (
                medicine_id, batch_number, date, old_quantity, change_quantity, new_quantity, reason, notes, user
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (batch["medicine_id"], batch["batch_number"], date_str, old_quantity, change, new_quantity, reason, notes, user))

        # 3. Log movement
        move_type = "ADJUST_IN" if change > 0 else "ADJUST_OUT"
        log_stock_movement(cursor, batch["medicine_id"], batch["batch_number"], move_type, abs(change), f"ADJ-{batch_id}", f"Reason: {reason} | {notes}")

        # 4. Audit log entry
        cursor.execute("""
            INSERT INTO audit_logs (date, timestamp, user, action, table_name, record_id, details, previous_values, new_values)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (date_str, date_str, user, "STOCK_ADJUSTMENT", "medicine_batches", str(batch_id), f"Stock adjusted ({reason})", f"quantity={old_quantity}", f"quantity={new_quantity}"))

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_stock_adjustments(medicine_id: int = None, limit: int = 100):
    conn = get_connection()
    cursor = conn.cursor()
    if medicine_id:
        cursor.execute("""
            SELECT sa.*, m.name as medicine_name
            FROM stock_adjustments sa
            JOIN medicines m ON sa.medicine_id = m.id
            WHERE sa.medicine_id = ?
            ORDER BY sa.date DESC LIMIT ?;
        """, (medicine_id, limit))
    else:
        cursor.execute("""
            SELECT sa.*, m.name as medicine_name
            FROM stock_adjustments sa
            JOIN medicines m ON sa.medicine_id = m.id
            ORDER BY sa.date DESC LIMIT ?;
        """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ------------------------------------------------------------------------------
# 6. Expired Stock Authorization Override (Section 8)
# ------------------------------------------------------------------------------

def authorize_expired_sale_override(medicine_id: int, batch_number: str, user: str, reason: str, cursor: sqlite3.Cursor = None) -> bool:
    """
    Creates an official administrative override record permitting an expired medicine sale.
    Records timestamp, user, medicine, batch, and operational reason.
    Accepts an optional cursor for inclusion in an active atomic transaction.
    """
    if not reason.strip():
        raise ValueError("A formal operational reason must be supplied for an expired stock override.")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    should_close = False
    if cursor is None:
        conn = get_connection()
        cursor = conn.cursor()
        should_close = True

    try:
        cursor.execute("""
            INSERT INTO audit_logs (date, timestamp, user, action, table_name, record_id, details)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (now_str, now_str, user, "EXPIRED_SALE_OVERRIDE", "medicine_batches", f"{medicine_id}:{batch_number}", f"Reason: {reason.strip()}"))
        if should_close:
            conn.commit()
        return True
    except Exception:
        if should_close:
            conn.rollback()
        raise
    finally:
        if should_close:
            conn.close()


# ------------------------------------------------------------------------------
# 7. Stock Queries & Search (Section 42 & 44)
# ------------------------------------------------------------------------------

def get_all_medicines():
    """
    Returns all active stock batches joined with master medicine details.
    Directly supplies UI components with formatted stock metrics.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mb.id, mb.batch_number, mb.expiry_date, mb.purchase_price, mb.selling_price, mb.mrp, 
               mb.quantity, mb.free_quantity, mb.discount, mb.gst, mb.purchase_invoice, mb.purchase_date,
               mb.tablets_per_strip, mb.low_stock_threshold,
               m.id as medicine_id, m.name, m.manufacturer, m.generic_name, m.brand, m.category, 
               m.dosage_form, m.strength, m.pack_size, m.unit, m.hsn_code, m.gst_rate, 
               m.prescription_required, m.reorder_level, m.minimum_stock, m.maximum_stock, 
               m.rack_shelf, m.status,
               s.name as supplier_name
        FROM medicine_batches mb
        JOIN medicines m ON mb.medicine_id = m.id
        LEFT JOIN suppliers s ON mb.supplier_id = s.id
        WHERE m.status = 'Active'
        ORDER BY m.name ASC, mb.expiry_date ASC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return [_format_batch_row(row) for row in rows]


def get_medicine_by_id(batch_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mb.id, mb.batch_number, mb.expiry_date, mb.purchase_price, mb.selling_price, mb.mrp, 
               mb.quantity, mb.free_quantity, mb.discount, mb.gst, mb.purchase_invoice, mb.purchase_date,
               mb.tablets_per_strip, mb.low_stock_threshold,
               m.id as medicine_id, m.name, m.manufacturer, m.generic_name, m.brand, m.category, 
               m.dosage_form, m.strength, m.pack_size, m.unit, m.hsn_code, m.gst_rate, 
               m.prescription_required, m.reorder_level, m.minimum_stock, m.maximum_stock, 
               m.rack_shelf, m.status,
               s.name as supplier_name
        FROM medicine_batches mb
        JOIN medicines m ON mb.medicine_id = m.id
        LEFT JOIN suppliers s ON mb.supplier_id = s.id
        WHERE mb.id = ?;
    """, (batch_id,))
    row = cursor.fetchone()
    conn.close()
    return _format_batch_row(row) if row else None


def search_medicines(query: str):
    """
    Search medicines and batches.
    Matches across medicine name, generic name, batch number, manufacturer, and brand.
    Prioritizes exact and prefix name matches.
    """
    clean_query = query.strip() if query else ""
    if not clean_query:
        return get_all_medicines()

    conn = get_connection()
    cursor = conn.cursor()
    pattern = f"%{clean_query}%"
    prefix = f"{clean_query}%"

    cursor.execute("""
        SELECT mb.id, mb.batch_number, mb.expiry_date, mb.purchase_price, mb.selling_price, mb.mrp, 
               mb.quantity, mb.free_quantity, mb.discount, mb.gst, mb.purchase_invoice, mb.purchase_date,
               mb.tablets_per_strip, mb.low_stock_threshold,
               m.id as medicine_id, m.name, m.manufacturer, m.generic_name, m.brand, m.category, 
               m.dosage_form, m.strength, m.pack_size, m.unit, m.hsn_code, m.gst_rate, 
               m.prescription_required, m.reorder_level, m.minimum_stock, m.maximum_stock, 
               m.rack_shelf, m.status,
               s.name as supplier_name
        FROM medicine_batches mb
        JOIN medicines m ON mb.medicine_id = m.id
        LEFT JOIN suppliers s ON mb.supplier_id = s.id
        WHERE m.status = 'Active' AND (
            m.name LIKE ? OR 
            m.generic_name LIKE ? OR 
            mb.batch_number LIKE ? OR 
            m.brand LIKE ? OR 
            m.manufacturer LIKE ?
        )
        ORDER BY 
            CASE WHEN m.name LIKE ? THEN 1
                 WHEN mb.batch_number LIKE ? THEN 2
                 ELSE 3 END,
            m.name ASC, mb.expiry_date ASC;
    """, (pattern, pattern, pattern, pattern, pattern, prefix, prefix))
    rows = cursor.fetchall()
    conn.close()
    return [_format_batch_row(row) for row in rows]


# ------------------------------------------------------------------------------
# 8. FEFO Batch Engine (Section 15)
# ------------------------------------------------------------------------------

def get_fefo_batches_for_medicine(medicine_id: int, today_str: str = None, include_expired: bool = False):
    """
    Retrieves available inventory batches sorted by FEFO (First Expiry, First Out).
    By default excludes expired stock.
    Returns fully populated, UI-ready dictionaries with unit tablet prices.
    """
    if today_str is None:
        today_str = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()

    if include_expired:
        query = """
            SELECT mb.id, mb.batch_number, mb.expiry_date, mb.purchase_price, mb.selling_price, mb.mrp, 
                   mb.quantity, mb.free_quantity, mb.discount, mb.gst, mb.purchase_invoice, mb.purchase_date,
                   mb.tablets_per_strip, mb.low_stock_threshold,
                   m.id as medicine_id, m.name, m.manufacturer, m.generic_name, m.brand, m.category, 
                   m.dosage_form, m.strength, m.pack_size, m.unit, m.hsn_code, m.gst_rate, 
                   m.prescription_required, m.reorder_level, m.minimum_stock, m.maximum_stock, 
                   m.rack_shelf, m.status,
                   s.name as supplier_name
            FROM medicine_batches mb
            JOIN medicines m ON mb.medicine_id = m.id
            LEFT JOIN suppliers s ON mb.supplier_id = s.id
            WHERE mb.medicine_id = ? AND mb.quantity > 0
            ORDER BY mb.expiry_date ASC, mb.id ASC;
        """
        params = (medicine_id,)
    else:
        query = """
            SELECT mb.id, mb.batch_number, mb.expiry_date, mb.purchase_price, mb.selling_price, mb.mrp, 
                   mb.quantity, mb.free_quantity, mb.discount, mb.gst, mb.purchase_invoice, mb.purchase_date,
                   mb.tablets_per_strip, mb.low_stock_threshold,
                   m.id as medicine_id, m.name, m.manufacturer, m.generic_name, m.brand, m.category, 
                   m.dosage_form, m.strength, m.pack_size, m.unit, m.hsn_code, m.gst_rate, 
                   m.prescription_required, m.reorder_level, m.minimum_stock, m.maximum_stock, 
                   m.rack_shelf, m.status,
                   s.name as supplier_name
            FROM medicine_batches mb
            JOIN medicines m ON mb.medicine_id = m.id
            LEFT JOIN suppliers s ON mb.supplier_id = s.id
            WHERE mb.medicine_id = ? AND mb.quantity > 0 AND mb.expiry_date >= ?
            ORDER BY mb.expiry_date ASC, mb.id ASC;
        """
        params = (medicine_id, today_str)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [_format_batch_row(row) for row in rows]


# ------------------------------------------------------------------------------
# 9. Expiry & Low Stock Alerts (Section 8 & 9)
# ------------------------------------------------------------------------------

def get_expired_medicines(today_str: str = None):
    if today_str is None:
        today_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mb.id, mb.batch_number, mb.expiry_date, mb.purchase_price, mb.selling_price, mb.mrp, 
               mb.quantity, mb.free_quantity, mb.discount, mb.gst, mb.purchase_invoice, mb.purchase_date,
               mb.tablets_per_strip, mb.low_stock_threshold,
               m.id as medicine_id, m.name, m.manufacturer, m.generic_name, m.brand, m.category, 
               m.dosage_form, m.strength, m.pack_size, m.unit, m.hsn_code, m.gst_rate, 
               m.prescription_required, m.reorder_level, m.minimum_stock, m.maximum_stock, 
               m.rack_shelf, m.status,
               s.name as supplier_name
        FROM medicine_batches mb
        JOIN medicines m ON mb.medicine_id = m.id
        LEFT JOIN suppliers s ON mb.supplier_id = s.id
        WHERE mb.expiry_date < ?
        ORDER BY mb.expiry_date ASC;
    """, (today_str,))
    rows = cursor.fetchall()
    conn.close()
    return [_format_batch_row(row) for row in rows]


def get_expiring_soon_medicines(today_str: str = None, days_threshold: int = 90):
    if today_str is None:
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
    else:
        today = datetime.strptime(today_str, "%Y-%m-%d")
        
    limit_date_str = (today + timedelta(days=days_threshold)).strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mb.id, mb.batch_number, mb.expiry_date, mb.purchase_price, mb.selling_price, mb.mrp, 
               mb.quantity, mb.free_quantity, mb.discount, mb.gst, mb.purchase_invoice, mb.purchase_date,
               mb.tablets_per_strip, mb.low_stock_threshold,
               m.id as medicine_id, m.name, m.manufacturer, m.generic_name, m.brand, m.category, 
               m.dosage_form, m.strength, m.pack_size, m.unit, m.hsn_code, m.gst_rate, 
               m.prescription_required, m.reorder_level, m.minimum_stock, m.maximum_stock, 
               m.rack_shelf, m.status,
               s.name as supplier_name
        FROM medicine_batches mb
        JOIN medicines m ON mb.medicine_id = m.id
        LEFT JOIN suppliers s ON mb.supplier_id = s.id
        WHERE mb.expiry_date >= ? AND mb.expiry_date <= ?
        ORDER BY mb.expiry_date ASC;
    """, (today_str, limit_date_str))
    rows = cursor.fetchall()
    conn.close()
    return [_format_batch_row(row) for row in rows]


def get_low_stock_medicines():
    """
    Identifies medicines whose aggregated active stock is <= threshold.
    Correctly aggregates tablets across batches and handles medicines with zero stock.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id as medicine_id, m.name, m.manufacturer, m.generic_name, m.brand, m.category,
               m.dosage_form, m.strength, m.pack_size, m.unit, m.hsn_code, m.gst_rate,
               m.prescription_required, m.reorder_level, m.minimum_stock, m.maximum_stock,
               m.rack_shelf, m.status,
               COALESCE(SUM(mb.quantity), 0) as total_tablets,
               MIN(mb.expiry_date) as nearest_expiry,
               COALESCE(MAX(mb.tablets_per_strip), 10) as tablets_per_strip
        FROM medicines m
        LEFT JOIN medicine_batches mb ON m.id = mb.medicine_id
        WHERE m.status = 'Active'
        GROUP BY m.id
        HAVING total_tablets <= m.reorder_level
        ORDER BY total_tablets ASC;
    """)
    rows = cursor.fetchall()
    conn.close()

    formatted = []
    for r in rows:
        med = dict(r)
        med["batch_number"] = "ALL BATCHES"
        med["batch"] = "ALL BATCHES"
        med["expiry_date"] = med["nearest_expiry"] or "N/A"
        med["purchase_price"] = 0.0
        med["selling_price"] = 0.0
        med["mrp"] = 0.0
        med["quantity"] = med["total_tablets"]
        med["threshold"] = med["reorder_level"]
        
        t_strip = med["tablets_per_strip"] or 10
        strips, loose = calculate_strips_details(med["quantity"], t_strip)
        med["strips"] = strips
        med["loose_tablets"] = loose
        med["stock_string"] = get_formatted_stock_string(med["quantity"], t_strip)
        
        status_code, status_label = get_batch_status(med["expiry_date"], med["quantity"], med["threshold"])
        med["stock_status"] = status_code
        med["status_label"] = status_label
        med["is_low_stock"] = True
        med["is_out_of_stock"] = (med["quantity"] <= 0)
        formatted.append(med)

    return formatted


# ------------------------------------------------------------------------------
# 10. Stock Movement Logging Helper (Section 40)
# ------------------------------------------------------------------------------

def log_stock_movement(cursor, medicine_id: int, batch_number: str, type_name: str, quantity: int, reference_id: str = None, description: str = ""):
    """Records an immutable stock movement entry."""
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO stock_movements (medicine_id, batch_number, date, type, quantity, reference_id, description)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (medicine_id, batch_number.strip(), date_str, type_name, quantity, reference_id, description))
