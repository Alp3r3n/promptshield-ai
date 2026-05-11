"""Deterministic mock LLM provider for development and testing."""

from __future__ import annotations

from app.llm_provider import LLMResult


def _approx_tokens(text: str) -> int:
    """Rough word-based token approximation (~1 token / 4 chars)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


class MockProvider:
    name = "mock"

    def __init__(self, model: str = "mock-llm-1") -> None:
        self.default_model = model

    def generate(self, prompt: str, model: str | None = None) -> LLMResult:
        chosen_model = model or self.default_model
        lowered = prompt.lower().strip()

        if "cuda" in lowered:
            text = (
                "[mock] A CUDA kernel launch dispatches a grid of thread blocks to the GPU. "
                "Each block runs in a streaming multiprocessor and threads execute the kernel "
                "function in parallel. Use <<<grid, block>>> syntax in C++ or torch.cuda APIs in Python."
            )
        elif "fastapi" in lowered:
            text = (
                "[mock] A clean FastAPI project usually splits routes, schemas, services, and "
                "config into separate modules and uses Pydantic models for request validation."
            )
        elif "prompt injection" in lowered:
            text = (
                "[mock] Prompt injection is when untrusted input manipulates an LLM into ignoring "
                "its instructions. Defenses include input filtering, output checking, and tools "
                "like NVIDIA NeMo Guardrails."
            )
        elif "pandas" in lowered:
            text = (
                "[mock] You can analyze logs in pandas by loading them with read_csv, parsing "
                "timestamps, then using groupby and value_counts to summarize."
            )
        elif "numpy" in lowered or "cupy" in lowered:
            text = (
                "[mock] NumPy runs on CPU; CuPy provides a NumPy-compatible API that runs on "
                "NVIDIA GPUs via CUDA, giving large speedups on array workloads."
            )
        else:
            text = (
                "[mock] This is a deterministic mock response generated locally. "
                "Set LLM_PROVIDER=openai and OPENAI_API_KEY to use a real model."
            )

        return LLMResult(
            text=text,
            input_tokens=_approx_tokens(prompt),
            output_tokens=_approx_tokens(text),
            model=chosen_model,
            provider=self.name,
        )
