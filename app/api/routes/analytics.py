from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, workspace_id
from app.schemas.analytics import ComparisonResponse, FailureBreakdown, OverviewStats, TrendResponse
from app.services import analytics_service, report_export

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewStats, summary="Workspace quality overview")
def overview(session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return analytics_service.overview(session, ws)


@router.get("/trends", response_model=TrendResponse, summary="Historical pass-rate and score trends")
def trends(
    session: Session = Depends(db_session),
    ws: str = Depends(workspace_id),
    granularity: str = Query("day", pattern="^(day|hour)$"),
    days: int = Query(30, ge=1, le=365),
    test_case_id: str | None = None,
    suite_id: str | None = None,
):
    return analytics_service.trends(
        session,
        ws,
        granularity=granularity,
        days=days,
        test_case_id=test_case_id,
        suite_id=suite_id,
    )


@router.get(
    "/failures",
    response_model=FailureBreakdown,
    summary="Failure categories, dimension aggregates and most frequent rules",
)
def failures(
    session: Session = Depends(db_session),
    ws: str = Depends(workspace_id),
    limit: int = Query(10, ge=1, le=100),
):
    return analytics_service.failure_breakdown(session, ws, limit=limit)


@router.get(
    "/compare/runs",
    response_model=ComparisonResponse,
    summary="Compare two evaluation runs",
)
def compare_runs(
    run_a: str = Query(..., description="Baseline run id"),
    run_b: str = Query(..., description="Candidate run id"),
    session: Session = Depends(db_session),
    ws: str = Depends(workspace_id),
):
    return analytics_service.compare_runs(session, run_a, run_b, ws)


@router.get(
    "/compare/suite-executions",
    response_model=ComparisonResponse,
    summary="Compare two suite executions",
)
def compare_suite_executions(
    execution_a: str = Query(..., alias="a", description="Baseline suite execution id"),
    execution_b: str = Query(..., alias="b", description="Candidate suite execution id"),
    session: Session = Depends(db_session),
    ws: str = Depends(workspace_id),
):
    return analytics_service.compare_suite_executions(session, execution_a, execution_b, ws)


@router.get("/export", summary="Download an analytics snapshot as JSON")
def export(
    session: Session = Depends(db_session),
    ws: str = Depends(workspace_id),
    days: int = Query(30, ge=1, le=365),
    granularity: str = Query("day", pattern="^(day|hour)$"),
):
    payload = report_export.build_analytics_export(
        overview_payload=analytics_service.overview(session, ws).model_dump(mode="json"),
        trends_payload=analytics_service.trends(
            session, ws, granularity=granularity, days=days
        ).model_dump(mode="json"),
        failures_payload=analytics_service.failure_breakdown(session, ws).model_dump(mode="json"),
    )
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": 'attachment; filename="agentguard-analytics.json"'},
    )