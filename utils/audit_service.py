"""
MediTrack ERP - System Audit Logging Engine
Immutable audit trails for administrative, inventory, pricing, and financial transactions.
Supports structured JSON delta snapshots, regulatory query filtering, and non-blocking cursor reuse.
"""

import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from database.db import get_connection


# ------------------------------------------------------------------------------
# 1. Immutable Audit Logging
# ------------------------------------------------------------------------------

def log_audit(
    user_or_id: str = "system",
    action: str = "ACTION",
    table_name: Optional[str] = None,
    record_id: Optional[Union[int, str]] = None,
    details: Union[str, Dict[str, Any]] = "",
    previous_values: Optional[Union[Dict[str, Any], str]] = None,
    new_values: Optional[Union[Dict[str, Any], str]] = None,
    date: Optional[str] = None,
    timestamp: Optional[str] = None,
    cursor: Optional[sqlite3.Cursor] = None
) -> Optional[int]:
    """
    Records an immutable audit event in the database.
    
    Supports:
      - Backward compatibility with legacy log_audit(user_id, action, details)
      - Structured JSON serialization for state deltas (previous_values, new_values)
      - In-transaction cursor reuse (cursor=cursor) to prevent nested-lock timeouts
      - Harmonized dual 'date' and 'timestamp' columns for database v1/v2 compatibility
    """
    now = datetime.now()
    date_str = date or now.strftime("%Y-%m-%d")
    timestamp_str = timestamp or now.strftime("%Y-%m-%d %H:%M:%S")

    user_clean = str(user_or_id).strip() if user_or_id else "system"
    action_clean = str(action).strip().upper() if action else "ACTION"
    table_clean = str(table_name).strip() if table_name else None
    rec_clean = str(record_id).strip() if record_id is not None else None

    # Serialize details if passed as dict
    if isinstance(details, dict):
        details_str = json.dumps(details, default=str)
    else:
        details_str = str(details) if details else ""

    # Serialize JSON delta snapshots
    prev_str = None
    if previous_values is not None:
        prev_str = json.dumps(previous_values, default=str) if isinstance(previous_values, dict) else str(previous_values)

    new_str = None
    if new_values is not None:
        new_str = json.dumps(new_values, default=str) if isinstance(new_values, dict) else str(new_values)

    should_close = False
    if cursor is None:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        should_close = True
    else:
        cur = cursor

    try:
        cur.execute("""
            INSERT INTO audit_logs (
                date, timestamp, user, action, table_name, record_id, details, previous_values, new_values
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            date_str, timestamp_str, user_clean, action_clean,
            table_clean, rec_clean, details_str, prev_str, new_str
        ))
        audit_id = cur.lastrowid

        if should_close:
            conn.commit()

        return audit_id

    except Exception as ex:
        # Fallback for old databases that had legacy user_id column
        try:
            cur.execute("""
                INSERT INTO audit_logs (date, timestamp, user_id, action, details)
                VALUES (?, ?, ?, ?, ?);
            """, (date_str, timestamp_str, user_clean, action_clean, details_str))
            if should_close:
                conn.commit()
            return cur.lastrowid
        except Exception:
            # Silent fallback: Audit logger must never crash core transaction if non-fatal
            return None
    finally:
        if should_close:
            conn.close()


# ------------------------------------------------------------------------------
# 2. Audit Trail Queries & Filtering
# ------------------------------------------------------------------------------

def get_all_audit_logs(
    limit: int = 200,
    offset: int = 0,
    action: Optional[str] = None,
    user: Optional[str] = None,
    table_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves filtered audit logs ordered by newest first.
    Automatically parses previous_values and new_values JSON payloads for caller convenience.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    conditions = []
    params = []

    if action:
        conditions.append("UPPER(action) = UPPER(?)")
        params.append(action.strip())

    if user:
        conditions.append("LOWER(user) = LOWER(?)")
        params.append(user.strip())

    if table_name:
        conditions.append("LOWER(table_name) = LOWER(?)")
        params.append(table_name.strip())

    if start_date:
        conditions.append("date >= ?")
        params.append(start_date.strip())

    if end_date:
        conditions.append("date <= ?")
        params.append(end_date.strip())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT * FROM audit_logs
        {where_clause}
        ORDER BY timestamp DESC, id DESC
        LIMIT ? OFFSET ?;
    """
    params.extend([max(1, int(limit)), max(0, int(offset))])

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        row_dict = dict(r)
        # Harmonize user vs user_id
        if "user" not in row_dict or not row_dict["user"]:
            row_dict["user"] = row_dict.get("user_id", "system")

        # Parse JSON deltas if present
        for col in ("previous_values", "new_values"):
            val = row_dict.get(col)
            if val and isinstance(val, str) and (val.startswith("{") or val.startswith("[")):
                try:
                    row_dict[col + "_json"] = json.loads(val)
                except Exception:
                    row_dict[col + "_json"] = None
            else:
                row_dict[col + "_json"] = None

        results.append(row_dict)

    return results


def get_audit_logs_for_record(table_name: str, record_id: Union[int, str], limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves all historical audit modifications for a specific database entity.
    Example: get_audit_logs_for_record('medicine_batches', '14')
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM audit_logs
        WHERE LOWER(table_name) = LOWER(?) AND record_id = ?
        ORDER BY timestamp DESC, id DESC
        LIMIT ?;
    """, (table_name.strip(), str(record_id).strip(), limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_critical_audits(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Queries high-impact administrative and compliance audit events:
      - EXPIRED_OVERRIDE (dispensing past expiry override)
      - STOCK_ADJUSTMENT (manual inventory write-offs / corrections)
      - RESTORE (database rollback)
      - PRICE_CHANGE (manual rate updates)
      - DELETE (entity deletions)
    """
    critical_actions = (
        "EXPIRED_OVERRIDE",
        "STOCK_ADJUSTMENT",
        "DATABASE_RESTORE",
        "PRICE_OVERRIDE",
        "USER_DELETE",
        "MEDICINE_DELETE"
    )
    placeholders = ", ".join("?" for _ in critical_actions)
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT * FROM audit_logs
        WHERE action IN ({placeholders})
        ORDER BY timestamp DESC, id DESC
        LIMIT ?;
    """, (*critical_actions, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
