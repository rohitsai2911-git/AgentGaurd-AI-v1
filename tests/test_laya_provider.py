"""Laya optional provider: init, outputs, fallback, aggregation.

Real inference used in exactly one test (cached english checkpoint).
Everything else uses controlled fakes — never faked as success.
"""

import httpx

from app.core.config import get_settings
from app.evaluation.laya import provider as laya_provider
from app.evaluation.types import TestCaseCriteria

API = "/api/v1"


def _criteria():
    return TestCaseCriteria(
        id="x",
        name="y",
        input_prompt="Can I get a refund for my 45-day-old order?",
        expected_answer="Refunds within 30 days only. This order is 45 days old.",
        referenced_facts=["Refund window is 30 days."],
        required_keywords=["refund"],
    )


def _disable(monkeypatch):
    monkeypatch.setenv("LAYA_ENABLED", "false")
    monkeypatch.setenv("AGENTGUARD_LAYA_ENABLED", "false")
    get_settings.cache_clear()


def _enable(monkeypatch):
    monkeypatch.setenv("LAYA_ENABLED", "true")
    get_settings.cache_clear()


def _fake_raw(**over):
    base = {
        "routing": {"model": "english"},
        "answers": {
            "compliance_ok": {"type": "noul", "noul": 0.9, "answer_confidence": 0.9},
            "policy_safe": {"type": "noul", "noul": 0.95, "answer_confidence": 0.95},
            "grounded": {"type": "noul", "noul": 0.8, "answer_confidence": 0.8},
            "failure_category": {
                "type": "choice",
                "choice": "none",
                "probabilities": {"none": 0.8, "accuracy_deviation": 0.2},
                "answer_confidence": 0.8,
            },
            "severity": {
                "type": "score",
                "score": 0.2,
                "legend": {"0": "low", "1": "medium", "2": "high", "3": "critical"},
                "probabilities": {"0": 0.8, "1": 0.2},
                "answer_confidence": 0.8,
            },
        },
    }
    base["answers"].update(over)
    return base


class _FakeRouter:
    def __init__(self, raw=None, exc=None, delay=0.0):
        self._raw = raw
        self._exc = exc
        self._delay = delay

    def predict(self, *a, **k):
        import time

        if self._delay:
            time.sleep(self._delay)
        if self._exc:
            raise self._exc
        return self._raw


# --- init / fallback ---


def test_disabled_by_default_without_env(monkeypatch):
    _disable(monkeypatch)
    try:
        assert laya_provider.is_available() is True  # package installed
        assert laya_provider.is_enabled() is False
        out = laya_provider.evaluate_with_laya(_criteria(), ["hello"])
        assert out.status == "skipped_disabled"
        assert out.error_code == "DISABLED"
    finally:
        get_settings.cache_clear()


def test_unavailable_package_falls_back(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(laya_provider, "is_available", lambda: False)
    try:
        out = laya_provider.evaluate_with_laya(_criteria(), ["hello"])
        assert out.status == "skipped_unavailable"
        assert out.error_code == "UNAVAILABLE"
    finally:
        get_settings.cache_clear()


def test_init_failure_falls_back(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(laya_provider, "_router", None)
    monkeypatch.setattr(laya_provider, "_router_error", "Nope")
    try:
        out = laya_provider.evaluate_with_laya(_criteria(), ["hello"])
        assert out.status == "error"
        assert out.error_code == "INIT_FAILED"
    finally:
        laya_provider._router_error = None
        get_settings.cache_clear()


def test_empty_responses_error(monkeypatch):
    _enable(monkeypatch)
    try:
        out = laya_provider.evaluate_with_laya(_criteria(), ["   "])
        assert out.status == "error"
        assert out.error_code == "EMPTY_RESPONSES"
    finally:
        get_settings.cache_clear()


# --- valid / invalid outputs (mocked router) ---


def test_valid_outputs_parsed(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(laya_provider, "_router", _FakeRouter(_fake_raw()))
    try:
        out = laya_provider.evaluate_with_laya(_criteria(), ["some answer"])
        assert out.status == "success"
        assert out.provider == "laya"
        assert out.compliance_ok.prob_true == 0.9
        assert out.policy_safe.prob_true == 0.95
        assert out.grounded.prob_true == 0.8
        assert out.failure_category.choice == "none"
        assert out.severity.level == "low"
        assert out.overall_reasoning
        assert out.model_used == "english"
    finally:
        monkeypatch.setattr(laya_provider, "_router", None)
        get_settings.cache_clear()


def test_invalid_choice_rejected(monkeypatch):
    _enable(monkeypatch)
    raw = _fake_raw(failure_category={"type": "choice", "choice": "bogus"})
    monkeypatch.setattr(laya_provider, "_router", _FakeRouter(raw))
    try:
        out = laya_provider.evaluate_with_laya(_criteria(), ["hi"])
        assert out.status == "error"
        assert out.error_code == "INVALID_OUTPUT"
    finally:
        monkeypatch.setattr(laya_provider, "_router", None)
        get_settings.cache_clear()


def test_non_mapping_payload_rejected(monkeypatch):
    _enable(monkeypatch)

    class Weird:
        def predict(self, *a, **k):
            return ["not", "a", "mapping"]

    monkeypatch.setattr(laya_provider, "_router", Weird())
    try:
        out = laya_provider.evaluate_with_laya(_criteria(), ["hi"])
        assert out.status == "error"
        assert out.error_code == "INVALID_OUTPUT"
    finally:
        monkeypatch.setattr(laya_provider, "_router", None)
        get_settings.cache_clear()


def test_inference_exception_falls_back(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(laya_provider, "_router", _FakeRouter(exc=RuntimeError("boom")))
    try:
        out = laya_provider.evaluate_with_laya(_criteria(), ["hi"])
        assert out.status == "error"
        assert out.error_code == "INFERENCE_ERROR"
    finally:
        monkeypatch.setattr(laya_provider, "_router", None)
        get_settings.cache_clear()


def test_timeout_falls_back(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setenv("LAYA_TIMEOUT_SECONDS", "0.2")
    get_settings.cache_clear()
    monkeypatch.setattr(laya_provider, "_router", _FakeRouter(_fake_raw(), delay=2.0))
    try:
        out = laya_provider.evaluate_with_laya(_criteria(), ["hi"])
        assert out.status == "error"
        assert out.error_code == "TIMEOUT"
    finally:
        monkeypatch.setattr(laya_provider, "_router", None)
        monkeypatch.delenv("LAYA_TIMEOUT_SECONDS", raising=False)
        get_settings.cache_clear()


# --- real inference (one test, cached checkpoint) ---


def test_real_laya_inference(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(laya_provider, "_router", None)
    laya_provider._router_error = None
    try:
        out = laya_provider.evaluate_with_laya(
            _criteria(), ["Refunds are available within 30 days of purchase."]
        )
        assert out.status == "success"
        assert out.failure_category.choice in {
            "accuracy_deviation",
            "hallucination_risk",
            "policy_violation",
            "instruction_violation",
            "consistency_defect",
            "none",
        }
        assert out.severity.level in {"low", "medium", "high", "critical"}
        assert 0.0 <= out.compliance_ok.prob_true <= 1.0
    finally:
        get_settings.cache_clear()


# --- aggregation: deterministic intact ---


def test_deterministic_intact_with_laya(client, test_case, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(laya_provider, "_router", _FakeRouter(_fake_raw()))
    try:
        plain = client.post(f"{API}/evaluations/preview", json={
            "test_case_id": test_case["id"],
            "responses": [test_case["sample_good_response"]]},
        ).json()
        hybrid = client.post(f"{API}/evaluations/preview", json={
            "test_case_id": test_case["id"],
            "responses": [test_case["sample_good_response"]],
            "use_laya": True},
        ).json()
        assert hybrid["laya_evaluation"]["status"] == "success"
        # Deterministic verdict/scores/dimensions identical — no double-count.
        assert hybrid["verdict"] == plain["verdict"]
        assert hybrid["overall_score"] == plain["overall_score"]
        assert [d["score"] for d in hybrid["dimensions"]] == [d["score"] for d in plain["dimensions"]]
        assert len(hybrid["dimensions"]) == 5
    finally:
        monkeypatch.setattr(laya_provider, "_router", None)
        get_settings.cache_clear()


def test_use_laya_without_env_skips_gracefully(client, test_case, monkeypatch):
    _disable(monkeypatch)
    try:
        body = client.post(f"{API}/evaluations/preview", json={
            "test_case_id": test_case["id"],
            "responses": [test_case["sample_good_response"]],
            "use_laya": True},
        ).json()
        assert len(body["dimensions"]) == 5
        assert body["laya_evaluation"]["status"] == "skipped_disabled"
    finally:
        get_settings.cache_clear()


def test_laya_evaluate_and_status_endpoints(client, test_case, monkeypatch):
    _disable(monkeypatch)
    try:
        body = client.post(f"{API}/evaluations/laya-evaluate", json={
            "test_case_id": test_case["id"], "responses": ["hello"]},
        ).json()
        assert body["provider"] == "laya"
        assert body["status"] == "skipped_disabled"
        st = client.get(f"{API}/evaluations/laya-status").json()
        assert st["provider"] == "laya" and st["deterministic_fallback"] is True
        meta = client.get(f"{API}/meta/laya-status").json()
        assert meta["provider"] == "laya" and "use_laya" in meta["usage"]
    finally:
        get_settings.cache_clear()


def test_hybrid_laya_plus_llm_without_keys(client, test_case, monkeypatch):
    _disable(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("AGENTGUARD_OPENROUTER_API_KEY", "")
    get_settings.cache_clear()
    try:
        body = client.post(f"{API}/evaluations/preview", json={
            "test_case_id": test_case["id"],
            "responses": [test_case["sample_good_response"]],
            "use_laya": True, "use_llm": True},
        ).json()
        assert body["verdict"] == "pass"
        assert body["laya_evaluation"]["status"] == "skipped_disabled"
        assert body["llm_evaluation"]["status"] == "skipped_no_key"
    finally:
        get_settings.cache_clear()


# --- OpenRouter timeout handling (hybrid pipeline coverage) ---


def test_openrouter_timeout_graceful(client, test_case, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    get_settings.cache_clear()

    class TimeoutClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            raise httpx.TimeoutException("slow")

    monkeypatch.setattr(httpx, "Client", TimeoutClient)
    try:
        body = client.post(f"{API}/evaluations/preview", json={
            "test_case_id": test_case["id"],
            "responses": [test_case["sample_good_response"]],
            "use_llm": True},
        ).json()
        assert body["verdict"] in ("pass", "fail")
        assert body["llm_evaluation"]["status"] == "error"
        assert body["llm_evaluation"]["error_code"] == "TIMEOUT"
    finally:
        get_settings.cache_clear()
