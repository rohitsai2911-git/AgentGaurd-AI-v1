# AgentGuard AI — Stages 1 & 2 Implementation Plan

> **For agentic workers:** execute task-by-task, checkbox tracking. TDD cycle per task.

**Goal:** Build the Stage 1 evaluation engine (5 deterministic dimensions, SQLite persistence, REST API) and the Stage 2 orchestration/reporting layer (test suites, suite execution, failure intelligence, analytics, trends, comparison, JSON export) as one working backend. Stage 3 (frontend) is out of scope.

**Architecture:** Strictly one-directional layering — `api` → `services` → (`evaluation` | `db`). Evaluation modules are pure functions `(TestCaseCriteria, responses) -> DimensionResult` with no I/O. Stage 2 reuses the Stage 1 `evaluation_service` per test case and adds suite-level aggregation on top, so Stage 1 endpoints stay byte-compatible.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync) + SQLite, pytest, httpx.

## Global Constraints

- No paid APIs, no external network calls, no LLM calls. Fully offline.
- Deterministic: identical input always yields identical scores. No `random`, no `datetime.now()` inside evaluation modules.
- Honesty contract: `Finding.verification ∈ {verified, risk}`. Risk is never reported as verified hallucination. Every hallucination assessment carries a non-empty disclaimer.
- Dependencies limited to: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `pytest`, `httpx`.
- No hardcoded demo results, no placeholder functions, no mock success responses. Missing agent responses produce `skipped`, never `pass`.
- Evaluation modules must not import FastAPI, SQLAlchemy, or anything from `app.db` / `app.services` / `app.api`.
- Stage 1 endpoints keep their existing paths and response shapes.

---

## File Map

### Stage 1
| File | Responsibility |
|---|---|
| `pyproject.toml` | packaging + pytest config |
| `requirements.txt` | pinned runtime deps |
| `.env.example` | settings reference |
| `.gitignore` | venv, db, pycache |
| `app/core/config.py` | `Settings` via pydantic-settings, cached |
| `app/core/logging.py` | structured logging, request id filter/contextvar |
| `app/core/exceptions.py` | `AppError` hierarchy + codes |
| `app/db/base.py` | `DeclarativeBase` |
| `app/db/session.py` | engine, `SessionLocal`, `get_session` |
| `app/db/models.py` | `TestCase`, `EvaluationRun` |
| `app/evaluation/types.py` | enums, `Finding`, `DimensionResult`, `TestCaseCriteria`, `EvaluationReport`, defaults |
| `app/evaluation/normalize.py` | `normalize_text`, `tokenize`, `split_sentences`, `extract_numbers`, `extract_entities`, `extract_labeled_values`, `jaccard`, `contains_phrase` |
| `app/evaluation/scoring.py` | `merge_results`, `compute_overall`, `SEVERITY_PENALTY` |
| `app/evaluation/registry.py` | `Dimension` → module, `run_dimensions` |
| `app/evaluation/report.py` | `build_report`, `build_summary` |
| `app/evaluation/modules/accuracy.py` | expected-answer matching, numeric checks |
| `app/evaluation/modules/hallucination.py` | ungrounded claims, verified contradictions, assessment |
| `app/evaluation/modules/safety.py` | 10 policy rules |
| `app/evaluation/modules/compliance.py` | constraint registry + validators |
| `app/evaluation/modules/consistency.py` | cross-response + internal modes |
| `app/evaluation/failure_intel.py` | **Stage 2** classify / explain / remediate |
| `app/schemas/*.py` | Pydantic API contracts |
| `app/services/test_case_service.py` | test case CRUD + db↔criteria mapping |
| `app/services/evaluation_service.py` | run / preview / history |
| `app/services/analytics_service.py` | overview, trends, failures, comparison |
| `app/services/suite_service.py` | **Stage 2** suite CRUD + membership |
| `app/services/orchestrator.py` | **Stage 2** suite execution |
| `app/services/report_export.py` | **Stage 2** JSON download payload |
| `app/services/seed.py` | idempotent seed (6 cases + 1 suite) |
| `app/api/routes/*.py` | health, test_cases, evaluations, meta, admin, suites, analytics |
| `app/main.py` | app factory, middleware, handlers |

### Stage 2 tests
`tests/test_failure_intel.py`, `tests/test_suite_service.py`, `tests/test_orchestrator.py`, `tests/test_analytics.py`, `tests/test_report_export.py`, `tests/test_api_suites.py`, `tests/test_api_analytics.py`.

---

## Task 1: Scaffold

Files: `pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`

Steps:
1. Write files.
2. `python -m venv .venv`
3. `.venv\Scripts\pip install -r requirements.txt`
4. Verify: `.venv\Scripts\python -c "import fastapi, sqlalchemy, pydantic; print('ok')"`

## Task 2: Core layer

Files: `app/core/config.py`, `app/core/logging.py`, `app/core/exceptions.py`

Produces: `get_settings() -> Settings` with `database_url`, `app_name`, `version`, `log_level`, `debug`; `configure_logging()`; `request_id_var` ContextVar; `AppError`/`NotFoundError`/`ConflictError`/`AppValidationError`/`EvaluationError` with `.code`, `.message`, `.details`, `.status_code`.

Verify: `python -c "from app.core.config import get_settings; print(get_settings().app_name)"`

## Task 3: Database

Files: `app/db/base.py`, `app/db/session.py`, `app/db/models.py`

Produces: `TestCase` (all Stage 1 columns, criteria as JSON), `EvaluationRun` (id, test_case_id, responses, dimension_scores, overall_score, verdict, max_severity, finding_counts, report, duration_ms, created_at), indexes on `test_case_id` + `created_at` + `verdict`.

Verify: `python -c "from app.db.models import TestCase, EvaluationRun; print('ok')"`

## Task 4: Normalization primitives

File: `app/evaluation/normalize.py`
Test: `tests/test_normalize.py`

Steps: write failing tests for `normalize_text`, `tokenize`, `split_sentences` (decimal-safe), `extract_numbers` (currency/comma, ignores `1st`), `extract_entities` (drops "The", keeps "Amazon"), `extract_labeled_values`, `jaccard`, `contains_phrase`. Implement. `pytest tests/test_normalize.py -v` → PASS.

## Task 5: Evaluation types and scoring

Files: `app/evaluation/types.py`, `app/evaluation/scoring.py`
Tests: `tests/test_types.py`, `tests/test_scoring.py`

Produces: `Severity`, `Verification`, `Dimension`, `RunVerdict`, `ConstraintType`, `Constraint`, `Finding`, `DimensionResult`, `HallucinationAssessment`, `TestCaseCriteria`, `EvaluationReport`, `DEFAULT_WEIGHTS`, `DEFAULT_THRESHOLDS`; `merge_results`, `compute_overall`.

Test cases to write: weight renormalisation when a dimension is disabled; critical finding blocks PASS even at overall score 95; `merge_results` takes mean score and max severity.

## Task 6: Accuracy module

File: `app/evaluation/modules/accuracy.py`
Test: `tests/test_accuracy.py`

Steps: tests for (a) near-identical expected answer passes, (b) missing required keyword lowers score, (c) wrong expected number fails, (d) forbidden keyword caps score at 40 and fails, (e) threshold respected. Implement per spec §6.1.

## Task 7: Hallucination module

File: `app/evaluation/modules/hallucination.py`
Test: `tests/test_hallucination.py`

Steps: tests for (a) unsupported number → `RISK` medium, (b) unsupported email/order-id → `RISK` high, (c) grounded labeled-value contradiction → `VERIFIED` high, (d) verdict string per case, (e) disclaimer non-empty in all cases. Implement per spec §6.2.

## Task 8: Safety module

File: `app/evaluation/modules/safety.py`
Test: `tests/test_safety.py`

Steps: tests for (a) card number → `critical` and fail regardless of score, (b) `require_disclaimer=False` reports `skipped` in details rather than passing silently, (c) medical advice without disclaimer → `medium` when flag true, (d) safe response scores 100. Implement all 10 rules per spec §6.3.

## Task 9: Compliance module

File: `app/evaluation/modules/compliance.py`
Test: `tests/test_compliance.py`

Steps: one test per `ConstraintType` (8 types), plus empty-constraint-list scores 100 with `constraints_evaluated = 0`. Implement registry + validators per spec §6.4.

## Task 10: Consistency module

File: `app/evaluation/modules/consistency.py`
Test: `tests/test_consistency.py`

Steps: tests for (a) 3 agreeing responses → high score, (b) cross-response labeled-value contradiction → `high` verified + score capped 40, (c) single response with two different values for same label → self-contradiction, (d) polarity flip → `medium` risk, (e) `consistency_mode` reported. Implement per spec §6.5.

## Task 11: Registry + report builder

Files: `app/evaluation/registry.py`, `app/evaluation/report.py`
Test: `tests/test_registry.py`, `tests/test_report.py`

Produces: `run_dimensions(criteria, responses) -> list[DimensionResult]` executing enabled dimensions in registry order and wrapping failures in `EvaluationError`; `build_report(...)` with deterministic `summary` text; `build_hallucination_assessment`.

## Task 12: Pydantic API schemas

Files: `app/schemas/common.py`, `test_case.py`, `evaluation.py`, `report.py`, `suite.py`, `analytics.py`

Produces request/response models with `model_config = ConfigDict(from_attributes=True)` where needed.

## Task 13: Services

Files: `app/services/test_case_service.py`, `evaluation_service.py`, `analytics_service.py`, `seed.py`, `suite_service.py`, `orchestrator.py`, `report_export.py`, `failure_intel` is evaluation-side

Key contract: `test_case_service.to_criteria(model) -> TestCaseCriteria` is the only db→evaluation boundary.

## Task 14: API routes + app factory

Files: `app/api/deps.py`, `router.py`, `routes/health.py`, `test_cases.py`, `evaluations.py`, `meta.py`, `admin.py`, `suites.py`, `analytics.py`, `app/main.py`

Error envelope `{ "error": {code, message, details}, "request_id": ... }` registered for `AppError` and `RequestValidationError`. Request-id middleware.

## Task 15: Stage 1 tests

`pytest tests -v` → all PASS. Smoke-test every Stage 1 endpoint.

## Task 16: Stage 2 — suites

Models `TestSuite`, `SuiteTestCase`, `SuiteExecution`, `SuiteCaseResult`. Suite execution statuses `pending|running|completed|partial|failed`. Missing response → `skipped` status for that case, counted separately, never counted as pass.

## Task 17: Stage 2 — failure intelligence

`app/evaluation/failure_intel.py`: `classify_failure(finding) -> FailureCategory` (`policy_violation`, `hallucination_risk`, `accuracy_deviation`, `instruction_violation`, `consistency_defect`), `explain(finding, criteria) -> str`, `remediate(finding) -> str`. Enforces verified-vs-risk distinction in output text.

## Task 18: Stage 2 — orchestrator + analytics + export

Orchestrator runs Stage 1 `evaluation_service` per case, aggregates weighted suite score, classifies failures, writes `SuiteExecution` + `SuiteCaseResult`. Analytics: `overview`, `trends` (day bucket), `failure_categories`, `top_rules`, `compare_runs`, `compare_suite_executions`. Export: `build_export_payload` + `Response` with `Content-Disposition: attachment`.

## Task 19: Stage 2 tests + full verification

`pytest tests -v` → PASS. Boot uvicorn, curl every endpoint, confirm Stage 1 paths unchanged.

## Task 20: README

Exact commands: venv activate, install, seed, run, test.

---

## Self-Review

- **Spec coverage:** PRD FR-1..FR-10 → Tasks 3, 6-11, 13, 14. Stage 2 objective items 1-5 → Tasks 16-19. Non-functional (logging, validation, error handling, structured errors, purity, determinism) → Tasks 2, 4, 11, 14, 15.
- **Placeholder scan:** no TBD/TODO; every task names concrete files and test scenarios.
- **Type consistency:** `TestCaseCriteria` is the single evaluation input type across all 5 modules and both stages; `EvaluationReport.report` is the stored JSON for single runs; `SuiteExecution.report` is the stored JSON for suite runs. `Dimension` enum string values are used as weight/threshold keys throughout.