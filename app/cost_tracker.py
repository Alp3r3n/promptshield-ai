"""Token usage and cost estimation."""

from __future__ import annotations

# USD per 1K tokens. Approximate pricing — adjust to current rates as needed.
PRICING_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "mock-llm-1": {"input": 0.0, "output": 0.0},
}

DEFAULT_PRICE = {"input": 0.0005, "output": 0.0015}


def approx_tokens(text: str) -> int:
    """Cheap token estimator used when a provider does not report usage."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICING_PER_1K.get(model.lower(), DEFAULT_PRICE)
    cost = (input_tokens / 1000.0) * price["input"] + (output_tokens / 1000.0) * price["output"]
    return round(cost, 6)
