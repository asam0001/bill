import os
import sys
import sqlite3
from contextlib import contextmanager

# Ensure project root is accessible for absolute imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ==============================================================================
# MediTrack Core Database Module
# Production-Quality, Offline-First SQLite Engine
# ==============================================================================

APP_VERSION = "2.0.0"
DATABASE_VERSION = 2
DB_NAME = "medical_shop.db"


def get_db_path() -> str:
    """
    Resolves the SQLite database file path.
    Prioritizes:
      1. Environment variable 'MEDITRACK_DB_PATH' if set.
      2. Local workspace directory alongside application code (portable/dev mode).
      3. User AppData directory if running in packaged/frozen executable mode.
    """
    env_path = os.environ.get("MEDITRACK_DB_PATH")
    if env_path and os.path.exists(os.path.dirname(os.path.abspath(env_path))):
        return os.path.abspath(env_path)

    # Check if running as packaged binary (e.g. PyInstaller)
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        local_db = os.path.join(exe_dir, DB_NAME)
        # 1. If local database already exists next to executable, prioritize it
        if os.path.exists(local_db):
            return local_db
        # 2. If the folder is writable, operate in true zero-install portable mode
        try:
            test_file = os.path.join(exe_dir, ".meditrack_write_test")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return local_db
        except Exception:
            # 3. Fall back to user AppData if running from read-only directory (e.g. Program Files)
            app_data = os.environ.get("APPDATA") or os.path.expanduser("~")
            data_dir = os.path.join(app_data, "MediTrack")
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, DB_NAME)

    # Default to local development/portable directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, DB_NAME)


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Returns an optimized, transaction-ready SQLite connection.
    Enforces:
      - PRAGMA foreign_keys = ON (referential integrity)
      - PRAGMA journal_mode = WAL (concurrency, crash resistance, performance)
      - PRAGMA busy_timeout = 5000 (prevents 'database is locked' errors)
      - PRAGMA synchronous = NORMAL (safe with WAL, faster writes)
      - sqlite3.Row row factory for clean dict/column access
    """
    path = db_path or get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Performance and integrity pragmas
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    return conn


@contextmanager
def transaction(conn: sqlite3.Connection = None):
    """
    Context manager for atomic database operations.
    Ensures:
      - Explicit BEGIN before operations
      - Automatic COMMIT on success
      - Automatic ROLLBACK on any failure
      - Never silently swallows exceptions
    Usage:
        with transaction() as conn:
            conn.execute(...)
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        conn.execute("BEGIN TRANSACTION;")
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        if should_close:
            conn.close()


def init_db(db_path: str = None) -> None:
    """
    Initializes the MediTrack SQLite schema.
    Creates all core tables, constraints, default settings, and performance indexes.
    Subsequently triggers run_migrations() to guarantee schema currency.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # --------------------------------------------------------------------------
    # 0. Schema Version Tracking (Section 61)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL,
        description TEXT
    );
    """)

    # --------------------------------------------------------------------------
    # 1. System Settings Table (Section 25)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    default_settings = [
        ("shop_name", "MediTrack Pharmacy"),
        ("owner_name", "Registered Pharmacist"),
        ("phone", "9999999999"),
        ("address", "123 Healthcare Ave, Medical District"),
        ("gst_number", "GSTIN1234567890"),
        ("upi_id", "meditrack@upi"),
        ("bill_prefix", "MT-2026-"),
        ("starting_bill_number", "1"),
        ("default_payment_mode", "Cash"),
        ("expiry_warning_days", "90"),
        ("app_version", APP_VERSION),
        ("database_version", str(DATABASE_VERSION))
    ]
    for key, val in default_settings:
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?);", (key, val))

    # --------------------------------------------------------------------------
    # 2. Authentication & Users Table (Section 47)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('Admin', 'Pharmacist', 'Cashier'))
    );
    """)

    # Initial seed users with cryptographic salted hashes (Zero plaintext storage)
    cursor.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('admin', 'b658329973f212f1c6eea8a7355feed53ba9d8d9ae3842ebb200c7665a7d584b', 'Admin');")
    cursor.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('pharmacist', '6b258b526347beb114fab9175d054e4cc32730f3ad51b023f32aee8364d3809d', 'Pharmacist');")
    cursor.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('cashier', 'ffd2b6c83c74fe069fd535dbef511f0c8a5dc355848f9451d71d514337fb7013', 'Cashier');")

    # --------------------------------------------------------------------------
    # 3. Suppliers Table (Section 10)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        gst_number TEXT,
        payment_terms TEXT DEFAULT 'Net 30',
        opening_balance REAL DEFAULT 0.0,
        current_balance REAL DEFAULT 0.0,
        notes TEXT,
        status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive'))
    );
    """)

    # --------------------------------------------------------------------------
    # 4. Supplier Ledger Table (Section 10 & 21)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS supplier_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        reference_id TEXT,
        debit REAL DEFAULT 0.0,
        credit REAL DEFAULT 0.0,
        balance REAL DEFAULT 0.0,
        description TEXT,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
    );
    """)

    # --------------------------------------------------------------------------
    # 5. Customers Table (Section 46)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        phone TEXT,
        email TEXT,
        address TEXT,
        gst_number TEXT,
        credit_limit REAL DEFAULT 5000.0,
        outstanding_balance REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive'))
    );
    """)

    # --------------------------------------------------------------------------
    # 6. Customer Ledger Table (Section 46)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        reference_id TEXT,
        debit REAL DEFAULT 0.0,
        credit REAL DEFAULT 0.0,
        balance REAL DEFAULT 0.0,
        description TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
    );
    """)

    # --------------------------------------------------------------------------
    # 7. Medicines Master Table (Section 5 & 7)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
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

    # --------------------------------------------------------------------------
    # 8. Medicine Batches Table (Section 5, 7, 8)
    # Authoritative inventory is 'quantity' (total_tablets)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicine_batches (
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

    # --------------------------------------------------------------------------
    # 9. Purchases Table (Section 11 & 12)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_invoice_number TEXT NOT NULL,
        supplier_id INTEGER NOT NULL,
        purchase_date TEXT NOT NULL,
        due_date TEXT,
        payment_status TEXT NOT NULL CHECK(payment_status IN ('Paid', 'Unpaid', 'Partial')),
        total_amount REAL NOT NULL,
        discount_percent REAL DEFAULT 0.0,
        gst_amount REAL DEFAULT 0.0,
        grand_total REAL NOT NULL,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
        UNIQUE(supplier_id, purchase_invoice_number, purchase_date)
    );
    """)

    # --------------------------------------------------------------------------
    # 10. Purchase Items Table (Section 11)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        batch_number TEXT NOT NULL,
        expiry_date TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        free_quantity INTEGER DEFAULT 0,
        purchase_price REAL NOT NULL,
        mrp REAL NOT NULL,
        discount_percent REAL DEFAULT 0.0,
        gst_percent REAL DEFAULT 12.0,
        total_amount REAL NOT NULL,
        FOREIGN KEY (purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    );
    """)

    # --------------------------------------------------------------------------
    # 11. Purchase Returns (Section 21)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        return_date TEXT NOT NULL,
        total_refund REAL NOT NULL,
        reference_invoice TEXT,
        reason TEXT,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_return_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_return_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        batch_number TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        purchase_price REAL NOT NULL,
        gst_percent REAL DEFAULT 12.0,
        total_amount REAL NOT NULL,
        FOREIGN KEY (purchase_return_id) REFERENCES purchase_returns(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    );
    """)

    # --------------------------------------------------------------------------
    # 12. Bills Table (Section 13, 14, 18)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
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

    # --------------------------------------------------------------------------
    # 13. Bill Items Table (Section 19)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bill_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_number TEXT NOT NULL,
        medicine_id INTEGER,
        medicine_name TEXT NOT NULL,
        batch TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price_per_tablet REAL NOT NULL,
        discount_percent REAL NOT NULL,
        subtotal REAL NOT NULL,
        profit REAL NOT NULL,
        gst_percent REAL DEFAULT 12.0,
        FOREIGN KEY (bill_number) REFERENCES bills(bill_number) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    );
    """)

    # --------------------------------------------------------------------------
    # 14. Sales Returns Table (Section 21)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_number TEXT NOT NULL,
        return_date TEXT NOT NULL,
        total_refund REAL NOT NULL,
        refund_mode TEXT NOT NULL,
        reason TEXT,
        FOREIGN KEY (bill_number) REFERENCES bills(bill_number)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales_return_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sales_return_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        batch TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price_per_tablet REAL NOT NULL,
        gst_percent REAL DEFAULT 12.0,
        total_refund REAL NOT NULL,
        FOREIGN KEY (sales_return_id) REFERENCES sales_returns(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    );
    """)

    # --------------------------------------------------------------------------
    # 15. Stock Movements Log (Section 40)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        batch_number TEXT NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        reference_id TEXT,
        description TEXT,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    );
    """)

    # --------------------------------------------------------------------------
    # 16. Stock Adjustments Table (Section 40)
    # Dedicated audit record for physical counts, damage, expiry write-offs, etc.
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # 17. Audit Logs Table (Section 39)
    # --------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        timestamp TEXT NOT NULL,
        user TEXT NOT NULL,
        action TEXT NOT NULL,
        table_name TEXT,
        record_id TEXT,
        details TEXT,
        previous_values TEXT,
        new_values TEXT
    );
    """)

    # --------------------------------------------------------------------------
    # 18. Smart Purchase Import Tables (Section 29, 31, 34, 38)
    # --------------------------------------------------------------------------
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

    conn.commit()
    conn.close()

    # Trigger safe migrations for existing installations (ensures all columns are present)
    from database.migrations import run_migrations
    run_migrations(db_path)

    # Re-connect to ensure all performance indexes are verified and created
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # --------------------------------------------------------------------------
    # 19. Core Performance Indexes (Section 4, 48)
    # --------------------------------------------------------------------------
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

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", get_db_path())
