from __future__ import annotations

from datetime import datetime, timezone

from app.evaluation.modules import hallucination
from app.evaluation.modules.consistency import mode_for
from app.evaluation.scoring import compute_overall, effective_weights
from app.evaluation.types import (
    HALLUCINATION_DISCLAIMER,
    Dimension,
    DimensionResult,
    EvaluationReport,
    HallucinationAssessment,
    RunVerdict,
    Severity,
    TestCaseCriteria,
    Verification,
)


def build_hallucination_assessment(
    criteria: TestCaseCriteria,
    results: list[DimensionResult],
) -> HallucinationAssessment:
    result = next((r for r in results if r.dimension == Dimension.HALLUCINATION), None)
    verdict = hallucination.VERDICT_NONE
    unsupported: list[str] = []
    contradicted: list[str] = []

    if result is not None:
        verdict = result.details.get("verdict", hallucination.VERDICT_NONE)
        for finding in result.findings:
            if finding.verification == Verification.VERIFIED:
                contradicted.append(finding.message)
            else:
                unsupported.append(finding.message)

    return HallucinationAssessment(
        verdict=verdict,
        grounding_sources=[criteria.expected_answer, *criteria.referenced_facts],
        unsupported_claims=unsupported[:50],
        contradicted_values=contradicted[:50],
        disclaimer=HALLUCINATION_DISCLAIMER,
    )


def build_summary(
    criteria: TestCaseCriteria,
    results: list[DimensionResult],
    overall_score: int,
    verdict: RunVerdict,
) -> str:
    failed = [r for r in results if not r.passed]
    lines: list[str] = []

    if verdict == RunVerdict.PASS:
        lines.append(
            f"PASS with an overall quality score of {overall_score}. "
            f"All {len(results)} evaluated dimensions met their thresholds."
        )
    else:
        lines.append(
            f"FAIL with an overall quality score of {overall_score}. "
            f"{len(failed)} of {len(results)} dimensions failed."
        )

    for result in failed:
        names = ", ".join(sorted({f.rule_id for f in result.findings})) or "no rule detail"
        lines.append(
            f"- {result.dimension.value}: score {result.score} "
            f"(threshold {result.details.get('threshold', 'n/a')}), {len(result.findings)} finding(s) [{names}]."
        )

    critical = [
        f
        for r in results
        for f in r.findings
        if f.severity == Severity.CRITICAL
    ]
    if critical:
        lines.append(
            f"- {len(critical)} critical finding(s) present: "
            + ", ".join(sorted({f.rule_id for f in critical}))
            + ". A critical finding fails the run regardless of the numeric score."
        )

    consistency = next(
        (r for r in results if r.dimension == Dimension.CONSISTENCY), None
    )
    if consistency is not None and consistency.details.get("mode") == "internal":
        lines.append(
            "Single-response evaluation: consistency was assessed for internal "
            "self-contradiction only. Submit multiple responses to measure "
            "cross-response consistency."
        )

    return " ".join(lines)


def build_report(
    criteria: TestCaseCriteria,
    responses: list[str],
    results: list[DimensionResult],
    run_id: str | None = None,
    duration_ms: int = 0,
    created_at: datetime | None = None,
) -> EvaluationReport:
    overall_score, verdict, severity = compute_overall(criteria, results)
    return EvaluationReport(
        run_id=run_id,
        test_case_id=criteria.id,
        test_case_name=criteria.name,
        agent_name=criteria.agent_name,
        overall_score=overall_score,
        verdict=verdict,
        max_severity=Severity(severity),
        summary=build_summary(criteria, results, overall_score, verdict),
        dimensions=results,
        hallucination_assessment=build_hallucination_assessment(criteria, results),
        responses_submitted=len(responses),
        consistency_mode=mode_for(len(responses)),
        weights_used=effective_weights(criteria, results),
        disclaimer=HALLUCINATION_DISCLAIMER,
        duration_ms=duration_ms,
        created_at=created_at or datetime.now(timezone.utc),
    )


def tally_findings(results: list[DimensionResult]) -> dict[str, int]:
    counts = {s.value: 0 for s in Severity}
    for result in results:
        for finding in result.findings:
            counts[finding.severity.value] += 1
    counts["total"] = sum(counts.values())
    return counts


def dimension_scores(results: list[DimensionResult]) -> dict[str, int]:
    return {r.dimension.value: r.score for r in results}