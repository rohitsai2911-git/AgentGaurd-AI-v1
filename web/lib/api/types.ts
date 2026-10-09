/**
 * Typed mirrors of the AgentGuard AI Pydantic schemas.
 * Source of truth: app/schemas/*.py and app/evaluation/types.py
 */

export type Severity = "none" | "info" | "low" | "medium" | "high" | "critical";
export type Verification = "verified" | "risk";
export type RunVerdict = "pass" | "fail";

export type Dimension =
  | "accuracy"
  | "hallucination_risk"
  | "safety"
  | "instruction_compliance"
  | "consistency";

export type ConstraintType =
  | "max_words"
  | "min_words"
  | "must_include"
  | "must_exclude"
  | "must_answer_prompt"
  | "ascii_letters_only"
  | "non_empty"
  | "no_all_caps_shouting";

/* ------------------------------------------------------------------ */
/* Evaluation engine                                                   */
/* ------------------------------------------------------------------ */

export interface Constraint {
  type: ConstraintType;
  value?: number | string | null;
  phrases?: string[];
  severity?: Severity;
  message?: string | null;
}

export interface Finding {
  rule_id: string;
  dimension: Dimension;
  severity: Severity;
  verification: Verification;
  message: string;
  evidence?: string | null;
  remediation: string;
  response_index?: number | null;
}

export interface DimensionResult {
  dimension: Dimension;
  score: number;
  passed: boolean;
  severity: Severity;
  findings: Finding[];
  methodology: string;
  details: Record<string, unknown>;
  forced_fail: boolean;
}

export interface HallucinationAssessment {
  verdict: string;
  grounding_sources: string[];
  unsupported_claims: string[];
  contradicted_values: string[];
  disclaimer: string;
}

export interface LlmDimensionAssessment {
  score: number;
  reasoning: string;
  issues: string[];
  recommendations: string[];
}

export interface LlmEvaluation {
  provider?: string;
  model: string;
  model_used: string;
  status: string;
  overall_reasoning: string;
  dimensions: Record<string, LlmDimensionAssessment>;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms: number;
  fallback_note?: string | null;
}

export interface EvaluationReport {
  run_id: string | null;
  test_case_id: string;
  test_case_name: string;
  agent_name: string;
  overall_score: number;
  verdict: RunVerdict;
  max_severity: Severity;
  summary: string;
  dimensions: DimensionResult[];
  hallucination_assessment: HallucinationAssessment;
  responses_submitted: number;
  consistency_mode: string | null;
  weights_used: Record<string, number>;
  disclaimer: string;
  duration_ms: number;
  created_at: string | null;
  llm_evaluation: LlmEvaluation | null;
  laya_evaluation: LayaEvaluation | null;
}

/* ------------------------------------------------------------------ */
/* Failure intelligence                                                */
/* ------------------------------------------------------------------ */

export interface FailureExplanation {
  rule_id: string;
  dimension: Dimension;
  severity: Severity;
  verification: Verification;
  category: string;
  explanation: string;
  remediation: string;
  evidence?: string | null;
}

export interface FailureReport {
  total_failures: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
  critical_count: number;
  verified_count: number;
  risk_count: number;
  explanations: FailureExplanation[];
  narrative: string;
}

/* ------------------------------------------------------------------ */
/* Test cases                                                          */
/* ------------------------------------------------------------------ */

export interface TestCase {
  id: string;
  name: string;
  description: string;
  agent_name: string;
  scenario_tags: string[];
  input_prompt: string;
  expected_answer: string;
  referenced_facts: string[];
  required_keywords: string[];
  forbidden_keywords: string[];
  expected_numbers: number[];
  require_disclaimer: boolean;
  constraints: Constraint[];
  thresholds: Record<string, number>;
  weights: Record<string, number>;
  enabled_dimensions: Dimension[];
  sample_good_response: string | null;
  created_at: string;
  updated_at: string;
}

export interface TestCaseCreateInput {
  name: string;
  description?: string;
  agent_name?: string;
  scenario_tags?: string[];
  input_prompt: string;
  expected_answer: string;
  referenced_facts?: string[];
  required_keywords?: string[];
  forbidden_keywords?: string[];
  expected_numbers?: number[];
  require_disclaimer?: boolean;
  constraints?: Constraint[];
  thresholds?: Record<string, number>;
  weights?: Record<string, number>;
  enabled_dimensions?: Dimension[];
  sample_good_response?: string | null;
}

export type TestCaseUpdateInput = Partial<TestCaseCreateInput>;

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export type TestCaseListResponse = Page<TestCase>;

/* ------------------------------------------------------------------ */
/* Suites & executions                                                 */
/* ------------------------------------------------------------------ */

export interface SuiteTestCaseRef {
  test_case_id: string;
  test_case_name: string;
  position: number;
}

export interface TestSuite {
  id: string;
  name: string;
  description: string;
  tags: string[];
  test_cases: SuiteTestCaseRef[];
  test_case_count: number;
  created_at: string;
  updated_at: string;
}

export interface SuiteCreateInput {
  name: string;
  description?: string;
  tags?: string[];
  test_case_ids?: string[];
}

export interface SuiteUpdateInput {
  name?: string;
  description?: string;
  tags?: string[];
}

export interface SuiteListResponse {
  items: TestSuite[];
  total: number;
}

export interface SuiteCaseResult {
  test_case_id: string;
  test_case_name: string;
  run_id: string | null;
  status: "evaluated" | "skipped" | "error";
  passed: boolean;
  overall_score: number;
  max_severity: Severity;
  failure_categories: string[];
  duration_ms: number;
}

export interface SuiteExecution {
  id: string;
  suite_id: string;
  suite_name: string;
  agent_name: string;
  status: "completed" | "partial" | "failed";
  started_at: string | null;
  completed_at: string | null;
  total_cases: number;
  evaluated_cases: number;
  passed_cases: number;
  failed_cases: number;
  skipped_cases: number;
  overall_score: number;
  verdict: RunVerdict;
  max_severity: Severity;
  failure_categories: Record<string, number>;
  duration_ms: number;
  created_at: string;
}

export interface SuiteExecutionDetail extends SuiteExecution {
  results: SuiteCaseResult[];
  failure_intelligence: FailureReport;
  report: Record<string, unknown>;
}

export type SuiteExecutionListResponse = Page<SuiteExecution>;

/* ------------------------------------------------------------------ */
/* Runs                                                                */
/* ------------------------------------------------------------------ */

export interface RunSummary {
  id: string;
  test_case_id: string;
  test_case_name: string;
  agent_name: string;
  overall_score: number;
  verdict: RunVerdict;
  max_severity: Severity;
  responses_submitted: number;
  duration_ms: number;
  created_at: string;
}

export interface RunDetail extends RunSummary {
  dimension_scores: Record<string, number>;
  finding_counts: Record<string, number>;
  report: EvaluationReport;
}

export type RunListResponse = Page<RunSummary>;

/* ------------------------------------------------------------------ */
/* Analytics                                                           */
/* ------------------------------------------------------------------ */

export interface OverviewStats {
  total_test_cases: number;
  total_runs: number;
  total_suites: number;
  total_suite_executions: number;
  pass_rate: number;
  fail_rate: number;
  average_overall_score: number;
  best_overall_score: number;
  worst_overall_score: number;
  suite_pass_rate: number;
}

export interface DimensionAggregate {
  dimension: Dimension;
  average_score: number;
  pass_rate: number;
  failure_count: number;
}

export interface FailureCategoryAggregate {
  category: string;
  count: number;
  percentage: number;
}

export interface TopRule {
  rule_id: string;
  count: number;
  verification: Verification | string;
  worst_severity: Severity;
}

export interface TrendPoint {
  bucket: string;
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  average_score: number;
  max_severity: Severity;
}

export interface TrendResponse {
  granularity: "day" | "hour";
  test_case_id: string | null;
  suite_id: string | null;
  points: TrendPoint[];
  total_points: number;
}

export interface FailureBreakdown {
  by_category: FailureCategoryAggregate[];
  by_severity: Record<string, number>;
  by_dimension: DimensionAggregate[];
  top_rules: TopRule[];
  critical_findings: number;
  verified_findings: number;
  risk_findings: number;
}

export interface ScoreDelta {
  label: string;
  overall_score: number;
  verdict: string;
  passed: number;
  failed: number;
  total: number;
}

export interface ComparisonResponse {
  kind: "runs" | "suite_executions";
  a: ScoreDelta;
  b: ScoreDelta;
  score_delta: number;
  verdict_changed: boolean;
  regression: boolean;
  per_dimension_delta: Record<string, number>;
  findings_delta: Record<string, number>;
  new_rules: string[];
  resolved_rules: string[];
}

/* ------------------------------------------------------------------ */
/* Meta & health                                                       */
/* ------------------------------------------------------------------ */

export interface DimensionMeta {
  dimension: Dimension;
  default_weight: number;
  default_threshold: number;
  methodology: string;
}

export interface MetaDimensions {
  dimensions: DimensionMeta[];
  evaluation_order: Dimension[];
  severity_levels: Severity[];
  scoring_rule: string;
  disclaimer: string;
}

export interface SafetyRuleMeta {
  rule_id: string;
  severity: Severity;
  message: string;
  remediation: string;
}

export interface ConstraintTypeMeta {
  type: ConstraintType;
  requires_value: boolean;
  requires_phrases: boolean;
}

export interface ConsistencyModeMeta {
  mode: string;
  trigger: string;
  methodology: string;
}

export interface LlmStatus {
  configured: boolean;
  provider: string;
  model: string;
  base_url: string;
  timeout_seconds: number;
  key_hint: string;
  deterministic_fallback: boolean;
  usage?: string;
}

export interface HealthStatus {
  status: string;
  name: string;
  version: string;
  database: string;
  database_ok: boolean;
  test_cases: number | null;
  runs: number | null;
  suites: number | null;
  stage: string;
}

export interface ApiIndex {
  name: string;
  version: string;
  stage: string;
  docs: string;
  openapi: string;
  health: string;
}

export interface SeedResult {
  status: string;
  test_cases_created?: number;
  test_cases_skipped?: number;
  suites_created?: number;
  suite_name?: string;
  demo_responses?: number;
  runs_created?: number;
  note?: string;
  removed?: Record<string, number>;
}

/* ------------------------------------------------------------------ */
/* Laya local decision judge (optional, advisory)                      */
/* ------------------------------------------------------------------ */

export interface LayaNoulDecision {
  prob_true: number;
  confidence: number;
  abstained: boolean;
}

export interface LayaChoiceDecision {
  choice: string;
  probabilities: Record<string, number>;
  confidence: number;
  abstained: boolean;
}

export interface LayaScoreDecision {
  level: string;
  expected_level: number;
  probabilities: Record<string, number>;
  confidence: number;
  abstained: boolean;
}

export interface LayaEvaluation {
  provider?: string;
  model: string;
  model_used: string;
  status: string;
  compliance_ok: LayaNoulDecision;
  policy_safe: LayaNoulDecision;
  grounded: LayaNoulDecision;
  failure_category: LayaChoiceDecision;
  severity: LayaScoreDecision;
  overall_reasoning: string;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms: number;
  fallback_note?: string | null;
}

export interface LayaStatus {
  enabled: boolean;
  available: boolean;
  provider: string;
  model: string;
  timeout_seconds: number;
  loaded: boolean;
  deterministic_fallback: boolean;
  usage?: string;
}

/* ------------------------------------------------------------------ */
/* Auth / multi-tenancy                                                */
/* ------------------------------------------------------------------ */

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
  workspace_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
  workspace: Workspace;
}

export interface MeResponse {
  user: AuthUser;
  workspace: Workspace;
}