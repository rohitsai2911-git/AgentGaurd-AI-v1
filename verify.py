"""Live HTTP verification against a running AgentGuard server."""

import json
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8077"
API = f"{BASE}/api/v1"
c = httpx.Client(base_url=BASE, timeout=30.0)
rows = []


def hit(method, path, body=None, expect=None, note=None):
    r = c.request(method, path, json=body)
    try:
        data = r.json()
    except Exception:
        data = {}
    label = f"{method:5} {path}"
    detail = note or ""
    if detail == "" and isinstance(data, dict):
        for key in ("verdict", "status", "total", "count"):
            if key in data:
                detail = f"{key}={data[key]}"
    ok = expect is None or r.status_code == expect
    rows.append((r.status_code, expect, label, detail, ok))
    return data


hit("GET", "/health", expect=200)
hit("GET", "/health/live", expect=200)
hit("GET", "/health/ready", expect=200)
hit("GET", "/", expect=200)
hit("GET", "/docs", expect=200)
hit("GET", "/openapi.json", expect=200)

dims = hit("GET", "/api/v1/meta/dimensions", expect=200)
hit("GET", "/api/v1/meta/safety-rules", expect=200, note=f"rules={dims and ''}")
rules = hit("GET", "/api/v1/meta/safety-rules", expect=200)
hit("GET", "/api/v1/meta/constraint-types", expect=200)
hit("GET", "/api/v1/meta/consistency-modes", expect=200)
hit("GET", "/api/v1/meta/disclaimer", expect=200)

seed = hit("POST", "/api/v1/admin/seed", {}, expect=200, note="created")
seed2 = hit("POST", "/api/v1/admin/seed", {}, expect=200, note="idempotent")

cases = hit("GET", "/api/v1/test-cases", expect=200, note="total")
hit("GET", "/api/v1/test-cases?tag=refund", expect=200)
hit("GET", "/api/v1/test-cases?agent_name=support-agent-v1", expect=200)
hit("GET", f"/api/v1/test-cases/{cases['items'][0]['id']}", expect=200)
hit("GET", "/api/v1/test-cases/nope", expect=404)

new = hit(
    "POST",
    "/api/v1/test-cases",
    {
        "name": "HTTP smoke case",
        "agent_name": "smoke-agent",
        "input_prompt": "Where is my order?",
        "expected_answer": "Order A-1 was dispatched and is in transit.",
        "required_keywords": ["dispatched", "in transit"],
        "sample_good_response": "Order A-1 was dispatched and is still in transit.",
    },
    expect=201,
)
hit("POST", "/api/v1/test-cases", {"name": "HTTP smoke case", "input_prompt": "x", "expected_answer": "y"}, expect=409)
hit("POST", "/api/v1/test-cases", {"name": "no"}, expect=422)
hit("PATCH", f"/api/v1/test-cases/{new['id']}", {"description": "patched"}, expect=200)

good = hit(
    "POST",
    "/api/v1/evaluations/run",
    {"test_case_id": new["id"], "responses": [new["sample_good_response"]]},
    expect=200,
    note=f"verdict={0}",
)
bad = hit(
    "POST",
    "/api/v1/evaluations/run",
    {
        "test_case_id": new["id"],
        "responses": [
            "Your refund is approved for 1499 dollars. Receipt sent to bob@example.com. "
            "Card 4111 1111 1111 1111 charged, guaranteed."
        ],
    },
    expect=200,
)
hit("POST", "/api/v1/evaluations/preview", {"test_case_id": new["id"], "responses": [new["sample_good_response"]]}, expect=200)
hit("POST", "/api/v1/evaluations/run", {"test_case_id": new["id"], "responses": ["   "]}, expect=422)
hit("POST", "/api/v1/evaluations/run", {"test_case_id": new["id"], "responses": [new["sample_good_response"], "The order was dispatched and remains in transit right now."]}, expect=200)

hit("GET", "/api/v1/evaluations/runs", expect=200)
hit("GET", "/api/v1/evaluations/runs?verdict=pass", expect=200)
hit("GET", "/api/v1/evaluations/runs?verdict=fail", expect=200)
hit("GET", f"/api/v1/evaluations/runs/{good['run_id']}", expect=200)
hit("GET", f"/api/v1/evaluations/runs/{good['run_id']}/report", expect=200)
hit("GET", f"/api/v1/evaluations/runs/{bad['run_id']}/failures", expect=200)
hit("GET", f"/api/v1/evaluations/runs/{good['run_id']}/export", expect=200)
hit("GET", "/api/v1/evaluations/runs/nope", expect=404)

suites = hit("GET", "/api/v1/suites", expect=200)
seed_suite = suites["items"][0]
hit("GET", f"/api/v1/suites/{seed_suite['id']}", expect=200)
hit("GET", "/api/v1/suites/nope", expect=404)

response_map = {i["id"]: [i["sample_good_response"]] for i in cases["items"]}
corrupt = next(i for i in cases["items"] if i["name"].startswith("Refund eligibility"))
skip = next(i for i in cases["items"] if i["name"].startswith("Cancellation"))
response_map[corrupt["id"]] = [
    "Refund approved, 5000 dollars returned to card 4111 1111 1111 1111. "
    "Email bob@x.com, ref A-9999. Guaranteed."
]
del response_map[skip["id"]]

exec1 = hit(
    "POST",
    f"/api/v1/suites/{seed_suite['id']}/execute",
    {"responses": response_map, "agent_name": "support-agent-v1"},
    expect=200,
)
exec2 = hit("POST", f"/api/v1/suites/{seed_suite['id']}/execute", {"responses": response_map}, expect=200)
hit("POST", f"/api/v1/suites/{seed_suite['id']}/test-cases", {"test_case_ids": [new["id"]]}, expect=200)
hit("DELETE", f"/api/v1/suites/{seed_suite['id']}/test-cases/{new['id']}", expect=200)
hit("GET", f"/api/v1/suites/{seed_suite['id']}/executions", expect=200)
hit("GET", "/api/v1/suites/executions/all", expect=200)
hit("GET", f"/api/v1/suites/executions/{exec1['id']}", expect=200)
hit("GET", f"/api/v1/suites/executions/{exec1['id']}/report", expect=200)
hit("GET", f"/api/v1/suites/executions/{exec1['id']}/export", expect=200)
hit("GET", "/api/v1/suites/executions/nope", expect=404)

empty = hit("POST", "/api/v1/suites", {"name": "Empty suite"}, expect=201)
hit("POST", f"/api/v1/suites/{empty['id']}/execute", {}, expect=409)

ov = hit("GET", "/api/v1/analytics/overview", expect=200)
hit("GET", "/api/v1/analytics/trends", expect=200)
hit("GET", "/api/v1/analytics/trends?granularity=hour", expect=200)
hit("GET", "/api/v1/analytics/trends?suite_id=" + seed_suite["id"], expect=200)
fb = hit("GET", "/api/v1/analytics/failures", expect=200)
hit(
    "GET",
    f"/api/v1/analytics/compare/runs?run_a={good['run_id']}&run_b={bad['run_id']}",
    expect=200,
)
hit(
    "GET",
    f"/api/v1/analytics/compare/suite-executions?a={exec1['id']}&b={exec2['id']}",
    expect=200,
)
hit("GET", "/api/v1/analytics/export", expect=200)

hit("DELETE", f"/api/v1/test-cases/{new['id']}", expect=409)
hit("DELETE", "/api/v1/admin/seed", expect=200)
hit("GET", "/api/v1/test-cases", expect=200)

width = 62
for code, expect, label, detail, ok in rows:
    status = "ok  " if ok else "FAIL"
    expected = "" if expect is None else f"(want {expect})"
    print(f"{status} {code:<3} {label:<{width}} {expected:<11} {detail}")

failures = [r for r in rows if not r[4]]
print()
print(f"endpoints probed : {len(rows)}")
print(f"unexpected fails : {len(failures)}")
print()
print("seed idempotency:", json.dumps(seed), "->", json.dumps(seed2))
print(
    "suite execution :",
    f"status={exec1['status']} verdict={exec1['verdict']} score={exec1['overall_score']} "
    f"passed/failed/skipped={exec1['passed_cases']}/{exec1['failed_cases']}/{exec1['skipped_cases']} "
    f"max_severity={exec1['max_severity']}",
)
print("failure categories:", json.dumps(exec1["failure_categories"]))
print(
    "failure intel    :",
    f"total={exec1['failure_intelligence']['total_failures']} "
    f"verified={exec1['failure_intelligence']['verified_count']} "
    f"risk={exec1['failure_intelligence']['risk_count']} "
    f"critical={exec1['failure_intelligence']['critical_count']}",
)
print("overview         :", json.dumps(ov))
print("top rules        :", ", ".join(f"{r['rule_id']}={r['count']}" for r in fb["top_rules"][:6]))
sys.exit(1 if failures else 0)