from tests.conftest import BAD_RESPONSE, case_payload, responses_for

API = "/api/v1"


def test_create_read_update_and_delete_suite(client, suite):
    assert suite["test_case_count"] == 2
    assert [t["position"] for t in suite["test_cases"]] == [0, 1]

    fetched = client.get(f"{API}/suites/{suite['id']}").json()
    assert fetched["name"] == suite["name"]

    updated = client.patch(
        f"{API}/suites/{suite['id']}", json={"description": "updated", "tags": ["qa"]}
    ).json()
    assert updated["description"] == "updated"
    assert updated["tags"] == ["qa"]

    assert client.delete(f"{API}/suites/{suite['id']}").status_code == 204
    assert client.get(f"{API}/suites/{suite['id']}").status_code == 404


def test_duplicate_suite_name_conflicts(client, suite):
    response = client.post(f"{API}/suites", json={"name": suite["name"]})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUITE_CONFLICT"


def test_missing_suite_returns_404(client):
    assert client.get(f"{API}/suites/nope").status_code == 404
    assert client.get(f"{API}/suites/nope/executions").status_code == 404


def test_suite_membership_can_be_extended_and_pruned(client, suite, test_case):
    extra = client.post(f"{API}/test-cases", json=case_payload(name="Third case")).json()

    added = client.post(
        f"{API}/suites/{suite['id']}/test-cases", json={"test_case_ids": [extra["id"]]}
    ).json()
    assert added["test_case_count"] == 3

    pruned = client.delete(f"{API}/suites/{suite['id']}/test-cases/{extra['id']}").json()
    assert pruned["test_case_count"] == 2


def test_adding_an_unknown_test_case_is_rejected(client, suite):
    response = client.post(
        f"{API}/suites/{suite['id']}/test-cases", json={"test_case_ids": ["nope"]}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TEST_CASE_NOT_FOUND"


def test_adding_the_same_case_twice_is_a_no_op(client, suite, test_case):
    body = client.post(
        f"{API}/suites/{suite['id']}/test-cases", json={"test_case_ids": [test_case["id"]]}
    ).json()

    assert body["test_case_count"] == 2


def test_execute_suite_with_good_responses_passes(client, suite, test_case, second_case):
    body = client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={"responses": responses_for(test_case, second_case), "agent_name": "v1"},
    ).json()

    assert body["status"] == "completed"
    assert body["verdict"] == "pass"
    assert body["evaluated_cases"] == 2
    assert body["passed_cases"] == 2
    assert body["failed_cases"] == 0
    assert body["skipped_cases"] == 0
    assert body["overall_score"] > 0
    assert body["failure_categories"] == {}
    assert body["failure_intelligence"]["total_failures"] == 0
    assert body["max_severity"] in {"none", "info", "low", "medium"}
    assert all(r["status"] == "evaluated" and r["passed"] for r in body["results"])


def test_execute_suite_records_a_skip_when_no_response_is_supplied(
    client, suite, test_case, second_case
):
    responses = {test_case["id"]: [test_case["sample_good_response"]]}
    body = client.post(
        f"{API}/suites/{suite['id']}/execute", json={"responses": responses}
    ).json()

    assert body["status"] == "partial"
    assert body["verdict"] == "fail"
    assert body["evaluated_cases"] == 1
    assert body["skipped_cases"] == 1
    skipped = next(r for r in body["results"] if r["status"] == "skipped")
    assert skipped["passed"] is False
    assert skipped["test_case_id"] == second_case["id"]


def test_skipping_every_case_never_reports_success(client, suite):
    body = client.post(f"{API}/suites/{suite['id']}/execute", json={}).json()

    assert body["evaluated_cases"] == 0
    assert body["skipped_cases"] == 2
    assert body["verdict"] == "fail"
    assert body["status"] == "partial"


def test_execute_suite_with_a_bad_response_classifies_failures(
    client, suite, test_case, second_case
):
    responses = responses_for(second_case)
    responses[test_case["id"]] = [BAD_RESPONSE]

    body = client.post(f"{API}/suites/{suite['id']}/execute", json={"responses": responses}).json()

    assert body["status"] == "failed"
    assert body["verdict"] == "fail"
    assert body["failed_cases"] == 1
    assert body["passed_cases"] == 1
    assert body["max_severity"] == "critical"
    assert body["failure_categories"]["policy_violation"] >= 1
    assert body["failure_categories"]["hallucination_risk"] >= 1

    intelligence = body["failure_intelligence"]
    assert intelligence["critical_count"] >= 1
    assert intelligence["verified_count"] > 0
    assert intelligence["risk_count"] > 0
    assert all(e["remediation"] for e in intelligence["explanations"])


def test_responses_can_be_keyed_by_test_case_name(client, suite, test_case, second_case):
    body = client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={
            "responses": {
                test_case["name"]: [test_case["sample_good_response"]],
                second_case["name"]: [second_case["sample_good_response"]],
            }
        },
    ).json()

    assert body["evaluated_cases"] == 2


def test_execution_summary_text_is_generated(client, suite, test_case, second_case):
    body = client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={"responses": responses_for(test_case, second_case)},
    ).json()

    assert "Support regression suite" in body["report"]["summary"]
    assert "2 passed" in body["report"]["summary"]


def test_suite_execution_persists_case_level_runs(client, suite, test_case, second_case):
    body = client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={"responses": responses_for(test_case, second_case)},
    ).json()

    run_ids = [r["run_id"] for r in body["results"]]
    assert all(run_ids)
    for run_id in run_ids:
        assert client.get(f"{API}/evaluations/runs/{run_id}").status_code == 200


def test_execution_history_and_single_execution_lookup(client, suite, test_case, second_case):
    client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={"responses": responses_for(test_case, second_case)},
    )
    client.post(
        f"{API}/suites/{suite['id']}/execute", json={"responses": responses_for(test_case)}
    )

    history = client.get(f"{API}/suites/{suite['id']}/executions").json()
    assert history["total"] == 2

    execution_id = history["items"][0]["id"]
    detail = client.get(f"{API}/suites/executions/{execution_id}").json()
    assert detail["id"] == execution_id
    assert len(detail["results"]) == 2
    assert detail["report"]["totals"]["total_cases"] == 2

    assert client.get(f"{API}/suites/executions/all").json()["total"] == 2


def test_suite_execution_export_is_a_json_download(client, suite, test_case, second_case):
    execution_id = client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={"responses": responses_for(test_case, second_case)},
    ).json()["id"]

    response = client.get(f"{API}/suites/executions/{execution_id}/export")

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    payload = response.json()
    assert payload["meta"]["kind"] == "suite_execution"
    assert payload["suite_execution"]["suite_id"] == suite["id"]
    assert len(payload["report"]["case_reports"]) == 2


def test_missing_suite_execution_returns_404(client):
    assert client.get(f"{API}/suites/executions/nope").status_code == 404
    assert client.get(f"{API}/suites/executions/nope/export").status_code == 404


def test_executing_an_empty_suite_is_rejected(client):
    created = client.post(f"{API}/suites", json={"name": "Empty suite"}).json()
    response = client.post(f"{API}/suites/{created['id']}/execute", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUITE_EMPTY"


def test_deleting_a_suite_removes_its_execution_history(client, suite, test_case, second_case):
    client.post(
        f"{API}/suites/{suite['id']}/execute",
        json={"responses": responses_for(test_case, second_case)},
    )

    client.delete(f"{API}/suites/{suite['id']}")
    assert client.get(f"{API}/suites/executions/all").json()["total"] == 0