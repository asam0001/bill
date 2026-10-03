import sqlite3
import os
import sys
from datetime import datetime

# Ensure project root is accessible for absolute imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import get_connection, DATABASE_VERSION

# ==============================================================================
# MediTrack Safe Database Migration Engine (Idempotent & Version-Tracked)
# ==============================================================================

def get_table_columns(cursor: sqlite3.Cursor, table_name: str) -> set:
    """Helper to retrieve existing column names for a table."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name});")
        return {row["name"] for row in cursor.fetchall()}
    except Exception:
        return set()

def table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """Checks whether a table exists in the database."""
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
    return cursor.fetchone() is not None

def run_migrations(db_path: str = None) -> None:
    """
    Executes incremental, idempotent database migrations.
    Safely evolves existing databases while preserving all past transactions,
    billing history, and supplier records.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = OFF;")

    try:
        # ----------------------------------------------------------------------
        # Step 0: Ensure schema_version table exists
        # ----------------------------------------------------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT
        );
        """)

        # ----------------------------------------------------------------------
        # Step 1: Migrate legacy v1 single-table medicines if still present
        # ----------------------------------------------------------------------
        if table_exists(cursor, "medicines"):
            med_cols = get_table_columns(cursor, "medicines")
            if "batch" in med_cols:
                print("[MIGRATION] Legacy v1 coupled schema detected. Converting to normalized Master/Batch schema...")
                cursor.execute("DROP TABLE IF EXISTS old_medicines;")
                cursor.execute("ALTER TABLE medicines RENAME TO old_medicines;")

                cursor.execute("""
                CREATE TABLE medicines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    manufacturer TEXT,
                    generic_name TEXT,
                    brand TEXT,
                    category TEXT,
                    dosage_form TEXT DEFAULT 'Tablet',
                    strength TEXT,
                    pack_size TEXT DEFAULT '10',
                    unit TEXT DEFAULT 'Strip',
                    hsn_code TEXT,
                    gst_rate REAL DEFAULT 12.0,
                    prescription_required INTEGER DEFAULT 0,
                    reorder_level INTEGER DEFAULT 20,
                    minimum_stock INTEGER DEFAULT 10,
                    maximum_stock INTEGER DEFAULT 500,
                    rack_shelf TEXT,
                    status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive'))
                );
                """)

                cursor.execute("""
                CREATE TABLE medicine_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_number TEXT NOT NULL,
                    medicine_id INTEGER NOT NULL,
                    expiry_date TEXT NOT NULL,
                    purchase_price REAL NOT NULL,
                    selling_price REAL NOT NULL,
                    mrp REAL NOT NULL,
                    tablets_per_strip INTEGER NOT NULL CHECK(tablets_per_strip > 0),
                    quantity INTEGER NOT NULL DEFAULT 0,
                    free_quantity INTEGER DEFAULT 0,
                    discount REAL DEFAULT 0.0,
                    gst REAL DEFAULT 12.0,
                    supplier_id INTEGER,
                    purchase_invoice TEXT,
                    purchase_date TEXT,
                    low_stock_threshold INTEGER DEFAULT 20,
                    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
                    UNIQUE(medicine_id, batch_number)
                );
                """)

                # Populate medicines master
                cursor.execute("""
                INSERT INTO medicines (name, manufacturer, reorder_level, status)
                SELECT DISTINCT name, manufacturer, COALESCE(threshold, 20), 'Active'
                FROM old_medicines;
                """)

                # Populate batches
                cursor.execute("""
                INSERT INTO medicine_batches (batch_number, medicine_id, expiry_date, purchase_price, selling_price, mrp, tablets_per_strip, quantity, supplier_id)
                SELECT om.batch, m.id, om.expiry_date, om.purchase_price, om.selling_price, om.mrp, om.tablets_per_strip, om.total_tablets, om.supplier_id
                FROM old_medicines om
                JOIN medicines m ON om.name = m.name;
                """)

                # Re-link bill items
                if table_exists(cursor, "bill_items"):
                    cursor.execute("""
                    UPDATE bill_items
                    SET medicine_id = (
                        SELECT id FROM medicines WHERE medicines.name = bill_items.medicine_name
                    )
                    WHERE EXISTS (
                        SELECT 1 FROM medicines WHERE medicines.name = bill_items.medicine_name
                    );
                    """)

                cursor.execute("DROP TABLE IF EXISTS old_medicines;")
                print("[MIGRATION] Legacy v1 medicines successfully decoupled into master and batches!")

        # Clean up old_medicines if still present as an artifact
        if table_exists(cursor, "old_medicines"):
            cursor.execute("DROP TABLE old_medicines;")

        # Self-heal foreign key in medicine_batches if legacy migration left it referencing old_medicines
        if table_exists(cursor, "medicine_batches"):
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='medicine_batches';")
            mb_sql_row = cursor.fetchone()
            if mb_sql_row and mb_sql_row[0] and "old_medicines" in mb_sql_row[0]:
                print("[MIGRATION] Repairing medicine_batches schema to decouple old_medicines foreign key...")
                cursor.execute("""
                CREATE TABLE medicine_batches_healed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_number TEXT NOT NULL,
                    medicine_id INTEGER NOT NULL,
                    expiry_date TEXT NOT NULL,
                    purchase_price REAL NOT NULL,
                    selling_price REAL NOT NULL,
                    mrp REAL NOT NULL,
                    tablets_per_strip INTEGER NOT NULL CHECK(tablets_per_strip > 0),
                    quantity INTEGER NOT NULL DEFAULT 0,
                    free_quantity INTEGER DEFAULT 0,
                    discount REAL DEFAULT 0.0,
                    gst REAL DEFAULT 12.0,
                    supplier_id INTEGER,
                    purchase_invoice TEXT,
                    purchase_date TEXT,
                    low_stock_threshold INTEGER DEFAULT 20,
                    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
                    UNIQUE(medicine_id, batch_number)
                );
                """)
                cursor.execute("""
                INSERT INTO medicine_batches_healed (
                    id, batch_number, medicine_id, expiry_date, purchase_price, selling_price,
                    mrp, tablets_per_strip, quantity, free_quantity, discount, gst,
                    supplier_id, purchase_invoice, purchase_date, low_stock_threshold
                )
                SELECT 
                    id, batch_number, medicine_id, expiry_date, purchase_price, selling_price,
                    mrp, tablets_per_strip, quantity, free_quantity, discount, gst,
                    supplier_id, purchase_invoice, purchase_date, COALESCE(low_stock_threshold, 20)
                FROM medicine_batches;
                """)
                cursor.execute("DROP TABLE medicine_batches;")
                cursor.execute("ALTER TABLE medicine_batches_healed RENAME TO medicine_batches;")
                print("[MIGRATION] medicine_batches schema healed successfully.")

        # ----------------------------------------------------------------------
        # Step 2: Ensure all tables have required columns
        # ----------------------------------------------------------------------
        # Medicine Batches
        if table_exists(cursor, "medicine_batches"):
            mb_cols = get_table_columns(cursor, "medicine_batches")
            if "low_stock_threshold" not in mb_cols:
                cursor.execute("ALTER TABLE medicine_batches ADD COLUMN low_stock_threshold INTEGER DEFAULT 20;")

        # Suppliers
        if table_exists(cursor, "suppliers"):
            supp_cols = get_table_columns(cursor, "suppliers")
            if "contact_person" not in supp_cols:
                cursor.execute("ALTER TABLE suppliers ADD COLUMN contact_person TEXT;")
            if "gst_number" not in supp_cols:
                cursor.execute("ALTER TABLE suppliers ADD COLUMN gst_number TEXT;")
            if "payment_terms" not in supp_cols:
                cursor.execute("ALTER TABLE suppliers ADD COLUMN payment_terms TEXT DEFAULT 'Net 30';")
            if "opening_balance" not in supp_cols:
                cursor.execute("ALTER TABLE suppliers ADD COLUMN opening_balance REAL DEFAULT 0.0;")
            if "current_balance" not in supp_cols:
                cursor.execute("ALTER TABLE suppliers ADD COLUMN current_balance REAL DEFAULT 0.0;")
            if "notes" not in supp_cols:
                cursor.execute("ALTER TABLE suppliers ADD COLUMN notes TEXT;")
            if "status" not in supp_cols:
                cursor.execute("ALTER TABLE suppliers ADD COLUMN status TEXT DEFAULT 'Active';")

        # Bills
        if table_exists(cursor, "bills"):
            cursor.execute("PRAGMA table_info(bills);")
            cols_info = cursor.fetchall()
            bill_num_col = next((c for c in cols_info if c[1] == "bill_number"), None)
            if bill_num_col and str(bill_num_col[2]).upper() == "INTEGER":
                print("[MIGRATION] Upgrading bills table to support string invoice numbers (TEXT PRIMARY KEY)...")
                cursor.execute("""
                CREATE TABLE bills_v2 (
                    bill_number TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    customer_id INTEGER,
                    customer_name TEXT,
                    customer_phone TEXT,
                    payment_mode TEXT DEFAULT 'Cash',
                    total_amount REAL NOT NULL,
                    discount REAL NOT NULL,
                    discount_amount REAL NOT NULL,
                    grand_total REAL NOT NULL,
                    total_profit REAL NOT NULL,
                    sgst REAL DEFAULT 0.0,
                    cgst REAL DEFAULT 0.0,
                    igst REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Cancelled', 'Returned')),
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
                );
                """)
                cursor.execute("""
                INSERT INTO bills_v2 (
                    bill_number, date, customer_id, customer_name, customer_phone,
                    payment_mode, total_amount, discount, discount_amount,
                    grand_total, total_profit, sgst, cgst, igst, status
                )
                SELECT 
                    CAST(bill_number AS TEXT), date, 
                    CASE WHEN 'customer_id' IN (SELECT name FROM pragma_table_info('bills')) THEN customer_id ELSE NULL END,
                    customer_name, customer_phone,
                    COALESCE(payment_mode, 'Cash'), total_amount, discount, discount_amount,
                    grand_total, total_profit, 
                    CASE WHEN 'sgst' IN (SELECT name FROM pragma_table_info('bills')) THEN COALESCE(sgst, 0.0) ELSE 0.0 END,
                    CASE WHEN 'cgst' IN (SELECT name FROM pragma_table_info('bills')) THEN COALESCE(cgst, 0.0) ELSE 0.0 END,
                    CASE WHEN 'igst' IN (SELECT name FROM pragma_table_info('bills')) THEN COALESCE(igst, 0.0) ELSE 0.0 END,
                    CASE WHEN 'status' IN (SELECT name FROM pragma_table_info('bills')) THEN COALESCE(status, 'Active') ELSE 'Active' END
                FROM bills;
                """)
                cursor.execute("DROP TABLE bills;")
                cursor.execute("ALTER TABLE bills_v2 RENAME TO bills;")
                print("[MIGRATION] bills table upgraded to TEXT PRIMARY KEY successfully.")
            else:
                bills_cols = get_table_columns(cursor, "bills")
                if "customer_id" not in bills_cols:
                    cursor.execute("ALTER TABLE bills ADD COLUMN customer_id INTEGER;")
                if "sgst" not in bills_cols:
                    cursor.execute("ALTER TABLE bills ADD COLUMN sgst REAL DEFAULT 0.0;")
                if "cgst" not in bills_cols:
                    cursor.execute("ALTER TABLE bills ADD COLUMN cgst REAL DEFAULT 0.0;")
                if "igst" not in bills_cols:
                    cursor.execute("ALTER TABLE bills ADD COLUMN igst REAL DEFAULT 0.0;")
                if "status" not in bills_cols:
                    cursor.execute("ALTER TABLE bills ADD COLUMN status TEXT DEFAULT 'Active';")

        # Bill Items
        if table_exists(cursor, "bill_items"):
            bi_cols = get_table_columns(cursor, "bill_items")
            if "gst_percent" not in bi_cols:
                cursor.execute("ALTER TABLE bill_items ADD COLUMN gst_percent REAL DEFAULT 12.0;")

        # Purchases
        if table_exists(cursor, "purchases"):
            p_cols = get_table_columns(cursor, "purchases")
            if "discount_percent" not in p_cols:
                cursor.execute("ALTER TABLE purchases ADD COLUMN discount_percent REAL DEFAULT 0.0;")
            if "gst_amount" not in p_cols:
                cursor.execute("ALTER TABLE purchases ADD COLUMN gst_amount REAL DEFAULT 0.0;")

        # Purchase Returns
        if table_exists(cursor, "purchase_returns"):
            pr_cols = get_table_columns(cursor, "purchase_returns")
            if "reason" not in pr_cols:
                cursor.execute("ALTER TABLE purchase_returns ADD COLUMN reason TEXT;")

        # Sales Returns
        if table_exists(cursor, "sales_returns"):
            sr_cols = get_table_columns(cursor, "sales_returns")
            if "reason" not in sr_cols:
                cursor.execute("ALTER TABLE sales_returns ADD COLUMN reason TEXT;")

        # Audit Logs
        if table_exists(cursor, "audit_logs"):
            al_cols = get_table_columns(cursor, "audit_logs")
            if "date" not in al_cols:
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN date TEXT;")
                if "timestamp" in al_cols:
                    cursor.execute("UPDATE audit_logs SET date = timestamp WHERE date IS NULL;")
                else:
                    cursor.execute("UPDATE audit_logs SET date = datetime('now') WHERE date IS NULL;")
            if "timestamp" not in al_cols:
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN timestamp TEXT;")
                if "date" in al_cols:
                    cursor.execute("UPDATE audit_logs SET timestamp = date WHERE timestamp IS NULL;")
                else:
                    cursor.execute("UPDATE audit_logs SET timestamp = datetime('now') WHERE timestamp IS NULL;")
            if "user" not in al_cols:
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN user TEXT DEFAULT 'system';")
                if "user_id" in al_cols:
                    cursor.execute("UPDATE audit_logs SET user = user_id WHERE user IS NULL;")
            if "details" not in al_cols:
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN details TEXT;")

        # ----------------------------------------------------------------------
        # Step 3: Ensure newly specified tables exist
        # ----------------------------------------------------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER NOT NULL,
            batch_number TEXT NOT NULL,
            date TEXT NOT NULL,
            old_quantity INTEGER NOT NULL,
            change_quantity INTEGER NOT NULL,
            new_quantity INTEGER NOT NULL,
            reason TEXT NOT NULL CHECK(reason IN ('damaged', 'expired', 'missing', 'count_correction', 'supplier_return', 'opening_balance', 'other')),
            notes TEXT,
            user TEXT,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS imported_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            source TEXT DEFAULT 'Manual Upload',
            supplier_id INTEGER,
            invoice_number TEXT,
            invoice_date TEXT,
            total_amount REAL,
            status TEXT DEFAULT 'RECEIVED' CHECK(status IN ('RECEIVED', 'PROCESSING', 'EXTRACTED', 'REVIEW_REQUIRED', 'READY', 'IMPORTED', 'FAILED', 'DUPLICATE', 'CANCELLED')),
            extraction_notes TEXT,
            created_at TEXT NOT NULL,
            processed_at TEXT,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS imported_invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imported_invoice_id INTEGER NOT NULL,
            raw_medicine_name TEXT NOT NULL,
            matched_medicine_id INTEGER,
            matched_batch TEXT,
            matched_status TEXT DEFAULT 'REVIEW_REQUIRED' CHECK(matched_status IN ('EXACT_MATCH', 'POSSIBLE_MATCH', 'NEW_MEDICINE', 'REVIEW_REQUIRED')),
            quantity INTEGER DEFAULT 0,
            unit TEXT DEFAULT 'Strip',
            tablets_per_strip INTEGER DEFAULT 10,
            purchase_price REAL DEFAULT 0.0,
            selling_price REAL DEFAULT 0.0,
            mrp REAL DEFAULT 0.0,
            expiry_date TEXT,
            gst_percent REAL DEFAULT 12.0,
            discount_percent REAL DEFAULT 0.0,
            total_amount REAL DEFAULT 0.0,
            is_accepted INTEGER DEFAULT 1,
            FOREIGN KEY (imported_invoice_id) REFERENCES imported_invoices(id) ON DELETE CASCADE,
            FOREIGN KEY (matched_medicine_id) REFERENCES medicines(id)
        );
        """)

        # ----------------------------------------------------------------------
        # Step 4: Ensure all performance indexes are active
        # ----------------------------------------------------------------------
        indexes = [
            ("idx_med_batches_med_id", "medicine_batches(medicine_id)"),
            ("idx_med_batches_expiry", "medicine_batches(expiry_date)"),
            ("idx_med_batches_batch", "medicine_batches(batch_number)"),
            ("idx_bill_items_bill_num", "bill_items(bill_number)"),
            ("idx_bills_date", "bills(date)"),
            ("idx_bills_customer", "bills(customer_id)"),
            ("idx_purchases_supplier", "purchases(supplier_id)"),
            ("idx_purchases_date", "purchases(purchase_date)"),
            ("idx_purchase_items_purch_id", "purchase_items(purchase_id)"),
            ("idx_stock_mov_med_batch", "stock_movements(medicine_id, batch_number)"),
            ("idx_stock_adj_med_batch", "stock_adjustments(medicine_id, batch_number)"),
            ("idx_audit_logs_timestamp", "audit_logs(timestamp)"),
            ("idx_supp_ledger_supp", "supplier_ledger(supplier_id)"),
            ("idx_cust_ledger_cust", "customer_ledger(customer_id)"),
            ("idx_imported_inv_status", "imported_invoices(status)")
        ]
        for idx_name, idx_target in indexes:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_target};")

        # ----------------------------------------------------------------------
        # Step 5: Record Schema Version 2
        # ----------------------------------------------------------------------
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT OR REPLACE INTO schema_version (version, applied_at, description)
        VALUES (?, ?, ?);
        """, (DATABASE_VERSION, now_str, f"MediTrack ERP v{DATABASE_VERSION} - Full normalized schema, indexes, and import pipelines."))

        conn.commit()
        print(f"[MIGRATION] Migration to Database Version {DATABASE_VERSION} completed successfully.")

    except Exception as ex:
        conn.rollback()
        print(f"[MIGRATION ERROR] Migration failed: {ex}")
        raise ex
    finally:
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.close()

if __name__ == "__main__":
    run_migrations()
