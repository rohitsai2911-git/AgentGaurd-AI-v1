"use client";

import { Layers, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";

import { DimensionChart } from "@/components/charts";
import { AppShell } from "@/components/shell";
import { TestCaseForm } from "@/components/features/test-case-form";
import { SuiteForm } from "@/components/features/suite-form";
import { useToast } from "@/components/toast";
import { ConfirmDialog } from "@/components/modal";
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
import { endpoints, type SuiteExecuteInput } from "@/lib/api/endpoints";
import {
  displayList,
  formatRelative,
  shortId,
  verdictLabel,
} from "@/lib/format";
import { useAction, useResource } from "@/lib/hooks";
import type { TestCase, TestSuite } from "@/lib/api/types";

export default function TestSuitesPage() {
  const toast = useToast();
  const cases = useResource(() => endpoints.listTestCases({ limit: 200 }));
  const suites = useResource(() => endpoints.listSuites());
  const executions = useResource(() => endpoints.listAllExecutions({ limit: 10 }));
  const overview = useResource(() => endpoints.overview());

  const [activeSuite, setActiveSuite] = useState<string | null>(null);
  const [caseFormOpen, setCaseFormOpen] = useState(false);
  const [editingCase, setEditingCase] = useState<TestCase | null>(null);
  const [suiteFormOpen, setSuiteFormOpen] = useState(false);
  const [editingSuite, setEditingSuite] = useState<TestSuite | null>(null);
  const [pendingDeleteCase, setPendingDeleteCase] = useState<TestCase | null>(null);
  const [pendingDeleteSuite, setPendingDeleteSuite] = useState<TestSuite | null>(null);

  const removeCase = useAction((id: string) => endpoints.deleteTestCase(id));
  const removeSuite = useAction((id: string) => endpoints.deleteSuite(id));
  const runSuite = useAction((id: string, payload: SuiteExecuteInput) =>
    endpoints.executeSuite(id, payload),
  );

  const suite = suites.data?.items.find((item) => item.id === activeSuite) ?? null;

  /**
   * Builds the response map from each member case's known-good sample and runs
   * the suite for real. Cases without a sample are skipped by the backend and
   * reported as skipped, never as passes.
   */
  async function executeSelected(target: TestSuite) {
    const responses: Record<string, string[]> = {};
    for (const ref of target.test_cases) {
      const member = cases.data?.items.find(
        (item) => item.id === ref.test_case_id,
      );
      const sample = member?.sample_good_response?.trim();
      if (sample) responses[ref.test_case_name] = [sample];
    }

    const execution = await runSuite.run(target.id, {
      responses,
      agent_name: target.name,
      persist: true,
    });

    if (!execution) {
      toast.push(
        runSuite.error?.message ?? "Suite execution failed.",
        "error",
        "Execution failed",
      );
      return;
    }

    toast.push(
      `${execution.passed_cases} passed · ${execution.failed_cases} failed · ${execution.skipped_cases} skipped`,
      execution.verdict === "pass" ? "success" : "error",
      `Suite verdict: ${verdictLabel(execution.verdict)}`,
    );
    refreshAll();
  }

  function refreshAll() {
    cases.refresh();
    suites.refresh();
    executions.refresh();
    overview.refresh();
  }

  async function confirmDeleteCase() {
    if (!pendingDeleteCase) return;
    const result = await removeCase.run(pendingDeleteCase.id);
    if (result === null && removeCase.error) {
      toast.push(removeCase.error.message, "error", "Delete failed");
      setPendingDeleteCase(null);
      return;
    }
    toast.push(`Deleted “${pendingDeleteCase.name}”.`, "success");
    setPendingDeleteCase(null);
    refreshAll();
  }

  async function confirmDeleteSuite() {
    if (!pendingDeleteSuite) return;
    const result = await removeSuite.run(pendingDeleteSuite.id);
    if (result === null && removeSuite.error) {
      toast.push(removeSuite.error.message, "error", "Delete failed");
      setPendingDeleteSuite(null);
      return;
    }
    toast.push(`Deleted suite “${pendingDeleteSuite.name}”.`, "success");
    setPendingDeleteSuite(null);
    setActiveSuite(null);
    refreshAll();
  }

  return (
    <AppShell
      eyebrow="Test suites"
      title="Cases and suites"
      description="A test case encodes the expectation. A suite groups cases into one repeatable release gate."
      actions={
        <>
          <Button
            variant="secondary"
            size="sm"
            icon={<RefreshCw size={14} />}
            onClick={refreshAll}
            loading={cases.refreshing || suites.refreshing}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={<Plus size={14} />}
            onClick={() => {
              setEditingCase(null);
              setCaseFormOpen(true);
            }}
          >
            New test case
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="ag-eyebrow">Test suites</p>
              <p className="mt-1 text-micro text-pebble">
                {suites.data?.total ?? 0} suite(s) · a suite aggregates one verdict
                across its member cases
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              icon={<Layers size={14} />}
              onClick={() => {
                setEditingSuite(null);
                setSuiteFormOpen(true);
              }}
            >
              New suite
            </Button>
          </div>

          {suiteFormOpen ? null : (suites.loading ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-40" />
              ))}
            </div>
          ) : suites.error ? (
            <ErrorState error={suites.error} onRetry={suites.refresh} />
          ) : (suites.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              icon={<Layers size={20} />}
              title="No suites yet"
              description="Group test cases into a suite to run them together and read a single aggregated verdict."
              action={
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    setEditingSuite(null);
                    setSuiteFormOpen(true);
                  }}
                >
                  Create the first suite
                </Button>
              }
            />
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {suites.data?.items.map((item) => {
                const active = item.id === activeSuite;
                return (
                  <div
                    key={item.id}
                    className={
                      "ag-card flex flex-col p-5 " +
                      (active ? "shadow-hairline-strong" : "")
                    }
                  >
                    <div className="flex items-start justify-between gap-3">
                      <button
                        type="button"
                        onClick={() => setActiveSuite(active ? null : item.id)}
                        className="min-w-0 text-left"
                        aria-expanded={active}
                      >
                        <p className="text-body-sm font-semibold text-obsidian">
                          {item.name}
                        </p>
                        <p className="mt-1 font-mono text-micro text-pebble">
                          {shortId(item.id)}
                        </p>
                      </button>
                      <Badge tone="neutral">
                        {item.test_case_count} case
                        {item.test_case_count === 1 ? "" : "s"}
                      </Badge>
                    </div>

                    {item.description ? (
                      <p className="mt-3 line-clamp-2 text-caption text-slate">
                        {item.description}
                      </p>
                    ) : null}

                    {item.tags.length > 0 ? (
                      <p className="mt-3 text-micro text-pebble">
                        {displayList(item.tags)}
                      </p>
                    ) : null}

                    <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-fog pt-4">
                      <Button
                        variant={active ? "primary" : "secondary"}
                        size="sm"
                        onClick={() => setActiveSuite(active ? null : item.id)}
                      >
                        {active ? "Hide details" : "Open"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingSuite(item);
                          setSuiteFormOpen(true);
                        }}
                      >
                        Edit
                      </Button>
                      <IconButton
                        label={`Delete suite ${item.name}`}
                        tone="danger"
                        size="sm"
                        className="ml-auto"
                        onClick={() => setPendingDeleteSuite(item)}
                      >
                        <Trash2 size={15} />
                      </IconButton>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </section>

        {suite ? (
        <Card className="overflow-hidden">
          <CardHeader
            title={suite?.name ?? ""}            description={
              suite
                ? `${suite.test_case_count} member case(s) · executes in declared order`
                : undefined
            }
            action={
              suite ? (
                <>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => executeSelected(suite)}
                    loading={runSuite.pending}
                  >
                    Execute suite
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setEditingSuite(suite);
                      setSuiteFormOpen(true);
                    }}
                  >
                    Edit members
                  </Button>
                </>
              ) : null
            }
          />
          {suite ? (
            (suite.test_cases.length ?? 0) === 0 ? (
              <div className="p-4">
                <EmptyState
                  title="This suite has no members"
                  description="Use “Edit members” to attach test cases. Executing an empty suite returns 409 SUITE_EMPTY."
                />
              </div>
            ) : (
              <ul>
                {suite.test_cases.map((ref) => {
                  const member = cases.data?.items.find(
                    (item) => item.id === ref.test_case_id,
                  );
                  return (
                    <li
                      key={ref.test_case_id}
                      className="flex flex-wrap items-center justify-between gap-3 border-t border-fog px-4 py-3 first:border-t-0"
                    >
                      <div className="min-w-0">
                        <p className="text-caption font-medium text-forest-ink">
                          {ref.position + 1}. {ref.test_case_name}
                        </p>
                        <p className="mt-0.5 font-mono text-micro text-pebble">
                          {shortId(ref.test_case_id)}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone="neutral">
                          {member?.enabled_dimensions.length ?? 0} dim
                        </Badge>
                        <Badge
                          tone={
                            member?.sample_good_response ? "good" : "neutral"
                          }
                        >
                          {member?.sample_good_response
                            ? "sample ready"
                            : "no sample"}
                        </Badge>
                        {member ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setEditingCase(member);
                              setCaseFormOpen(true);
                            }}
                          >
                            Edit case
                          </Button>
                        ) : null}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )
          ) : null}
        </Card>
        ) : null}

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="ag-eyebrow">Test cases</p>
              <p className="mt-1 text-micro text-pebble">
                {cases.data?.total ?? 0} case(s) · each carries its own thresholds,
                weights and enabled dimensions
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              icon={<Plus size={14} />}
              onClick={() => {
                setEditingCase(null);
                setCaseFormOpen(true);
              }}
            >
              New test case
            </Button>
          </div>

          {cases.loading ? (
            <Skeleton className="h-48" />
          ) : cases.error ? (
            <ErrorState error={cases.error} onRetry={cases.refresh} />
          ) : (cases.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              title="No test cases yet"
              description="A test case encodes the expected answer and the criteria the engine scores against."
            />
          ) : (
            <Card className="overflow-hidden">
              <div className="ag-scroll overflow-x-auto">
                <table className="w-full min-w-[820px] text-left">
                  <thead>
                    <tr className="border-b border-fog">
                      {["Name", "Agent", "Tags", "Dimensions", "Sample", ""].map(
                        (heading, index) => (
                          <th
                            key={heading || `col-${index}`}
                            className="px-4 py-2.5 text-micro font-semibold text-slate"
                          >
                            {heading}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {cases.data?.items.map((item) => (
                      <tr
                        key={item.id}
                        className="border-b border-fog transition-colors duration-150 ease-out last:border-b-0 hover:bg-fog/50"
                      >
                        <td className="px-4 py-3">
                          <p className="text-caption font-medium text-forest-ink">
                            {item.name}
                          </p>
                          <p className="font-mono text-micro text-pebble">
                            {shortId(item.id)}
                          </p>
                        </td>
                        <td className="px-4 py-3 text-caption text-slate">
                          {item.agent_name || "—"}
                        </td>
                        <td className="px-4 py-3 text-caption text-slate">
                          {displayList(item.scenario_tags)}
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone="neutral">
                            {item.enabled_dimensions.length}/5
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            tone={item.sample_good_response ? "good" : "neutral"}
                          >
                            {item.sample_good_response ? "ready" : "missing"}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEditingCase(item);
                                setCaseFormOpen(true);
                              }}
                            >
                              Edit
                            </Button>
                            <IconButton
                              label={`Delete test case ${item.name}`}
                              tone="danger"
                              size="sm"
                              onClick={() => setPendingDeleteCase(item)}
                            >
                              <Trash2 size={15} />
                            </IconButton>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </section>

        <section className="space-y-3">
          <div>
            <p className="ag-eyebrow">Suite execution history</p>
            <p className="mt-1 text-micro text-pebble">
              Every suite run is stored with its aggregated verdict and failure
              categories
            </p>
          </div>

          {executions.loading ? (
            <Skeleton className="h-40" />
          ) : executions.error ? (
            <ErrorState error={executions.error} onRetry={executions.refresh} />
          ) : (executions.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              title="No suite executions yet"
              description="Open a suite and press Execute to produce a real aggregated run."
            />
          ) : (
            <Card className="overflow-hidden">
              <div className="ag-scroll overflow-x-auto">
                <table className="w-full min-w-[760px] text-left">
                  <thead>
                    <tr className="border-b border-fog">
                      {[
                        "Verdict",
                        "Suite",
                        "Passed",
                        "Failed",
                        "Skipped",
                        "Score",
                        "When",
                      ].map((heading) => (
                        <th
                          key={heading}
                          className="px-4 py-2.5 text-micro font-semibold text-slate"
                        >
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {executions.data?.items.map((item) => (
                      <tr
                        key={item.id}
                        className="border-b border-fog transition-colors duration-150 ease-out last:border-b-0 hover:bg-fog/50"
                      >
                        <td className="px-4 py-3">
                          <Badge tone={item.verdict === "pass" ? "good" : "bad"}>
                            {verdictLabel(item.verdict)}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-caption font-medium text-forest-ink">
                            {item.suite_name}
                          </p>
                          <p className="font-mono text-micro text-pebble">
                            {shortId(item.id)}
                          </p>
                        </td>
                        <td className="ag-num px-4 py-3 text-caption text-forest-ink">
                          {item.passed_cases}
                        </td>
                        <td className="ag-num px-4 py-3 text-caption text-forest-ink">
                          {item.failed_cases}
                        </td>
                        <td className="ag-num px-4 py-3 text-caption text-slate">
                          {item.skipped_cases}
                        </td>
                        <td className="ag-num px-4 py-3 text-caption font-semibold text-forest-ink">
                          {item.overall_score}
                        </td>
                        <td className="px-4 py-3 text-caption text-slate">
                          {formatRelative(item.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </section>
      </div>

      <TestCaseForm
        open={caseFormOpen}
        testCase={editingCase}
        onClose={() => setCaseFormOpen(false)}
        onSaved={() => {
          setCaseFormOpen(false);
          toast.push(
            editingCase ? "Test case updated." : "Test case created.",
            "success",
          );
          refreshAll();
        }}
      />

      <SuiteForm
        open={suiteFormOpen}
        suite={editingSuite}
        onClose={() => setSuiteFormOpen(false)}
        onSaved={() => {
          setSuiteFormOpen(false);
          toast.push(editingSuite ? "Suite updated." : "Suite created.", "success");
          refreshAll();
        }}
      />

      <ConfirmDialog
        open={Boolean(pendingDeleteCase)}
        onClose={() => setPendingDeleteCase(null)}
        onConfirm={confirmDeleteCase}
        pending={removeCase.pending}
        title="Delete this test case?"
        message={`“${pendingDeleteCase?.name}” will be removed. Deletion is refused while any stored run still references it — the backend returns 409 TEST_CASE_HAS_RUNS.`}
      />

      <ConfirmDialog
        open={Boolean(pendingDeleteSuite)}
        onClose={() => setPendingDeleteSuite(null)}
        onConfirm={confirmDeleteSuite}
        pending={removeSuite.pending}
        title="Delete this suite?"
        message={`“${pendingDeleteSuite?.name}” and its execution history will be permanently removed. Test cases themselves are not deleted.`}
      />
    </AppShell>
  );
}