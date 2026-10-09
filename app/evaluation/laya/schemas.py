"""Structured schemas for the optional Laya local judge.

Deterministic evaluation remains authoritative. These models only carry
advisory local-decision output — yes/no probabilities, failure category,
severity — plus explicit status so callers can distinguish success from
graceful fallback. Model confidence is never treated as correctness.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LayaNoulDecision(BaseModel):
    prob_true: float = 0.0
    confidence: float = 0.0
    abstained: bool = False


class LayaChoiceDecision(BaseModel):
    choice: str = "none"
    probabilities: dict[str, float] = Field(default_factory=dict)
    confidence: float = 0.0
    abstained: bool = False


class LayaScoreDecision(BaseModel):
    level: str = "low"
    expected_level: float = 0.0
    probabilities: dict[str, float] = Field(default_factory=dict)
    confidence: float = 0.0
    abstained: bool = False


class LayaEvaluationResult(BaseModel):
    provider: str = "laya"
    model: str = ""
    # success | skipped_disabled | skipped_unavailable | error
    status: str = "success"
    # Advisory yes/no signals (P(true)).
    compliance_ok: LayaNoulDecision = Field(default_factory=LayaNoulDecision)
    policy_safe: LayaNoulDecision = Field(default_factory=LayaNoulDecision)
    grounded: LayaNoulDecision = Field(default_factory=LayaNoulDecision)
    # Advisory categorization / severity.
    failure_category: LayaChoiceDecision = Field(default_factory=LayaChoiceDecision)
    severity: LayaScoreDecision = Field(default_factory=LayaScoreDecision)
    overall_reasoning: str = ""
    # Machine-readable failure info when status != success.
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0
    model_used: str = ""
    fallback_note: str = (
        "Advisory only. Deterministic evaluation remains authoritative; "
        "model confidence is not correctness."
    )


class LayaStatus(BaseModel):
    enabled: bool
    available: bool
    provider: str = "laya"
    model: str = ""
    timeout_seconds: float = 60.0
    loaded: bool = False
    deterministic_fallback: bool = True


__all__ = [
    "LayaChoiceDecision",
    "LayaEvaluationResult",
    "LayaNoulDecision",
    "LayaScoreDecision",
    "LayaStatus",
]
