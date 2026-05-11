"""Provider-agnostic LLM interface and factory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str


class LLMProvider(Protocol):
    """Minimal contract every LLM provider must satisfy."""

    name: str

    def generate(self, prompt: str, model: str | None = None) -> LLMResult:
        ...


def get_provider(name: str) -> LLMProvider:
    """Factory that returns a provider by name.

    Falls back to the mock provider when no API key is configured for OpenAI.
    """
    from app.config import settings
    from app.mock_provider import MockProvider
    from app.openai_provider import OpenAIProvider

    name = (name or settings.llm_provider).lower()

    if name == "openai":
        if not settings.openai_api_key or settings.enable_mock_mode and not settings.openai_api_key:
            # Quietly fall back to mock so the project remains runnable without keys.
            return MockProvider()
        return OpenAIProvider()

    return MockProvider()
