from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SQLiteLogStore:
    def __init__(self, database_path: str | Path | None = None) -> None:
        configured_path = database_path or os.getenv("SQLITE_DB_PATH", "data/nr1.db")
        self.database_path = Path(configured_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_table()

    def _create_table(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def list_logs(self) -> list[dict[str, object]]:
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, session_id, level, event, message, created_at
                FROM logs
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def save_alert(self, session_id: str, classification: str, message: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO logs (session_id, level, event, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    "WARNING",
                    "ADMIN_REPORT_ALERT",
                    f"classification={classification}; {message}",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
