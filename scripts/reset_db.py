#!/usr/bin/env python3
"""Reset the persistent application data stored in SQLite."""
import argparse
import os
import sqlite3
from pathlib import Path

import sqlite_vec

TABLES = ["logs", "reports", "vec_chunks"]

def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn

def reset_database(db_path: Path) -> int:
    if not db_path.exists():
        print(f"Banco de dados não encontrado: {db_path}")
        return 1

    with get_conn(db_path) as conn:
        existing_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')"
            )
        }
        for table in TABLES:
            if table not in existing_tables:
                print(f"  Ignorada (não existe): {table}")
                continue
            conn.execute(f"DELETE FROM {table}")
            print(f"  Limpa: {table}")
        
        # Reset auto-increment sequences
        if "sqlite_sequence" in existing_tables:
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('logs', 'reports')")
        
        conn.commit()
    
    # VACUUM must run outside transaction
    with get_conn(db_path) as conn:
        conn.execute("VACUUM")
    
    print(f"Reset concluído em {db_path}.")
    print("Observação: reinicie o processo/container do agente para descartar sessões em memória.")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpa os dados persistentes do agente")
    parser.add_argument(
        "--database",
        type=Path,
        help="Caminho do SQLite (padrão: SQLITE_DB_PATH ou data/nr1.db)",
    )
    args = parser.parse_args()
    database_path = args.database or Path(os.getenv("SQLITE_DB_PATH", "data/nr1.db"))
    raise SystemExit(reset_database(database_path))
