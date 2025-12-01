import sqlite3
import pandas as pd
from pathlib import Path

# Path to your database
DB_PATH = Path("database/applications.db")

def inspect_db():
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return

    print(f"📂 Connecting to database: {DB_PATH}\n")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. List Tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"📊 Found {len(tables)} tables:")
    for t in tables:
        print(f"  - {t[0]}")
    print("-" * 30)

    # 2. Show Data for each table
    for t in tables:
        table_name = t[0]
        print(f"\n📋 Table: {table_name}")
        
        # Get row count
        count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"   Rows: {count}")
        
        if count > 0:
            # Show first 5 rows using pandas for nice formatting
            df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5", conn)
            print(df.to_string(index=False))
        else:
            print("   (Empty)")
        print("-" * 30)

    conn.close()

if __name__ == "__main__":
    inspect_db()
