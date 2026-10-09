from app.evaluation.modules.consistency import (
    MODE_CROSS,
    MODE_INTERNAL,
    evaluate,
    mode_for,
)
from app.evaluation.types import Severity, Verification
from tests.factories import make_criteria

AGREEING = [
    "Refunds are available within 30 days of purchase for eligible orders.",
    "Refunds are available within 30 days of purchase on eligible orders.",
    "Refunds are available within 30 days of purchase when the order is eligible.",
]

CONTRADICTING = [
    "The refund amount of 500 dollars has been issued to your card.",
    "The refund amount of 900 dollars has been issued to your card.",
]

SELF_CONTRADICTING = (
    "The refund amount of 500 dollars was issued. The refund amount of 900 dollars was confirmed."
)

POLARITY = "Refunds are always available within 30 days. Refunds are never available within 30 days."


def test_mode_selection_matches_response_count():
    assert mode_for(1) == MODE_INTERNAL
    assert mode_for(2) == MODE_CROSS
    assert mode_for(5) == MODE_CROSS


def test_agreeing_responses_score_high_in_cross_mode():
    result = evaluate(make_criteria(), AGREEING)

    assert result.details["mode"] == MODE_CROSS
    assert result.passed is True
    assert result.score >= 70
    assert result.details["pairs_compared"] == 3


def test_cross_response_contradiction_is_verified_and_caps_score():
    result = evaluate(make_criteria(), CONTRADICTING)

    finding = next(
        f for f in result.findings if f.rule_id == "CON_CROSS_RESPONSE_CONTRADICTION"
    )
    assert finding.verification == Verification.VERIFIED
    assert finding.severity == Severity.HIGH
    assert result.score <= 40
    assert result.passed is False
    assert result.forced_fail is True


def test_single_response_contradiction_is_detected_in_internal_mode():
    result = evaluate(make_criteria(), [SELF_CONTRADICTING])

    assert result.details["mode"] == MODE_INTERNAL
    assert any(f.rule_id == "CON_SELF_CONTRADICTION" for f in result.findings)
    assert result.passed is False


def test_polarity_flip_is_reported_as_risk_not_verified():
    result = evaluate(make_criteria(), [POLARITY])

    finding = next(f for f in result.findings if f.rule_id == "CON_POLARITY_FLIP")
    assert finding.verification == Verification.RISK
    assert finding.severity == Severity.MEDIUM


def test_consistent_single_response_scores_one_hundred():
    result = evaluate(make_criteria(), ["Refunds are available within 30 days."])

    assert result.score == 100
    assert result.passed is True
    assert result.findings == []


def test_low_agreement_across_responses_is_flagged_as_risk():
    divergent = [
        "Bananas ripen quickly when stored near other fruit.",
        "Quarterly revenue rose across every operating segment.",
        "The library opens at nine on weekdays and closes at six.",
    ]
    result = evaluate(make_criteria(), divergent)

    assert result.passed is False
    assert any(f.rule_id == "CON_LOW_AGREEMENT" for f in result.findings)


def test_methodology_states_which_mode_ran():
    cross = evaluate(make_criteria(), AGREEING)
    internal = evaluate(make_criteria(), [SELF_CONTRADICTING])

    assert "Cross-response" in cross.methodology
    assert "Internal mode" in internal.methodology