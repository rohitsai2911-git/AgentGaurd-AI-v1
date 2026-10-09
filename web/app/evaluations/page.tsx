"use client";

import {
  FlaskConical,
  Minus,
  Play,
  Plus,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import {
  DimensionCard,
  FailureIntelligence,
  RunReport,
} from "@/components/features/run-report";
import { AppShell } from "@/components/shell";
import { useToast } from "@/components/toast";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  IconButton,
  Skeleton,
} from "@/components/ui";
import type { EvaluationReport } from "@/lib/api/types";
import { endpoints } from "@/lib/api/endpoints";
import { formatRelative, shortId } from "@/lib/format";
import { useAction, useResource } from "@/lib/hooks";

const SAMPLE_GOOD =
  "I can help with that. Based on the record on file, the order is outside the 30-day refund window.";

export default function EvaluationsPage() {
  const toast = useToast();
  const cases = useResource(() => endpoints.listTestCases({ limit: 200 }));
  const llm = useResource(() => endpoints.llmStatus());
  const laya = useResource(() => endpoints.layaStatus());
  const history = useResource(() => endpoints.listRuns({ limit: 10 }));

  const [testCaseId, setTestCaseId] = useState("");
  const [responses, setResponses] = useState<string[]>([""]);
  const [persist, setPersist] = useState(true);
  const [useLlm, setUseLlm] = useState(false);
  const [useLaya, setUseLaya] = useState(false);
  const [report, setReport] = useState<EvaluationReport | null>(null);

  const runAction = useAction(async (preview: boolean) => {
    if (!testCaseId) throw new Error("Select a test case first.");
    const cleaned = responses.map((value) => value.trim()).filter(Boolean);
    if (cleaned.length === 0) throw new Error("Enter at least one agent response.");
    return preview
      ? endpoints.previewEvaluation({ test_case_id: testCaseId, responses: cleaned, use_llm: useLlm, use_laya: useLaya })
      : endpoints.runEvaluation({
          test_case_id: testCaseId,
          responses: cleaned,
          persist,
          use_llm: useLlm,
          use_laya: useLaya,
        });
  });

  const exportAction = useAction(async (runId: string) => {
    await endpoints.exportRun(runId);
  });

  const selectedCase = cases.data?.items.find((item) => item.id === testCaseId);
  const llmReady = llm.data?.configured === true;
  const reportRunId = report?.run_id ?? null;
  const llmEval = report?.llm_evaluation ?? null;
  const layaEval = report?.laya_evaluation ?? null;
  const layaReady = laya.data?.enabled === true && laya.data?.available === true;

  // Failure intelligence is a real backend endpoint; only persisted runs have one.
  const failureDetail = useResource(
    () => endpoints.getRunFailures(reportRunId as string),
    [reportRunId],
    { enabled: Boolean(reportRunId) },
  );

  async function submit(preview: boolean) {
    const result = await runAction.run(preview);
    if (!result) {
      toast.push(
        runAction.error?.message ?? "Evaluation failed.",
        "error",
        preview ? "Preview failed" : "Run failed",
      );
      return;
    }
    setReport(result);
    toast.push(
      `${result.test_case_name} → ${result.verdict.toUpperCase()} (score ${
        result.overall_score
      })`,
      result.verdict === "pass" ? "success" : "error",
      preview ? "Preview complete (not persisted)" : "Run stored",
    );
    if (!preview) history.refresh();
  }

  function fillFromSeed() {
    const sample =
      selectedCase?.sample_good_response?.trim() ||
      selectedCase?.expected_answer?.trim() ||
      SAMPLE_GOOD;
    setResponses([sample]);
  }

  return (
    <AppShell
      eyebrow="Evaluations"
      title="Run an evaluation"
      description="Submit one or more agent responses against a test case. The engine scores all five dimensions deterministically and names the rule behind every score."
      actions={
        <>
          <Button
            variant="secondary"
            size="sm"
            icon={<Sparkles size={14} />}
            onClick={fillFromSeed}
            disabled={!selectedCase}
          >
            Use sample response
          </Button>
          <Link href="/test-suites">
            <Button variant="ghost" size="sm">
              Manage cases
            </Button>
          </Link>
        </>
      }
    >
      <div className="space-y-4">
        <Card>
          <CardHeader
            title="Test case and agent responses"
            description="Everything the engine scores comes from the selected test case's criteria and declared constraints."
            action={
              <Badge tone="neutral">
                {cases.data?.total ?? 0} test case(s)
              </Badge>
            }
          />
          <div className="space-y-5 p-5">
            {cases.loading ? (
              <Skeleton className="h-10" />
            ) : cases.error ? (
              <ErrorState error={cases.error} onRetry={cases.refresh} />
            ) : (cases.data?.items.length ?? 0) === 0 ? (
              <EmptyState
                title="No test cases yet"
                description="Create a test case first — it carries the expected answer, keywords, numbers and constraints the engine scores against."
                action={
                  <Link href="/test-suites">
                    <Button variant="primary" size="sm">
                      Create a test case
                    </Button>
                  </Link>
                }
              />
            ) : (
              <>
                <div>
                  <label
                    htmlFor="test-case"
                    className="mb-1.5 block text-micro font-semibold text-slate"
                  >
                    Test case
                  </label>
                  <select
                    id="test-case"
                    value={testCaseId}
                    onChange={(event) => {
                      setTestCaseId(event.target.value);
                      setReport(null);
                    }}
                    className="h-11 w-full rounded-card bg-paper px-3 text-body-sm text-charcoal shadow-hairline outline-none transition-shadow duration-150 ease-out focus:shadow-hairline-strong"
                  >
                    <option value="">Select a test case…</option>
                    {cases.data?.items.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                        {item.agent_name ? ` · ${item.agent_name}` : ""}
                      </option>
                    ))}
                  </select>
                </div>

                {selectedCase ? (
                  <div className="rounded-card bg-fog/60 p-4">
                    <p className="ag-eyebrow">Expected answer</p>
                    <p className="mt-1.5 text-caption text-charcoal">
                      {selectedCase.expected_answer}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Badge tone="neutral">
                        {selectedCase.enabled_dimensions.length} dimension(s)
                      </Badge>
                      <Badge tone="neutral">
                        {selectedCase.required_keywords.length} required keyword(s)
                      </Badge>
                      <Badge tone="neutral">
                        {selectedCase.constraints.length} constraint(s)
                      </Badge>
                    </div>
                  </div>
                ) : null}

                <div className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-micro font-semibold text-slate">
                      Agent responses
                    </p>
                    <span className="text-micro text-pebble">
                      Two or more unlock cross-response consistency
                    </span>
                  </div>

                  {responses.map((value, index) => (
                    <div key={index} className="flex items-start gap-2">
                      <span className="ag-num mt-3 w-6 shrink-0 text-micro text-pebble">
                        #{index + 1}
                      </span>
                      <textarea
                        value={value}
                        onChange={(event) => {
                          const next = [...responses];
                          next[index] = event.target.value;
                          setResponses(next);
                        }}
                        rows={4}
                        placeholder="Paste the agent's response verbatim…"
                        className="ag-scroll w-full resize-y rounded-card bg-paper px-3 py-2.5 text-caption text-charcoal shadow-hairline outline-none transition-shadow duration-150 ease-out placeholder:text-pebble focus:shadow-hairline-strong"
                      />
                      {responses.length > 1 ? (
                        <IconButton
                          label={`Remove response ${index + 1}`}
                          tone="danger"
                          className="mt-1"
                          onClick={() =>
                            setResponses(responses.filter((_, i) => i !== index))
                          }
                        >
                          <Minus size={15} />
                        </IconButton>
                      ) : null}
                    </div>
                  ))}

                  <Button
                    variant="ghost"
                    size="sm"
                    icon={<Plus size={14} />}
                    onClick={() => setResponses([...responses, ""])}
                  >
                    Add another response
                  </Button>
                </div>

                <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-fog pt-4">
                  <label className="flex items-center gap-2 text-caption text-charcoal">
                    <input
                      type="checkbox"
                      checked={persist}
                      onChange={(event) => setPersist(event.target.checked)}
                      className="size-4 accent-[#163300]"
                    />
                    Store this run in history
                  </label>
                  <label
                    className="flex items-center gap-2 text-caption text-charcoal"
                    title={
                      llmReady
                        ? "Adds an advisory OpenRouter judge on top of the deterministic result"
                        : "No OPENROUTER_API_KEY configured — the report returns status skipped_no_key"
                    }
                  >
                    <input
                      type="checkbox"
                      checked={useLlm}
                      onChange={(event) => setUseLlm(event.target.checked)}
                      className="size-4 accent-[#163300]"
                    />
                    Advisory LLM judge
                    {llmReady ? (
                      <Badge tone="good">{llm.data?.key_hint || "configured"}</Badge>
                    ) : (
                      <Badge tone="neutral">no key</Badge>
                    )}
                  </label>
                  <label
                    className="flex items-center gap-2 text-caption text-charcoal"
                    title={
                      layaReady
                        ? "Adds advisory local structured decisions (no API key, runs on CPU)"
                        : "Laya is off — set LAYA_ENABLED=true and install the laya package to enable"
                    }
                  >
                    <input
                      type="checkbox"
                      checked={useLaya}
                      onChange={(event) => setUseLaya(event.target.checked)}
                      className="size-4 accent-[#163300]"
                    />
                    Local Laya judge
                    {layaReady ? (
                      <Badge tone="good">ready</Badge>
                    ) : (
                      <Badge tone="neutral">off</Badge>
                    )}
                  </label>
                </div>

                <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                  <Button
                    variant="primary"
                    icon={<Play size={15} />}
                    loading={runAction.pending}
                    disabled={!testCaseId}
                    onClick={() => submit(false)}
                  >
                    Run evaluation
                  </Button>
                  <Button
                    variant="secondary"
                    icon={<FlaskConical size={15} />}
                    loading={runAction.pending}
                    disabled={!testCaseId}
                    onClick={() => submit(true)}
                  >
                    Preview only
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={<RotateCcw size={14} />}
                    onClick={() => {
                      setResponses([""]);
                      setReport(null);
                    }}
                  >
                    Clear
                  </Button>
                </div>

                {runAction.error ? (
                  <p className="rounded-card bg-fog px-3 py-2 text-caption text-charcoal">
                    {runAction.error.message}
                  </p>
                ) : null}
              </>
            )}
          </div>
        </Card>

        {report ? (
          <div className="space-y-4">
            <RunReport
              report={report}
              exporting={exportAction.pending}
              onExport={
                report.run_id
                  ? () => exportAction.run(report.run_id as string)
                  : undefined
              }
            />

            <div>
              <p className="ag-eyebrow">Dimension breakdown</p>
              <div className="mt-3 grid gap-4 xl:grid-cols-2">
                {report.dimensions.map((result) => (
                  <DimensionCard key={result.dimension} result={result} />
                ))}
              </div>
            </div>

            <div>
              <p className="ag-eyebrow">Failure intelligence</p>
              <div className="mt-3">
                {!report.run_id ? (
                  <EmptyState
                    title="This was a preview"
                    description="Failure intelligence is served from stored runs. Re-run with “Store this run in history” enabled to get the classified failure report."
                  />
                ) : failureDetail.loading ? (
                  <Skeleton className="h-40" />
                ) : failureDetail.error ? (
                  <ErrorState
                    error={failureDetail.error}
                    onRetry={failureDetail.refresh}
                  />
                ) : failureDetail.data ? (
                  <FailureIntelligence report={failureDetail.data} />
                ) : null}
              </div>
            </div>

            {llmEval ? (
              <Card className="p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="ag-eyebrow">Advisory LLM judge</p>
                  <Badge tone={llmEval.status === "success" ? "good" : "neutral"}>
                    {llmEval.status}
                  </Badge>
                </div>
                <p className="mt-3 text-caption text-slate">
                  Advisory only — the deterministic scores above remain authoritative and
                  the verdict never changes because of this section.
                </p>

                {llmEval.status === "success" ? (
                  <>
                    {llmEval.overall_reasoning ? (
                      <p className="mt-3 text-caption text-charcoal">
                        {llmEval.overall_reasoning}
                      </p>
                    ) : null}
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      {Object.entries(llmEval.dimensions).map(
                        ([dimension, assessment]) => (
                          <div
                            key={dimension}
                            className="rounded-card bg-fog/60 px-3 py-2.5"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-micro font-semibold text-forest-ink">
                                {dimension.replace(/_/g, " ")}
                              </span>
                              <span className="ag-num text-caption font-semibold text-forest-ink">
                                {assessment.score}
                              </span>
                            </div>
                            {assessment.reasoning ? (
                              <p className="mt-1 text-micro text-slate">
                                {assessment.reasoning}
                              </p>
                            ) : null}
                          </div>
                        ),
                      )}
                    </div>
                  </>
                ) : (
                  <p className="mt-2 font-mono text-micro break-all text-pebble">
                    {llmEval.error_code} · {llmEval.error_message}
                  </p>
                )}
              </Card>
            ) : null}

            {layaEval ? (
              <Card className="p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="ag-eyebrow">Local Laya decisions</p>
                  <Badge tone={layaEval.status === "success" ? "good" : "neutral"}>
                    {layaEval.status}
                  </Badge>
                </div>
                <p className="mt-3 text-caption text-slate">
                  Advisory only — local structured decisions that never change the
                  deterministic verdict or scores.
                </p>

                {layaEval.status === "success" ? (
                  <>
                    <div className="mt-4 grid gap-3 sm:grid-cols-3">
                      {[
                        ["Compliance", layaEval.compliance_ok.prob_true],
                        ["Policy safe", layaEval.policy_safe.prob_true],
                        ["Grounded", layaEval.grounded.prob_true],
                      ].map(([label, prob]) => (
                        <div
                          key={String(label)}
                          className="rounded-card bg-fog/60 px-3 py-2.5"
                        >
                          <p className="text-micro text-slate">{label}</p>
                          <p className="ag-num mt-1 text-body-sm font-semibold text-forest-ink">
                            {(Number(prob) * 100).toFixed(0)}%
                          </p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Badge tone="neutral">
                        category: {layaEval.failure_category.choice}
                      </Badge>
                      <Badge tone="neutral">
                        severity: {layaEval.severity.level}
                      </Badge>
                    </div>
                    {layaEval.overall_reasoning ? (
                      <p className="mt-3 text-caption text-charcoal">
                        {layaEval.overall_reasoning}
                      </p>
                    ) : null}
                  </>
                ) : (
                  <p className="mt-2 font-mono text-micro break-all text-pebble">
                    {layaEval.error_code} · {layaEval.error_message}
                  </p>
                )}
              </Card>
            ) : null}
          </div>
        ) : (
          <Card className="p-6">
            <EmptyState
              icon={<Sparkles size={20} />}
              title="No evaluation run yet"
              description="Pick a test case, paste one or more agent responses, then run the evaluation. Nothing is scored until you press run."
            />
          </Card>
        )}
      </div>
    </AppShell>
  );
}