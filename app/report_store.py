from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SQLiteReportStore:
    def __init__(self, database_path: str | Path | None = None) -> None:
        configured_path = database_path or os.getenv("SQLITE_DB_PATH", "data/nr1.db")
        self.database_path = Path(configured_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_table()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    user_name TEXT,
                    sector TEXT,
                    report TEXT NOT NULL,
                    classification TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(reports)")
            }
            if "classification" not in columns:
                connection.execute("ALTER TABLE reports ADD COLUMN classification TEXT")

    def save(
        self,
        session_id: str,
        user_name: str | None,
        sector: str | None,
        report: str,
        classification: str,
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reports (session_id, user_name, sector, report, classification, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    user_name = excluded.user_name,
                    sector = excluded.sector,
                    report = excluded.report,
                    classification = excluded.classification,
                    created_at = excluded.created_at
                """,
                (session_id, user_name, sector, report, classification, created_at),
            )

    def list_reports(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT session_id, user_name, sector, report, classification, created_at
                FROM reports
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_report(self, session_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, user_name, sector, report, classification, created_at
                FROM reports
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        return dict(row) if row is not None else None
