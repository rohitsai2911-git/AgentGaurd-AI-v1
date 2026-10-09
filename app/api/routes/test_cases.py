from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, workspace_id
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseListResponse,
    TestCaseRead,
    TestCaseUpdate,
)
from app.services import test_case_service

router = APIRouter(prefix="/test-cases", tags=["test-cases"])


@router.post("", response_model=TestCaseRead, status_code=status.HTTP_201_CREATED, summary="Create a test case")
def create(payload: TestCaseCreate, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return test_case_service.create(session, payload, ws)


@router.get("", response_model=TestCaseListResponse, summary="List test cases")
def list_test_cases(
    session: Session = Depends(db_session),
    ws: str = Depends(workspace_id),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tag: str | None = None,
    agent_name: str | None = None,
):
    items, total = test_case_service.list_all(
        session, ws, limit=limit, offset=offset, tag=tag, agent_name=agent_name
    )
    return {
        "items": [TestCaseRead.model_validate(i) for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{test_case_id}", response_model=TestCaseRead, summary="Get a test case")
def get(test_case_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return TestCaseRead.model_validate(test_case_service.get(session, test_case_id, ws))


@router.patch("/{test_case_id}", response_model=TestCaseRead, summary="Update a test case")
def update(test_case_id: str, payload: TestCaseUpdate, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return TestCaseRead.model_validate(test_case_service.update(session, test_case_id, payload, ws))


@router.delete("/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a test case")
def delete(test_case_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    test_case_service.delete(session, test_case_id, ws)