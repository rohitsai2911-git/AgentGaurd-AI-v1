from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.evaluation.types import EvaluationReport, RunVerdict, Severity


class EvaluationRequest(BaseModel):
    test_case_id: str
    responses: list[str] = Field(min_length=1, max_length=25)
    persist: bool = True
    # Optional LLM judge. False by default so runs stay free/offline.
    # When True without OPENROUTER_API_KEY, deterministic report returns
    # with llm_evaluation.status = skipped_no_key (never fails).
    use_llm: bool = False
    llm_model: str | None = None
    # Optional Laya local judge. False by default so runs stay deterministic-only.
    # When True without LAYA_ENABLED, report returns laya_evaluation.status =
    # skipped_disabled (never fails).
    use_laya: bool = False

    @model_validator(mode="after")
    def _non_empty_responses(self) -> "EvaluationRequest":
        cleaned = [r for r in (resp.strip() for resp in self.responses) if r]
        if not cleaned:
            raise ValueError("responses must contain at least one non-empty string")
        self.responses = cleaned
        return self


class PreviewRequest(BaseModel):
    test_case_id: str
    responses: list[str] = Field(min_length=1, max_length=25)
    use_llm: bool = False
    llm_model: str | None = None
    use_laya: bool = False

    @model_validator(mode="after")
    def _non_empty_responses(self) -> "PreviewRequest":
        cleaned = [r for r in (resp.strip() for resp in self.responses) if r]
        if not cleaned:
            raise ValueError("responses must contain at least one non-empty string")
        self.responses = cleaned
        return self


class RunSummary(BaseModel):
    id: str
    test_case_id: str
    test_case_name: str
    agent_name: str
    overall_score: int
    verdict: RunVerdict
    max_severity: Severity
    responses_submitted: int
    duration_ms: int
    created_at: datetime


class RunListResponse(BaseModel):
    items: list[RunSummary]
    total: int
    limit: int
    offset: int


class RunDetail(RunSummary):
    dimension_scores: dict[str, int]
    finding_counts: dict[str, int]
    report: EvaluationReport