import sqlite3
from database.db import get_connection

def get_all_customers(include_inactive=False):
    conn = get_connection()
    cursor = conn.cursor()
    if include_inactive:
        cursor.execute("SELECT * FROM customers ORDER BY name ASC;")
    else:
        cursor.execute("SELECT * FROM customers WHERE status = 'Active' ORDER BY name ASC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_customer_by_id(customer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = ?;", (customer_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_customer(name, phone="", email="", address="", gst_number="", credit_limit=5000.0):
    if not name.strip():
        raise ValueError("Customer name cannot be empty.")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO customers (name, phone, email, address, gst_number, credit_limit, outstanding_balance, status)
            VALUES (?, ?, ?, ?, ?, ?, 0.0, 'Active');
        """, (name.strip(), phone.strip(), email.strip(), address.strip(), gst_number.strip(), credit_limit))
        conn.commit()
        customer_id = cursor.lastrowid
        
        # Log opening balance in ledger
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO customer_ledger (customer_id, date, type, reference_id, debit, credit, balance, description)
            VALUES (?, ?, 'OPENING_BAL', 'OP-BAL', 0.0, 0.0, 0.0, 'Customer profile initialized');
        """, (customer_id, date_str))
        conn.commit()
        
        return customer_id
    except sqlite3.IntegrityError:
        raise ValueError(f"Customer with name '{name}' already exists.")
    finally:
        conn.close()

def update_customer(customer_id, name, phone="", email="", address="", gst_number="", credit_limit=5000.0, status="Active"):
    if not name.strip():
        raise ValueError("Customer name cannot be empty.")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE customers SET 
                name = ?, phone = ?, email = ?, address = ?, gst_number = ?, 
                credit_limit = ?, status = ?
            WHERE id = ?;
        """, (name.strip(), phone.strip(), email.strip(), address.strip(), gst_number.strip(), credit_limit, status, customer_id))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"Customer with name '{name}' already exists.")
    finally:
        conn.close()

def delete_customer(customer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE customers SET status = 'Inactive' WHERE id = ?;", (customer_id,))
    conn.commit()
    conn.close()

def record_customer_payment(customer_id, date_str, amount, payment_mode="Cash", reference_no="", description=""):
    if amount <= 0:
        raise ValueError("Payment amount must be greater than 0.")
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        cursor.execute("SELECT outstanding_balance FROM customers WHERE id = ?;", (customer_id,))
        cust = cursor.fetchone()
        if not cust:
            raise ValueError("Customer not found.")
            
        new_balance = cust['outstanding_balance'] - amount
        
        cursor.execute("UPDATE customers SET outstanding_balance = ? WHERE id = ?;", (new_balance, customer_id))
        
        cursor.execute("""
            INSERT INTO customer_ledger (customer_id, date, type, reference_id, debit, credit, balance, description)
            VALUES (?, ?, 'PAYMENT', ?, 0.0, ?, ?, ?);
        """, (customer_id, date_str, reference_no, amount, new_balance, f"Payment received via {payment_mode}. {description}"))
        
        cursor.execute("COMMIT;")
    except Exception as e:
        cursor.execute("ROLLBACK;")
        raise e
    finally:
        conn.close()

def get_customer_ledger(customer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM customer_ledger 
        WHERE customer_id = ? 
        ORDER BY date ASC, id ASC;
    """, (customer_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
