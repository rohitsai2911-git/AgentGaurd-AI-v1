from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, workspace_id
from app.evaluation.types import EvaluationReport
from app.schemas.evaluation import (
    EvaluationRequest,
    PreviewRequest,
    RunDetail,
    RunListResponse,
    RunSummary,
)
from app.services import evaluation_service, test_case_service

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post(
    "/run",
    response_model=EvaluationReport,
    summary="Evaluate an agent response and persist the run",
)
def run(payload: EvaluationRequest, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    test_case = test_case_service.get(session, payload.test_case_id, ws)
    report, _ = evaluation_service.evaluate(
        session,
        test_case,
        payload.responses,
        persist=payload.persist,
        use_llm=payload.use_llm,
        llm_model=payload.llm_model,
        use_laya=payload.use_laya,
    )
    return report


@router.post(
    "/preview",
    response_model=EvaluationReport,
    summary="Evaluate without persisting",
)
def preview(payload: PreviewRequest, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    test_case = test_case_service.get(session, payload.test_case_id, ws)
    report, _ = evaluation_service.evaluate(
        session,
        test_case,
        payload.responses,
        persist=False,
        use_llm=payload.use_llm,
        llm_model=payload.llm_model,
        use_laya=payload.use_laya,
    )
    return report


@router.post(
    "/llm-evaluate",
    summary="LLM-only advisory evaluation (no persistence, no deterministic run)",
)
def llm_evaluate(payload: PreviewRequest, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    """Direct OpenRouter judge call. Useful for UI try-out.

    Never requires a key to be callable: without OPENROUTER_API_KEY returns
    status skipped_no_key with deterministic fallback note.
    """
    from app.evaluation.llm import evaluate_with_llm

    test_case = test_case_service.get(session, payload.test_case_id, ws)
    criteria = test_case_service.to_criteria(test_case)
    result = evaluate_with_llm(criteria, payload.responses, model_override=payload.llm_model)
    return result.model_dump(mode="json")


@router.get("/llm-status", summary="LLM provider availability (key never exposed)")
def llm_status():
    from app.evaluation.llm import status_payload

    return status_payload()


@router.post(
    "/laya-evaluate",
    summary="Laya-only advisory decisions (no persistence, no deterministic run)",
)
def laya_evaluate(payload: PreviewRequest, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    """Direct Laya judge call. Useful for UI try-out.

    Never requires setup to be callable: when disabled or unavailable returns
    a skipped status with deterministic fallback note.
    """
    from app.evaluation.laya import evaluate_with_laya

    test_case = test_case_service.get(session, payload.test_case_id, ws)
    criteria = test_case_service.to_criteria(test_case)
    result = evaluate_with_laya(criteria, payload.responses)
    return result.model_dump(mode="json")


@router.get("/laya-status", summary="Laya provider availability and config")
def laya_status():
    from app.evaluation.laya import status_payload

    return status_payload()


@router.get("/runs", response_model=RunListResponse, summary="Evaluation run history")
def list_runs(session: Session = Depends(db_session), ws: str = Depends(workspace_id),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    test_case_id: str | None = None,
    verdict: str | None = Query(None, pattern="^(pass|fail)$"),
):
    items, total = evaluation_service.list_runs(session, ws, limit=limit, offset=offset, test_case_id=test_case_id, verdict=verdict
    )
    return {
        "items": [evaluation_service.to_summary(i) for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/runs/{run_id}", response_model=RunDetail, summary="Get one run")
def get_run(run_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return evaluation_service.to_detail(evaluation_service.get_run(session, run_id, ws))


@router.get(
    "/runs/{run_id}/report",
    summary="Full stored JSON evaluation report",
)
def get_report(run_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    run = evaluation_service.get_run(session, run_id, ws)
    return JSONResponse(content=run.report or {})


@router.get(
    "/runs/{run_id}/failures",
    summary="Classified failure intelligence for one run",
)
def get_failures(run_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    run = evaluation_service.get_run(session, run_id, ws)
    report = EvaluationReport(**(run.report or {}))
    return evaluation_service.failure_report(report)


@router.get(
    "/runs/{run_id}/export",
    summary="Download the run report as JSON",
)
def export_run(run_id: str, session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    from app.services import report_export

    run = evaluation_service.get_run(session, run_id, ws)
    payload = report_export.build_run_export(session, run)
    filename = f"agentguard-run-{run_id}.json"
    return JSONResponse(
        content=payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )