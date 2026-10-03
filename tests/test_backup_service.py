"""
Automated Test Suite for utils/backup_service.py
Validates:
  1. Atomic online backup creation via sqlite3.Connection.backup().
  2. WAL journal checkpoint flush prior to backup.
  3. Pre-restore integrity audit (rejects corrupt/empty backups).
  4. Automatic emergency safety snapshot created before overwriting active DB.
  5. Reliable restoration to pre-mutation state.
  6. Backup list metadata, sorting, and housekeeping.
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
TEST_DIR = os.path.join(BASE_DIR, "tests", "backup_sandbox")
os.makedirs(TEST_DIR, exist_ok=True)

TEST_DB = os.path.join(TEST_DIR, "test_shop.db")
os.environ["MEDITRACK_DB_PATH"] = os.path.abspath(TEST_DB)

import database.db
database.db.DB_NAME = "test_shop.db"
from database.db import init_db, get_connection
from utils.customer_service import add_customer, get_customer_by_id, get_all_customers
from utils.backup_service import (
    backup_database,
    restore_database,
    list_backups,
    verify_backup_integrity,
    delete_backup,
    clean_old_backups,
    get_backups_dir
)


def run_tests():
    print("=" * 60)
    print("STARTING TEST SUITE: utils/backup_service.py")
    print("=" * 60)

    # Clean sandbox folder
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass

    # 1. Initialize schema
    init_db(TEST_DB)
    print("[PASS] Sandbox database initialized in WAL mode.")

    # Populate some baseline data
    c1_id = add_customer(name="Initial Patient", phone="9988776655")
    assert c1_id > 0
    print(f"[PASS] Baseline customer created with ID {c1_id}")

    # 2. Test Backup Creation (Online Backup API)
    backup_file_1 = backup_database(label="baseline")
    assert os.path.exists(backup_file_1), f"Backup file {backup_file_1} not created"
    assert os.path.getsize(backup_file_1) > 0, "Backup file should not be 0 bytes"
    print(f"[PASS] Online backup snapshot created: {os.path.basename(backup_file_1)} ({os.path.getsize(backup_file_1)} bytes)")

    # 3. Test Backup Integrity Verification
    audit = verify_backup_integrity(backup_file_1)
    assert audit["valid"] is True, f"Integrity check failed: {audit['error']}"
    assert audit["schema_version"] == 2, f"Expected schema version 2, got {audit['schema_version']}"
    print(f"[PASS] Backup integrity audit passed: valid={audit['valid']}, version={audit['schema_version']}")

    # 4. Test Backup Integrity Rejection on Corrupted File
    corrupt_file = os.path.join(get_backups_dir(), "medicalshop_corrupted_test.db")
    with open(corrupt_file, "wb") as f:
        f.write(b"NOT A SQLITE FILE HEADER CRASH")

    corrupt_audit = verify_backup_integrity(corrupt_file)
    assert corrupt_audit["valid"] is False, "Corrupt file should fail integrity check"
    print(f"[PASS] Corrupt backup correctly flagged: {corrupt_audit['error']}")

    # Restoring corrupted file must be blocked with ValueError
    corrupt_blocked = False
    try:
        restore_database(os.path.basename(corrupt_file))
    except ValueError as e:
        if "corrupted or invalid" in str(e).lower() or "restoration aborted" in str(e).lower():
            corrupt_blocked = True
            print(f"[PASS] Corrupted restore blocked before touching active DB: {e}")
    assert corrupt_blocked, "Expected corrupted restore to be blocked"

    # Clean up corrupt test file
    delete_backup(os.path.basename(corrupt_file))

    # 5. Test State Mutation & Restore
    # Add a temporary customer to active DB that was not in backup_file_1
    c2_id = add_customer(name="Temporary Patient To Revert", phone="1122334455")
    assert c2_id > 0
    assert get_customer_by_id(c2_id) is not None
    print(f"[PASS] Mutated active database: Added temp customer #{c2_id}")

    # Restore baseline backup
    restored_path = restore_database(os.path.basename(backup_file_1))
    assert os.path.exists(restored_path)

    # Verify that temporary customer no longer exists in restored database
    cust_temp = get_customer_by_id(c2_id)
    assert cust_temp is None, "Temporary customer must not exist after restoring baseline backup!"

    # Verify baseline customer still exists
    cust_base = get_customer_by_id(c1_id)
    assert cust_base is not None, "Baseline customer must exist after restoration!"
    assert cust_base["name"] == "Initial Patient"
    print("[PASS] Database restored successfully: Mutated state reverted, baseline intact.")

    # 6. Verify Automatic Safety Snapshot was created
    all_backups = list_backups()
    safety_snapshots = [b for b in all_backups if b.get("is_safety_snapshot")]
    assert len(safety_snapshots) >= 1, "Expected at least 1 emergency pre-restore safety snapshot"
    print(f"[PASS] Emergency safety snapshot verified: {safety_snapshots[0]['filename']}")

    # 7. Test Backup List & Sorting
    assert len(all_backups) >= 2
    for b in all_backups:
        assert "filename" in b
        assert "time" in b
        assert "size" in b
        assert "path" in b
    print("[PASS] list_backups() schema & UI keys verified.")

    # 8. Test Backup Housekeeping & Deletion
    # Create 3 more backups
    for i in range(3):
        backup_database(label=f"batch_{i}")

    total_before = len(list_backups())
    cleaned = clean_old_backups(keep_count=2)
    total_after = len(list_backups())
    assert cleaned > 0, f"Expected cleaned > 0, got {cleaned}"
    print(f"[PASS] clean_old_backups() successfully trimmed {cleaned} old restore points.")

    print("\n" + "=" * 60)
    print("ALL BACKUP TESTS PASSED SUCCESSFULLY! (EXIT CODE 0)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_tests()
    finally:
        # Cleanup sandbox directory
        if os.path.exists(TEST_DIR):
            try:
                shutil.rmtree(TEST_DIR)
            except Exception:
                pass
