from __future__ import annotations

from datetime import datetime, timezone

from app.db.models import EvaluationRun, SuiteExecution, TestCase
from app.schemas.analytics import ExportMeta

PLATFORM = "AgentGuard AI"


def build_run_export(session, run: EvaluationRun) -> dict:
    report = run.report or {}
    test_case = session.get(TestCase, run.test_case_id)
    return {
        "meta": _meta("run", run.created_at),
        "run": {
            "id": run.id,
            "test_case_id": run.test_case_id,
            "test_case_name": report.get("test_case_name", ""),
            "agent_name": report.get("agent_name", ""),
            "verdict": run.verdict,
            "overall_score": run.overall_score,
            "max_severity": run.max_severity,
            "duration_ms": run.duration_ms,
            "created_at": _iso(run.created_at),
            "responses": list(run.responses or []),
            "dimension_scores": dict(run.dimension_scores or {}),
            "finding_counts": dict(run.finding_counts or {}),
        },
        "test_case_criteria": (
            {
                "input_prompt": test_case.input_prompt,
                "expected_answer": test_case.expected_answer,
                "referenced_facts": list(test_case.referenced_facts or []),
                "required_keywords": list(test_case.required_keywords or []),
                "forbidden_keywords": list(test_case.forbidden_keywords or []),
                "expected_numbers": list(test_case.expected_numbers or []),
                "enabled_dimensions": list(test_case.enabled_dimensions or []),
                "thresholds": dict(test_case.thresholds or {}),
                "weights": dict(test_case.weights or {}),
            }
            if test_case is not None
            else None
        ),
        "report": report,
    }


def build_suite_export(execution: SuiteExecution) -> dict:
    return {
        "meta": _meta("suite_execution", execution.created_at),
        "suite_execution": {
            "id": execution.id,
            "suite_id": execution.suite_id,
            "suite_name": execution.suite_name,
            "agent_name": execution.agent_name,
            "status": execution.status,
            "verdict": execution.verdict,
            "overall_score": execution.overall_score,
            "max_severity": execution.max_severity,
            "total_cases": execution.total_cases,
            "evaluated_cases": execution.evaluated_cases,
            "passed_cases": execution.passed_cases,
            "failed_cases": execution.failed_cases,
            "skipped_cases": execution.skipped_cases,
            "failure_categories": dict(execution.failure_categories or {}),
            "duration_ms": execution.duration_ms,
            "started_at": _iso(execution.started_at),
            "completed_at": _iso(execution.completed_at),
            "created_at": _iso(execution.created_at),
        },
        "report": execution.report or {},
    }


def build_analytics_export(
    overview_payload: dict,
    trends_payload: dict,
    failures_payload: dict,
) -> dict:
    return {
        "meta": _meta("analytics", None),
        "overview": overview_payload,
        "trends": trends_payload,
        "failure_breakdown": failures_payload,
    }


def _meta(kind: str, created_at) -> dict:
    from app.core.config import get_settings

    settings = get_settings()
    return ExportMeta(
        generated_at=datetime.now(timezone.utc),
        platform=PLATFORM,
        version=settings.version,
        kind=kind,  # type: ignore[arg-type]
    ).model_dump(mode="json")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None