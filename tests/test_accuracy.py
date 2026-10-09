from app.evaluation.modules.accuracy import evaluate_single
from app.evaluation.types import Severity, Verification
from tests.factories import REFUND_GOOD_RESPONSE, make_criteria


def test_accurate_response_scores_high_and_passes():
    criteria = make_criteria(
        required_keywords=["refund", "30 days", "store credit"],
        expected_numbers=[30, 45],
    )
    result = evaluate_single(criteria, REFUND_GOOD_RESPONSE)

    assert result.passed is True
    assert result.score >= 70
    assert result.findings == []
    assert result.details["forbidden_hits"] == 0


def test_missing_required_keyword_lowers_score_and_records_finding():
    criteria = make_criteria(required_keywords=["refund", "30 days", "store credit"])
    result = evaluate_single(criteria, "Refunds are available within 30 days of purchase.")

    assert result.passed is False
    assert "ACC_MISSING_REQUIRED_KEYWORD" in {f.rule_id for f in result.findings}
    assert result.details["keyword_coverage"] == round(2 / 3, 4)


def test_missing_expected_number_is_a_high_severity_finding():
    criteria = make_criteria(expected_numbers=[30, 45])
    result = evaluate_single(criteria, "A refund is possible. Contact us for a store credit.")

    finding = next(f for f in result.findings if f.rule_id == "ACC_MISSING_EXPECTED_NUMBER")
    assert finding.severity == Severity.HIGH
    assert finding.verification == Verification.VERIFIED
    assert result.passed is False


def test_forbidden_keyword_caps_score_and_forces_failure():
    criteria = make_criteria(
        required_keywords=["refund"],
        forbidden_keywords=["refund approved"],
    )
    result = evaluate_single(criteria, f"Refund approved. {REFUND_GOOD_RESPONSE}")

    assert result.score <= 40
    assert result.passed is False
    assert result.forced_fail is True
    assert any(f.rule_id == "ACC_FORBIDDEN_CONTENT" for f in result.findings)


def test_threshold_is_respected_when_no_rule_fires():
    criteria = make_criteria(thresholds={"accuracy": 99})
    result = evaluate_single(criteria, REFUND_GOOD_RESPONSE)

    assert result.passed is False
    assert any(f.rule_id == "ACC_BELOW_THRESHOLD" for f in result.findings)


def test_empty_response_scores_zero():
    result = evaluate_single(make_criteria(), "")

    assert result.score == 0
    assert result.passed is False


def test_methodology_is_reported_for_transparency():
    result = evaluate_single(make_criteria(), REFUND_GOOD_RESPONSE)

    assert "Jaccard" in result.methodology
    assert "required-keyword" in result.methodology