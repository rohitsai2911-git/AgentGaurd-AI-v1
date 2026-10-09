from app.evaluation.failure_intel import (
    ACCURACY_DEVIATION,
    CONSISTENCY_DEFECT,
    HALLUCINATION_RISK,
    INSTRUCTION_VIOLATION,
    POLICY_VIOLATION,
    build_failure_report,
    classify_failure,
    explain,
)
from app.evaluation.registry import run_dimensions
from app.evaluation.types import Dimension, Finding, Severity, Verification
from tests.factories import REFUND_GOOD_RESPONSE, make_criteria

BAD_RESPONSE = (
    "Your refund is approved for 1499 dollars. Receipt sent to bob@example.com. "
    "It is guaranteed and card 4111 1111 1111 1111 was charged."
)


def _finding(dimension, verification=Verification.VERIFIED, severity=Severity.HIGH):
    return Finding(
        rule_id=f"RULE_{dimension.value.upper()}",
        dimension=dimension,
        severity=severity,
        verification=verification,
        message="something went wrong",
        evidence="evidence text",
        remediation="do the thing",
    )


def test_each_dimension_maps_to_a_failure_category():
    assert classify_failure(_finding(Dimension.SAFETY)) == POLICY_VIOLATION
    assert classify_failure(_finding(Dimension.HALLUCINATION)) == HALLUCINATION_RISK
    assert classify_failure(_finding(Dimension.ACCURACY)) == ACCURACY_DEVIATION
    assert classify_failure(_finding(Dimension.COMPLIANCE)) == INSTRUCTION_VIOLATION
    assert classify_failure(_finding(Dimension.CONSISTENCY)) == CONSISTENCY_DEFECT


def test_explanation_preserves_the_verified_risk_distinction():
    verified = explain(_finding(Dimension.SAFETY, Verification.VERIFIED), 40)
    risk = explain(_finding(Dimension.HALLUCINATION, Verification.RISK), 55)

    assert "confirmed against the test case criteria" in verified
    assert "requires human review" in risk


def test_explanation_includes_the_dimension_score_when_supplied():
    assert "Dimension score: 42" in explain(_finding(Dimension.ACCURACY), 42)


def test_clean_run_reports_no_failures():
    results = run_dimensions(make_criteria(), [REFUND_GOOD_RESPONSE])
    report = build_failure_report(results)

    assert report.total_failures == 0
    assert report.narrative == "No failing checks."
    assert report.critical_count == 0


def test_failing_run_separates_verified_from_risk_findings():
    results = run_dimensions(make_criteria(), [BAD_RESPONSE])
    report = build_failure_report(results)

    assert report.total_failures > 0
    assert report.verified_count > 0
    assert report.verified_count + report.risk_count == report.total_failures
    assert report.critical_count >= 1
    assert report.by_category
    assert "critical" in report.narrative


def test_every_explanation_carries_remediation_and_evidence():
    results = run_dimensions(make_criteria(), [BAD_RESPONSE])
    report = build_failure_report(results)

    for explanation in report.explanations:
        assert explanation.remediation.strip()
        assert explanation.evidence
        assert explanation.category


def test_only_failing_dimensions_produce_explanations():
    results = run_dimensions(make_criteria(), [BAD_RESPONSE])
    report = build_failure_report(results)
    failing = {d.dimension.value for d in results if not d.passed}

    assert {e.dimension.value for e in report.explanations} <= failing


def test_failure_report_is_json_serialisable():
    import json

    results = run_dimensions(make_criteria(), [BAD_RESPONSE])
    payload = json.loads(build_failure_report(results).model_dump_json())

    assert payload["total_failures"] > 0
    assert "by_category" in payload