from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.evaluation.types import Constraint, ConstraintType, Dimension, Severity


class CriteriaValidators(BaseModel):
    """Shared field validators for test-case criteria."""

    @field_validator("enabled_dimensions", check_fields=False)
    @classmethod
    def _valid_dimensions(cls, value: list[str]) -> list[str]:
        allowed = {d.value for d in Dimension}
        invalid = [v for v in value if v not in allowed]
        if invalid:
            raise ValueError(
                f"unknown dimension(s) {invalid}; allowed: {sorted(allowed)}"
            )
        if not value:
            raise ValueError("enabled_dimensions must not be empty")
        return value

    @field_validator("thresholds", check_fields=False)
    @classmethod
    def _valid_thresholds(cls, value: dict[str, int]) -> dict[str, int]:
        allowed = {d.value for d in Dimension}
        for key, threshold in value.items():
            if key not in allowed:
                raise ValueError(f"unknown dimension '{key}' in thresholds")
            if not 0 <= int(threshold) <= 100:
                raise ValueError(f"threshold for '{key}' must be between 0 and 100")
        return value

    @field_validator("weights", check_fields=False)
    @classmethod
    def _valid_weights(cls, value: dict[str, float]) -> dict[str, float]:
        allowed = {d.value for d in Dimension}
        for key, weight in value.items():
            if key not in allowed:
                raise ValueError(f"unknown dimension '{key}' in weights")
            if float(weight) < 0:
                raise ValueError(f"weight for '{key}' must be non-negative")
        return value

    @field_validator("constraints", check_fields=False)
    @classmethod
    def _valid_constraints(cls, value: list[Constraint]) -> list[Constraint]:
        for constraint in value:
            needs_value = constraint.type in {
                ConstraintType.MAX_WORDS,
                ConstraintType.MIN_WORDS,
            }
            needs_phrases = constraint.type in {
                ConstraintType.MUST_INCLUDE,
                ConstraintType.MUST_EXCLUDE,
            }
            if needs_value and constraint.value is None:
                raise ValueError(
                    f"constraint '{constraint.type.value}' requires 'value'"
                )
            if needs_phrases and not constraint.phrases:
                raise ValueError(
                    f"constraint '{constraint.type.value}' requires 'phrases'"
                )
        return value


class TestCaseBase(CriteriaValidators):
    name: str = Field(min_length=3, max_length=200)
    description: str = ""
    agent_name: str = Field(default="", max_length=120)
    scenario_tags: list[str] = Field(default_factory=list)
    input_prompt: str = Field(min_length=1)
    expected_answer: str = Field(min_length=1)
    referenced_facts: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)
    forbidden_keywords: list[str] = Field(default_factory=list)
    expected_numbers: list[float] = Field(default_factory=list)
    require_disclaimer: bool = True
    constraints: list[Constraint] = Field(default_factory=list)
    thresholds: dict[str, int] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)
    enabled_dimensions: list[str] = Field(
        default_factory=lambda: [d.value for d in Dimension]
    )
    sample_good_response: str | None = None


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(CriteriaValidators):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    agent_name: str | None = None
    scenario_tags: list[str] | None = None
    input_prompt: str | None = None
    expected_answer: str | None = None
    referenced_facts: list[str] | None = None
    required_keywords: list[str] | None = None
    forbidden_keywords: list[str] | None = None
    expected_numbers: list[float] | None = None
    require_disclaimer: bool | None = None
    constraints: list[Constraint] | None = None
    thresholds: dict[str, int] | None = None
    weights: dict[str, float] | None = None
    enabled_dimensions: list[str] | None = None
    sample_good_response: str | None = None


class TestCaseRead(TestCaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class TestCaseListResponse(BaseModel):
    items: list[TestCaseRead]
    total: int
    limit: int
    offset: int