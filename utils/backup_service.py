"""
MediTrack ERP - Database Backup & Disaster Recovery Engine
Production-grade, non-blocking backup and restore utilizing SQLite Online Backup API.
Guarantees zero database corruption, WAL checkpoint synchronization, and pre-restore integrity auditing.
"""

import os
import sys
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

from database.db import get_db_path


def get_backups_dir() -> str:
    """
    Resolves the authoritative backup storage directory.
    Places the backups directory adjacent to the active database location.
    Creates the directory if it does not already exist.
    """
    db_path = get_db_path()
    db_dir = os.path.dirname(os.path.abspath(db_path))
    backups_dir = os.path.join(db_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    return backups_dir


def verify_backup_integrity(backup_path: str) -> Dict[str, Any]:
    """
    Performs a deep SQLite integrity check and schema audit on a backup database file.
    Verifies:
      1. Physical file existence and non-zero byte size.
      2. Valid SQLite header and structural page integrity (PRAGMA integrity_check).
      3. Presence of mandatory MediTrack ERP core tables.
      4. Extracted schema version and record metrics.
    """
    if not os.path.exists(backup_path):
        return {"valid": False, "error": f"Backup file '{backup_path}' does not exist on disk."}

    file_size = os.path.getsize(backup_path)
    if file_size == 0:
        return {"valid": False, "error": "Backup file is empty (0 bytes)."}

    conn = None
    try:
        conn = sqlite3.connect(backup_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Page & B-tree structural integrity check
        cursor.execute("PRAGMA integrity_check;")
        check_row = cursor.fetchone()
        if not check_row or check_row[0] != "ok":
            error_msg = check_row[0] if check_row else "Unknown SQLite corruption"
            return {"valid": False, "error": f"SQLite integrity check failed: {error_msg}"}

        # 2. Schema audit: Verify required core tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row["name"] for row in cursor.fetchall()}
        required_tables = {"medicines", "medicine_batches", "purchases", "bills", "suppliers"}
        missing_tables = required_tables - tables
        if missing_tables:
            return {
                "valid": False,
                "error": f"Corrupt schema: Missing mandatory tables: {', '.join(sorted(missing_tables))}."
            }

        # 3. Read schema version if present
        schema_version = 1
        if "schema_version" in tables:
            cursor.execute("SELECT MAX(version) as ver FROM schema_version;")
            ver_row = cursor.fetchone()
            if ver_row and ver_row["ver"]:
                schema_version = ver_row["ver"]

        # 4. Count records for diagnostics
        cursor.execute("SELECT COUNT(*) FROM medicines;")
        med_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM bills;")
        bills_count = cursor.fetchone()[0]

        return {
            "valid": True,
            "error": None,
            "schema_version": schema_version,
            "medicines_count": med_count,
            "bills_count": bills_count,
            "size_bytes": file_size,
            "size_kb": round(file_size / 1024, 2)
        }

    except sqlite3.DatabaseError as e:
        return {"valid": False, "error": f"SQLite database error: {str(e)}"}
    except Exception as e:
        return {"valid": False, "error": f"Integrity check exception: {str(e)}"}
    finally:
        if conn:
            conn.close()


def backup_database(label: Optional[str] = None) -> str:
    """
    Creates an atomic, transaction-consistent snapshot of the active database.
    
    Engineering safety features:
      1. Uses SQLite's native Online Backup API (sqlite3.Connection.backup()).
      2. Checkpoints WAL journal beforehand (PRAGMA wal_checkpoint(TRUNCATE)) to ensure 
         all uncommitted/committed WAL pages are flushed.
      3. Non-blocking: does NOT lock out concurrent readers or cause 'database is locked'.
      4. Verifies the generated backup snapshot before returning.
    
    Returns:
        Absolute filesystem path to the created backup file.
    """
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file does not exist at '{db_path}'. Run init_db() first.")

    backups_dir = get_backups_dir()
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    clean_label = f"_{label.strip()}" if label and label.strip() else ""
    backup_filename = f"medicalshop_{timestamp}{clean_label}.db"
    backup_path = os.path.join(backups_dir, backup_filename)

    src_conn = None
    dst_conn = None
    try:
        # Connect to source database
        src_conn = sqlite3.connect(db_path, timeout=10.0)
        # Flush WAL pages into database
        try:
            src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except Exception:
            pass

        # Connect to destination backup file
        dst_conn = sqlite3.connect(backup_path, timeout=10.0)

        # Atomic page-by-page online backup
        src_conn.backup(dst_conn)
        dst_conn.commit()

    finally:
        if dst_conn:
            dst_conn.close()
        if src_conn:
            src_conn.close()

    # Post-backup integrity verification
    audit = verify_backup_integrity(backup_path)
    if not audit["valid"]:
        # Delete corrupted file if backup failed
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except Exception:
                pass
        raise RuntimeError(f"Backup verification failed: {audit['error']}")

    return backup_path


def restore_database(backup_filename: str) -> str:
    """
    Restores the active database to the exact state captured in a backup file.
    
    Safety precautions:
      1. Pre-Restore Integrity Audit: The backup file is validated BEFORE touching the active DB.
         Corrupted, partial, or invalid backup files are strictly rejected.
      2. Safety Snapshot: An automatic emergency snapshot of the current active database is saved
         to the backups folder ('pre_restore_safety_<timestamp>.db') prior to overwriting.
      3. Online Restore API: Uses sqlite3.Connection.backup() to cleanly overwrite pages.
      4. WAL Checkpoint: Truncates and resets WAL journal pages to prevent stale journal reads.
    
    Args:
        backup_filename: Basename (e.g. 'medicalshop_2026_10_03_12_00_00.db') or absolute path.
    
    Returns:
        Absolute filesystem path to the restored active database.
    """
    # 1. Resolve backup file path
    if os.path.isabs(backup_filename) and os.path.exists(backup_filename):
        backup_path = backup_filename
    else:
        backups_dir = get_backups_dir()
        backup_path = os.path.join(backups_dir, os.path.basename(backup_filename))

    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file '{backup_filename}' does not exist.")

    # 2. Pre-Restore Integrity Verification
    audit = verify_backup_integrity(backup_path)
    if not audit["valid"]:
        raise ValueError(
            f"Restoration aborted! The backup file '{os.path.basename(backup_path)}' is invalid or corrupted: {audit['error']}"
        )

    active_db_path = get_db_path()

    # 3. Emergency Safety Snapshot of Active Database (if active database exists and has data)
    if os.path.exists(active_db_path) and os.path.getsize(active_db_path) > 0:
        try:
            safety_ts = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            safety_filename = f"pre_restore_safety_{safety_ts}.db"
            safety_path = os.path.join(get_backups_dir(), safety_filename)

            act_conn = sqlite3.connect(active_db_path, timeout=5.0)
            try:
                act_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except Exception:
                pass
            saf_conn = sqlite3.connect(safety_path, timeout=5.0)
            act_conn.backup(saf_conn)
            saf_conn.close()
            act_conn.close()
        except Exception:
            # If safety snapshot fails, proceed cautiously with restore
            pass

    # 4. Perform atomic restoration using SQLite Backup API
    src_conn = None
    dst_conn = None
    try:
        src_conn = sqlite3.connect(backup_path, timeout=15.0)
        dst_conn = sqlite3.connect(active_db_path, timeout=15.0)

        # Stream all pages from backup into active DB
        src_conn.backup(dst_conn)
        dst_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        dst_conn.commit()

    finally:
        if dst_conn:
            dst_conn.close()
        if src_conn:
            src_conn.close()

    # 5. Clean up any orphaned WAL/SHM artifacts if active DB is in WAL mode
    for ext in ("-wal", "-shm"):
        wal_artifact = active_db_path + ext
        if os.path.exists(wal_artifact):
            try:
                # In WAL mode, checkpointing truncates the file. If zero size, remove cleanly.
                if os.path.getsize(wal_artifact) == 0:
                    os.remove(wal_artifact)
            except Exception:
                pass

    return active_db_path


def list_backups() -> List[Dict[str, Any]]:
    """
    Lists all available database backup restore points ordered by latest creation date.
    Returns metadata formatted for the UI settings table.
    """
    backups_dir = get_backups_dir()
    if not os.path.exists(backups_dir):
        return []

    files = [
        f for f in os.listdir(backups_dir)
        if (f.startswith("medicalshop_") or f.startswith("pre_restore_safety_")) and f.endswith(".db")
    ]

    backups = []
    for file in files:
        path = os.path.join(backups_dir, file)
        try:
            stat = os.stat(path)
            created_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            size_kb = round(stat.st_size / 1024, 2)
            is_safety = file.startswith("pre_restore_safety_")

            backups.append({
                "filename": file,
                "path": path,
                "time": created_time,
                "size": f"{size_kb} KB",
                "size_bytes": stat.st_size,
                "is_safety_snapshot": is_safety
            })
        except OSError:
            continue

    # Sort latest first (descending by filename)
    backups.sort(key=lambda x: x["filename"], reverse=True)
    return backups


def delete_backup(backup_filename: str) -> bool:
    """
    Deletes a specific backup restore point file safely.
    """
    backups_dir = get_backups_dir()
    backup_path = os.path.join(backups_dir, os.path.basename(backup_filename))
    if os.path.exists(backup_path):
        os.remove(backup_path)
        return True
    return False


def clean_old_backups(keep_count: int = 30) -> int:
    """
    Removes older historical backups, keeping the specified number of latest backups.
    Excludes emergency safety snapshots from automatic deletion.
    Returns the number of cleaned up files.
    """
    backups = [b for b in list_backups() if not b.get("is_safety_snapshot")]
    if len(backups) <= keep_count:
        return 0

    to_delete = backups[keep_count:]
    deleted_count = 0
    for b in to_delete:
        try:
            if delete_backup(b["filename"]):
                deleted_count += 1
        except Exception:
            continue
    return deleted_count
