"""Structured schemas for the optional LLM judge.

Deterministic evaluation remains authoritative. These models only carry
advisory LLM output — scores, reasoning, issues, recommendations — plus
explicit status so callers can distinguish success from graceful fallback.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LLMDimensionAssessment(BaseModel):
    score: int = Field(ge=0, le=100)
    reasoning: str = ""
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class LLMEvaluationResult(BaseModel):
    provider: str = "openrouter"
    model: str = ""
    # success | skipped_no_key | error (api/timeout/rate_limit/invalid_response/...)
    status: str = "success"
    # Overall advisory text across dimensions.
    overall_reasoning: str = ""
    dimensions: dict[str, LLMDimensionAssessment] = Field(default_factory=dict)
    # Machine-readable failure info when status != success. Never contains key.
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0
    # Raw model name actually used (after override resolution).
    model_used: str = ""
    fallback_note: str = (
        "Advisory only. Deterministic evaluation remains authoritative."
    )


class LLMStatus(BaseModel):
    configured: bool
    provider: Literal["openrouter"] = "openrouter"
    model: str
    base_url: str
    timeout_seconds: float
    # Never expose key. Only shape hint.
    key_hint: str = ""
    deterministic_fallback: bool = True


__all__ = [
    "LLMDimensionAssessment",
    "LLMEvaluationResult",
    "LLMStatus",
]
