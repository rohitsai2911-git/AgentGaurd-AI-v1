import pytest

from app.evaluation.modules.accuracy import evaluate_single
from app.evaluation.modules.consistency import evaluate as evaluate_consistency
from app.evaluation.scoring import (
    clamp,
    compute_overall,
    default_thresholds,
    default_weights,
    effective_weights,
    merge_results,
)
from app.evaluation.types import (
    DEFAULT_THRESHOLDS,
    DEFAULT_WEIGHTS,
    Dimension,
    DimensionResult,
    Finding,
    Severity,
    Verification,
)
from tests.factories import REFUND_GOOD_RESPONSE, make_criteria


def _result(dimension, score, passed=True, findings=None, forced_fail=False):
    return DimensionResult(
        dimension=dimension,
        score=score,
        passed=passed,
        severity=Severity.NONE if not findings else findings[0].severity,
        findings=findings or [],
        methodology="test",
        details={"threshold": 70},
        forced_fail=forced_fail,
    )


def _finding(severity=Severity.HIGH, dimension=Dimension.SAFETY):
    return Finding(
        rule_id="TEST_RULE",
        dimension=dimension,
        severity=severity,
        verification=Verification.VERIFIED,
        message="test finding",
        evidence="evidence",
        remediation="fix it",
    )


def test_clamp_keeps_scores_in_range():
    assert clamp(-5) == 0
    assert clamp(140) == 100
    assert clamp(42.4) == 42


def test_default_weights_sum_to_one():
    assert round(sum(DEFAULT_WEIGHTS.values()), 6) == 1.0
    assert default_weights() == DEFAULT_WEIGHTS
    assert default_thresholds() == DEFAULT_THRESHOLDS


def test_overall_score_is_the_weighted_mean():
    criteria = make_criteria()
    results = [
        _result(Dimension.ACCURACY, 100),
        _result(Dimension.SAFETY, 0, passed=False),
        _result(Dimension.HALLUCINATION, 100),
        _result(Dimension.COMPLIANCE, 100),
        _result(Dimension.CONSISTENCY, 100),
    ]
    score, verdict, severity = compute_overall(criteria, results)

    assert score == 75
    assert verdict.value == "fail"
    assert severity == Severity.NONE


def test_disabled_dimension_redistributes_its_weight():
    criteria = make_criteria(enabled_dimensions=["accuracy", "safety"])
    results = [_result(Dimension.ACCURACY, 100), _result(Dimension.SAFETY, 0)]

    weights = effective_weights(criteria, results)
    score, _, _ = compute_overall(criteria, results)

    assert weights == {"accuracy": 0.5455, "safety": 0.4545}
    assert round(sum(weights.values()), 4) == 1.0
    assert score == 55


def test_critical_finding_blocks_pass_even_at_a_high_score():
    criteria = make_criteria()
    results = [_result(Dimension.SAFETY, 95, passed=False, findings=[_finding(Severity.CRITICAL)])]

    score, verdict, severity = compute_overall(criteria, results)

    assert score == 95
    assert verdict.value == "fail"
    assert severity == Severity.CRITICAL


def test_all_dimensions_passing_and_no_critical_yields_pass():
    criteria = make_criteria()
    results = [_result(d, 100) for d in Dimension]

    _, verdict, severity = compute_overall(criteria, results)

    assert verdict.value == "pass"
    assert severity == Severity.NONE


def test_one_failing_dimension_fails_the_run_regardless_of_score():
    criteria = make_criteria()
    results = [
        _result(Dimension.ACCURACY, 100),
        _result(Dimension.HALLUCINATION, 100),
        _result(Dimension.SAFETY, 100),
        _result(Dimension.COMPLIANCE, 100),
        _result(Dimension.CONSISTENCY, 30, passed=False),
    ]

    _, verdict, _ = compute_overall(criteria, results)

    assert verdict.value == "fail"


def test_merge_results_averages_scores_and_takes_max_severity():
    merged = merge_results(
        [
            _result(Dimension.ACCURACY, 80),
            _result(
                Dimension.ACCURACY,
                40,
                passed=False,
                findings=[_finding(Severity.HIGH, Dimension.ACCURACY)],
            ),
        ]
    )

    assert merged.score == 60
    assert merged.passed is False
    assert merged.severity == Severity.HIGH
    assert merged.details["responses_merged"] == 2
    assert len(merged.details["per_response"]) == 2


def test_merge_results_of_one_returns_the_same_object():
    single = _result(Dimension.ACCURACY, 80)
    assert merge_results([single]) is single


def test_scoring_is_deterministic():
    criteria = make_criteria()
    results = [_result(d, 70) for d in Dimension]
    first = compute_overall(criteria, results)
    second = compute_overall(criteria, results)

    assert first == second


def test_evaluation_modules_are_pure_and_repeatable():
    criteria = make_criteria(required_keywords=["refund", "30 days"])
    first = evaluate_single(criteria, REFUND_GOOD_RESPONSE)
    second = evaluate_single(criteria, REFUND_GOOD_RESPONSE)

    assert first.model_dump() == second.model_dump()


def test_consistency_module_is_pure_and_repeatable():
    responses = ["Refunds are available within 30 days.", "Refunds are available within 30 days."]
    assert evaluate_consistency(criteria_or_default(), responses).model_dump() == (
        evaluate_consistency(criteria_or_default(), responses).model_dump()
    )


def criteria_or_default():
    return make_criteria()


@pytest.mark.parametrize("dimension", list(Dimension))
def test_every_dimension_has_a_default_weight_and_threshold(dimension):
    assert dimension.value in DEFAULT_WEIGHTS
    assert dimension.value in DEFAULT_THRESHOLDS