from __future__ import annotations

from app.evaluation.types import (
    DEFAULT_THRESHOLDS,
    DEFAULT_WEIGHTS,
    Dimension,
    DimensionResult,
    RunVerdict,
    Severity,
    max_severity,
)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> int:
    return int(round(max(low, min(high, value))))


def merge_results(results: list[DimensionResult]) -> DimensionResult:
    """Average multiple per-response results of the same dimension."""
    if len(results) == 1:
        return results[0]

    score = clamp(sum(r.score for r in results) / len(results))
    forced_fail = any(r.forced_fail for r in results)
    passed = all(r.passed for r in results) and not forced_fail
    findings = [f for r in results for f in r.findings]
    severity = Severity(max_severity([f.severity.value for f in findings]) or Severity.NONE.value)

    details: dict = {}
    per_response = []
    for index, r in enumerate(results):
        per_response.append({"response_index": index, "score": r.score, "passed": r.passed})
        for key, value in r.details.items():
            if isinstance(value, (int, float, bool, str)):
                details[f"last_{key}"] = value
    details["per_response"] = per_response
    details["responses_merged"] = len(results)

    return DimensionResult(
        dimension=results[0].dimension,
        score=score,
        passed=passed,
        severity=severity,
        findings=findings,
        methodology=results[0].methodology,
        details=details,
        forced_fail=forced_fail,
    )


def effective_weights(criteria, results: list[DimensionResult]) -> dict[str, float]:
    """Weights renormalised over the dimensions actually evaluated."""
    raw = {r.dimension.value: criteria.weight_for(r.dimension) for r in results}
    total = sum(raw.values())
    if total <= 0:
        return {k: round(1.0 / len(raw), 4) for k in raw} if raw else {}
    return {k: round(v / total, 4) for k, v in raw.items()}


def compute_overall(
    criteria,
    results: list[DimensionResult],
) -> tuple[int, RunVerdict, str]:
    """Weighted overall score plus a hard-gated verdict.

    A high weighted score can never mask a dimension-level failure or a
    critical finding; pass/fail is decided by gates, not by the score.
    """
    weights = effective_weights(criteria, results)
    overall = clamp(
        sum(r.score * weights.get(r.dimension.value, 0.0) for r in results)
    )

    all_passed = all(r.passed for r in results)
    has_critical = any(f.severity == Severity.CRITICAL for r in results for f in r.findings)
    verdict = RunVerdict.PASS if (all_passed and not has_critical) else RunVerdict.FAIL

    severity = max_severity([f.severity.value for r in results for f in r.findings])
    return overall, verdict, severity


def default_thresholds() -> dict[str, int]:
    return dict(DEFAULT_THRESHOLDS)


def default_weights() -> dict[str, float]:
    return dict(DEFAULT_WEIGHTS)


__all__ = [
    "Dimension",
    "clamp",
    "compute_overall",
    "default_thresholds",
    "default_weights",
    "effective_weights",
    "merge_results",
]