from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, settings_dep, workspace_id
from app.core.config import Settings
from app.db.models import EvaluationRun, TestCase, TestSuite
from app.schemas.common import HealthStatus
from app.services import evaluation_service, suite_service, test_case_service
from sqlalchemy import func, select

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus, summary="Full health check")
def health(
    response: Response,
    session: Session = Depends(db_session),
    settings: Settings = Depends(settings_dep),
    ws: str = Depends(workspace_id),
):
    healthy = True
    try:
        session.execute(select(func.count()).select_from(TestCase))
    except Exception:
        healthy = False
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthStatus(
        status="ok" if healthy else "degraded",
        name=settings.name,
        version=settings.version,
        database=str(settings.database_url),
        database_ok=healthy,
        test_cases=_count(session, TestCase, ws),
        runs=_count(session, EvaluationRun, ws),
        suites=_count(session, TestSuite, ws),
    )


@router.get("/health/live", summary="Liveness probe")
def live():
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness probe")
def ready(session: Session = Depends(db_session), settings: Settings = Depends(settings_dep)):
    from fastapi.responses import JSONResponse

    try:
        session.execute(select(func.count()).select_from(TestCase))
    except Exception:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "not_ready"})
    return {"status": "ready", "database": str(settings.database_url)}


def _count(session: Session, model, workspace_id: str) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(model).where(model.workspace_id == workspace_id)
        )
        or 0
    )