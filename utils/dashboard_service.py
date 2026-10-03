from datetime import datetime, timedelta
from database.db import get_connection

def get_dashboard_stats():
    conn = get_connection()
    cursor = conn.cursor()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    limit_date_str = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    
    stats = {}
    
    # 1. Today's Sales, Profit, and Bill Count
    cursor.execute("""
        SELECT COUNT(*) as today_bills, SUM(grand_total) as today_sales, SUM(total_profit) as today_profit 
        FROM bills 
        WHERE date LIKE ? AND status = 'Active';
    """, (f"{today_str}%",))
    row = cursor.fetchone()
    stats['today_bills'] = row['today_bills'] if row['today_bills'] is not None else 0
    stats['today_sales'] = row['today_sales'] if row['today_sales'] is not None else 0.0
    stats['today_profit'] = row['today_profit'] if row['today_profit'] is not None else 0.0
    
    # 2. Lifetime Sales and Profit
    cursor.execute("""
        SELECT SUM(grand_total) as life_sales, SUM(total_profit) as life_profit 
        FROM bills WHERE status = 'Active';
    """)
    row = cursor.fetchone()
    stats['lifetime_sales'] = row['life_sales'] if row['life_sales'] is not None else 0.0
    stats['lifetime_profit'] = row['life_profit'] if row['life_profit'] is not None else 0.0
    
    # 3. Total Medicines Count (Unique Master Items)
    cursor.execute("SELECT COUNT(*) as total_meds FROM medicines WHERE status = 'Active';")
    row = cursor.fetchone()
    stats['total_medicines'] = row['total_meds'] if row['total_meds'] is not None else 0
    
    # 4. Total Batches Count
    cursor.execute("SELECT COUNT(*) as total_batches FROM medicine_batches;")
    row = cursor.fetchone()
    stats['total_batches'] = row['total_batches'] if row['total_batches'] is not None else 0
    
    # 5. Low Stock Count (sum of batch quantities < medicine reorder_level)
    cursor.execute("""
        SELECT COUNT(*) as low_stock FROM (
            SELECT m.id
            FROM medicines m
            LEFT JOIN medicine_batches mb ON m.id = mb.medicine_id
            WHERE m.status = 'Active'
            GROUP BY m.id
            HAVING SUM(COALESCE(mb.quantity, 0)) < m.reorder_level
        );
    """)
    row = cursor.fetchone()
    stats['low_stock_count'] = row['low_stock'] if row['low_stock'] is not None else 0
    
    # 6. Expired Medicines Count (expiry_date < today)
    cursor.execute("SELECT COUNT(*) as expired FROM medicine_batches WHERE expiry_date < ?;", (today_str,))
    row = cursor.fetchone()
    stats['expired_count'] = row['expired'] if row['expired'] is not None else 0
    
    # 7. Expiring Soon Count (expiry_date between today and today+90 days)
    cursor.execute("""
        SELECT COUNT(*) as expiring 
        FROM medicine_batches 
        WHERE expiry_date >= ? AND expiry_date <= ?;
    """, (today_str, limit_date_str))
    row = cursor.fetchone()
    stats['expiring_soon_count'] = row['expiring'] if row['expiring'] is not None else 0
    
    # 8. Unpaid metrics (Customer Outstanding Dues sum)
    cursor.execute("SELECT SUM(outstanding_balance) as unpaid_total FROM customers WHERE status = 'Active';")
    row = cursor.fetchone()
    stats['unpaid_total'] = row['unpaid_total'] if row['unpaid_total'] is not None else 0.0
    
    conn.close()
    return stats
