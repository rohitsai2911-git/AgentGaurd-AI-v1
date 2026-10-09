"use client";

import { Download, FileJson, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

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
  VerdictBadge,
} from "@/components/ui";
import { endpoints } from "@/lib/api/endpoints";
import { formatDateTime, formatPercent, shortId } from "@/lib/format";
import { useAction, useDebounced, useResource } from "@/lib/hooks";

export default function ReportsPage() {
  const toast = useToast();
  const [verdict, setVerdict] = useState<"" | "pass" | "fail">("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const debouncedQuery = useDebounced(query, 200);

  const runs = useResource(() =>
    endpoints.listRuns({ limit: 100, verdict: verdict || undefined }),
  );
  const overview = useResource(() => endpoints.overview());

  // Deep-link support: /reports?run=<id>
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("run");
    if (fromUrl) setSelected(fromUrl);
  }, []);

  function selectRun(id: string | null) {
    setSelected(id);
    const url = new URL(window.location.href);
    if (id) url.searchParams.set("run", id);
    else url.searchParams.delete("run");
    window.history.replaceState(null, "", url.toString());
  }

  const detail = useResource(
    () => endpoints.getRun(selected as string),
    [selected],
    { enabled: Boolean(selected) },
  );
  const failures = useResource(
    () => endpoints.getRunFailures(selected as string),
    [selected],
    { enabled: Boolean(selected) },
  );

  const exportRun = useAction((id: string) => endpoints.exportRun(id));
  const exportAnalytics = useAction(() =>
    endpoints.exportAnalytics({ days: 30, granularity: "day" }),
  );

  const filtered = useMemo(() => {
    const items = runs.data?.items ?? [];
    const needle = debouncedQuery.trim().toLowerCase();
    if (!needle) return items;
    return items.filter(
      (run) =>
        run.test_case_name.toLowerCase().includes(needle) ||
        run.agent_name.toLowerCase().includes(needle) ||
        run.id.toLowerCase().includes(needle),
    );
  }, [runs.data, debouncedQuery]);

  async function runExport(id: string) {
    const result = await exportRun.run(id);
    if (result === null && exportRun.error) {
      toast.push(exportRun.error.message, "error", "Export failed");
      return;
    }
    toast.push("Report downloaded as JSON.", "success");
  }

  async function analyticsExport() {
    const result = await exportAnalytics.run();
    if (result === null && exportAnalytics.error) {
      toast.push(exportAnalytics.error.message, "error", "Export failed");
      return;
    }
    toast.push("Analytics snapshot downloaded.", "success");
  }

return (
    <AppShell
      eyebrow="Reports"
      title="Reports and exports"
      description="Every stored evaluation run, its full deterministic report, and the classified failure intelligence behind it — all downloadable as JSON."
      actions={
        <Button
          variant="secondary"
          size="sm"
          icon={<Download size={14} />}
          onClick={analyticsExport}
          loading={exportAnalytics.pending}
        >
          Export analytics snapshot
        </Button>
      }
    >
      <div className="space-y-4">
        {runs.error ? (
          <ErrorState error={runs.error} onRetry={runs.refresh} />
        ) : null}

        <Card className="overflow-hidden">
          <CardHeader
            title="Evaluation runs"
            description={
              runs.data
                ? `${runs.data.total} run(s)${
                    overview.data
                      ? ` · pass rate ${formatPercent(overview.data.pass_rate, 1)}`
                      : ""
                  }`
                : "Loading run history…"
            }
            action={
              <select
                value={verdict}
                onChange={(event) =>
                  setVerdict(event.target.value as "" | "pass" | "fail")
                }
                aria-label="Filter by verdict"
                className="h-9 rounded-pill bg-paper px-3 text-caption text-charcoal shadow-hairline outline-none transition-shadow duration-150 ease-out focus:shadow-hairline-strong"
              >
                <option value="">All verdicts</option>
                <option value="pass">Pass only</option>
                <option value="fail">Fail only</option>
              </select>
            }
          />

          {runs.loading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-12" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-4">
              <EmptyState
                icon={<FileJson size={20} />}
                title={
                  (runs.data?.items.length ?? 0) === 0
                    ? "No stored runs yet"
                    : "No runs match this filter"
                }
                description={
                  (runs.data?.items.length ?? 0) === 0
                    ? "Run an evaluation from the Evaluations page to create the first report."
                    : "Switch the verdict filter to see the rest."
                }
              />
            </div>
          ) : (
            <div className="ag-scroll overflow-x-auto">
              <table className="w-full min-w-[720px] text-left">
                <thead>
                  <tr className="border-b border-fog">
                    {["Verdict", "Test case", "Score", "Severity", "Created", ""].map(
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
                  {filtered.map((run) => (
                    <tr
                      key={run.id}
                      className={
                        "border-b border-fog transition-colors duration-150 ease-out last:border-b-0 hover:bg-fog/50 " +
                        (run.id === selected ? "bg-fog/60" : "")
                      }
                    >
                      <td className="px-4 py-3">
                        <VerdictBadge verdict={run.verdict} size="sm" />
                      </td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => selectRun(run.id)}
                          className="text-left text-caption font-medium text-forest-ink hover:underline"
                        >
                          {run.test_case_name}
                        </button>
                        <p className="font-mono text-micro text-pebble">
                          {shortId(run.id)}
                        </p>
                      </td>
                      <td className="ag-num px-4 py-3 text-caption font-semibold text-forest-ink">
                        {run.overall_score}
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone="neutral">{run.max_severity}</Badge>
                      </td>
                      <td className="px-4 py-3 text-caption text-slate">
                        {formatDateTime(run.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => selectRun(run.id)}
                          >
                            Open
                          </Button>
                          <IconButton
                            label="Export run as JSON"
                            size="sm"
                            onClick={() => runExport(run.id)}
                          >
                            <Download size={15} />
                          </IconButton>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {!selected ? (
          <Card className="p-6">
            <EmptyState
              icon={<FileJson size={20} />}
              title="Select a run to open its report"
              description="The full deterministically-scored report, every dimension, and the classified failures are loaded from the backend."
            />
          </Card>
        ) : detail.loading ? (
          <Skeleton className="h-72" />
        ) : detail.error ? (
          <ErrorState error={detail.error} onRetry={detail.refresh} />
        ) : detail.data ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="ag-eyebrow">Report · {shortId(selected)}</p>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Download size={14} />}
                  onClick={() => {
                    if (detail.data) runExport(detail.data.id);
                  }}
                  loading={exportRun.pending}
                >
                  Export run JSON
                </Button>
                <Button variant="ghost" size="sm" onClick={() => selectRun(null)}>
                  Close report
                </Button>
              </div>
            </div>

            <RunReport report={detail.data.report} />

            <div>
              <p className="ag-eyebrow">Dimension breakdown</p>
              <div className="mt-3 grid gap-4 xl:grid-cols-2">
                {detail.data.report.dimensions.map((result) => (
                  <DimensionCard key={result.dimension} result={result} />
                ))}
              </div>
            </div>

            <div>
              <p className="ag-eyebrow">Failure intelligence</p>
              <div className="mt-3">
                {failures.loading ? (
                  <Skeleton className="h-40" />
                ) : failures.error ? (
                  <ErrorState error={failures.error} onRetry={failures.refresh} />
                ) : failures.data ? (
                  <FailureIntelligence report={failures.data} />
                ) : null}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}