"""OpenAI / OpenAI-compatible LLM provider."""

from __future__ import annotations

from app.config import settings
from app.llm_provider import LLMResult


class OpenAIProvider:
    name = "openai"

    def __init__(self) -> None:
        from openai import OpenAI  # imported lazily to keep mock mode dependency-light

        kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        self._client = OpenAI(**kwargs)
        self.default_model = settings.openai_model

    def generate(self, prompt: str, model: str | None = None) -> LLMResult:
        chosen_model = model or self.default_model
        completion = self._client.chat.completions.create(
            model=chosen_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant for technical, programming, and AI questions. "
                        "Refuse unsafe, malicious, or out-of-scope requests."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        choice = completion.choices[0].message.content or ""
        usage = getattr(completion, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return LLMResult(
            text=choice,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            model=chosen_model,
            provider=self.name,
        )
