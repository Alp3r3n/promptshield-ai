"""Run the safe and unsafe prompt suites against the guardrail service."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAFE_PATH = ROOT / "examples" / "safe_prompts.json"
UNSAFE_PATH = ROOT / "examples" / "unsafe_prompts.json"


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_minimum_corpus_size():
    safe = _load(SAFE_PATH)
    unsafe = _load(UNSAFE_PATH)
    assert len(safe) >= 10
    assert len(unsafe) >= 10


@pytest.mark.parametrize("prompt", _load(SAFE_PATH))
def test_safe_prompts_pass_input_check(prompt):
    from app.guardrail_service import get_guardrail_service

    verdict = get_guardrail_service().check_input(prompt)
    assert verdict.allowed is True, f"Safe prompt was blocked: {prompt!r} ({verdict.reason})"


@pytest.mark.parametrize("entry", _load(UNSAFE_PATH))
def test_unsafe_prompts_are_blocked(entry):
    from app.guardrail_service import get_guardrail_service

    verdict = get_guardrail_service().check_input(entry["prompt"])
    assert verdict.allowed is False, f"Unsafe prompt slipped through: {entry['prompt']!r}"
    assert verdict.category == entry["expected_category"], (
        f"Wrong category for {entry['prompt']!r}: "
        f"expected {entry['expected_category']}, got {verdict.category}"
    )
