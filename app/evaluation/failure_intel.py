from __future__ import annotations

from pydantic import BaseModel, Field

from app.evaluation.types import Dimension, Finding, Verification

POLICY_VIOLATION = "policy_violation"
HALLUCINATION_RISK = "hallucination_risk"
ACCURACY_DEVIATION = "accuracy_deviation"
INSTRUCTION_VIOLATION = "instruction_violation"
CONSISTENCY_DEFECT = "consistency_defect"
OTHER = "other"

CATEGORY_DIMENSION = {
    Dimension.SAFETY.value: POLICY_VIOLATION,
    Dimension.HALLUCINATION.value: HALLUCINATION_RISK,
    Dimension.ACCURACY.value: ACCURACY_DEVIATION,
    Dimension.COMPLIANCE.value: INSTRUCTION_VIOLATION,
    Dimension.CONSISTENCY.value: CONSISTENCY_DEFECT,
}

DIMENSION_CATEGORY = {v: k for k, v in CATEGORY_DIMENSION.items()}


class FailureExplanation(BaseModel):
    rule_id: str
    dimension: Dimension
    severity: str
    verification: Verification
    category: str
    explanation: str
    remediation: str
    evidence: str | None = None


class FailureReport(BaseModel):
    total_failures: int
    by_category: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    critical_count: int
    verified_count: int
    risk_count: int
    explanations: list[FailureExplanation] = Field(default_factory=list)
    narrative: str = ""


def classify_failure(finding: Finding) -> str:
    return CATEGORY_DIMENSION.get(finding.dimension.value, OTHER)


def explain(finding: Finding, dimension_score: int | None = None) -> str:
    """Plain-language explanation that preserves the verified/risk distinction."""
    prefix = {
        POLICY_VIOLATION: "Policy breach",
        HALLUCINATION_RISK: "Grounding deviation",
        ACCURACY_DEVIATION: "Accuracy deviation",
        INSTRUCTION_VIOLATION: "Instruction violation",
        CONSISTENCY_DEFECT: "Consistency defect",
        OTHER: "Evaluation finding",
    }.get(classify_failure(finding), "Evaluation finding")

    confidence = (
        "confirmed against the test case criteria"
        if finding.verification == Verification.VERIFIED
        else "a heuristic indicator that requires human review"
    )
    tail = f" Dimension score: {dimension_score}." if dimension_score is not None else ""
    return f"{prefix} ({confidence}): {finding.message}{tail}"


def remediate(finding: Finding) -> str:
    return finding.remediation


def build_failure_report(dimension_results: list) -> FailureReport:
    from app.evaluation.report import tally_findings
    from app.evaluation.types import Severity

    scores = {r.dimension.value: r.score for r in dimension_results}
    explanations: list[FailureExplanation] = []

    for result in dimension_results:
        if result.passed:
            continue
        for finding in result.findings:
            explanations.append(
                FailureExplanation(
                    rule_id=finding.rule_id,
                    dimension=finding.dimension,
                    severity=finding.severity.value,
                    verification=finding.verification,
                    category=classify_failure(finding),
                    explanation=explain(finding, scores.get(finding.dimension.value)),
                    remediation=remediate(finding),
                    evidence=finding.evidence,
                )
            )

    by_category: dict[str, int] = {}
    by_severity = {s.value: 0 for s in Severity}
    for e in explanations:
        by_category[e.category] = by_category.get(e.category, 0) + 1
        by_severity[e.severity] += 1

    verified = sum(1 for e in explanations if e.verification == Verification.VERIFIED)
    risk = sum(1 for e in explanations if e.verification == Verification.RISK)
    critical = by_severity.get(Severity.CRITICAL.value, 0)

    if explanations:
        narrative = (
            f"{len(explanations)} failing check(s): "
            + ", ".join(f"{count} {category.replace('_', ' ')}" for category, count in sorted(by_category.items()))
            + f". {critical} critical. {verified} confirmed against the test case, "
            f"{risk} heuristic indicators requiring human review."
        )
    else:
        narrative = "No failing checks."

    return FailureReport(
        total_failures=len(explanations),
        by_category=by_category,
        by_severity=by_severity,
        critical_count=critical,
        verified_count=verified,
        risk_count=risk,
        explanations=explanations,
        narrative=narrative,
    )