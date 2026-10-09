import pytest

from app.evaluation.types import Severity
from tests.conftest import BAD_RESPONSE, case_payload, responses_for

API = "/api/v1"


def test_health_reports_database_state(client):
    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["database_ok"] is True
    assert body["stage"] == "1-2"
    assert client.get("/health/live").json() == {"status": "alive"}
    assert client.get("/health/ready").json()["status"] == "ready"


def test_index_advertises_the_docs(client):
    body = client.get("/").json()

    assert body["docs"] == "/docs"
    assert "frontend pending" in body["stage"]


def test_openapi_document_is_served(client):
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "AgentGuard AI"
    assert f"{API}/suites/{{suite_id}}/execute" in schema["paths"]


def test_create_and_read_test_case(client):
    created = client.post(f"{API}/test-cases", json=case_payload()).json()
    fetched = client.get(f"{API}/test-cases/{created['id']}").json()

    assert fetched["name"] == created["name"]
    assert fetched["constraints"][0]["type"] == "max_words"
    assert fetched["sample_good_response"]


def test_duplicate_test_case_name_conflicts(client, test_case):
    response = client.post(f"{API}/test-cases", json=case_payload())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TEST_CASE_CONFLICT"
    assert response.json()["request_id"]


def test_missing_test_case_returns_404_envelope(client):
    response = client.get(f"{API}/test-cases/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TEST_CASE_NOT_FOUND"


def test_validation_error_lists_offending_fields(client):
    response = client.post(f"{API}/test-cases", json={"name": "x"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert any("input_prompt" in field["field"] for field in body["error"]["details"]["fields"])


def test_unknown_dimension_is_rejected(client):
    response = client.post(
        f"{API}/test-cases", json=case_payload(enabled_dimensions=["accuracy", "vibes"])
    )

    assert response.status_code == 422


def test_list_and_filter_test_cases(client, test_case):
    client.post(f"{API}/test-cases", json=case_payload(name="Other case", scenario_tags=["shipping"]))

    assert client.get(f"{API}/test-cases").json()["total"] == 2
    assert client.get(f"{API}/test-cases", params={"tag": "refund"}).json()["total"] == 1
    assert client.get(
        f"{API}/test-cases", params={"agent_name": "support-agent-v1"}
    ).json()["total"] == 2
    assert client.get(f"{API}/test-cases", params={"agent_name": "nope"}).json()["total"] == 0


def test_patch_updates_only_supplied_fields(client, test_case):
    updated = client.patch(
        f"{API}/test-cases/{test_case['id']}", json={"description": "new description"}
    ).json()

    assert updated["description"] == "new description"
    assert updated["name"] == test_case["name"]


def test_patch_to_an_existing_name_conflicts(client, test_case, second_case):
    response = client.patch(
        f"{API}/test-cases/{test_case['id']}", json={"name": second_case["name"]}
    )

    assert response.status_code == 409


def test_delete_is_blocked_while_runs_exist(client, test_case):
    client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]},
    )
    response = client.delete(f"{API}/test-cases/{test_case['id']}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TEST_CASE_HAS_RUNS"


def test_delete_succeeds_without_runs(client, test_case):
    assert client.delete(f"{API}/test-cases/{test_case['id']}").status_code == 204
    assert client.get(f"{API}/test-cases/{test_case['id']}").status_code == 404


def test_run_persists_and_returns_a_full_report(client, test_case):
    response = client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["verdict"] == "pass"
    assert body["overall_score"] > 0
    assert len(body["dimensions"]) == 5
    assert body["run_id"]
    assert body["disclaimer"]
    assert client.get(f"{API}/evaluations/runs").json()["total"] == 1


def test_preview_does_not_persist(client, test_case):
    response = client.post(
        f"{API}/evaluations/preview",
        json={"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]},
    )

    assert response.status_code == 200
    assert response.json()["run_id"] is None
    assert client.get(f"{API}/evaluations/runs").json()["total"] == 0


def test_bad_response_fails_with_actionable_findings(client, test_case):
    body = client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": test_case["id"], "responses": [BAD_RESPONSE]},
    ).json()

    assert body["verdict"] == "fail"
    assert body["max_severity"] in {"high", "critical"}
    findings = [f for d in body["dimensions"] for f in d["findings"]]
    assert findings
    assert all(f["remediation"] for f in findings)
    assert all(f["verification"] in {"verified", "risk"} for f in findings)
    assert body["hallucination_assessment"]["disclaimer"]


def test_evaluation_is_reproducible(client, test_case):
    payload = {"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]}
    first = client.post(f"{API}/evaluations/preview", json=payload).json()
    second = client.post(f"{API}/evaluations/preview", json=payload).json()

    for key in ("overall_score", "verdict", "max_severity", "weights_used"):
        assert first[key] == second[key]
    assert [d["score"] for d in first["dimensions"]] == [d["score"] for d in second["dimensions"]]


def test_run_history_filters_by_verdict_and_case(client, test_case, second_case):
    client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]},
    )
    client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": test_case["id"], "responses": [BAD_RESPONSE]},
    )
    client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": second_case["id"], "responses": [BAD_RESPONSE]},
    )

    assert client.get(f"{API}/evaluations/runs", params={"verdict": "pass"}).json()["total"] == 1
    assert client.get(f"{API}/evaluations/runs", params={"verdict": "fail"}).json()["total"] == 2
    assert client.get(
        f"{API}/evaluations/runs", params={"test_case_id": test_case["id"]}
    ).json()["total"] == 2


def test_run_detail_and_stored_report(client, test_case):
    run_id = client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]},
    ).json()["run_id"]

    detail = client.get(f"{API}/evaluations/runs/{run_id}").json()
    report = client.get(f"{API}/evaluations/runs/{run_id}/report").json()

    assert detail["dimension_scores"]
    assert report["run_id"] == run_id
    assert report["verdict"] == "pass"


def test_run_failure_intelligence_endpoint(client, test_case):
    run_id = client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": test_case["id"], "responses": [BAD_RESPONSE]},
    ).json()["run_id"]

    body = client.get(f"{API}/evaluations/runs/{run_id}/failures").json()

    assert body["total_failures"] > 0
    assert body["verified_count"] + body["risk_count"] == body["total_failures"]
    assert body["narrative"]


def test_run_export_is_a_json_download(client, test_case):
    run_id = client.post(
        f"{API}/evaluations/run",
        json={"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]},
    ).json()["run_id"]

    response = client.get(f"{API}/evaluations/runs/{run_id}/export")

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.json()["meta"]["kind"] == "run"
    assert response.json()["run"]["id"] == run_id


def test_missing_run_returns_404(client):
    assert client.get(f"{API}/evaluations/runs/nope").status_code == 404
    assert client.get(f"{API}/evaluations/runs/nope/report").status_code == 404


def test_empty_responses_are_rejected(client, test_case):
    response = client.post(
        f"{API}/evaluations/run", json={"test_case_id": test_case["id"], "responses": ["   "]}
    )

    assert response.status_code == 422


def test_multi_response_run_uses_cross_response_consistency(client, test_case):
    body = client.post(
        f"{API}/evaluations/run",
        json={
            "test_case_id": test_case["id"],
            "responses": [
                test_case["sample_good_response"],
                "Refunds are available within 30 days. This order is 45 days old, so no "
                "refund applies. Store credit is available instead.",
            ],
        },
    ).json()

    consistency = next(d for d in body["dimensions"] if d["dimension"] == "consistency")
    assert body["consistency_mode"] == "cross_response"
    assert consistency["details"]["mode"] == "cross_response"


def test_meta_endpoints_document_the_engine(client):
    dimensions = client.get(f"{API}/meta/dimensions").json()
    rules = client.get(f"{API}/meta/safety-rules").json()
    constraints = client.get(f"{API}/meta/constraint-types").json()
    modes = client.get(f"{API}/meta/consistency-modes").json()
    disclaimer = client.get(f"{API}/meta/disclaimer").json()

    assert len(dimensions["dimensions"]) == 5
    assert all(entry["methodology"] for entry in dimensions["dimensions"])
    assert round(sum(entry["default_weight"] for entry in dimensions["dimensions"]), 4) == 1.0
    assert rules["count"] == 10
    assert constraints["count"] == 8
    assert len(modes["modes"]) == 2
    assert disclaimer["verified_means"]


def test_seed_is_idempotent_and_removable(client):
    first = client.post(f"{API}/admin/seed").json()
    second = client.post(f"{API}/admin/seed").json()

    assert first["test_cases_created"] == 6
    assert second["test_cases_created"] == 0
    assert second["test_cases_skipped"] == 6
    assert first["suites_created"] == 1
    assert second["suites_created"] == 0
    assert client.get(f"{API}/test-cases").json()["total"] == 6
    assert client.get(f"{API}/suites").json()["total"] == 1

    removed = client.delete(f"{API}/admin/seed").json()
    assert removed["test_cases_removed"] == 6
    assert client.get(f"{API}/test-cases").json()["total"] == 0


def test_seed_demo_runs_produce_real_history(client):
    client.post(f"{API}/admin/seed")
    body = client.post(f"{API}/admin/seed/demo-runs").json()

    assert body["runs_created"] > 0
    runs = client.get(f"{API}/evaluations/runs").json()
    assert runs["total"] == body["runs_created"]
    assert all(item["verdict"] == "pass" for item in runs["items"])


def test_every_seeded_case_passes_its_sample_response(client):
    client.post(f"{API}/admin/seed")
    for case in client.get(f"{API}/test-cases").json()["items"]:
        report = client.post(
            f"{API}/evaluations/preview",
            json={"test_case_id": case["id"], "responses": [case["sample_good_response"]]},
        ).json()
        failing = [d["dimension"] for d in report["dimensions"] if not d["passed"]]
        assert report["verdict"] == "pass", f"{case['name']} failed: {failing}"


def test_request_id_is_echoed_and_correlated(client):
    response = client.get("/health", headers={"X-Request-ID": "trace-123"})

    assert response.headers["X-Request-ID"] == "trace-123"
    assert client.get("/health").headers["X-Request-ID"]


@pytest.mark.parametrize(
    "path",
    [
        "/test-cases",
        "/suites",
        "/evaluations/runs",
        "/analytics/overview",
        "/analytics/trends",
        "/analytics/failures",
        "/meta/dimensions",
    ],
)
def test_read_endpoints_are_listed_in_openapi(client, path):
    schema = client.get("/openapi.json").json()

    assert f"{API}{path}" in schema["paths"]