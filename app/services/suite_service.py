from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import SuiteConflictError, SuiteNotFoundError
from app.db.models import SuiteTestCase, TestCase, TestSuite
from app.schemas.suite import SuiteCreate, SuiteRead, SuiteTestCaseRef, SuiteUpdate
from app.services import test_case_service

logger = logging.getLogger(__name__)


def to_read(suite: TestSuite) -> SuiteRead:
    refs = [
        SuiteTestCaseRef(
            test_case_id=link.test_case_id,
            test_case_name=link.test_case.name if link.test_case else "",
            position=link.position,
        )
        for link in suite.test_cases
    ]
    return SuiteRead(
        id=suite.id,
        name=suite.name,
        description=suite.description or "",
        tags=list(suite.tags or []),
        test_cases=refs,
        test_case_count=len(refs),
        created_at=suite.created_at,
        updated_at=suite.updated_at,
    )


def create(session: Session, payload: SuiteCreate, workspace_id: str) -> TestSuite:
    if session.scalar(
        select(TestSuite).where(
            TestSuite.name == payload.name,
            TestSuite.workspace_id == workspace_id,
        )
    ):
        raise SuiteConflictError(
            f"A test suite named '{payload.name}' already exists.",
            details={"name": payload.name},
        )

    suite = TestSuite(
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
        tags=list(payload.tags),
    )
    session.add(suite)
    session.commit()

    if payload.test_case_ids:
        _attach(session, suite, payload.test_case_ids, workspace_id)

    session.refresh(suite)
    logger.info("Created suite %s (%s) with %d test case(s)", suite.id, suite.name, len(suite.test_cases))
    return suite


def get(session: Session, suite_id: str, workspace_id: str) -> TestSuite:
    suite = session.get(TestSuite, suite_id)
    if suite is None or suite.workspace_id != workspace_id:
        raise SuiteNotFoundError(
            f"Test suite '{suite_id}' does not exist.", details={"suite_id": suite_id}
        )
    return suite


def get_by_name(session: Session, name: str, workspace_id: str) -> TestSuite | None:
    return session.scalar(
        select(TestSuite).where(
            TestSuite.name == name,
            TestSuite.workspace_id == workspace_id,
        )
    )


def list_all(session: Session, workspace_id: str) -> list[TestSuite]:
    return list(
        session.scalars(
            select(TestSuite)
            .where(TestSuite.workspace_id == workspace_id)
            .order_by(TestSuite.created_at.desc())
        )
    )


def update(
    session: Session, suite_id: str, payload: SuiteUpdate, workspace_id: str
) -> TestSuite:
    suite = get(session, suite_id, workspace_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != suite.name:
        clash = session.scalar(
            select(TestSuite).where(
                TestSuite.name == data["name"],
                TestSuite.id != suite.id,
                TestSuite.workspace_id == workspace_id,
            )
        )
        if clash is not None:
            raise SuiteConflictError(
                f"A test suite named '{data['name']}' already exists.",
                details={"name": data["name"]},
            )
    for field, value in data.items():
        setattr(suite, field, value)
    session.commit()
    session.refresh(suite)
    return suite


def delete(session: Session, suite_id: str, workspace_id: str) -> None:
    suite = get(session, suite_id, workspace_id)
    session.delete(suite)
    session.commit()
    logger.info("Deleted suite %s", suite_id)


def _attach(
    session: Session, suite: TestSuite, test_case_ids: list[str], workspace_id: str
) -> int:
    existing = {link.test_case_id for link in suite.test_cases}
    position = max((link.position for link in suite.test_cases), default=-1) + 1
    added = 0
    for test_case_id in test_case_ids:
        if test_case_id in existing:
            continue
        test_case_service.get(session, test_case_id, workspace_id)  # 404s on unknown/foreign id
        session.add(
            SuiteTestCase(suite_id=suite.id, test_case_id=test_case_id, position=position)
        )
        position += 1
        added += 1
    session.commit()
    session.refresh(suite)
    return added


def add_test_cases(
    session: Session, suite_id: str, test_case_ids: list[str], workspace_id: str
) -> TestSuite:
    suite = get(session, suite_id, workspace_id)
    added = _attach(session, suite, test_case_ids, workspace_id)
    logger.info("Added %d test case(s) to suite %s", added, suite_id)
    session.refresh(suite)
    return suite


def remove_test_case(
    session: Session, suite_id: str, test_case_id: str, workspace_id: str
) -> TestSuite:
    suite = get(session, suite_id, workspace_id)
    link = session.scalar(
        select(SuiteTestCase).where(
            SuiteTestCase.suite_id == suite_id,
            SuiteTestCase.test_case_id == test_case_id,
        )
    )
    if link is None:
        raise SuiteNotFoundError(
            "Test case is not a member of this suite.",
            details={"suite_id": suite_id, "test_case_id": test_case_id},
        )
    session.delete(link)
    session.commit()
    session.refresh(suite)
    return suite


def resolve_cases(session: Session, suite: TestSuite) -> list[TestCase]:
    """Suite membership in declared order, skipping links whose case vanished."""
    cases: list[TestCase] = []
    for link in suite.test_cases:
        case = session.get(TestCase, link.test_case_id)
        if case is not None:
            cases.append(case)
    return cases


def count(session: Session, workspace_id: str) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(TestSuite).where(TestSuite.workspace_id == workspace_id)
        )
        or 0
    )