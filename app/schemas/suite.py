from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.evaluation.failure_intel import FailureReport
from app.evaluation.types import EvaluationReport, RunVerdict, Severity


class SuiteCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    test_case_ids: list[str] = Field(default_factory=list)


class SuiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    tags: list[str] | None = None


class SuiteTestCaseRef(BaseModel):
    test_case_id: str
    test_case_name: str
    position: int


class SuiteRead(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str]
    test_cases: list[SuiteTestCaseRef]
    test_case_count: int
    created_at: datetime
    updated_at: datetime


class SuiteListResponse(BaseModel):
    items: list[SuiteRead]
    total: int


class AddTestCasesRequest(BaseModel):
    test_case_ids: list[str] = Field(min_length=1)


class SuiteExecuteRequest(BaseModel):
    """Agent responses keyed by test-case id or test-case name.

    Cases absent from this mapping are recorded as ``skipped``; they are never
    counted as passes and never silently reported as success.
    """

    responses: dict[str, list[str]] = Field(default_factory=dict)
    agent_name: str = ""
    persist: bool = True

    @model_validator(mode="after")
    def _clean_responses(self) -> "SuiteExecuteRequest":
        cleaned: dict[str, list[str]] = {}
        for key, value in self.responses.items():
            entries = [r for r in (v.strip() for v in value) if r]
            if entries:
                cleaned[key.strip()] = entries
        self.responses = cleaned
        return self


class SuiteCaseResultRead(BaseModel):
    test_case_id: str
    test_case_name: str
    run_id: str | None
    status: Literal["evaluated", "skipped", "error"]
    passed: bool
    overall_score: int
    max_severity: Severity
    failure_categories: list[str]
    duration_ms: int


class SuiteExecutionRead(BaseModel):
    id: str
    suite_id: str
    suite_name: str
    agent_name: str
    status: Literal["completed", "partial", "failed"]
    started_at: datetime | None
    completed_at: datetime | None
    total_cases: int
    evaluated_cases: int
    passed_cases: int
    failed_cases: int
    skipped_cases: int
    overall_score: float
    verdict: RunVerdict
    max_severity: Severity
    failure_categories: dict[str, int]
    duration_ms: int
    created_at: datetime


class SuiteExecutionDetail(SuiteExecutionRead):
    results: list[SuiteCaseResultRead]
    failure_intelligence: FailureReport
    report: dict


class SuiteExecutionListResponse(BaseModel):
    items: list[SuiteExecutionRead]
    total: int
    limit: int
    offset: int