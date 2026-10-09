from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import SuiteEmptyError
from app.db.models import SuiteCaseResult, SuiteExecution, TestSuite
from app.evaluation.failure_intel import build_failure_report
from app.evaluation.types import DimensionResult, EvaluationReport, Severity
from app.schemas.suite import SuiteCaseResultRead, SuiteExecuteRequest
from app.services import evaluation_service, suite_service

logger = logging.getLogger(__name__)

STATUS_COMPLETED = "completed"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"

CASE_EVALUATED = "evaluated"
CASE_SKIPPED = "skipped"


def _resolve_responses(
    case_name: str, case_id: str, responses: dict[str, list[str]]
) -> list[str]:
    """Responses may be keyed by test-case id or by test-case name."""
    return responses.get(case_id) or responses.get(case_name) or []


def execute_suite(
    session: Session,
    suite: TestSuite,
    request: SuiteExecuteRequest,
) -> SuiteExecution:
    cases = suite_service.resolve_cases(session, suite)
    if not cases:
        raise SuiteEmptyError(
            f"Suite '{suite.name}' has no test cases to execute.",
            details={"suite_id": suite.id},
        )

    started = time.perf_counter()
    started_at = datetime.now(timezone.utc)
    agent_name = request.agent_name or next((c.agent_name for c in cases if c.agent_name), "")

    execution = SuiteExecution(
        workspace_id=suite.workspace_id,
        suite_id=suite.id,
        suite_name=suite.name,
        agent_name=agent_name,
        status=STATUS_COMPLETED,
        started_at=started_at,
        total_cases=len(cases),
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)

    evaluated_reports: list[EvaluationReport] = []
    aggregated: list[DimensionResult] = []
    category_totals: dict[str, int] = {}
    severity_values: list[str] = []
    passed = failed = skipped = 0

    for case in cases:
        responses = _resolve_responses(case.name, case.id, request.responses)

        if not responses:
            skipped += 1
            session.add(
                SuiteCaseResult(
                    suite_execution_id=execution.id,
                    test_case_id=case.id,
                    test_case_name=case.name,
                    status=CASE_SKIPPED,
                    passed=False,
                    overall_score=0,
                    max_severity=Severity.NONE.value,
                    failure_categories=[],
                    duration_ms=0,
                )
            )
            continue

        case_started = time.perf_counter()
        report, run_id = evaluation_service.evaluate(
            session, case, responses, persist=request.persist
        )
        case_ms = int((time.perf_counter() - case_started) * 1000)

        case_failures = build_failure_report(report.dimensions)
        categories = sorted(case_failures.by_category.keys())

        for category, count in case_failures.by_category.items():
            category_totals[category] = category_totals.get(category, 0) + count

        severity_values.extend(
            f.severity.value for d in report.dimensions for f in d.findings
        )

        if report.verdict.value == "pass":
            passed += 1
        else:
            failed += 1

        evaluated_reports.append(report)
        aggregated.extend(report.dimensions)

        session.add(
            SuiteCaseResult(
                suite_execution_id=execution.id,
                test_case_id=case.id,
                test_case_name=case.name,
                run_id=run_id,
                status=CASE_EVALUATED,
                passed=report.verdict.value == "pass",
                overall_score=report.overall_score,
                max_severity=report.max_severity.value,
                failure_categories=categories,
                duration_ms=case_ms,
            )
        )

    session.flush()

    duration_ms = int((time.perf_counter() - started) * 1000)
    execution.evaluated_cases = len(evaluated_reports)
    execution.passed_cases = passed
    execution.failed_cases = failed
    execution.skipped_cases = skipped
    execution.duration_ms = duration_ms
    execution.completed_at = datetime.now(timezone.utc)
    execution.failure_categories = category_totals
    execution.max_severity = (
        max(severity_values, key=lambda s: _rank(s)) if severity_values else Severity.NONE.value
    )

    if not evaluated_reports:
        execution.status = STATUS_PARTIAL
        execution.verdict = "fail"
        execution.overall_score = 0.0
    else:
        execution.overall_score = round(
            sum(r.overall_score for r in evaluated_reports) / len(evaluated_reports), 2
        )
        execution.verdict = (
            "pass" if failed == 0 and skipped == 0 and not _has_critical(severity_values) else "fail"
        )
        if failed:
            execution.status = STATUS_FAILED
        elif skipped:
            execution.status = STATUS_PARTIAL

    failure_intelligence = build_failure_report(_failed_only(aggregated))

    execution.report = {
        "suite_id": suite.id,
        "suite_name": suite.name,
        "agent_name": agent_name,
        "status": execution.status,
        "started_at": started_at.isoformat(),
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "duration_ms": duration_ms,
        "summary": _build_summary(execution, failure_intelligence.narrative),
        "totals": {
            "total_cases": execution.total_cases,
            "evaluated_cases": execution.evaluated_cases,
            "passed_cases": execution.passed_cases,
            "failed_cases": execution.failed_cases,
            "skipped_cases": execution.skipped_cases,
        },
        "overall_score": execution.overall_score,
        "verdict": execution.verdict,
        "max_severity": execution.max_severity,
        "failure_categories": category_totals,
        "failure_intelligence": failure_intelligence.model_dump(mode="json"),
        "cases": [
            {
                "test_case_id": r.test_case_id,
                "test_case_name": r.test_case_name,
                "run_id": r.run_id,
                "status": r.status,
                "passed": r.passed,
                "overall_score": r.overall_score,
                "max_severity": r.max_severity,
                "failure_categories": r.failure_categories,
                "duration_ms": r.duration_ms,
            }
            for r in execution.results
        ],
        "case_reports": [r.model_dump(mode="json") for r in evaluated_reports],
        "disclaimer": (
            "Suite aggregation of deterministic heuristic checks. Verified findings are "
            "provable against each test case's grounding source; risk findings are "
            "indicators requiring human review."
        ),
    }

    session.commit()
    session.refresh(execution)
    logger.info(
        "Executed suite %s: %d passed, %d failed, %d skipped (score %.2f, %d ms)",
        suite.name,
        passed,
        failed,
        skipped,
        execution.overall_score,
        duration_ms,
    )
    return execution


def _failed_only(dimensions: list[DimensionResult]) -> list[DimensionResult]:
    return [d for d in dimensions if not d.passed]


def _has_critical(severities: list[str]) -> bool:
    return Severity.CRITICAL.value in severities


def _rank(severity: str) -> int:
    from app.evaluation.types import SEVERITY_RANK

    return SEVERITY_RANK.get(severity, 0)


def _build_summary(execution: SuiteExecution, failure_narrative: str) -> str:
    return (
        f"Suite '{execution.suite_name}' evaluated {execution.evaluated_cases} of "
        f"{execution.total_cases} test case(s): {execution.passed_cases} passed, "
        f"{execution.failed_cases} failed, {execution.skipped_cases} skipped. "
        f"Average overall score {execution.overall_score}. "
        f"Suite verdict {execution.verdict}. {failure_narrative}"
    )


def to_case_results(execution: SuiteExecution) -> list[SuiteCaseResultRead]:
    return [
        SuiteCaseResultRead(
            test_case_id=r.test_case_id,
            test_case_name=r.test_case_name,
            run_id=r.run_id,
            status=r.status,
            passed=r.passed,
            overall_score=r.overall_score,
            max_severity=Severity(r.max_severity),
            failure_categories=list(r.failure_categories or []),
            duration_ms=r.duration_ms,
        )
        for r in execution.results
    ]


def failure_intelligence(execution: SuiteExecution):
    from app.evaluation.failure_intel import FailureReport

    stored = (execution.report or {}).get("failure_intelligence")
    if stored:
        return FailureReport(**stored)
    return build_failure_report([])