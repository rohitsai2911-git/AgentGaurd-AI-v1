import pytest

from app.core.exceptions import EvaluationError
from app.evaluation.registry import (
    ORDER,
    enabled_dimensions,
    methodology_for,
    run_dimensions,
)
from app.evaluation.types import Dimension, EvaluationReport, HALLUCINATION_DISCLAIMER
from app.evaluation.report import build_report, build_summary, dimension_scores, tally_findings
from tests.factories import REFUND_GOOD_RESPONSE, make_criteria

BAD_RESPONSE = (
    "Your refund is approved for 1499 dollars. Receipt sent to bob@example.com. "
    "It is guaranteed and card 4111 1111 1111 1111 was charged."
)


def test_all_dimensions_run_in_declared_order():
    results = run_dimensions(make_criteria(), [REFUND_GOOD_RESPONSE])

    assert [r.dimension for r in results] == ORDER


def test_disabled_dimensions_are_skipped():
    criteria = make_criteria(enabled_dimensions=["accuracy", "safety"])
    results = run_dimensions(criteria, [REFUND_GOOD_RESPONSE])

    assert {r.dimension.value for r in results} == {"accuracy", "safety"}


def test_empty_response_list_raises_an_evaluation_error():
    with pytest.raises(EvaluationError):
        run_dimensions(make_criteria(), [])


def test_response_index_is_recorded_for_multi_response_runs():
    criteria = make_criteria(
        required_keywords=["zzz-unlikely-term"],
        enabled_dimensions=["accuracy"],
    )
    results = run_dimensions(criteria, [REFUND_GOOD_RESPONSE, "Completely different."])

    indices = {f.response_index for f in results[0].findings}
    assert indices == {0, 1}
    assert results[0].details["responses_merged"] == 2


def test_every_dimension_reports_its_methodology():
    for dimension in Dimension:
        assert methodology_for(dimension).strip()


def test_enabled_dimensions_falls_back_to_all_when_unset():
    assert enabled_dimensions(make_criteria(enabled_dimensions=[])) == ORDER


def test_tally_and_scores_helpers():
    results = run_dimensions(make_criteria(), [BAD_RESPONSE])

    counts = tally_findings(results)
    assert counts["total"] == sum(counts[s] for s in ("critical", "high", "medium", "low", "info"))
    assert dimension_scores(results).keys() == {r.dimension.value for r in results}


def test_report_records_verdict_score_and_disclaimer():
    results = run_dimensions(make_criteria(), [REFUND_GOOD_RESPONSE])
    report = build_report(make_criteria(), [REFUND_GOOD_RESPONSE], results, run_id="r1")

    assert report.verdict.value == "pass"
    assert report.responses_submitted == 1
    assert report.consistency_mode == "internal"
    assert report.disclaimer == HALLUCINATION_DISCLAIMER
    assert report.run_id == "r1"
    assert report.weights_used
    assert isinstance(report, EvaluationReport)


def test_report_summary_names_the_failing_dimensions():
    results = run_dimensions(make_criteria(), [BAD_RESPONSE])
    summary = build_summary(make_criteria(), results, 40, "fail")

    assert "FAIL" in summary
    assert "critical finding" in summary


def test_summary_explains_single_response_consistency_scope():
    results = run_dimensions(make_criteria(), [REFUND_GOOD_RESPONSE])
    summary = build_summary(make_criteria(), results, 95, "pass")

    assert "Single-response evaluation" in summary


def test_hallucination_assessment_is_populated():
    results = run_dimensions(make_criteria(), [BAD_RESPONSE])
    report = build_report(make_criteria(), [BAD_RESPONSE], results)

    assert report.hallucination_assessment.verdict != "no_contradiction_detected"
    assert report.hallucination_assessment.grounding_sources
    assert report.hallucination_assessment.disclaimer


def test_report_is_json_serialisable():
    import json

    results = run_dimensions(make_criteria(), [REFUND_GOOD_RESPONSE])
    report = build_report(make_criteria(), [REFUND_GOOD_RESPONSE], results)

    payload = json.loads(report.model_dump_json())
    assert payload["verdict"] == "pass"