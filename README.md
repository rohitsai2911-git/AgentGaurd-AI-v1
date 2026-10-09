# AgentGuard AI

Deterministic quality and reliability testing for AI agents. Five evaluation
dimensions — accuracy, hallucination risk, safety, instruction compliance,
consistency. Every score names the rule that produced it.

Backend status: Hybrid (deterministic + optional Laya + optional OpenRouter).
218/218 tests passing. Frontend pending.

## Stack

- Python >= 3.12, FastAPI, SQLAlchemy, Pydantic v2
- SQLite (default `./agentguard.db`), no external services required
- Optional Laya local decision engine (opt-in, additive only)
- Optional LLM judge via OpenRouter (OpenAI-compatible, additive only)

## Quickstart

```powershell
# 1. Create environment and install
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configure (optional — app runs offline without this)
Copy-Item .env.example .env
# Edit .env as needed. Key variables:
#   AGENTGUARD_DATABASE_URL=sqlite:///./agentguard.db
#   AGENTGUARD_AUTO_SEED=false
#   OPENROUTER_API_KEY=          # leave blank for offline mode
#   OPENROUTER_MODEL=openai/gpt-4o-mini
#   LAYA_ENABLED=false           # set true for local structured decisions
#   LAYA_TIMEOUT_SECONDS=60

# 3. Start backend (port 8077 matches verify scripts)
uvicorn app.main:app --host 127.0.0.1 --port 8077

# 4. Open docs
#   Swagger : http://127.0.0.1:8077/docs
#   ReDoc   : http://127.0.0.1:8077/redoc
#   OpenAPI : http://127.0.0.1:8077/openapi.json
#   Health  : http://127.0.0.1:8077/health
```

## Seed demo data

```powershell
# Load 6 test cases + 1 suite (idempotent)
Invoke-RestMethod -Method Post http://127.0.0.1:8077/api/v1/admin/seed

# Produce real evaluation history from known-good responses
Invoke-RestMethod -Method Post http://127.0.0.1:8077/api/v1/admin/seed/demo-runs

# Remove seed data
Invoke-RestMethod -Method Delete http://127.0.0.1:8077/api/v1/admin/seed
```

## Core API (prefix `/api/v1`)

| Area | Endpoints |
|---|---|
| Test cases | `POST/GET /test-cases`, `GET/PATCH/DELETE /test-cases/{id}` |
| Evaluations | `POST /evaluations/run`, `POST /evaluations/preview`, `GET /evaluations/runs`, `GET /evaluations/runs/{id}[/report\|/failures\|/export]` |
| Suites | `POST/GET /suites`, `GET/PATCH/DELETE /suites/{id}`, `POST/DELETE /suites/{id}/test-cases[/{tc}]`, `POST /suites/{id}/execute`, `GET /suites/executions/...` |
| Analytics | `GET /analytics/overview`, `/analytics/trends`, `/analytics/failures`, `/analytics/compare/runs`, `/analytics/compare/suite-executions`, `/analytics/export` |
| Meta | `GET /meta/dimensions`, `/meta/safety-rules`, `/meta/constraint-types`, `/meta/consistency-modes`, `/meta/disclaimer`, `/meta/llm-status`, `/meta/laya-status` |
| Admin | `POST /admin/seed`, `POST /admin/seed/demo-runs`, `DELETE /admin/seed` |
| LLM (optional) | `POST /evaluations/llm-evaluate`, `GET /evaluations/llm-status` |
| Laya (optional) | `POST /evaluations/laya-evaluate`, `GET /evaluations/laya-status` |

Pipeline order: deterministic → Laya → OpenRouter → aggregate.
Deterministic dimensions solely decide verdict/scores; Laya and OpenRouter
are independent advisory enrichments (`laya_evaluation`, `llm_evaluation`)
and can never double-count a failure in scoring.

Evaluate with the advisory LLM judge by adding `"use_llm": true` to
`/evaluations/run` or `/evaluations/preview`. Without `OPENROUTER_API_KEY`
the report returns `llm_evaluation.status = "skipped_no_key"` and
deterministic scores stand. The key is never logged or returned; status
endpoints expose only a `***last4` hint.

Evaluate with the advisory Laya judge by adding `"use_laya": true`.
Without `LAYA_ENABLED=true` the report returns
`laya_evaluation.status = "skipped_disabled"`. First inference downloads
the routed checkpoint once (~400MB, Hugging Face), then runs offline
(~35ms on CPU). Model confidence is surfaced, never treated as correctness.

## Testing

```powershell
# Full suite (218 tests)
python -m pytest tests/ -v

# Laya provider only (15 tests, 1 live inference)
python -m pytest tests/test_laya_provider.py -v

# QA gate only (21 tests across 7 areas)
python -m pytest tests/test_qa_stage12.py -v

# Live HTTP check against a running server
python verify.py http://127.0.0.1:8077
.\verify.ps1
```

## Project layout

```text
app/main.py            # FastAPI app, lifespan (init_db + optional seed)
app/core/              # config (env), exceptions, logging
app/db/                # models, session (TestCase, EvaluationRun, TestSuite, ...)
app/evaluation/        # deterministic engine: registry, scoring, report, modules/
app/evaluation/llm/    # optional OpenRouter judge (never required)
app/evaluation/laya/   # optional Laya local judge (never required)
app/services/          # evaluation_service, suite_service, orchestrator, analytics
app/api/routes/        # health, test_cases, evaluations, suites, analytics, meta, admin
app/schemas/           # request/response models
tests/                 # pytest suite (TestClient, isolated temp DB)
verify.py / verify.ps1 # live endpoint probes
```

## Honesty contract

Findings are labelled `verified` (provable against the test case grounding
source) or `risk` (heuristic indicator requiring human review). Heuristic
detection cannot find every hallucination; absence of findings is not proof
of correctness.
