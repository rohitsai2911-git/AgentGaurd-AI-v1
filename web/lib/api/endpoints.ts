import { api, buildQuery, downloadJson } from "./client";
import type {
  ApiIndex,
  ComparisonResponse,
  ConstraintTypeMeta,
  ConsistencyModeMeta,
  EvaluationReport,
  FailureBreakdown,
  FailureReport,
  HealthStatus,
  LlmEvaluation,
  LlmStatus,
  LoginRequest,
  LayaStatus,
  MeResponse,
  MetaDimensions,
  OverviewStats,
  RegisterRequest,
  RunDetail,
  RunListResponse,
  SafetyRuleMeta,
  SeedResult,
  SuiteCreateInput,
  SuiteExecutionDetail,
  SuiteExecutionListResponse,
  SuiteListResponse,
  SuiteUpdateInput,
  TestCase,
  TestCaseCreateInput,
  TestCaseListResponse,
  TestCaseUpdateInput,
  TestSuite,
  TokenResponse,
  TrendResponse,
} from "./types";

const V1 = "/api/v1";

export interface RunListParams {
  limit?: number;
  offset?: number;
  test_case_id?: string;
  verdict?: "pass" | "fail";
}

export interface TestCaseListParams {
  limit?: number;
  offset?: number;
  tag?: string;
  agent_name?: string;
}

export interface TrendParams {
  granularity?: "day" | "hour";
  days?: number;
  test_case_id?: string;
  suite_id?: string;
}

export interface EvaluationRunInput {
  test_case_id: string;
  responses: string[];
  persist?: boolean;
  use_llm?: boolean;
  llm_model?: string | null;
  use_laya?: boolean;
}

export interface PreviewInput {
  test_case_id: string;
  responses: string[];
  use_llm?: boolean;
  llm_model?: string | null;
  use_laya?: boolean;
}

export interface SuiteExecuteInput {
  responses?: Record<string, string[]>;
  agent_name?: string;
  persist?: boolean;
}

/** Every call maps 1:1 to a live FastAPI route under /api/v1. */
export const endpoints = {
  /* ---------------- system ---------------- */
  index: () => api.get<ApiIndex>("/"),
  health: () => api.get<HealthStatus>("/health"),

  /* ---------------- auth ---------------- */
  register: (body: RegisterRequest) =>
    api.post<TokenResponse>(`${V1}/auth/register`, body),
  login: (body: LoginRequest) => api.post<TokenResponse>(`${V1}/auth/login`, body),
  me: () => api.get<MeResponse>(`${V1}/auth/me`),
  layaStatus: () => api.get<LayaStatus>(`${V1}/meta/laya-status`),

  /* ---------------- test cases ---------------- */
  listTestCases: (params: TestCaseListParams = {}) =>
    api.get<TestCaseListResponse>(`${V1}/test-cases${buildQuery(params)}`),
  getTestCase: (id: string) => api.get<TestCase>(`${V1}/test-cases/${id}`),
  createTestCase: (body: TestCaseCreateInput) =>
    api.post<TestCase>(`${V1}/test-cases`, body),
  updateTestCase: (id: string, body: TestCaseUpdateInput) =>
    api.patch<TestCase>(`${V1}/test-cases/${id}`, body),
  deleteTestCase: (id: string) => api.delete<void>(`${V1}/test-cases/${id}`),

  /* ---------------- evaluations ---------------- */
  runEvaluation: (body: EvaluationRunInput) =>
    api.post<EvaluationReport>(`${V1}/evaluations/run`, body),
  previewEvaluation: (body: PreviewInput) =>
    api.post<EvaluationReport>(`${V1}/evaluations/preview`, body),
  llmEvaluate: (body: PreviewInput) =>
    api.post<LlmEvaluation>(`${V1}/evaluations/llm-evaluate`, body),
  listRuns: (params: RunListParams = {}) =>
    api.get<RunListResponse>(`${V1}/evaluations/runs${buildQuery(params)}`),
  getRun: (id: string) => api.get<RunDetail>(`${V1}/evaluations/runs/${id}`),
  getRunReport: (id: string) =>
    api.get<EvaluationReport>(`${V1}/evaluations/runs/${id}/report`),
  getRunFailures: (id: string) =>
    api.get<FailureReport>(`${V1}/evaluations/runs/${id}/failures`),
  exportRun: (id: string) =>
    downloadJson(`${V1}/evaluations/runs/${id}/export`, `agentguard-run-${id}.json`),
  llmStatus: () => api.get<LlmStatus>(`${V1}/evaluations/llm-status`),

  /* ---------------- suites ---------------- */
  listSuites: () => api.get<SuiteListResponse>(`${V1}/suites`),
  getSuite: (id: string) => api.get<TestSuite>(`${V1}/suites/${id}`),
  createSuite: (body: SuiteCreateInput) =>
    api.post<TestSuite>(`${V1}/suites`, body),
  updateSuite: (id: string, body: SuiteUpdateInput) =>
    api.patch<TestSuite>(`${V1}/suites/${id}`, body),
  deleteSuite: (id: string) => api.delete<void>(`${V1}/suites/${id}`),
  addSuiteTestCases: (id: string, test_case_ids: string[]) =>
    api.post<TestSuite>(`${V1}/suites/${id}/test-cases`, { test_case_ids }),
  removeSuiteTestCase: (id: string, testCaseId: string) =>
    api.delete<TestSuite>(`${V1}/suites/${id}/test-cases/${testCaseId}`),
  executeSuite: (id: string, body: SuiteExecuteInput) =>
    api.post<SuiteExecutionDetail>(`${V1}/suites/${id}/execute`, body),
  listAllExecutions: (params: { limit?: number; offset?: number } = {}) =>
    api.get<SuiteExecutionListResponse>(
      `${V1}/suites/executions/all${buildQuery(params)}`,
    ),
  listSuiteExecutions: (
    id: string,
    params: { limit?: number; offset?: number } = {},
  ) =>
    api.get<SuiteExecutionListResponse>(
      `${V1}/suites/${id}/executions${buildQuery(params)}`,
    ),
  getExecution: (id: string) =>
    api.get<SuiteExecutionDetail>(`${V1}/suites/executions/${id}`),
  getExecutionReport: (id: string) =>
    api.get<Record<string, unknown>>(`${V1}/suites/executions/${id}/report`),
  exportExecution: (id: string, suiteName: string) =>
    downloadJson(
      `${V1}/suites/executions/${id}/export`,
      `agentguard-suite-${suiteName.replace(/\s+/g, "_")}-${id}.json`,
    ),

  /* ---------------- analytics ---------------- */
  overview: () => api.get<OverviewStats>(`${V1}/analytics/overview`),
  trends: (params: TrendParams = {}) =>
    api.get<TrendResponse>(`${V1}/analytics/trends${buildQuery(params)}`),
  failures: (limit = 10) =>
    api.get<FailureBreakdown>(`${V1}/analytics/failures${buildQuery({ limit })}`),
  compareRuns: (runA: string, runB: string) =>
    api.get<ComparisonResponse>(
      `${V1}/analytics/compare/runs${buildQuery({ run_a: runA, run_b: runB })}`,
    ),
  compareExecutions: (executionA: string, executionB: string) =>
    api.get<ComparisonResponse>(
      `${V1}/analytics/compare/suite-executions${buildQuery({
        a: executionA,
        b: executionB,
      })}`,
    ),
  exportAnalytics: (params: TrendParams = {}) =>
    downloadJson(
      `${V1}/analytics/export${buildQuery(params)}`,
      "agentguard-analytics.json",
    ),

  /* ---------------- meta ---------------- */
  dimensions: () => api.get<MetaDimensions>(`${V1}/meta/dimensions`),
  safetyRules: () =>
    api.get<{ rules: SafetyRuleMeta[]; count: number }>(
      `${V1}/meta/safety-rules`,
    ),
  constraintTypes: () =>
    api.get<{ constraint_types: ConstraintTypeMeta[]; count: number }>(
      `${V1}/meta/constraint-types`,
    ),
  consistencyModes: () =>
    api.get<{ modes: ConsistencyModeMeta[] }>(`${V1}/meta/consistency-modes`),
  disclaimer: () =>
    api.get<{
      disclaimer: string;
      verified_means: string;
      risk_means: string;
      dimensions: string[];
    }>(`${V1}/meta/disclaimer`),
  metaLlmStatus: () => api.get<LlmStatus & { usage: string }>(`${V1}/meta/llm-status`),

  /* ---------------- admin ---------------- */
  seed: () => api.post<SeedResult>(`${V1}/admin/seed`),
  seedDemoRuns: () => api.post<SeedResult>(`${V1}/admin/seed/demo-runs`),
  removeSeed: () => api.delete<SeedResult>(`${V1}/admin/seed`),
};