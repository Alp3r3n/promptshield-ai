"""Guardrail service.

Provides a fast, deterministic rule-based check that runs in both mock and real
mode. NeMo Guardrails is loaded only when ENABLE_NEMO_GUARDRAILS=true so the
project remains runnable without installing the optional dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.config import settings


@dataclass
class GuardrailVerdict:
    allowed: bool
    category: str  # "" when allowed
    reason: str  # human-readable reason
    sanitized_text: str | None = None  # populated when status == "modified"


# --- Input rule patterns ---------------------------------------------------

INPUT_RULES: dict[str, list[str]] = {
    "prompt_injection": [
        r"\bignore\s+(all\s+)?(previous|prior|above)\s+instructions?\b",
        r"\bforget\s+(the\s+)?(policy|rules|instructions)\b",
        r"\bdisregard\s+(the\s+)?(previous|prior|above|safety)\b",
        r"\boverride\s+(the\s+)?(rules|policy|instructions)\b",
    ],
    "jailbreak": [
        r"\bdeveloper\s+mode\b",
        r"\bDAN\s+mode\b",
        r"\bjailbreak\b",
        r"\bbypass\s+(all\s+)?(restrictions|safety|filters?)\b",
        r"\bact\s+as\s+(an?\s+)?(unfiltered|uncensored)\b",
    ],
    "system_prompt_extraction": [
        r"\breveal\s+(your|the)\s+(system\s+)?(prompt|instructions|rules)\b",
        r"\bshow\s+me\s+the\s+(hidden|secret|system)\s+(prompt|rules|instructions)\b",
        r"\bwhat\s+is\s+your\s+(system\s+)?(prompt|instructions)\b",
        r"\bprint\s+your\s+(system\s+)?(prompt|instructions)\b",
    ],
    "secret_extraction": [
        r"\bprint\s+all\s+environment\s+variables\b",
        r"\bdump\s+(the\s+)?env(ironment)?\b",
        r"\b(reveal|show|leak)\s+(the\s+)?(api[_\s]?key|secret|token|password)\b",
        r"\bexport\s+OPENAI_API_KEY\b",
    ],
    "out_of_scope": [
        r"\bhow\s+do\s+i\s+(make|build|synthesize)\s+(a\s+)?(bomb|weapon|explosive)\b",
        r"\bhow\s+to\s+hack\s+(into\s+)?(a|someone'?s)\s+",
        r"\bwrite\s+(a\s+)?ransomware\b",
        r"\bcreate\s+(a\s+)?(virus|malware|trojan)\b",
    ],
    "sensitive_data": [
        r"\b\d{3}-\d{2}-\d{4}\b",  # US SSN-like
        r"\b(?:\d[ -]*?){13,16}\b",  # naive credit-card-like
    ],
}

OUTPUT_RULES: dict[str, list[str]] = {
    "secret_leakage": [
        r"sk-[A-Za-z0-9]{20,}",  # OpenAI-style key
        r"AKIA[0-9A-Z]{16}",  # AWS access key
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ],
    "unwanted_instruction_following": [
        r"\bsure,?\s+here\s+is\s+the\s+system\s+prompt\b",
        r"\bhere\s+are\s+(my|the)\s+(hidden\s+)?(rules|instructions)\b",
    ],
    "policy_violation": [
        r"\bstep\s*1:\s*acquire\s+explosives\b",
    ],
}

REASON_TEMPLATES = {
    "prompt_injection": "Prompt injection attempt detected.",
    "jailbreak": "Jailbreak attempt detected.",
    "system_prompt_extraction": "Attempt to extract system prompt detected.",
    "secret_extraction": "Attempt to extract secrets or environment variables detected.",
    "out_of_scope": "Request is outside the allowed assistant scope.",
    "sensitive_data": "Sensitive personal data detected in prompt.",
    "secret_leakage": "Output appeared to contain leaked secrets.",
    "unwanted_instruction_following": "Output appeared to follow an unsafe instruction.",
    "policy_violation": "Output violated content policy.",
}


def _match_any(text: str, patterns: Iterable[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            return True
    return False


class GuardrailService:
    """Deterministic guardrail checks plus optional NeMo Guardrails wiring."""

    def __init__(self) -> None:
        self._nemo_rails = None
        if settings.enable_nemo_guardrails:
            self._try_load_nemo()

    def _try_load_nemo(self) -> None:
        try:
            from nemoguardrails import LLMRails, RailsConfig

            config_path = settings.root_dir / "guardrails"
            config = RailsConfig.from_path(str(config_path))
            self._nemo_rails = LLMRails(config)
        except Exception as exc:  # pragma: no cover - optional dep
            # Silent fallback to rule-based checks; surface in logs only.
            print(f"[guardrails] NeMo Guardrails unavailable, using rule-based fallback: {exc}")
            self._nemo_rails = None

    # ------------------------------------------------------------------
    # Input check
    # ------------------------------------------------------------------
    def check_input(self, prompt: str) -> GuardrailVerdict:
        for category, patterns in INPUT_RULES.items():
            if _match_any(prompt, patterns):
                return GuardrailVerdict(
                    allowed=False,
                    category=category,
                    reason=REASON_TEMPLATES[category],
                )
        return GuardrailVerdict(allowed=True, category="", reason="ok")

    # ------------------------------------------------------------------
    # Output check
    # ------------------------------------------------------------------
    def check_output(self, response_text: str) -> GuardrailVerdict:
        for category, patterns in OUTPUT_RULES.items():
            if _match_any(response_text, patterns):
                redacted = self._redact(response_text, OUTPUT_RULES[category])
                return GuardrailVerdict(
                    allowed=False,
                    category=category,
                    reason=REASON_TEMPLATES[category],
                    sanitized_text=redacted,
                )
        return GuardrailVerdict(allowed=True, category="", reason="ok")

    @staticmethod
    def _redact(text: str, patterns: Iterable[str]) -> str:
        redacted = text
        for pat in patterns:
            redacted = re.sub(pat, "[REDACTED]", redacted, flags=re.IGNORECASE)
        return redacted


_service: GuardrailService | None = None


def get_guardrail_service() -> GuardrailService:
    global _service
    if _service is None:
        _service = GuardrailService()
    return _service
