"""Shared pytest fixtures.

Each test runs against an isolated SQLite file under a tmp dir so production
data is never touched.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    """Point the SQLite path at a per-test tmp file."""
    from app import config as cfg

    db_file = tmp_path / "test_logs.db"
    test_settings = replace(
        cfg.settings,
        database_url=f"sqlite:///{db_file}",
        llm_provider="mock",
        enable_mock_mode=True,
        enable_nemo_guardrails=False,
    )
    monkeypatch.setattr(cfg, "settings", test_settings)

    # Patch the already-imported references too.
    from app import database, logger
    monkeypatch.setattr(database, "settings", test_settings, raising=False)
    monkeypatch.setattr(logger, "settings", test_settings, raising=False)

    yield db_file
