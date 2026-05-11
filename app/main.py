"""FastAPI entry point for PromptShield AI."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import database, logger
from app.config import settings
from app.cost_tracker import approx_tokens, estimate_cost_usd
from app.guardrail_service import get_guardrail_service
from app.llm_provider import get_provider
from app.schemas import ChatRequest, ChatResponse, HealthResponse


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.init_db()
    yield


app = FastAPI(
    title="PromptShield AI",
    description="LLM security gateway with input/output guardrails and cost tracking.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        provider=settings.llm_provider,
        mock_mode=settings.enable_mock_mode,
        nemo_enabled=settings.enable_nemo_guardrails,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    guardrails = get_guardrail_service()

    # 1. Input check
    input_verdict = guardrails.check_input(req.prompt)
    if not input_verdict.allowed:
        in_tokens = approx_tokens(req.prompt)
        entry = {
            "user_id": req.user_id,
            "provider": req.provider,
            "model": req.model or "",
            "prompt": req.prompt,
            "status": "blocked",
            "guardrail_reason": f"input/{input_verdict.category}: {input_verdict.reason}",
            "input_tokens": in_tokens,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "response": "",
        }
        logger.log_request(entry)
        return ChatResponse(
            status="blocked",
            guardrail_reason=entry["guardrail_reason"],
            response="",
            input_tokens=in_tokens,
            output_tokens=0,
            estimated_cost_usd=0.0,
            provider=req.provider,
            model=req.model or "",
        )

    # 2. LLM call
    try:
        provider = get_provider(req.provider)
        llm_result = provider.generate(req.prompt, model=req.model)
    except Exception as exc:  # network / auth errors
        entry = {
            "user_id": req.user_id,
            "provider": req.provider,
            "model": req.model or "",
            "prompt": req.prompt,
            "status": "error",
            "guardrail_reason": f"provider_error: {exc}",
            "input_tokens": approx_tokens(req.prompt),
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "response": "",
        }
        logger.log_request(entry)
        raise HTTPException(status_code=502, detail=f"LLM provider failed: {exc}") from exc

    # 3. Output check
    output_verdict = guardrails.check_output(llm_result.text)

    if not output_verdict.allowed:
        sanitized = output_verdict.sanitized_text or ""
        cost = (
            estimate_cost_usd(llm_result.model, llm_result.input_tokens, llm_result.output_tokens)
            if settings.enable_cost_tracking
            else 0.0
        )
        entry = {
            "user_id": req.user_id,
            "provider": llm_result.provider,
            "model": llm_result.model,
            "prompt": req.prompt,
            "status": "modified",
            "guardrail_reason": f"output/{output_verdict.category}: {output_verdict.reason}",
            "input_tokens": llm_result.input_tokens,
            "output_tokens": llm_result.output_tokens,
            "estimated_cost_usd": cost,
            "response": sanitized,
        }
        logger.log_request(entry)
        return ChatResponse(
            status="modified",
            guardrail_reason=entry["guardrail_reason"],
            response=sanitized,
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
            estimated_cost_usd=cost,
            provider=llm_result.provider,
            model=llm_result.model,
        )

    # 4. Allowed path
    cost = (
        estimate_cost_usd(llm_result.model, llm_result.input_tokens, llm_result.output_tokens)
        if settings.enable_cost_tracking
        else 0.0
    )
    entry = {
        "user_id": req.user_id,
        "provider": llm_result.provider,
        "model": llm_result.model,
        "prompt": req.prompt,
        "status": "allowed",
        "guardrail_reason": "",
        "input_tokens": llm_result.input_tokens,
        "output_tokens": llm_result.output_tokens,
        "estimated_cost_usd": cost,
        "response": llm_result.text,
    }
    logger.log_request(entry)
    return ChatResponse(
        status="allowed",
        guardrail_reason="",
        response=llm_result.text,
        input_tokens=llm_result.input_tokens,
        output_tokens=llm_result.output_tokens,
        estimated_cost_usd=cost,
        provider=llm_result.provider,
        model=llm_result.model,
    )


@app.get("/logs/recent")
def logs_recent(limit: int = 50) -> list[dict]:
    """Helper endpoint used by the dashboard / scripts."""
    limit = max(1, min(limit, 500))
    return database.fetch_recent(limit)
