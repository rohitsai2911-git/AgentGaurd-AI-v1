from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, workspace_id
from app.core.exceptions import SuiteExecutionNotFoundError
from app.db.models import SuiteExecution
from app.evaluation.types import RunVerdict, Severity
from app.schemas.suite import (
    AddTestCasesRequest,
    SuiteCreate,
    SuiteExecuteRequest,
    SuiteExecutionDetail,
    SuiteExecutionListResponse,
    SuiteExecutionRead,
    SuiteListResponse,
    SuiteRead,
    SuiteUpdate,
)
from app.services import orchestrator, suite_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/suites", tags=["suites"])


@router.post("", response_model=SuiteRead, status_code=status.HTTP_201_CREATED, summary="Create a test suite")
def create(payload: SuiteCreate, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return suite_service.to_read(suite_service.create(session, payload, ws))


@router.get("", response_model=SuiteListResponse, summary="List test suites")
def list_suites(session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    suites = suite_service.list_all(session, ws)
    return {"items": [suite_service.to_read(s) for s in suites], "total": len(suites)}


@router.get("/{suite_id}", response_model=SuiteRead, summary="Get a test suite")
def get_suite(suite_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return suite_service.to_read(suite_service.get(session, suite_id, ws))


@router.patch("/{suite_id}", response_model=SuiteRead, summary="Update a test suite")
def update_suite(suite_id: str, payload: SuiteUpdate, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return suite_service.to_read(suite_service.update(session, suite_id, payload, ws))


@router.delete(
    "/{suite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a test suite and its execution history",
)
def delete_suite(suite_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    suite_service.delete(session, suite_id, ws)


@router.post(
    "/{suite_id}/test-cases",
    response_model=SuiteRead,
    summary="Add test cases to a suite",
)
def add_test_cases(
    suite_id: str, payload: AddTestCasesRequest, session: Session = Depends(db_session), ws: str = Depends(workspace_id)
):
    return suite_service.to_read(
        suite_service.add_test_cases(session, suite_id, payload.test_case_ids, ws)
    )


@router.delete(
    "/{suite_id}/test-cases/{test_case_id}",
    response_model=SuiteRead,
    summary="Remove a test case from a suite",
)
def remove_test_case(suite_id: str, test_case_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return suite_service.to_read(
        suite_service.remove_test_case(session, suite_id, test_case_id, ws)
    )


@router.post(
    "/{suite_id}/execute",
    response_model=SuiteExecutionDetail,
    summary="Execute every test case in the suite",
)
def execute(suite_id: str, payload: SuiteExecuteRequest, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    suite = suite_service.get(session, suite_id, ws)
    execution = orchestrator.execute_suite(session, suite, payload)
    return _to_detail(execution)


@router.get(
    "/executions/all",
    response_model=SuiteExecutionListResponse,
    summary="All suite executions across suites",
)
def all_executions(
    session: Session = Depends(db_session),
    ws: str = Depends(workspace_id),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    total = (
        session.scalar(
            select(func.count()).select_from(SuiteExecution).where(SuiteExecution.workspace_id == ws)
        )
        or 0
    )
    items = list(
        session.scalars(
            select(SuiteExecution)
            .where(SuiteExecution.workspace_id == ws)
            .order_by(SuiteExecution.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return {
        "items": [_to_read(i) for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{suite_id}/executions",
    response_model=SuiteExecutionListResponse,
    summary="Execution history for one suite",
)
def suite_executions(
    suite_id: str,
    session: Session = Depends(db_session),
    ws: str = Depends(workspace_id),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    suite_service.get(session, suite_id, ws)
    total = (
        session.scalar(
            select(func.count())
            .select_from(SuiteExecution)
            .where(SuiteExecution.suite_id == suite_id)
        )
        or 0
    )
    items = list(
        session.scalars(
            select(SuiteExecution)
            .where(SuiteExecution.suite_id == suite_id)
            .order_by(SuiteExecution.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return {
        "items": [_to_read(i) for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/executions/{execution_id}",
    response_model=SuiteExecutionDetail,
    summary="Get one suite execution",
)
def get_execution(execution_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return _to_detail(_get_execution(session, execution_id, ws))


@router.get(
    "/executions/{execution_id}/report",
    summary="Full stored JSON suite execution report",
)
def get_execution_report(execution_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    execution = _get_execution(session, execution_id, ws)
    return execution.report or {}


@router.get(
    "/executions/{execution_id}/export",
    summary="Download the suite execution report as JSON",
)
def export_execution(execution_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    from fastapi.responses import JSONResponse

    from app.services import report_export

    execution = _get_execution(session, execution_id, ws)
    payload = report_export.build_suite_export(execution)
    filename = f"agentguard-suite-{execution.suite_name}-{execution_id}.json".replace(" ", "_")
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _get_execution(session: Session, execution_id: str, workspace_id: str) -> SuiteExecution:
    model = session.get(SuiteExecution, execution_id)
    if model is None or model.workspace_id != workspace_id:
        raise SuiteExecutionNotFoundError(
            f"Suite execution '{execution_id}' does not exist.",
            details={"execution_id": execution_id},
        )
    return model


def _to_read(execution: SuiteExecution) -> SuiteExecutionRead:
    return SuiteExecutionRead(
        id=execution.id,
        suite_id=execution.suite_id,
        suite_name=execution.suite_name,
        agent_name=execution.agent_name or "",
        status=execution.status,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        total_cases=execution.total_cases,
        evaluated_cases=execution.evaluated_cases,
        passed_cases=execution.passed_cases,
        failed_cases=execution.failed_cases,
        skipped_cases=execution.skipped_cases,
        overall_score=execution.overall_score,
        verdict=RunVerdict(execution.verdict),
        max_severity=Severity(execution.max_severity),
        failure_categories=dict(execution.failure_categories or {}),
        duration_ms=execution.duration_ms,
        created_at=execution.created_at,
    )


def _to_detail(execution: SuiteExecution) -> SuiteExecutionDetail:
    return SuiteExecutionDetail(
        **_to_read(execution).model_dump(),
        results=orchestrator.to_case_results(execution),
        failure_intelligence=orchestrator.failure_intelligence(execution),
        report=execution.report or {},
    )