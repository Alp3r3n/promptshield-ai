"""Request logging facade."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import database
from app.config import settings


def _setup_file_logger() -> logging.Logger:
    log_dir = settings.root_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("promptshield")
    if not logger.handlers:
        handler = logging.FileHandler(log_dir / "promptshield.log")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


_file_logger = _setup_file_logger()


def log_request(entry: dict[str, Any]) -> int:
    """Persist a request to SQLite and append a line to the file log."""
    entry.setdefault(
        "timestamp",
        datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"),
    )
    row_id = database.insert_log(entry)
    _file_logger.info(
        "user=%s status=%s provider=%s model=%s tokens=%d/%d cost=$%.6f reason=%s",
        entry.get("user_id"),
        entry.get("status"),
        entry.get("provider"),
        entry.get("model"),
        entry.get("input_tokens", 0),
        entry.get("output_tokens", 0),
        entry.get("estimated_cost_usd", 0.0),
        entry.get("guardrail_reason", ""),
    )
    return row_id


def export_logs_csv() -> Path:
    target = settings.root_dir / "logs" / "prompt_logs.csv"
    return database.export_csv(target)
