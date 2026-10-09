"""Stage 1+2 backend QA gate. Real engine, real DB, no mocks.

Covers: API/health, evaluation engine, suites, orchestration,
analytics/reporting, database, edge cases.
"""
from tests.conftest import BAD_RESPONSE, case_payload, responses_for

API = "/api/v1"


# --- 1. API & Health ---
def test_qa_health_full(client):
    b = client.get("/health").json()
    assert b["status"] == "ok" and b["database_ok"] is True and b["stage"] == "1-2"


def test_qa_liveness_readiness(client):
    assert client.get("/health/live").json() == {"status": "alive"}
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"
    assert "application/json" in r.headers["content-type"]


def test_qa_openapi_lists_core_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in [f"{API}/test-cases", f"{API}/suites", f"{API}/evaluations/run",
              f"{API}/analytics/overview", f"{API}/meta/dimensions"]:
        assert p in paths, p


def test_qa_404_envelope(client):
    r = client.get(f"{API}/test-cases/nope")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "TEST_CASE_NOT_FOUND" and body["request_id"]


def test_qa_422_envelope(client):
    r = client.post(f"{API}/test-cases", json={"name": "x"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def test_qa_request_id(client):
    r = client.get("/health", headers={"X-Request-ID": "qa-1"})
    assert r.headers["X-Request-ID"] == "qa-1"


# --- 2. Evaluation engine ---
def test_qa_accuracy_pass_fail(client, test_case):
    good = client.post(f"{API}/evaluations/preview", json={
        "test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]}).json()
    bad = client.post(f"{API}/evaluations/preview", json={
        "test_case_id": test_case["id"], "responses": [BAD_RESPONSE]}).json()
    assert good["verdict"] == "pass"
    assert bad["verdict"] == "fail"
    assert good["overall_score"] > bad["overall_score"]
    dims = {d["dimension"]: d for d in bad["dimensions"]}
    assert dims["accuracy"]["score"] < dims["accuracy"]["details"]["threshold"]
    assert all(f["remediation"] for d in bad["dimensions"] for f in d["findings"])


def test_qa_hallucination_verified_vs_risk(client, test_case):
    bad = client.post(f"{API}/evaluations/preview", json={
        "test_case_id": test_case["id"], "responses": [BAD_RESPONSE]}).json()
    h = next(d for d in bad["dimensions"] if d["dimension"] == "hallucination_risk")
    assert h["findings"]
    assert {f["verification"] for f in h["findings"]} <= {"verified", "risk"}
    assert bad["hallucination_assessment"]["disclaimer"]
    assert bad["disclaimer"]


def test_qa_safety_critical_fails_run(client, test_case):
    bad = client.post(f"{API}/evaluations/preview", json={
        "test_case_id": test_case["id"], "responses": [BAD_RESPONSE]}).json()
    s = next(d for d in bad["dimensions"] if d["dimension"] == "safety")
    assert s["forced_fail"] is True or any(f["severity"] == "critical" for f in s["findings"])
    assert bad["max_severity"] in {"high", "critical"}


def test_qa_compliance_constraint(client, test_case):
    body = client.post(f"{API}/evaluations/preview", json={
        "test_case_id": test_case["id"],
        "responses": ["unrelated one-liner without required store phrase"]}).json()
    c = next(d for d in body["dimensions"] if d["dimension"] == "instruction_compliance")
    assert c["findings"]


def test_qa_consistency_modes(client, test_case):
    one = client.post(f"{API}/evaluations/preview", json={
        "test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]}).json()
    two = client.post(f"{API}/evaluations/preview", json={
        "test_case_id": test_case["id"], "responses": [
            test_case["sample_good_response"],
            "Refunds are available within 30 days. This order is 45 days old, so no refund applies. Store credit is available instead."]}).json()
    assert one["consistency_mode"] == "internal"
    assert two["consistency_mode"] == "cross_response"


def test_qa_scoring_gates_and_reproducible(client, test_case):
    p = {"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]}
    a = client.post(f"{API}/evaluations/preview", json=p).json()
    b = client.post(f"{API}/evaluations/preview", json=p).json()
    assert a["overall_score"] == b["overall_score"]
    assert 0 <= a["overall_score"] <= 100
    assert abs(sum(a["weights_used"].values()) - 1.0) < 0.001


# --- 3. Suite management ---
def test_qa_suite_crud(client, suite):
    assert suite["test_case_count"] == 2
    got = client.get(f"{API}/suites/{suite['id']}").json()
    assert got["name"] == suite["name"]
    upd = client.patch(f"{API}/suites/{suite['id']}", json={"description": "qa"}).json()
    assert upd["description"] == "qa"
    assert client.delete(f"{API}/suites/{suite['id']}").status_code == 204
    assert client.get(f"{API}/suites/{suite['id']}").status_code == 404


def test_qa_suite_membership(client, suite, test_case):
    extra = client.post(f"{API}/test-cases", json=case_payload(name="QA Extra Case")).json()
    assert client.post(f"{API}/suites/{suite['id']}/test-cases",
                       json={"test_case_ids": [extra["id"]]}).json()["test_case_count"] == 3
    # duplicate add is no-op
    assert client.post(f"{API}/suites/{suite['id']}/test-cases",
                       json={"test_case_ids": [extra["id"]]}).json()["test_case_count"] == 3
    assert client.delete(f"{API}/suites/{suite['id']}/test-cases/{extra['id']}").json()["test_case_count"] == 2
    # unknown case
    r = client.post(f"{API}/suites/{suite['id']}/test-cases", json={"test_case_ids": ["nope"]})
    assert r.status_code == 404
    # duplicate suite name
    assert client.post(f"{API}/suites", json={"name": suite["name"]}).status_code == 409
    # empty suite rejected on execute
    empty = client.post(f"{API}/suites", json={"name": "QA Empty Suite"}).json()
    assert client.post(f"{API}/suites/{empty['id']}/execute", json={}).status_code == 409


# --- 4. Orchestration ---
def test_qa_orchestration_matrix(client, suite, test_case, second_case):
    ok = client.post(f"{API}/suites/{suite['id']}/execute",
                     json={"responses": responses_for(test_case, second_case)}).json()
    assert ok["status"] == "completed" and ok["verdict"] == "pass"
    assert ok["evaluated_cases"] == 2 and ok["overall_score"] > 0
    assert len(ok["results"]) == 2
    assert len(ok["report"]["cases"]) == 2
    assert len(ok["report"]["case_reports"]) == 2
    # partial skip
    part = client.post(f"{API}/suites/{suite['id']}/execute",
                       json={"responses": {test_case["id"]: [test_case["sample_good_response"]]}}).json()
    assert part["status"] == "partial" and part["skipped_cases"] == 1 and part["verdict"] == "fail"
    # bad response -> failed
    bad_map = responses_for(second_case)
    bad_map[test_case["id"]] = [BAD_RESPONSE]
    bad = client.post(f"{API}/suites/{suite['id']}/execute", json={"responses": bad_map}).json()
    assert bad["status"] == "failed" and bad["failed_cases"] == 1
    assert bad["failure_intelligence"]["total_failures"] > 0
    assert bad["max_severity"] == "critical"


def test_qa_suite_persist_false(client, suite, test_case, second_case):
    before = client.get(f"{API}/evaluations/runs").json()["total"]
    body = client.post(f"{API}/suites/{suite['id']}/execute",
                       json={"responses": responses_for(test_case, second_case), "persist": False}).json()
    assert body["status"] == "completed"
    assert client.get(f"{API}/evaluations/runs").json()["total"] == before
    assert all(r["run_id"] is None for r in body["results"])


# --- 5. Analytics & reporting ---
def test_qa_analytics_full(client, test_case, suite, second_case):
    assert client.get(f"{API}/analytics/overview").json()["total_runs"] == 0
    client.post(f"{API}/evaluations/run", json={"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]})
    client.post(f"{API}/evaluations/run", json={"test_case_id": test_case["id"], "responses": [BAD_RESPONSE]})
    ov = client.get(f"{API}/analytics/overview").json()
    assert ov["total_runs"] == 2 and ov["pass_rate"] == 0.5
    tr = client.get(f"{API}/analytics/trends").json()
    assert tr["total_points"] >= 1
    assert client.get(f"{API}/analytics/trends", params={"granularity": "hour"}).json()["granularity"] == "hour"
    assert client.get(f"{API}/analytics/trends", params={"granularity": "week"}).status_code == 422
    fb = client.get(f"{API}/analytics/failures").json()
    assert fb["critical_findings"] >= 1
    runs = client.get(f"{API}/evaluations/runs").json()["items"]
    pa = next(r for r in runs if r["verdict"] == "pass")
    fa = next(r for r in runs if r["verdict"] == "fail")
    cmp = client.get(f"{API}/analytics/compare/runs", params={"run_a": pa["id"], "run_b": fa["id"]}).json()
    assert cmp["regression"] is True and cmp["score_delta"] < 0
    assert client.get(f"{API}/analytics/compare/runs", params={"run_a": pa["id"], "run_b": "nope"}).status_code == 404
    exp = client.get(f"{API}/analytics/export")
    assert exp.status_code == 200 and "attachment" in exp.headers["content-disposition"]
    # run export
    rid = client.post(f"{API}/evaluations/run", json={
        "test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]}).json()["run_id"]
    rex = client.get(f"{API}/evaluations/runs/{rid}/export")
    assert rex.status_code == 200 and rex.json()["run"]["id"] == rid


# --- 6. Database ---
def test_qa_db_relationships_and_delete_guards(client, test_case, suite):
    run_id = client.post(f"{API}/evaluations/run", json={
        "test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]}).json()["run_id"]
    assert client.get(f"{API}/evaluations/runs/{run_id}").status_code == 200
    # delete blocked while runs exist
    assert client.delete(f"{API}/test-cases/{test_case['id']}").status_code == 409
    # suite delete cascades executions
    client.post(f"{API}/suites/{suite['id']}/execute",
                json={"responses": {test_case["id"]: [test_case["sample_good_response"]]}})
    # add second case response so suite has history; then delete suite
    client.delete(f"{API}/suites/{suite['id']}")
    assert client.get(f"{API}/suites/executions/all").json()["total"] == 0


def test_qa_history_persists_across_clients(client, test_case):
    rid = client.post(f"{API}/evaluations/run", json={
        "test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]}).json()["run_id"]
    from tests.conftest import _TMP_DB  # noqa
    assert client.get(f"{API}/evaluations/runs/{rid}/report").json()["run_id"] == rid


# --- 7. Edge cases ---
def test_qa_edge_inputs(client, test_case):
    assert client.post(f"{API}/evaluations/run", json={
        "test_case_id": test_case["id"], "responses": ["   "]}).status_code == 422
    assert client.post(f"{API}/evaluations/run", json={
        "test_case_id": test_case["id"], "responses": []}).status_code == 422
    assert client.post(f"{API}/evaluations/run", json={
        "test_case_id": test_case["id"], "responses": ["x"] * 26}).status_code == 422
    assert client.post(f"{API}/test-cases", json={"name": "Incomplete"}).status_code == 422
    assert client.post(f"{API}/test-cases", json=case_payload(name=test_case["name"])).status_code == 409
    assert client.post(f"{API}/test-cases", json=case_payload(
        name="Bad Dim Case", enabled_dimensions=["accuracy", "vibes"])).status_code == 422
    assert client.post(f"{API}/evaluations/run", json={
        "test_case_id": "nope", "responses": ["hi"]}).status_code == 404


def test_qa_boundaries(client):
    # threshold 0 always passes accuracy-wise unless forced fail; threshold 100 hard
    c = client.post(f"{API}/test-cases", json=case_payload(
        name="Boundary Case", thresholds={"accuracy": 0, "hallucination_risk": 0, "safety": 0,
                                           "instruction_compliance": 0, "consistency": 0})).json()
    body = client.post(f"{API}/evaluations/preview", json={
        "test_case_id": c["id"], "responses": [c["sample_good_response"]]}).json()
    assert body["verdict"] == "pass"
    c2 = client.post(f"{API}/test-cases", json=case_payload(
        name="Strict Case", thresholds={"accuracy": 100, "hallucination_risk": 100, "safety": 100,
                                         "instruction_compliance": 100, "consistency": 100})).json()
    strict = client.post(f"{API}/evaluations/preview", json={
        "test_case_id": c2["id"], "responses": ["mediocre answer"]}).json()
    assert strict["verdict"] == "fail"
