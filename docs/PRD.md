# AgentGuard AI — Product Requirements Document

**Version:** 0.1 (Stage 1 MVP)
**Date:** 2026-10-02
**Status:** Approved for Stage 1 implementation
**Owner:** Rohit

---

## 1. Summary

AgentGuard AI is an AI agent quality and reliability testing platform. It takes an AI agent's response, compares it against a test case's expected answer and evaluation criteria, and returns a transparent, reproducible quality report covering accuracy, hallucination risk, safety, instruction compliance, and consistency.

Stage 1 delivers the backend evaluation engine and REST API. No frontend.

## 2. Problem

Teams shipping LLM-backed agents cannot answer three questions before release:

1. Is the answer correct?
2. Is the answer making things up?
3. Is the answer safe and on-policy?

Existing options are either manual spot-checking, which does not scale, or LLM-as-judge, which is non-deterministic, costs money per evaluation, and cannot be explained to a compliance reviewer. There is no lightweight, free, deterministic layer that produces a defensible report.

## 3. Target Users and Roles

| Role | Need | How AgentGuard serves it |
|---|---|---|
| AI Solutions Analyst | Validate AI systems against defined expectations | Test cases encode expectations; reports show per-dimension pass/fail |
| AI Automation Engineer | Detect agent reliability regressions | Versioned test cases + stored run history |
| AI Product Analyst | Track quality metrics over time | Aggregate analytics endpoint (pass rate, avg score, failure counts) |
| AI Engineer | Build evaluation pipelines | Modular rule-per-dimension engine with a stable registry seam |
| AI Product Manager | Quantify quality and risk | Overall quality score, severity levels, failure analysis |

## 4. Product Principles

1. **Transparent.** Every score names the exact rule that produced it. No black-box numbers.
2. **Deterministic.** Same input always yields the same score. No randomness, no external calls, no network dependency.
3. **Honest about limits.** Heuristic risk detection is labelled as risk and never reported as a verified hallucination. See §7.
4. **Zero cost.** No paid API keys, no external services, no cloud dependency.
5. **Composable.** Each evaluation dimension is an independent module behind a registry, so Stage 2 can add an LLM judge as a new module without rewriting the engine.

## 5. Scope

### 5.1 In scope (Stage 1)

- Test case CRUD with rich evaluation criteria
- Five evaluation dimensions: accuracy, hallucination risk, safety, instruction compliance, consistency
- Deterministic pass/fail verdicts, 0-100 quality scores, severity levels, per-finding explanations and remediation
- Structured JSON evaluation reports
- Run history persisted in local SQLite
- Analytics summary endpoint
- Health-check endpoints
- Swagger/OpenAPI documentation at `/docs`
- Idempotent seed data (customer-support domain)
- Unit tests for all evaluation logic

### 5.2 Out of scope (Stage 1)

- Frontend of any kind
- Authentication, multi-tenancy, RBAC
- LLM-as-judge, embedding similarity, semantic scoring
- External retrieval or grounding sources beyond the test case itself
- Celery/async workers, message queues
- Docker, Kubernetes, cloud deployment
- Vector stores, embeddings, RAG
- User-editable rule authoring UI
- Rate limiting, billing, telemetry export

## 6. Functional Requirements

### FR-1 Test case management

A test case MUST capture: name, description, agent identifier, scenario tags, input prompt, expected answer, referenced facts (grounding source), required keywords, forbidden keywords, numeric expectations, required-disclaimer flag, declarative instruction constraints, per-dimension pass thresholds, per-dimension weights, and which dimensions are enabled.

Endpoints: create, list (paginated), retrieve, update, delete.

### FR-2 Evaluation execution

The system MUST accept one or more agent responses for a test case and produce an evaluation.

- `POST /api/v1/evaluations/run` — evaluates and persists.
- `POST /api/v1/evaluations/preview` — evaluates without persisting.

A single response is valid. Multiple responses enable cross-response consistency checking.

### FR-3 Evaluation dimensions

| Dimension | Detects | Output |
|---|---|---|
| Accuracy | Deviation from expected answer; wrong numbers; forbidden content | Score, pass/fail, findings |
| Hallucination risk | Claims not supported by the grounding source; contradicted numbers | Score, verdict, disclaimer |
| Safety | Policy violations: PII disclosure, harmful instructions, missing disclaimers, jailbreak compliance | Score, pass/fail, findings |
| Instruction compliance | Violations of declared constraints (length, phrasing, language, answering the prompt) | Score, pass/fail, findings |
| Consistency | Internal self-contradiction (1 response) or cross-response disagreement (2+ responses) | Score, pass/fail, findings, mode |

### FR-4 Scoring and verdict

- Each dimension produces a 0-100 score and an independent pass/fail.
- Overall quality score = weighted mean of enabled dimension scores.
- Overall PASS requires **all** enabled dimensions to pass **and** zero findings at `critical` severity. A high numeric score must never mask a critical safety failure.
- Run severity = highest severity among all findings.
- Default weights: accuracy 0.30, hallucination risk 0.20, safety 0.25, instruction compliance 0.15, consistency 0.10. Per-test-case override supported.

### FR-5 Failure analysis

Every finding MUST include: rule identifier, severity, verification status, human-readable message, evidence excerpt from the agent response, and remediation guidance. Runs MUST include a generated plain-text summary of failures.

### FR-6 Run history

MUST persist and expose: run identifier, test case reference, submitted responses, per-dimension scores, overall score, verdict, max severity, finding counts, full JSON report, wall-clock duration, timestamp. Filterable by test case and verdict; paginated.

### FR-7 Analytics

MUST return aggregate pass rate, average and best overall score, total run count, verdict breakdown, per-dimension failure counts, and most common failing rules.

### FR-8 Methodology transparency

MUST expose the list of dimensions, their weights, and a human-readable methodology string per dimension. A reviewer must be able to read the API and understand exactly how each score was computed.

### FR-9 Health

Liveness and readiness endpoints reporting application status and database connectivity.

### FR-10 Seed data

MUST provide realistic customer-support test cases covering: refund eligibility, order status, cancellation, PII disclosure request, jailbreak attempt, and escalation. Each MUST include a known-good sample response that passes. Seed MUST be idempotent.

## 7. Hallucination Honesty Contract

This is a hard product requirement, not a nice-to-have.

- The engine detects **risk indicators** (specific claims absent from the grounding source) and **verified contradictions** (response states a value that the grounding source contradicts).
- `risk` findings MUST be labelled `risk` and worded as risk.
- `verified` findings MUST only be used where the grounding source makes the contradiction provable.
- Every hallucination assessment MUST carry a verdict plus an explicit disclaimer stating that the engine performs heuristic detection and cannot detect every hallucination.
- Absence of findings MUST NOT be reported as proof of correctness.

## 8. Non-Functional Requirements

- Python 3.12+
- FastAPI with Pydantic v2 validation
- SQLAlchemy 2.0 over local SQLite; file-based, no server
- Structured logging with request correlation identifiers
- Global exception handling returning a consistent error envelope
- Input validation on all write paths; no unvalidated data reaching the engine
- Evaluation modules are pure functions with no I/O
- Startup time under 2 seconds; evaluation under 100 ms per run
- Runs fully offline

## 9. Data Model

**TestCase** — id, name, description, agent_name, scenario_tags, input_prompt, expected_answer, referenced_facts, required_keywords, forbidden_keywords, expected_numbers, require_disclaimer, constraints, thresholds, weights, enabled_dimensions, sample_good_response, created_at, updated_at.

**EvaluationRun** — id, test_case_id, responses, per-dimension scores, overall_score, verdict, max_severity, finding_counts, report (JSON), duration_ms, created_at.

Indexed on `test_case_id` and `created_at`.

## 10. Success Criteria

Stage 1 is done when:

1. All listed endpoints return valid responses and are documented in Swagger.
2. `pytest` passes with no failures.
3. Seed data loads idempotently and known-good responses score PASS.
4. A deliberately corrupted response scores FAIL with severity and actionable findings.
5. Single-response and multi-response evaluations both work.
6. Scores are reproducible across repeated identical requests.
7. No hardcoded results, no placeholder functions, no unused dependencies.
8. The server starts with a single documented command.

## 11. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Heuristics mistaken for proof of correctness | Verification labels, disclaimer field, PRD §7 contract |
| Regex rules produce false positives | Findings carry evidence and remediation so a human adjudicates; thresholds are per-test-case |
| Scope creep into an LLM-judge product | Determinism is a stated principle; LLM judge deferred to Stage 2 as an optional module |
| Over-engineering | Rule-per-dimension modules only; no plugin framework, no event bus, no DI container |

## 12. Roadmap

- **Stage 1 (this spec):** backend engine, API, persistence, seed, tests.
- **Stage 2:** premium SaaS frontend (dashboard, test case builder, run explorer, failure drill-down), optional LLM-judge module, CI integration, batch test suite runs.
- **Stage 3:** regression tracking over time, alerting, multi-agent suites, custom rule authoring, export.