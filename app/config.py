"""Configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    openai_api_key: str
    openai_model: str
    openai_base_url: str | None
    database_url: str
    enable_cost_tracking: bool
    enable_mock_mode: bool
    enable_nemo_guardrails: bool
    api_host: str
    api_port: int
    root_dir: Path

    @property
    def sqlite_path(self) -> Path:
        url = self.database_url
        if url.startswith("sqlite:///"):
            return (self.root_dir / url.replace("sqlite:///", "", 1)).resolve()
        # Fallback default
        return self.root_dir / "data" / "prompt_logs.db"


def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        openai_base_url=(os.getenv("OPENAI_BASE_URL", "").strip() or None),
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/prompt_logs.db").strip(),
        enable_cost_tracking=_env_bool("ENABLE_COST_TRACKING", True),
        enable_mock_mode=_env_bool("ENABLE_MOCK_MODE", True),
        enable_nemo_guardrails=_env_bool("ENABLE_NEMO_GUARDRAILS", False),
        api_host=os.getenv("API_HOST", "0.0.0.0").strip(),
        api_port=int(os.getenv("API_PORT", "8000")),
        root_dir=ROOT_DIR,
    )


settings = get_settings()
