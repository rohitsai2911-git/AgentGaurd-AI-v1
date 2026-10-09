from __future__ import annotations

import logging
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import RunNotFoundError
from app.db.models import EvaluationRun, TestCase
from app.evaluation.failure_intel import FailureReport, build_failure_report
from app.evaluation.registry import run_dimensions
from app.evaluation.report import build_report, dimension_scores, tally_findings
from app.evaluation.types import EvaluationReport, RunVerdict
from app.schemas.evaluation import RunDetail, RunSummary
from app.services import test_case_service

logger = logging.getLogger(__name__)


def evaluate(
    session: Session,
    test_case: TestCase,
    responses: list[str],
    persist: bool = True,
    use_llm: bool = False,
    llm_model: str | None = None,
    use_laya: bool = False,
) -> tuple[EvaluationReport, str | None]:
    """Hybrid pipeline: deterministic -> Laya -> OpenRouter -> aggregate.

    Deterministic dimensions always run and solely decide verdict/scores.
    Laya and OpenRouter are independent, additive, advisory-only enrichments
    attached to the report. Neither can alter deterministic results, so the
    same failure is never double-counted in scoring.
    """
    criteria = test_case_service.to_criteria(test_case)

    started = time.perf_counter()
    results = run_dimensions(criteria, responses)
    duration_ms = int((time.perf_counter() - started) * 1000)

    report = build_report(
        criteria=criteria,
        responses=responses,
        results=results,
        duration_ms=duration_ms,
    )

    if use_laya:
        # Additive only. Laya never changes deterministic verdict/scores.
        try:
            from app.evaluation.laya import evaluate_with_laya as _laya_judge

            laya_result = _laya_judge(criteria, responses)
            report.laya_evaluation = laya_result.model_dump(mode="json")
        except Exception as exc:  # defensive: deterministic must survive
            logger.warning("Laya judge crashed (non-fatal): %s", type(exc).__name__)
            report.laya_evaluation = {
                "provider": "laya",
                "model": "",
                "model_used": "",
                "status": "error",
                "overall_reasoning": "",
                "error_code": "JUDGE_CRASH",
                "error_message": "Laya judge failed internally. Deterministic results stand.",
                "latency_ms": 0,
                "fallback_note": "Advisory only. Deterministic evaluation remains authoritative.",
            }

    if use_llm:
        # Additive only. LLM never changes deterministic verdict/scores.
        # Any LLM failure degrades to status != success inside llm_evaluation.
        try:
            from app.evaluation.llm import evaluate_with_llm as _llm_judge

            llm_result = _llm_judge(criteria, responses, model_override=llm_model)
            report.llm_evaluation = llm_result.model_dump(mode="json")
        except Exception as exc:  # defensive: deterministic must survive
            logger.warning("LLM judge crashed (non-fatal): %s", type(exc).__name__)
            report.llm_evaluation = {
                "provider": "openrouter",
                "model": llm_model or "",
                "model_used": llm_model or "",
                "status": "error",
                "overall_reasoning": "",
                "dimensions": {},
                "error_code": "JUDGE_CRASH",
                "error_message": "LLM judge failed internally. Deterministic results stand.",
                "latency_ms": 0,
                "fallback_note": "Advisory only. Deterministic evaluation remains authoritative.",
            }

    run_id: str | None = None
    if persist:
        model = EvaluationRun(
            workspace_id=test_case.workspace_id,
            test_case_id=test_case.id,
            responses=list(responses),
            dimension_scores=dimension_scores(results),
            overall_score=report.overall_score,
            verdict=report.verdict.value,
            max_severity=report.max_severity.value,
            finding_counts=tally_findings(results),
            report=report.model_dump(mode="json"),
            duration_ms=duration_ms,
        )
        session.add(model)
        session.commit()
        session.refresh(model)
        run_id = model.id
        report.run_id = run_id
        model.report = report.model_dump(mode="json")
        session.commit()
        finding_total = tally_findings(results).get("total", 0)
        logger.info(
            "Evaluated test case %s -> %s (score %s, %d finding(s))",
            test_case.name,
            report.verdict.value,
            report.overall_score,
            finding_total,
        )
    else:
        logger.info(
            "Previewed test case %s -> %s (score %s, not persisted)",
            test_case.name,
            report.verdict.value,
            report.overall_score,
        )

    return report, run_id


def failure_report(report: EvaluationReport) -> FailureReport:
    return build_failure_report(report.dimensions)


def get_run(session: Session, run_id: str, workspace_id: str) -> EvaluationRun:
    model = session.get(EvaluationRun, run_id)
    if model is None or model.workspace_id != workspace_id:
        raise RunNotFoundError(
            f"Run '{run_id}' does not exist.", details={"run_id": run_id}
        )
    return model


def to_summary(model: EvaluationRun, test_case_name: str = "") -> RunSummary:
    report = model.report or {}
    return RunSummary(
        id=model.id,
        test_case_id=model.test_case_id,
        test_case_name=test_case_name or report.get("test_case_name", ""),
        agent_name=report.get("agent_name", ""),
        overall_score=model.overall_score,
        verdict=RunVerdict(model.verdict),
        max_severity=model.max_severity,
        responses_submitted=len(model.responses or []),
        duration_ms=model.duration_ms,
        created_at=model.created_at,
    )


def to_detail(model: EvaluationRun) -> RunDetail:
    summary = to_summary(model)
    return RunDetail(
        **summary.model_dump(),
        dimension_scores=model.dimension_scores or {},
        finding_counts=model.finding_counts or {},
        report=EvaluationReport(**model.report),
    )


def list_runs(
    session: Session,
    workspace_id: str,
    limit: int = 50,
    offset: int = 0,
    test_case_id: str | None = None,
    verdict: str | None = None,
) -> tuple[list[EvaluationRun], int]:
    stmt = select(EvaluationRun).where(EvaluationRun.workspace_id == workspace_id)
    count_stmt = (
        select(func.count()).select_from(EvaluationRun).where(EvaluationRun.workspace_id == workspace_id)
    )
    if test_case_id:
        stmt = stmt.where(EvaluationRun.test_case_id == test_case_id)
        count_stmt = count_stmt.where(EvaluationRun.test_case_id == test_case_id)
    if verdict:
        stmt = stmt.where(EvaluationRun.verdict == verdict)
        count_stmt = count_stmt.where(EvaluationRun.verdict == verdict)

    total = session.scalar(count_stmt) or 0
    items = list(
        session.scalars(
            stmt.order_by(EvaluationRun.created_at.desc()).limit(limit).offset(offset)
        )
    )
    return items, total


def count(session: Session, workspace_id: str) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(EvaluationRun).where(EvaluationRun.workspace_id == workspace_id)
        )
        or 0
    )