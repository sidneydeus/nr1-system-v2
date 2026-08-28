from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "session_id"):
            log_obj["session_id"] = record.session_id
        if hasattr(record, "correlation_id"):
            log_obj["correlation_id"] = record.correlation_id
        if hasattr(record, "user_name"):
            log_obj["user_name"] = record.user_name
        if hasattr(record, "sector"):
            log_obj["sector"] = record.sector
        if hasattr(record, "event"):
            log_obj["event"] = record.event
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def setup_json_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


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
                    correlation_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            try:
                connection.execute("ALTER TABLE logs ADD COLUMN correlation_id TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_logs_session_id ON logs(session_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_logs_correlation_id ON logs(correlation_id)"
            )

    def list_logs(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, session_id, correlation_id, level, event, message, created_at
                FROM logs
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def save_alert(self, session_id: str, classification: str, message: str) -> None:
        self.log(
            session_id=session_id,
            correlation_id=self._generate_correlation_id(session_id),
            level="WARNING",
            event="ADMIN_REPORT_ALERT",
            message={"classification": classification, "detail": message},
        )

    def log(
        self,
        session_id: str,
        correlation_id: str,
        level: str,
        event: str,
        message: dict[str, Any] | str,
    ) -> None:
        message_json = json.dumps(message, ensure_ascii=False) if isinstance(message, dict) else message
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO logs (session_id, correlation_id, level, event, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    correlation_id,
                    level,
                    event,
                    message_json,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    @staticmethod
    def _generate_correlation_id(session_id: str) -> str:
        return f"{session_id}-{uuid.uuid4().hex[:8]}"


class StructuredLogger:
    def __init__(
        self,
        log_store: SQLiteLogStore,
        session_id: str,
        user_name: str | None = None,
        sector: str | None = None,
        logger_name: str = "nr1.agent",
    ) -> None:
        self.log_store = log_store
        self.session_id = session_id
        self.user_name = user_name
        self.sector = sector
        self.correlation_id = f"{session_id}-{uuid.uuid4().hex[:8]}"
        self._logger = logging.getLogger(logger_name)

    def _base_context(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_name": self.user_name,
            "sector": self.sector,
        }

    def _log_to_console(self, level: str, event: str, message: dict[str, Any]) -> None:
        extra = {
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "user_name": self.user_name,
            "sector": self.sector,
            "event": event,
            "extra_data": message,
        }
        getattr(self._logger, level.lower())(message, extra=extra)

    def log_event(self, level: str, event: str, message: dict[str, Any] | str) -> None:
        full_message = {"context": self._base_context(), **(message if isinstance(message, dict) else {"detail": message})}
        self.log_store.log(
            session_id=self.session_id,
            correlation_id=self.correlation_id,
            level=level,
            event=event,
            message=full_message,
        )
        self._log_to_console(level, event, full_message)

    def info(self, event: str, message: dict[str, Any] | str) -> None:
        self.log_event("INFO", event, message)

    def warning(self, event: str, message: dict[str, Any] | str) -> None:
        self.log_event("WARNING", event, message)

    def error(self, event: str, message: dict[str, Any] | str) -> None:
        self.log_event("ERROR", event, message)

    def risk_classification(self, classification: str, details: dict[str, Any]) -> None:
        serializable_details = {}
        for k, v in details.items():
            try:
                json.dumps(v)
                serializable_details[k] = v
            except (TypeError, ValueError):
                serializable_details[k] = str(v)
        self.info("RISK_CLASSIFICATION", {"classification": classification, **serializable_details})

    def rag_query(self, query: str, retrieved_docs: list[dict[str, Any]]) -> None:
        serializable_docs = []
        for doc in retrieved_docs:
            serializable_doc = {}
            for k, v in doc.items():
                try:
                    json.dumps(v)
                    serializable_doc[k] = v
                except (TypeError, ValueError):
                    serializable_doc[k] = str(v)
            serializable_docs.append(serializable_doc)
        self.info("RAG_QUERY", {"query": query, "retrieved_count": len(retrieved_docs), "documents": serializable_docs})

    def tool_invocation(self, tool_name: str, parameters: dict[str, Any], result: Any) -> None:
        serializable_result = result
        try:
            json.dumps(result)
        except (TypeError, ValueError):
            serializable_result = str(result)
        self.info("TOOL_INVOCATION", {"tool": tool_name, "parameters": parameters, "result": serializable_result})

    def human_approval(self, action: str, approved: bool, details: dict[str, Any]) -> None:
        self.info("HUMAN_APPROVAL", {"action": action, "approved": approved, **details})

    def state_transition(self, from_status: str, to_status: str, details: dict[str, Any]) -> None:
        self.info("STATE_TRANSITION", {"from": from_status, "to": to_status, **details})

    def session_start(self) -> None:
        self.info("SESSION_START", {"user_name": self.user_name, "sector": self.sector})

    def session_end(self, classification: str | None = None) -> None:
        self.info("SESSION_END", {"classification": classification, "user_name": self.user_name, "sector": self.sector})
