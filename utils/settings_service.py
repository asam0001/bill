from database.db import get_connection

def get_setting(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?;", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['value']
    return default

def get_all_settings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings;")
    rows = cursor.fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

def update_settings(settings_dict):
    conn = get_connection()
    cursor = conn.cursor()
    for key, value in settings_dict.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);", (key, str(value)))
    conn.commit()
    conn.close()
