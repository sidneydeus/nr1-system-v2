from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import sqlite_vec


VECTOR_DIM = 384
DB_PATH = Path(os.getenv("SQLITE_DB_PATH", "data/nr1.db"))


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn


def init_vector_table() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        conn.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
                embedding float[{VECTOR_DIM}],
                content TEXT,
                source TEXT
            )
            """
        )


def _serialize_vec(vec: list[float]) -> str:
    return json.dumps(vec)


def insert_chunks(chunks: list[dict[str, Any]]) -> int:
    if not chunks:
        return 0
    with get_db_connection() as conn:
        placeholders = ", ".join(["(?, ?, ?)"] * len(chunks))
        values = []
        for chunk in chunks:
            values.extend([_serialize_vec(chunk["embedding"]), chunk["content"], chunk.get("source", "")])
        conn.execute(
            f"INSERT INTO vec_chunks (embedding, content, source) VALUES {placeholders}",
            values,
        )
    return len(chunks)


def search_similar(query_embedding: list[float], k: int = 4) -> list[dict[str, Any]]:
    query_json = _serialize_vec(query_embedding)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT content, source, distance
            FROM vec_chunks
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
            """,
            (query_json, k),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_vectors() -> int:
    with get_db_connection() as conn:
        result = conn.execute("DELETE FROM vec_chunks").rowcount
    return result


def count_vectors() -> int:
    with get_db_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM vec_chunks").fetchone()
    return row[0] if row else 0


if __name__ == "__main__":
    init_vector_table()
    print(f"Vector table initialized at {DB_PATH}")
    print(f"Current vectors: {count_vectors()}")