"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ProviderName = Literal["mock", "openai"]
GuardrailStatus = Literal["allowed", "blocked", "modified", "error"]


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    prompt: str = Field(..., min_length=1, max_length=8000)
    provider: ProviderName = "mock"
    model: Optional[str] = None


class ChatResponse(BaseModel):
    status: GuardrailStatus
    guardrail_reason: str = ""
    response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    provider: str = "mock"
    model: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    provider: str
    mock_mode: bool
    nemo_enabled: bool


class LogEntry(BaseModel):
    id: int
    timestamp: str
    user_id: str
    provider: str
    model: str
    prompt: str
    status: GuardrailStatus
    guardrail_reason: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
