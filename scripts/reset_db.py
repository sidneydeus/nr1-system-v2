#!/usr/bin/env python3
"""Reset database - truncate all tables and vacuum."""
import sqlite3
import sqlite_vec
from pathlib import Path

DB_PATH = Path("data/nr1.db")

TABLES = ["logs", "reports", "vec_chunks"]

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn

def reset_database() -> None:
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    with get_conn() as conn:
        for table in TABLES:
            conn.execute(f"DELETE FROM {table}")
            print(f"  Truncated: {table}")
        
        # Reset auto-increment sequences
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('logs', 'reports')")
        
        conn.commit()
    
    # VACUUM must run outside transaction
    with get_conn() as conn:
        conn.execute("VACUUM")
    
    print("Database reset complete. Tables will be recreated on next run.")

if __name__ == "__main__":
    reset_database()
