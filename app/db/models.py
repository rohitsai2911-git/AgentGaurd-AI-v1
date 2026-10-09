from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------
# Multi-tenancy: users own workspaces; every data row is workspace-scoped
# --------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspaces: Mapped[list[Workspace]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="My Workspace")
    owner_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    owner: Mapped[User] = relationship(back_populates="workspaces")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    agent_name: Mapped[str] = mapped_column(String(120), default="")
    scenario_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    input_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    referenced_facts: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    forbidden_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    expected_numbers: Mapped[list[float]] = mapped_column(JSON, default=list)
    require_disclaimer: Mapped[bool] = mapped_column(Boolean, default=True)
    constraints: Mapped[list[dict]] = mapped_column(JSON, default=list)
    thresholds: Mapped[dict] = mapped_column(JSON, default=dict)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled_dimensions: Mapped[list[str]] = mapped_column(JSON, default=list)
    sample_good_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    runs: Mapped[list[EvaluationRun]] = relationship(
        back_populates="test_case", cascade="all, delete-orphan"
    )
    suite_links: Mapped[list[SuiteTestCase]] = relationship(
        back_populates="test_case", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_test_case_workspace_name"),
        Index("ix_test_cases_agent_name", "agent_name"),
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False
    )
    responses: Mapped[list[str]] = mapped_column(JSON, default=list)
    dimension_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_score: Mapped[int] = mapped_column(Integer, default=0)
    verdict: Mapped[str] = mapped_column(String(16), default="fail")
    max_severity: Mapped[str] = mapped_column(String(16), default="none")
    finding_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    test_case: Mapped[TestCase] = relationship(back_populates="runs")

    __table_args__ = (
        Index("ix_evaluation_runs_test_case_id", "test_case_id"),
        Index("ix_evaluation_runs_created_at", "created_at"),
        Index("ix_evaluation_runs_verdict", "verdict"),
    )


class TestSuite(Base):
    __tablename__ = "test_suites"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    test_cases: Mapped[list[SuiteTestCase]] = relationship(
        back_populates="suite",
        cascade="all, delete-orphan",
        order_by="SuiteTestCase.position",
    )
    executions: Mapped[list[SuiteExecution]] = relationship(
        back_populates="suite", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_suite_workspace_name"),
    )


class SuiteTestCase(Base):
    __tablename__ = "suite_test_cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    suite_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False
    )
    test_case_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0)

    suite: Mapped[TestSuite] = relationship(back_populates="test_cases")
    test_case: Mapped[TestCase] = relationship(back_populates="suite_links")

    __table_args__ = (
        UniqueConstraint("suite_id", "test_case_id", name="uq_suite_test_case"),
        Index("ix_suite_test_cases_suite_id", "suite_id"),
    )


class SuiteExecution(Base):
    __tablename__ = "suite_executions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suite_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False
    )
    suite_name: Mapped[str] = mapped_column(String(200), default="")
    agent_name: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    evaluated_cases: Mapped[int] = mapped_column(Integer, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0)
    skipped_cases: Mapped[int] = mapped_column(Integer, default=0)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    verdict: Mapped[str] = mapped_column(String(16), default="fail")
    max_severity: Mapped[str] = mapped_column(String(16), default="none")
    failure_categories: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    suite: Mapped[TestSuite] = relationship(back_populates="executions")
    results: Mapped[list[SuiteCaseResult]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_suite_executions_suite_id", "suite_id"),
        Index("ix_suite_executions_created_at", "created_at"),
    )


class SuiteCaseResult(Base):
    __tablename__ = "suite_case_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    suite_execution_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("suite_executions.id", ondelete="CASCADE"), nullable=False
    )
    test_case_id: Mapped[str] = mapped_column(String(32), nullable=False)
    test_case_name: Mapped[str] = mapped_column(String(200), default="")
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="evaluated")
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    overall_score: Mapped[int] = mapped_column(Integer, default=0)
    max_severity: Mapped[str] = mapped_column(String(16), default="none")
    failure_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    execution: Mapped[SuiteExecution] = relationship(back_populates="results")

    __table_args__ = (
        Index("ix_suite_case_results_execution_id", "suite_execution_id"),
    )