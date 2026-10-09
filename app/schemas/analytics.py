from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.evaluation.types import Severity


class OverviewStats(BaseModel):
    total_test_cases: int
    total_runs: int
    total_suites: int
    total_suite_executions: int
    pass_rate: float
    fail_rate: float
    average_overall_score: float
    best_overall_score: int
    worst_overall_score: int
    suite_pass_rate: float


class DimensionAggregate(BaseModel):
    dimension: str
    average_score: float
    pass_rate: float
    failure_count: int


class FailureCategoryAggregate(BaseModel):
    category: str
    count: int
    percentage: float


class TopRule(BaseModel):
    rule_id: str
    count: int
    verification: str
    worst_severity: Severity


class TrendPoint(BaseModel):
    bucket: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    average_score: float
    max_severity: Severity


class TrendResponse(BaseModel):
    granularity: Literal["day", "hour"]
    test_case_id: str | None = None
    suite_id: str | None = None
    points: list[TrendPoint]
    total_points: int


class FailureBreakdown(BaseModel):
    by_category: list[FailureCategoryAggregate]
    by_severity: dict[str, int]
    by_dimension: list[DimensionAggregate]
    top_rules: list[TopRule]
    critical_findings: int
    verified_findings: int
    risk_findings: int


class ScoreDelta(BaseModel):
    label: str
    overall_score: float
    verdict: str
    passed: int
    failed: int
    total: int


class ComparisonResponse(BaseModel):
    kind: Literal["runs", "suite_executions"]
    a: ScoreDelta
    b: ScoreDelta
    score_delta: float
    verdict_changed: bool
    regression: bool
    per_dimension_delta: dict[str, float]
    findings_delta: dict[str, int]
    new_rules: list[str]
    resolved_rules: list[str]


class AnalyticsQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=500)
    days: int = Field(default=30, ge=1, le=365)


class ExportMeta(BaseModel):
    generated_at: datetime
    platform: str
    version: str
    kind: Literal["run", "suite_execution", "analytics"]