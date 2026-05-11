"""SQLite storage for prompt logs."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS prompt_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL,
    guardrail_reason TEXT NOT NULL DEFAULT '',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
    response TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_prompt_logs_timestamp ON prompt_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_prompt_logs_status ON prompt_logs(status);
"""


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    return settings.sqlite_path


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    db_path = get_db_path()
    _ensure_dir(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def insert_log(entry: dict[str, Any]) -> int:
    init_db()
    timestamp = entry.get("timestamp") or datetime.now(timezone.utc).replace(
        tzinfo=None
    ).isoformat(timespec="seconds")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO prompt_logs (
                timestamp, user_id, provider, model, prompt, status,
                guardrail_reason, input_tokens, output_tokens,
                estimated_cost_usd, response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                entry["user_id"],
                entry["provider"],
                entry["model"],
                entry["prompt"],
                entry["status"],
                entry.get("guardrail_reason", ""),
                int(entry.get("input_tokens", 0)),
                int(entry.get("output_tokens", 0)),
                float(entry.get("estimated_cost_usd", 0.0)),
                entry.get("response", ""),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_recent(limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM prompt_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_all() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM prompt_logs ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def export_csv(target: Path) -> Path:
    """Export the full log table as a CSV file."""
    import csv

    rows = fetch_all()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as f:
        if not rows:
            f.write("")
            return target
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return target
