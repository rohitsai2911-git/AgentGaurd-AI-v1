from __future__ import annotations

from pydantic import BaseModel, Field

from app.evaluation.types import Severity


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str | None = None


class HealthStatus(BaseModel):
    status: str
    name: str
    version: str
    database: str
    database_ok: bool
    test_cases: int | None = None
    runs: int | None = None
    suites: int | None = None
    stage: str = "1-2"


class Page(BaseModel):
    limit: int = 50
    offset: int = 0
    total: int = 0


class SeverityCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    total: int = 0

    @classmethod
    def from_mapping(cls, mapping: dict) -> "SeverityCounts":
        return cls(
            critical=mapping.get("critical", 0),
            high=mapping.get("high", 0),
            medium=mapping.get("medium", 0),
            low=mapping.get("low", 0),
            info=mapping.get("info", 0),
            total=mapping.get("total", 0),
        )


class SeverityCountsOut(SeverityCounts):
    none_: int = Field(0, alias="none")

    model_config = {"populate_by_name": True}


ALL_SEVERITIES = [s.value for s in Severity]