from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    TestCaseConflictError,
    TestCaseHasRunsError,
    TestCaseNotFoundError,
)
from app.db.models import EvaluationRun, TestCase
from app.evaluation.types import Constraint, TestCaseCriteria
from app.schemas.test_case import TestCaseCreate, TestCaseUpdate

logger = logging.getLogger(__name__)

_CRITERIA_FIELDS = (
    "name",
    "description",
    "agent_name",
    "scenario_tags",
    "input_prompt",
    "expected_answer",
    "referenced_facts",
    "required_keywords",
    "forbidden_keywords",
    "expected_numbers",
    "require_disclaimer",
    "constraints",
    "thresholds",
    "weights",
    "enabled_dimensions",
    "sample_good_response",
)


def to_criteria(model: TestCase) -> TestCaseCriteria:
    """The single database-to-evaluation boundary."""
    return TestCaseCriteria(
        id=model.id,
        name=model.name,
        agent_name=model.agent_name or "",
        scenario_tags=list(model.scenario_tags or []),
        input_prompt=model.input_prompt,
        expected_answer=model.expected_answer,
        referenced_facts=list(model.referenced_facts or []),
        required_keywords=list(model.required_keywords or []),
        forbidden_keywords=list(model.forbidden_keywords or []),
        expected_numbers=[float(n) for n in (model.expected_numbers or [])],
        require_disclaimer=bool(model.require_disclaimer),
        constraints=[Constraint(**c) for c in (model.constraints or [])],
        thresholds=dict(model.thresholds or {}),
        weights=dict(model.weights or {}),
        enabled_dimensions=list(model.enabled_dimensions or []),
    )


def create(session: Session, payload: TestCaseCreate, workspace_id: str) -> TestCase:
    existing = session.scalar(
        select(TestCase).where(
            TestCase.name == payload.name,
            TestCase.workspace_id == workspace_id,
        )
    )
    if existing is not None:
        raise TestCaseConflictError(
            f"A test case named '{payload.name}' already exists.",
            details={"name": payload.name},
        )

    model = TestCase(
        workspace_id=workspace_id,
        **payload.model_dump(exclude={"constraints"}),
        constraints=[c.model_dump(mode="json") for c in payload.constraints],
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    logger.info("Created test case %s (%s)", model.id, model.name)
    return model


def get(session: Session, test_case_id: str, workspace_id: str) -> TestCase:
    model = session.get(TestCase, test_case_id)
    if model is None or model.workspace_id != workspace_id:
        raise TestCaseNotFoundError(
            f"Test case '{test_case_id}' does not exist.",
            details={"test_case_id": test_case_id},
        )
    return model


def get_by_name(session: Session, name: str, workspace_id: str) -> TestCase | None:
    return session.scalar(
        select(TestCase).where(
            TestCase.name == name,
            TestCase.workspace_id == workspace_id,
        )
    )


def list_all(
    session: Session,
    workspace_id: str,
    limit: int = 50,
    offset: int = 0,
    tag: str | None = None,
    agent_name: str | None = None,
) -> tuple[list[TestCase], int]:
    stmt = select(TestCase).where(TestCase.workspace_id == workspace_id)
    count_stmt = (
        select(func.count()).select_from(TestCase).where(TestCase.workspace_id == workspace_id)
    )
    if tag:
        stmt = stmt.where(TestCase.scenario_tags.contains([tag]))
        count_stmt = count_stmt.where(TestCase.scenario_tags.contains([tag]))
    if agent_name:
        stmt = stmt.where(TestCase.agent_name == agent_name)
        count_stmt = count_stmt.where(TestCase.agent_name == agent_name)

    total = session.scalar(count_stmt) or 0
    items = list(
        session.scalars(stmt.order_by(TestCase.created_at.desc()).limit(limit).offset(offset))
    )
    return items, total


def update(
    session: Session, test_case_id: str, payload: TestCaseUpdate, workspace_id: str
) -> TestCase:
    model = get(session, test_case_id, workspace_id)
    data = payload.model_dump(exclude_unset=True, exclude={"constraints"})

    if "name" in data and data["name"] != model.name:
        clash = session.scalar(
            select(TestCase).where(
                TestCase.name == data["name"],
                TestCase.id != model.id,
                TestCase.workspace_id == workspace_id,
            )
        )
        if clash is not None:
            raise TestCaseConflictError(
                f"A test case named '{data['name']}' already exists.",
                details={"name": data["name"]},
            )

    for field in _CRITERIA_FIELDS:
        if field in data:
            setattr(model, field, data[field])

    if "constraints" in payload.model_fields_set and payload.constraints is not None:
        model.constraints = [c.model_dump(mode="json") for c in payload.constraints]

    session.commit()
    session.refresh(model)
    logger.info("Updated test case %s", model.id)
    return model


def delete(session: Session, test_case_id: str, workspace_id: str) -> None:
    model = get(session, test_case_id, workspace_id)
    run_count = session.scalar(
        select(func.count()).select_from(EvaluationRun).where(EvaluationRun.test_case_id == model.id)
    )
    if run_count:
        raise TestCaseHasRunsError(
            f"Test case '{model.name}' has {run_count} stored run(s) and cannot be deleted.",
            details={"test_case_id": model.id, "runs": run_count},
        )
    session.delete(model)
    session.commit()
    logger.info("Deleted test case %s", test_case_id)


def count(session: Session, workspace_id: str) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(TestCase).where(TestCase.workspace_id == workspace_id)
        )
        or 0
    )