import sqlite3
from database.db import get_connection

def get_all_suppliers(include_inactive=False):
    conn = get_connection()
    cursor = conn.cursor()
    if include_inactive:
        cursor.execute("SELECT * FROM suppliers ORDER BY name ASC;")
    else:
        cursor.execute("SELECT * FROM suppliers WHERE status = 'Active' ORDER BY name ASC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_supplier_by_id(supplier_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers WHERE id = ?;", (supplier_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_supplier(name, phone="", email="", address="", contact_person="", gst_number="", 
                 payment_terms="Net 30", opening_balance=0.0):
    if not name.strip():
        raise ValueError("Supplier name cannot be empty.")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO suppliers (name, phone, email, address, contact_person, gst_number, payment_terms, opening_balance, current_balance, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active');
        """, (name.strip(), phone.strip(), email.strip(), address.strip(), contact_person.strip(), gst_number.strip(), payment_terms.strip(), opening_balance, opening_balance))
        conn.commit()
        supplier_id = cursor.lastrowid
        
        # Log opening balance in ledger
        if opening_balance != 0:
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO supplier_ledger (supplier_id, date, type, reference_id, debit, credit, balance, description)
                VALUES (?, ?, 'OPENING_BAL', 'OP-BAL', 0.0, ?, ?, 'Opening credit balance');
            """, (supplier_id, date_str, opening_balance, opening_balance))
            conn.commit()
            
        return supplier_id
    except sqlite3.IntegrityError:
        raise ValueError(f"Supplier with name '{name}' already exists.")
    finally:
        conn.close()

def update_supplier(supplier_id, name, phone="", email="", address="", contact_person="", gst_number="", 
                    payment_terms="Net 30", status="Active"):
    if not name.strip():
        raise ValueError("Supplier name cannot be empty.")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get old balance
        cursor.execute("SELECT opening_balance, current_balance FROM suppliers WHERE id=?;", (supplier_id,))
        old_data = cursor.fetchone()
        
        cursor.execute("""
            UPDATE suppliers SET 
                name = ?, phone = ?, email = ?, address = ?, contact_person = ?, 
                gst_number = ?, payment_terms = ?, status = ?
            WHERE id = ?;
        """, (name.strip(), phone.strip(), email.strip(), address.strip(), contact_person.strip(), gst_number.strip(), payment_terms.strip(), status, supplier_id))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"Supplier with name '{name}' already exists.")
    finally:
        conn.close()

def delete_supplier(supplier_id):
    """
    Soft delete a supplier by marking them Inactive.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE suppliers SET status = 'Inactive' WHERE id = ?;", (supplier_id,))
    conn.commit()
    conn.close()

# Supplier Ledger & Payments
def get_supplier_ledger(supplier_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM supplier_ledger 
        WHERE supplier_id = ? 
        ORDER BY date ASC, id ASC;
    """, (supplier_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def record_supplier_payment(supplier_id, date_str, amount, payment_mode="Cash", reference_no="", description=""):
    if amount <= 0:
        raise ValueError("Payment amount must be greater than 0.")
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Fetch current balance
        cursor.execute("SELECT current_balance FROM suppliers WHERE id = ?;", (supplier_id,))
        supp = cursor.fetchone()
        if not supp:
            raise ValueError("Supplier not found.")
            
        new_balance = supp['current_balance'] - amount
        
        # 2. Update supplier balance
        cursor.execute("UPDATE suppliers SET current_balance = ? WHERE id = ?;", (new_balance, supplier_id))
        
        # 3. Log to ledger (debit reduces our outstanding credit to them)
        cursor.execute("""
            INSERT INTO supplier_ledger (supplier_id, date, type, reference_id, debit, credit, balance, description)
            VALUES (?, ?, 'PAYMENT', ?, ?, 0.0, ?, ?);
        """, (supplier_id, date_str, reference_no, amount, new_balance, f"Payment via {payment_mode}. {description}"))
        
        cursor.execute("COMMIT;")
    except Exception as e:
        cursor.execute("ROLLBACK;")
        raise e
    finally:
        conn.close()
