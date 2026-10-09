from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import RunNotFoundError, SuiteExecutionNotFoundError
from app.db.models import EvaluationRun, SuiteExecution, TestCase, TestSuite
from app.evaluation.failure_intel import classify_failure
from app.evaluation.types import Severity
from app.schemas.analytics import (
    ComparisonResponse,
    DimensionAggregate,
    FailureBreakdown,
    FailureCategoryAggregate,
    OverviewStats,
    ScoreDelta,
    TopRule,
    TrendPoint,
    TrendResponse,
)
from app.services import evaluation_service

logger = logging.getLogger(__name__)


def overview(session: Session, workspace_id: str) -> OverviewStats:
    total_cases = (
        session.scalar(
            select(func.count()).select_from(TestCase).where(TestCase.workspace_id == workspace_id)
        )
        or 0
    )
    total_runs = (
        session.scalar(
            select(func.count()).select_from(EvaluationRun).where(EvaluationRun.workspace_id == workspace_id)
        )
        or 0
    )
    total_suites = (
        session.scalar(
            select(func.count()).select_from(TestSuite).where(TestSuite.workspace_id == workspace_id)
        )
        or 0
    )
    total_suite_runs = (
        session.scalar(
            select(func.count()).select_from(SuiteExecution).where(SuiteExecution.workspace_id == workspace_id)
        )
        or 0
    )

    passed = (
        session.scalar(
            select(func.count())
            .select_from(EvaluationRun)
            .where(EvaluationRun.verdict == "pass", EvaluationRun.workspace_id == workspace_id)
        )
        or 0
    )
    scores = list(
        session.scalars(
            select(EvaluationRun.overall_score).where(EvaluationRun.workspace_id == workspace_id)
        )
    )

    suite_passed = (
        session.scalar(
            select(func.count())
            .select_from(SuiteExecution)
            .where(SuiteExecution.verdict == "pass", SuiteExecution.workspace_id == workspace_id)
        )
        or 0
    )

    return OverviewStats(
        total_test_cases=total_cases,
        total_runs=total_runs,
        total_suites=total_suites,
        total_suite_executions=total_suite_runs,
        pass_rate=_ratio(passed, total_runs),
        fail_rate=_ratio(total_runs - passed, total_runs),
        average_overall_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
        best_overall_score=max(scores) if scores else 0,
        worst_overall_score=min(scores) if scores else 0,
        suite_pass_rate=_ratio(suite_passed, total_suite_runs),
    )


def trends(
    session: Session,
    workspace_id: str,
    granularity: str = "day",
    days: int = 30,
    test_case_id: str | None = None,
    suite_id: str | None = None,
) -> TrendResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(EvaluationRun).where(
        EvaluationRun.created_at >= cutoff,
        EvaluationRun.workspace_id == workspace_id,
    )
    if test_case_id:
        stmt = stmt.where(EvaluationRun.test_case_id == test_case_id)

    runs = list(session.scalars(stmt))
    if suite_id:
        suite_runs = list(
            session.scalars(
                select(SuiteExecution).where(
                    SuiteExecution.suite_id == suite_id,
                    SuiteExecution.created_at >= cutoff,
                    SuiteExecution.workspace_id == workspace_id,
                )
            )
        )
        runs = _project_suite_runs(suite_runs)

    buckets: dict[str, list[EvaluationRun]] = defaultdict(list)
    for run in runs:
        buckets[_bucket(run.created_at, granularity)].append(run)

    points: list[TrendPoint] = []
    for key in sorted(buckets):
        group = buckets[key]
        passed = sum(1 for r in group if r.verdict == "pass")
        scores = [r.overall_score for r in group]
        severities = [r.max_severity for r in group if r.max_severity]
        points.append(
            TrendPoint(
                bucket=key,
                total=len(group),
                passed=passed,
                failed=len(group) - passed,
                pass_rate=round(_ratio(passed, len(group)), 4),
                average_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
                max_severity=Severity(
                    max(severities, key=lambda s: _rank(s)) if severities else Severity.NONE.value
                ),
            )
        )

    logger.info("Built %d trend bucket(s) at %s granularity", len(points), granularity)
    return TrendResponse(
        granularity=granularity,  # type: ignore[arg-type]
        test_case_id=test_case_id,
        suite_id=suite_id,
        points=points,
        total_points=len(points),
    )


def _project_suite_runs(suite_runs: list[SuiteExecution]) -> list[EvaluationRun]:
    """Expose suite executions as score-only runs so both feed one trend model."""
    projected = []
    for sr in suite_runs:
        run = EvaluationRun(
            id=sr.id,
            test_case_id=sr.suite_id,
            overall_score=int(round(sr.overall_score)),
            verdict=sr.verdict,
            max_severity=sr.max_severity,
            created_at=sr.created_at,
        )
        projected.append(run)
    return projected


def failure_breakdown(session: Session, workspace_id: str, limit: int = 10) -> FailureBreakdown:
    runs = list(
        session.scalars(select(EvaluationRun).where(EvaluationRun.workspace_id == workspace_id))
    )

    category_counter: Counter[str] = Counter()
    severity_counter: Counter[str] = Counter()
    dimension_scores: dict[str, list[int]] = defaultdict(list)
    dimension_failures: Counter[str] = Counter()
    rule_counter: Counter[str] = Counter()
    rule_verification: dict[str, str] = {}
    rule_severity: dict[str, str] = {}
    total_findings = 0

    for run in runs:
        for dimension, score in (run.dimension_scores or {}).items():
            dimension_scores[dimension].append(score)
            if score < _threshold_for(dimension):
                dimension_failures[dimension] += 1
        for finding in (run.report or {}).get("dimensions", []):
            for f in finding.get("findings", []):
                total_findings += 1
                category = classify_failure(_as_finding(f))
                category_counter[category] += 1
                severity_counter[f.get("severity", "info")] += 1
                rule_counter[f.get("rule_id", "unknown")] += 1
                rule_verification[f.get("rule_id", "unknown")] = f.get("verification", "risk")
                rule_severity[f.get("rule_id", "unknown")] = f.get("severity", "info")

    by_category = [
        FailureCategoryAggregate(
            category=category,
            count=count,
            percentage=round(_ratio(count, total_findings), 4),
        )
        for category, count in category_counter.most_common()
    ]

    by_dimension = [
        DimensionAggregate(
            dimension=dimension,
            average_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
            pass_rate=round(
                _ratio(len(scores) - dimension_failures[dimension], len(scores)), 4
            ),
            failure_count=dimension_failures[dimension],
        )
        for dimension, scores in sorted(dimension_scores.items())
    ]

    top_rules = [
        TopRule(
            rule_id=rule_id,
            count=count,
            verification=rule_verification.get(rule_id, "risk"),
            worst_severity=Severity(rule_severity.get(rule_id, "info")),
        )
        for rule_id, count in rule_counter.most_common(limit)
    ]

    return FailureBreakdown(
        by_category=by_category,
        by_severity={s.value: severity_counter.get(s.value, 0) for s in Severity},
        by_dimension=by_dimension,
        top_rules=top_rules,
        critical_findings=severity_counter.get(Severity.CRITICAL.value, 0),
        verified_findings=sum(1 for r in runs for _ in _verified_findings(r)),
        risk_findings=sum(1 for r in runs for _ in _risk_findings(r)),
    )


def compare_runs(session: Session, run_a: str, run_b: str, workspace_id: str) -> ComparisonResponse:
    a = evaluation_service.get_run(session, run_a, workspace_id)
    b = evaluation_service.get_run(session, run_b, workspace_id)
    return _build_comparison(
        kind="runs",
        a=_run_delta(a),
        b=_run_delta(b),
        a_scores=dict(a.dimension_scores or {}),
        b_scores=dict(b.dimension_scores or {}),
        a_findings=_rule_set(a),
        b_findings=_rule_set(b),
        a_counts=dict(a.finding_counts or {}),
        b_counts=dict(b.finding_counts or {}),
    )


def compare_suite_executions(
    session: Session, exec_a: str, exec_b: str, workspace_id: str
) -> ComparisonResponse:
    a = _get_suite_execution(session, exec_a, workspace_id)
    b = _get_suite_execution(session, exec_b, workspace_id)
    return _build_comparison(
        kind="suite_executions",
        a=_suite_delta(a),
        b=_suite_delta(b),
        a_scores={},
        b_scores={},
        a_findings=_report_rule_set((a.report or {})),
        b_findings=_report_rule_set((b.report or {})),
        a_counts=_report_severity_counts((a.report or {})),
        b_counts=_report_severity_counts((b.report or {})),
    )


def _get_suite_execution(session: Session, execution_id: str, workspace_id: str) -> SuiteExecution:
    model = session.get(SuiteExecution, execution_id)
    if model is None or model.workspace_id != workspace_id:
        raise SuiteExecutionNotFoundError(
            f"Suite execution '{execution_id}' does not exist.",
            details={"execution_id": execution_id},
        )
    return model


def _build_comparison(
    kind: str,
    a: ScoreDelta,
    b: ScoreDelta,
    a_scores: dict[str, int],
    b_scores: dict[str, int],
    a_findings: set[str],
    b_findings: set[str],
    a_counts: dict[str, int],
    b_counts: dict[str, int],
) -> ComparisonResponse:
    per_dimension = {
        key: round(float(b_scores.get(key, 0)) - float(a_scores.get(key, 0)), 2)
        for key in sorted(set(a_scores) | set(b_scores))
    }
    severity_keys = set(a_counts) | set(b_counts)
    findings_delta = {key: int(b_counts.get(key, 0)) - int(a_counts.get(key, 0)) for key in sorted(severity_keys)}
    delta = round(b.overall_score - a.overall_score, 2)

    return ComparisonResponse(
        kind=kind,  # type: ignore[arg-type]
        a=a,
        b=b,
        score_delta=delta,
        verdict_changed=a.verdict != b.verdict,
        regression=delta < 0 or b.verdict == "fail",
        per_dimension_delta=per_dimension,
        findings_delta=findings_delta,
        new_rules=sorted(b_findings - a_findings),
        resolved_rules=sorted(a_findings - b_findings),
    )


def _run_delta(run: EvaluationRun) -> ScoreDelta:
    return ScoreDelta(
        label=run.id,
        overall_score=float(run.overall_score),
        verdict=run.verdict,
        passed=1 if run.verdict == "pass" else 0,
        failed=0 if run.verdict == "pass" else 1,
        total=1,
    )


def _suite_delta(execution: SuiteExecution) -> ScoreDelta:
    return ScoreDelta(
        label=execution.id,
        overall_score=float(execution.overall_score),
        verdict=execution.verdict,
        passed=execution.passed_cases,
        failed=execution.failed_cases,
        total=execution.evaluated_cases,
    )


def _rule_set(run: EvaluationRun) -> set[str]:
    return _report_rule_set(run.report or {})


def _report_rule_set(report: dict) -> set[str]:
    rules: set[str] = set()
    for dimension in report.get("dimensions", []):
        for finding in dimension.get("findings", []):
            rules.add(finding.get("rule_id", "unknown"))
    for finding in report.get("failure_intelligence", {}).get("explanations", []):
        rules.add(finding.get("rule_id", "unknown"))
    return rules


def _report_severity_counts(report: dict) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for dimension in report.get("dimensions", []):
        for finding in dimension.get("findings", []):
            counts[finding.get("severity", "info")] += 1
    if not report.get("dimensions"):
        by_severity = report.get("failure_intelligence", {}).get("by_severity", {})
        counts.update(by_severity)
    return dict(counts)


def _verified_findings(run: EvaluationRun):
    for dimension in (run.report or {}).get("dimensions", []):
        for finding in dimension.get("findings", []):
            if finding.get("verification") == "verified":
                yield finding


def _risk_findings(run: EvaluationRun):
    for dimension in (run.report or {}).get("dimensions", []):
        for finding in dimension.get("findings", []):
            if finding.get("verification") == "risk":
                yield finding


def _as_finding(payload: dict):
    from app.evaluation.types import Dimension, Finding, Severity as S, Verification

    return Finding(
        rule_id=payload.get("rule_id", "unknown"),
        dimension=Dimension(payload.get("dimension", "accuracy")),
        severity=S(payload.get("severity", "info")),
        verification=Verification(payload.get("verification", "risk")),
        message=payload.get("message", ""),
        evidence=payload.get("evidence"),
        remediation=payload.get("remediation", ""),
    )


def _threshold_for(dimension: str) -> int:
    from app.evaluation.types import DEFAULT_THRESHOLDS

    return DEFAULT_THRESHOLDS.get(dimension, 70)


def _bucket(moment: datetime, granularity: str) -> str:
    # SQLite returns naive datetimes; they are UTC by construction (utcnow).
    # astimezone() on naive assumes local time -> wrong bucket. Attach UTC.
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    if granularity == "hour":
        return moment.strftime("%Y-%m-%dT%H:00:00Z")
    return moment.strftime("%Y-%m-%d")


def _ratio(part: int | float, total: int | float) -> float:
    if not total:
        return 0.0
    return round(part / total, 4)


def _rank(severity: str) -> int:
    from app.evaluation.types import SEVERITY_RANK

    return SEVERITY_RANK.get(severity, 0)


__all__ = [
    "RunNotFoundError",
    "compare_runs",
    "compare_suite_executions",
    "failure_breakdown",
    "overview",
    "trends",
]