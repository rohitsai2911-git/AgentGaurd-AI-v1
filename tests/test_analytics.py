from tests.conftest import BAD_RESPONSE, responses_for

API = "/api/v1"


def _run(client, case, response_text):
    return client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": case["id"], "responses": [response_text]},
    ).json()


def test_overview_is_zeroed_on_an_empty_database(client):
    body = client.get(f"{API}/analytics/overview").json()

    assert body["total_runs"] == 0
    assert body["pass_rate"] == 0.0
    assert body["average_overall_score"] == 0.0
    assert body["best_overall_score"] == 0


def test_overview_aggregates_runs(client, test_case):
    _run(client, test_case, test_case["sample_good_response"])
    _run(client, test_case, BAD_RESPONSE)

    body = client.get(f"{API}/analytics/overview").json()

    assert body["total_runs"] == 2
    assert body["pass_rate"] == 0.5
    assert body["fail_rate"] == 0.5
    assert body["best_overall_score"] > body["worst_overall_score"]
    assert 0 < body["average_overall_score"] <= 100


def test_overview_includes_suite_metrics(client, suite, test_case, second_case):
    client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={"responses": responses_for(test_case, second_case)},
    )

    body = client.get(f"{API}/analytics/overview").json()

    assert body["total_suites"] == 1
    assert body["total_suite_executions"] == 1
    assert body["suite_pass_rate"] == 1.0


def test_trends_bucket_by_day(client, test_case):
    _run(client, test_case, test_case["sample_good_response"])
    _run(client, test_case, BAD_RESPONSE)

    body = client.get(f"{API}/analytics/trends").json()

    assert body["granularity"] == "day"
    assert body["total_points"] == 1
    point = body["points"][0]
    assert point["total"] == 2
    assert point["passed"] == 1
    assert point["failed"] == 1
    assert point["pass_rate"] == 0.5
    assert point["max_severity"] == "critical"


def test_trends_support_hourly_granularity_and_case_filter(client, test_case, second_case):
    _run(client, test_case, BAD_RESPONSE)
    _run(client, second_case, second_case["sample_good_response"])

    hourly = client.get(f"{API}/analytics/trends", params={"granularity": "hour"}).json()
    assert hourly["granularity"] == "hour"
    assert hourly["points"][0]["bucket"].count("T") == 1

    scoped = client.get(
        f"{API}/analytics/trends", params={"test_case_id": second_case["id"]}
    ).json()
    assert scoped["points"][0]["total"] == 1
    assert scoped["points"][0]["passed"] == 1


def test_trends_can_include_suite_executions(client, suite, test_case, second_case):
    client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={"responses": responses_for(test_case, second_case)},
    )

    body = client.get(
        f"{API}/analytics/trends", params={"suite_id": suite["id"]}
    ).json()

    assert body["total_points"] == 1
    assert body["points"][0]["total"] == 1


def test_trends_reject_an_invalid_granularity(client):
    assert client.get(f"{API}/analytics/trends", params={"granularity": "week"}).status_code == 422


def test_failure_breakdown_is_empty_without_findings(client):
    body = client.get(f"{API}/analytics/failures").json()

    assert body["top_rules"] == []
    assert body["by_category"] == []
    assert body["critical_findings"] == 0


def test_failure_breakdown_categorises_and_ranks_rules(client, test_case):
    _run(client, test_case, BAD_RESPONSE)
    _run(client, test_case, BAD_RESPONSE)

    body = client.get(f"{API}/analytics/failures").json()

    categories = {entry["category"] for entry in body["by_category"]}
    assert {"accuracy_deviation", "hallucination_risk"} <= categories
    assert sum(entry["count"] for entry in body["by_category"]) > 0
    assert body["critical_findings"] >= 1
    assert body["verified_findings"] > 0
    assert body["risk_findings"] > 0

    counts = [rule["count"] for rule in body["top_rules"]]
    assert counts == sorted(counts, reverse=True)
    assert all(rule["rule_id"] and rule["verification"] in {"verified", "risk"} for rule in body["top_rules"])


def test_failure_breakdown_aggregates_per_dimension(client, test_case):
    _run(client, test_case, BAD_RESPONSE)

    dimensions = {d["dimension"]: d for d in client.get(f"{API}/analytics/failures").json()["by_dimension"]}

    assert set(dimensions) == {
        "accuracy",
        "hallucination_risk",
        "safety",
        "instruction_compliance",
        "consistency",
    }
    assert all(0 <= d["average_score"] <= 100 for d in dimensions.values())


def test_failure_breakdown_respects_the_limit(client, test_case):
    _run(client, test_case, BAD_RESPONSE)

    body = client.get(f"{API}/analytics/failures", params={"limit": 3}).json()

    assert len(body["top_rules"]) <= 3


def test_compare_two_runs_detects_a_regression(client, test_case):
    baseline = _run(client, test_case, test_case["sample_good_response"])
    candidate = _run(client, test_case, BAD_RESPONSE)

    body = client.get(
        f"{API}/analytics/compare/runs",
        params={"run_a": baseline["run_id"], "run_b": candidate["run_id"]},
    ).json()

    assert body["kind"] == "runs"
    assert body["score_delta"] < 0
    assert body["verdict_changed"] is True
    assert body["regression"] is True
    assert body["new_rules"]
    assert body["per_dimension_delta"]["safety"] < 0
    assert body["findings_delta"]["critical"] > 0


def test_compare_identical_runs_shows_no_change(client, test_case):
    first = _run(client, test_case, BAD_RESPONSE)
    second = _run(client, test_case, BAD_RESPONSE)

    body = client.get(
        f"{API}/analytics/compare/runs",
        params={"run_a": first["run_id"], "run_b": second["run_id"]},
    ).json()

    assert body["score_delta"] == 0
    assert body["verdict_changed"] is False
    assert body["new_rules"] == []
    assert body["resolved_rules"] == []


def test_compare_suite_executions(client, suite, test_case, second_case):
    good = client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={"responses": responses_for(test_case, second_case)},
    ).json()
    responses = responses_for(second_case)
    responses[test_case["id"]] = [BAD_RESPONSE]
    bad = client.post(f"{API}/suites/{suite['id']}/execute", json={"responses": responses}).json()

    body = client.get(
        f"{API}/analytics/compare/suite-executions",
        params={"a": good["id"], "b": bad["id"]},
    ).json()

    assert body["kind"] == "suite_executions"
    assert body["a"]["passed"] == 2
    assert body["b"]["failed"] == 1
    assert body["score_delta"] < 0
    assert body["regression"] is True


def test_compare_with_an_unknown_run_returns_404(client, test_case):
    run_id = _run(client, test_case, BAD_RESPONSE)["run_id"]

    response = client.get(
        f"{API}/analytics/compare/runs", params={"run_a": run_id, "run_b": "nope"}
    )

    assert response.status_code == 404


def test_analytics_export_bundle(client, test_case):
    _run(client, test_case, BAD_RESPONSE)

    response = client.get(f"{API}/analytics/export")

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    payload = response.json()
    assert payload["meta"]["kind"] == "analytics"
    assert set(payload) == {"meta", "overview", "trends", "failure_breakdown"}
    assert payload["overview"]["total_runs"] == 1