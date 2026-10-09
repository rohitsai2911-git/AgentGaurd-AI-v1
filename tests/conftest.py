import os
import tempfile
from pathlib import Path

import pytest

_TMP_DB = Path(tempfile.mkdtemp(prefix="agentguard-tests-")) / "test.db"
os.environ["AGENTGUARD_DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["AGENTGUARD_LOG_LEVEL"] = "WARNING"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.models import (  # noqa: E402,F401
    EvaluationRun,
    SuiteCaseResult,
    SuiteExecution,
    SuiteTestCase,
    TestCase,
    TestSuite,
)
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(_schema, auth_token):
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {auth_token}"
        yield test_client


@pytest.fixture(scope="session")
def auth_token(_schema):
    """Register one workspace for the whole session and reuse its token.

    Every API route is now workspace-scoped, so the shared test client
    authenticates once and sends the bearer token on every request.
    """
    with TestClient(app) as registration_client:
        response = registration_client.post(
            "/api/v1/auth/register",
            json={
                "email": "tests@agentguard.local",
                "password": "test1234",
                "name": "Test Runner",
                "workspace_name": "Test Workspace",
            },
        )
        assert response.status_code in (200, 201), response.text
        return response.json()["access_token"]


@pytest.fixture(autouse=True)
def _clean_tables(client):
    """Every test starts from an empty database."""
    yield
    with engine.begin() as conn:
        for table in (
            SuiteCaseResult.__table__,
            SuiteExecution.__table__,
            SuiteTestCase.__table__,
            EvaluationRun.__table__,
            TestSuite.__table__,
            TestCase.__table__,
        ):
            conn.execute(table.delete())


# --- API payload factories ---


def case_payload(**overrides) -> dict:
    payload = {
        "name": "Refund policy check",
        "description": "Refund window enforcement",
        "agent_name": "support-agent-v1",
        "scenario_tags": ["refund"],
        "input_prompt": "I bought something 45 days ago and want a refund. Can I get one?",
        "expected_answer": (
            "Refunds are available within 30 days of purchase. This order was placed 45 "
            "days ago so it cannot be refunded. Store credit is offered instead."
        ),
        "referenced_facts": ["The refund window is 30 days from the order date."],
        "required_keywords": ["refund", "30 days", "store credit"],
        "forbidden_keywords": ["refund approved"],
        "expected_numbers": [30, 45],
        "require_disclaimer": False,
        "constraints": [
            {"type": "max_words", "value": 120},
            {"type": "must_include", "phrases": ["store credit"], "severity": "high"},
        ],
        "sample_good_response": (
            "Thanks for checking in. Refunds are available within 30 days of the order "
            "date. This order was placed 45 days ago so I cannot process a refund, but I "
            "can offer store credit for the order value."
        ),
    }
    payload.update(overrides)
    return payload


BAD_RESPONSE = (
    "Your refund is approved for 1499 dollars. Receipt sent to bob@example.com. "
    "Card 4111 1111 1111 1111 was charged and it is guaranteed."
)


@pytest.fixture
def test_case(client):
    response = client.post("/api/v1/test-cases", json=case_payload())
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def second_case(client):
    response = client.post(
        "/api/v1/test-cases", json=case_payload(name="Escalation policy check")
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def suite(client, test_case, second_case):
    response = client.post(
        "/api/v1/suites",
        json={
            "name": "Support regression suite",
            "description": "Two policy checks",
            "tags": ["regression"],
            "test_case_ids": [test_case["id"], second_case["id"]],
        },
    )
    assert response.status_code == 201
    return response.json()


def responses_for(*cases) -> dict:
    return {case["id"]: [case["sample_good_response"]] for case in cases}