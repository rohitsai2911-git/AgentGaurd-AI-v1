from app.evaluation.modules.hallucination import (
    VERDICT_CONTRADICTION,
    VERDICT_NONE,
    VERDICT_UNVERIFIABLE,
    evaluate_single,
)
from app.evaluation.types import Severity, Verification
from tests.factories import REFUND_GOOD_RESPONSE, make_criteria


def test_grounded_response_reports_no_claims_detected():
    result = evaluate_single(make_criteria(), REFUND_GOOD_RESPONSE)

    assert result.details["verdict"] == VERDICT_NONE
    assert result.passed is True


def test_unsupported_number_is_a_risk_not_a_verified_hallucination():
    criteria = make_criteria(expected_answer="Refunds are available within 30 days.")
    result = evaluate_single(criteria, "You will receive 1499 dollars back after 3 days.")

    finding = next(f for f in result.findings if f.rule_id == "HAL_UNSUPPORTED_NUMBER")
    assert finding.verification == Verification.RISK
    assert finding.severity == Severity.MEDIUM
    assert result.details["verdict"] == VERDICT_UNVERIFIABLE


def test_unsupported_email_is_high_severity_risk():
    criteria = make_criteria(expected_answer="Refunds are available within 30 days.")
    result = evaluate_single(criteria, "Receipt sent to bob@example.com already.")

    finding = next(f for f in result.findings if f.rule_id == "HAL_UNSUPPORTED_EMAIL")
    assert finding.verification == Verification.RISK
    assert finding.severity == Severity.HIGH


def test_identifier_present_in_grounding_is_not_flagged():
    criteria = make_criteria(
        expected_answer="Refunds are available within 30 days.",
        referenced_facts=["Replies go to support@acme.example."],
    )
    result = evaluate_single(criteria, "A reply was sent to support@acme.example.")

    assert "HAL_UNSUPPORTED_EMAIL" not in {f.rule_id for f in result.findings}


def test_contradicted_labelled_value_is_verified_and_forces_failure():
    criteria = make_criteria(
        expected_answer="Refunds are available within 30 days of purchase.",
        referenced_facts=["The refund window is 30 days."],
    )
    response = (
        "The refund window is 45 days for this customer, so a refund can be processed."
    )
    result = evaluate_single(criteria, response)

    finding = next(f for f in result.findings if f.rule_id == "HAL_CONTRADICTED_VALUE")
    assert finding.verification == Verification.VERIFIED
    assert result.details["verdict"] == VERDICT_CONTRADICTION
    assert result.forced_fail is True
    assert result.passed is False


def test_unsupported_absolute_claim_is_a_risk():
    criteria = make_criteria(expected_answer="Refunds are available within 30 days.")
    result = evaluate_single(criteria, "We are the fastest refund team in the world.")

    assert "HAL_UNSUPPORTED_ABSOLUTE_CLAIM" in {f.rule_id for f in result.findings}


def test_counts_separate_risk_from_verified_findings():
    criteria = make_criteria(expected_answer="Refunds are available within 30 days.")
    result = evaluate_single(
        criteria,
        "You will receive 1499 dollars back and a receipt went to bob@example.com.",
    )

    assert result.details["risk_finding_count"] >= 2
    assert result.details["verified_finding_count"] == 0


def test_no_finding_is_ever_labelled_a_verified_hallucination_by_default():
    criteria = make_criteria()
    result = evaluate_single(criteria, "Contact us at help@acme.example about order 55021.")

    for finding in result.findings:
        if finding.dimension.value == "hallucination_risk":
            assert finding.verification in {Verification.RISK, Verification.VERIFIED}