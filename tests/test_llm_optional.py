"""Optional LLM judge must never break deterministic flow."""

import httpx

from app.core.config import get_settings
from app.evaluation.llm import provider as llm_provider

API = "/api/v1"


def _no_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("AGENTGUARD_OPENROUTER_API_KEY", "")
    get_settings.cache_clear()
    # ensure empty after clear (env without key)
    s = get_settings()
    assert not s.llm_configured


def test_deterministic_runs_without_key_by_default(client, test_case):
    body = client.post(
        f"{API}/evaluations/preview",
        json={"test_case_id": test_case["id"], "responses": [test_case["sample_good_response"]]},
    ).json()
    assert len(body["dimensions"]) == 5
    assert body.get("llm_evaluation") is None


def test_use_llm_without_key_gracefully_skips(client, test_case, monkeypatch):
    _no_key(monkeypatch)
    try:
        body = client.post(
            f"{API}/evaluations/preview",
            json={
                "test_case_id": test_case["id"],
                "responses": [test_case["sample_good_response"]],
                "use_llm": True,
            },
        ).json()
        assert len(body["dimensions"]) == 5  # deterministic intact
        assert body["llm_evaluation"]["status"] == "skipped_no_key"
        assert body["llm_evaluation"]["error_code"] == "NO_API_KEY"
    finally:
        get_settings.cache_clear()


def test_llm_evaluate_endpoint_without_key(client, test_case, monkeypatch):
    _no_key(monkeypatch)
    try:
        body = client.post(
            f"{API}/evaluations/llm-evaluate",
            json={"test_case_id": test_case["id"], "responses": ["hello"]},
        ).json()
        assert body["status"] == "skipped_no_key"
        assert body["provider"] == "openrouter"
    finally:
        get_settings.cache_clear()


def test_llm_status_never_exposes_key(client):
    body = client.get(f"{API}/evaluations/llm-status").json()
    assert "configured" in body
    assert "deterministic_fallback" in body
    assert "OPENROUTER_API_KEY" not in str(body)
    # meta mirror
    meta = client.get(f"{API}/meta/llm-status").json()
    assert meta["provider"] == "openrouter"


def test_llm_success_path_mocked(client, test_case, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    get_settings.cache_clear()

    payload_json = {
        "accuracy": {"score": 90, "reasoning": "good", "issues": [], "recommendations": ["keep"]},
        "hallucination_risk": {"score": 95, "reasoning": "grounded", "issues": [], "recommendations": []},
        "safety": {"score": 100, "reasoning": "safe", "issues": [], "recommendations": []},
        "instruction_compliance": {"score": 88, "reasoning": "compliant", "issues": ["minor"], "recommendations": ["fix"]},
        "overall_reasoning": "solid answer",
    }

    class FakeResp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": __import__("json").dumps(payload_json)}}]}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            # assert auth header present but never log key
            assert "headers" in k
            assert k["headers"]["Authorization"].startswith("Bearer ")
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    try:
        body = client.post(
            f"{API}/evaluations/preview",
            json={
                "test_case_id": test_case["id"],
                "responses": [test_case["sample_good_response"]],
                "use_llm": True,
            },
        ).json()
        llm = body["llm_evaluation"]
        assert llm["status"] == "success"
        assert llm["dimensions"]["accuracy"]["score"] == 90
        assert llm["overall_reasoning"] == "solid answer"
        assert len(body["dimensions"]) == 5
    finally:
        get_settings.cache_clear()


def test_llm_rate_limit_graceful(client, test_case, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    get_settings.cache_clear()

    class FakeResp:
        status_code = 429

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    try:
        body = client.post(
            f"{API}/evaluations/preview",
            json={
                "test_case_id": test_case["id"],
                "responses": [test_case["sample_good_response"]],
                "use_llm": True,
            },
        ).json()
        assert body["verdict"] in ("pass", "fail")  # deterministic still decides
        assert body["llm_evaluation"]["status"] == "error"
        assert body["llm_evaluation"]["error_code"] == "RATE_LIMITED"
    finally:
        get_settings.cache_clear()


def test_llm_invalid_json_graceful(monkeypatch):
    from app.evaluation.types import TestCaseCriteria

    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    get_settings.cache_clear()

    class FakeResp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "not json at all"}}]}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    try:
        criteria = TestCaseCriteria(
            id="x",
            name="y",
            input_prompt="p",
            expected_answer="e",
        )
        out = llm_provider.evaluate_with_llm(criteria, ["hello"])
        assert out.status == "error"
        assert out.error_code == "INVALID_RESPONSE"
    finally:
        get_settings.cache_clear()
