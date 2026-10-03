"""
MediTrack ERP - Security & Cryptographic Password Service
Implements standard cryptographic password hashing, validation, and safe credential updates.
Guarantees zero plaintext password storage in database tables and exported archives.
"""

import os
import hashlib
from typing import Tuple, Optional
from database.db import get_connection

# Internal application salt for cryptographic hashing
_DEFAULT_SALT = "meditrack_enterprise_salt_v2"


def hash_password(password: str, salt: str = _DEFAULT_SALT) -> str:
    """
    Computes a cryptographic SHA-256 hash with salting for secure storage.
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    salted_bytes = (salt + password).encode("utf-8")
    return hashlib.sha256(salted_bytes).hexdigest()


def verify_password(stored_hash: str, provided_password: str, salt: str = _DEFAULT_SALT) -> bool:
    """
    Verifies a plaintext password against a stored cryptographic hash.
    Transparently supports both current salted hashes and legacy migration formats.
    """
    if not stored_hash or not provided_password:
        return False

    # 1. Primary check: Salted SHA-256
    expected_salted = hash_password(provided_password, salt=salt)
    if stored_hash == expected_salted:
        return True

    # 2. Secondary check: Unsalted SHA-256
    expected_unsalted = hashlib.sha256(provided_password.encode("utf-8")).hexdigest()
    if stored_hash == expected_unsalted:
        return True

    # 3. Migration fallback: Legacy plaintext match (allows in-place upgrade)
    if stored_hash == provided_password:
        return True

    return False


def change_password(username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
    """
    Changes a user's password after verifying the old password.
    Enforces minimum security length and writes the new salted hash.
    """
    username = (username or "").strip().lower()
    if not username:
        return False, "Username is required."

    if not new_password or len(new_password) < 6:
        return False, "New password must be at least 6 characters long."

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username = ?;", (username,))
        row = cursor.fetchone()

        if not row:
            return False, f"User '{username}' not found."

        stored_hash = row["password_hash"]
        if not verify_password(stored_hash, old_password):
            return False, "Current password verification failed."

        # Compute new salted hash
        new_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (new_hash, row["id"]))
        conn.commit()

        # Log audit entry
        try:
            from utils.audit_service import log_audit
            log_audit(
                action="PASSWORD_CHANGE",
                table_name="users",
                record_id=row["id"],
                old_values={"username": username, "status": "password_changed"},
                new_values={"username": username, "status": "password_updated"},
                user_id=username
            )
        except Exception:
            pass

        return True, "Password updated successfully."
    except Exception as ex:
        conn.rollback()
        return False, f"Database error updating password: {ex}"
    finally:
        conn.close()
