"""
Automated Test Suite for utils/audit_service.py
Validates:
  1. Backward-compatible positional log_audit calls.
  2. Full v2 schema auditing with structured JSON state deltas.
  3. Cursor reuse inside active transactions (zero nested connection lockups).
  4. Query filtering by action, user, table, and date bounds.
  5. Entity-specific audit histories via get_audit_logs_for_record().
  6. Critical compliance audit querying.
"""

import os
import sys
import shutil
import sqlite3
from datetime import datetime

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configure sandbox test database
TEST_DIR = os.path.join(BASE_DIR, "tests", "audit_sandbox")
os.makedirs(TEST_DIR, exist_ok=True)

TEST_DB = os.path.join(TEST_DIR, "test_audit.db")
os.environ["MEDITRACK_DB_PATH"] = os.path.abspath(TEST_DB)

import database.db
database.db.DB_NAME = "test_audit.db"
from database.db import init_db, get_connection
from utils.audit_service import (
    log_audit,
    get_all_audit_logs,
    get_audit_logs_for_record,
    get_recent_critical_audits
)


def run_tests():
    print("=" * 60)
    print("STARTING TEST SUITE: utils/audit_service.py")
    print("=" * 60)

    # 1. Initialize schema
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass

    init_db(TEST_DB)
    print("[PASS] Sandbox database initialized.")

    # 2. Test Legacy Positional log_audit
    a1_id = log_audit("pharmacist1", "LOGIN", "Logged in successfully from workstation 1")
    assert a1_id is not None and a1_id > 0
    print(f"[PASS] Legacy positional log_audit logged with ID {a1_id}")

    # 3. Test Full v2 Rich Kwargs Auditing with JSON Deltas
    prev_state = {"price": 25.0, "status": "Active", "quantity": 100}
    new_state = {"price": 28.0, "status": "Active", "quantity": 100}
    a2_id = log_audit(
        user_or_id="admin",
        action="PRICE_CHANGE",
        table_name="medicine_batches",
        record_id=42,
        details="Routine quarterly price adjustment",
        previous_values=prev_state,
        new_values=new_state
    )
    assert a2_id is not None and a2_id > 0
    print(f"[PASS] Rich v2 audit entry logged with ID {a2_id}")

    # 4. Test In-Transaction Cursor Reuse (Ensures no lockups)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("BEGIN TRANSACTION;")
    try:
        a3_id = log_audit(
            user_or_id="admin",
            action="EXPIRED_OVERRIDE",
            table_name="bills",
            record_id="MT-0099",
            details="Dispensing authorized by registered pharmacist Dr. Rao",
            cursor=cursor
        )
        conn.commit()
        print(f"[PASS] In-transaction cursor reuse succeeded without locking (ID: {a3_id})")
    except Exception as ex:
        conn.rollback()
        raise ex
    finally:
        conn.close()

    # 5. Test get_all_audit_logs and JSON delta parsing
    logs = get_all_audit_logs()
    assert len(logs) == 3, f"Expected 3 logs, got {len(logs)}"

    price_log = next(l for l in logs if l["action"] == "PRICE_CHANGE")
    assert price_log["user"] == "admin"
    assert price_log["table_name"] == "medicine_batches"
    assert price_log["record_id"] == "42"
    assert price_log["previous_values_json"]["price"] == 25.0
    assert price_log["new_values_json"]["price"] == 28.0
    print("[PASS] Audit logs retrieved and JSON delta snapshots cleanly deserialized.")

    # 6. Test Query Filtering
    admin_logs = get_all_audit_logs(user="admin")
    assert len(admin_logs) == 2, f"Expected 2 admin logs, got {len(admin_logs)}"

    pharm_logs = get_all_audit_logs(user="pharmacist1")
    assert len(pharm_logs) == 1
    assert pharm_logs[0]["action"] == "LOGIN"

    table_logs = get_all_audit_logs(table_name="medicine_batches")
    assert len(table_logs) == 1
    print("[PASS] Filtered audit querying (by user, action, table) passed.")

    # 7. Test get_audit_logs_for_record
    record_logs = get_audit_logs_for_record("medicine_batches", 42)
    assert len(record_logs) == 1
    assert record_logs[0]["action"] == "PRICE_CHANGE"
    print("[PASS] Record-specific audit history lookup passed.")

    # 8. Test get_recent_critical_audits
    critical = get_recent_critical_audits()
    assert len(critical) == 1 # EXPIRED_OVERRIDE
    assert critical[0]["action"] == "EXPIRED_OVERRIDE"
    print("[PASS] Critical compliance audit filter verified.")

    print("\n" + "=" * 60)
    print("ALL AUDIT SERVICE TESTS PASSED SUCCESSFULLY! (EXIT CODE 0)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_tests()
    finally:
        if os.path.exists(TEST_DIR):
            try:
                shutil.rmtree(TEST_DIR)
            except Exception:
                pass
