"""Cost tracker unit tests."""

from __future__ import annotations

from app.cost_tracker import approx_tokens, estimate_cost_usd


def test_approx_tokens_handles_empty_string():
    assert approx_tokens("") == 0


def test_approx_tokens_returns_positive_for_text():
    assert approx_tokens("hello world") >= 1


def test_known_model_pricing_is_nonzero():
    cost = estimate_cost_usd("gpt-4o-mini", 1000, 1000)
    assert cost > 0


def test_unknown_model_falls_back_to_default_pricing():
    cost = estimate_cost_usd("some-other-model", 1000, 1000)
    assert cost > 0


def test_mock_model_is_free():
    assert estimate_cost_usd("mock-llm-1", 1000, 1000) == 0.0
