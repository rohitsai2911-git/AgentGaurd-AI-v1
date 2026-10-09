"use client";

import { BarChart3, Download, TrendingDown, TrendingUp } from "lucide-react";
import { useState } from "react";

import {
  CategoryChart,
  DimensionChart,
  PassFailChart,
  SeverityChart,
  TrendChart,
} from "@/components/charts";
import { RunComparison } from "@/components/features/run-report";
import { AppShell } from "@/components/shell";
import { useToast } from "@/components/toast";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  Meter,
  Skeleton,
  StatTile,
} from "@/components/ui";
import { endpoints } from "@/lib/api/endpoints";
import {
  DIMENSION_LABEL,
  formatNumber,
  formatPercent,
  formatScore,
  scoreTone,
} from "@/lib/format";
import { useAction, useResource } from "@/lib/hooks";
import type { Dimension } from "@/lib/api/types";

export default function AnalyticsPage() {
  const toast = useToast();
  const [days, setDays] = useState(30);
  const [granularity, setGranularity] = useState<"day" | "hour">("day");

  const overview = useResource(() => endpoints.overview());
  const trends = useResource(
    () => endpoints.trends({ days, granularity }),
    [days, granularity],
  );
  const failures = useResource(() => endpoints.failures(10));
  const runs = useResource(() => endpoints.listRuns({ limit: 100 }));
  const executions = useResource(() =>
    endpoints.listAllExecutions({ limit: 50 }),
  );

  const exportSnapshot = useAction(() =>
    endpoints.exportAnalytics({ days, granularity }),
  );

  const [runA, setRunA] = useState("");
  const [runB, setRunB] = useState("");
  const comparison = useResource(
    () => endpoints.compareRuns(runA, runB),
    [runA, runB],
    { enabled: Boolean(runA && runB && runA !== runB) },
  );

  async function downloadSnapshot() {
    const result = await exportSnapshot.run();
    if (result === null && exportSnapshot.error) {
      toast.push(exportSnapshot.error.message, "error", "Export failed");
      return;
    }
    toast.push("Analytics snapshot downloaded.", "success");
  }

  const points = trends.data?.points ?? [];
  const stats = overview.data;

  return (
    <AppShell
      eyebrow="Analytics"
      title="Quality trends"
      description="Pass-rate history, failure distribution and dimension-level performance, computed from the same stored runs the engine wrote."
      actions={
        <>
          <select
            value={granularity}
            onChange={(event) =>
              setGranularity(event.target.value as "day" | "hour")
            }
            aria-label="Trend granularity"
            className="h-9 rounded-pill bg-paper px-3 text-caption text-charcoal shadow-hairline outline-none transition-shadow duration-150 ease-out focus:shadow-hairline-strong"
          >
            <option value="day">Daily buckets</option>
            <option value="hour">Hourly buckets</option>
          </select>
          <select
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
            aria-label="Window length"
            className="h-9 rounded-pill bg-paper px-3 text-caption text-charcoal shadow-hairline outline-none transition-shadow duration-150 ease-out focus:shadow-hairline-strong"
          >
            {[7, 14, 30, 90, 365].map((value) => (
              <option key={value} value={value}>
                Last {value} day{value === 1 ? "" : "s"}
              </option>
            ))}
          </select>
          <Button
            variant="secondary"
            size="sm"
            icon={<Download size={14} />}
            onClick={downloadSnapshot}
            loading={exportSnapshot.pending}
          >
            Export snapshot
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {overview.error ? (
          <ErrorState error={overview.error} onRetry={overview.refresh} />
        ) : null}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Average score"
            value={stats ? formatScore(stats.average_overall_score) : "—"}
            hint={stats ? `${stats.total_runs} run(s) in total` : undefined}
            tone={stats ? scoreTone(stats.average_overall_score) : "neutral"}
          />
          <StatTile
            label="Pass rate"
            value={stats ? formatPercent(stats.pass_rate, 1) : "—"}
            hint={stats ? `fail rate ${formatPercent(stats.fail_rate, 1)}` : undefined}
          />
          <StatTile
            label="Suite pass rate"
            value={stats ? formatPercent(stats.suite_pass_rate, 1) : "—"}
            hint={
              stats
                ? `${stats.total_suite_executions} suite execution(s)`
                : undefined
            }
          />
          <StatTile
            label="Critical findings"
            value={
              failures.data ? formatNumber(failures.data.critical_findings) : "—"
            }
            hint={
              failures.data
                ? `${failures.data.verified_findings} verified · ${failures.data.risk_findings} risk`
                : undefined
            }
            tone={(failures.data?.critical_findings ?? 0) > 0 ? "bad" : "good"}
          />
        </div>

        <Card>
          <CardHeader
            title={`Quality trend · last ${days} day(s)`}
            description="Average score (forest) against pass rate (lime), one point per bucket"
            action={
              <Badge tone="neutral">{trends.data?.total_points ?? 0} bucket(s)</Badge>
            }
          />
          <div className="p-4">
            {trends.loading ? (
              <Skeleton className="h-[280px]" />
            ) : trends.error ? (
              <ErrorState error={trends.error} onRetry={trends.refresh} />
            ) : points.length === 0 ? (
              <EmptyState
                icon={<BarChart3 size={20} />}
                title="No runs in this window"
                description="Widen the window or run an evaluation to populate the trend."
              />
            ) : (
              <TrendChart points={points} height={280} />
            )}
          </div>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Pass / fail volume"
              description="Outcome mix per bucket"
            />
            <div className="p-4">
              {trends.loading ? (
                <Skeleton className="h-[240px]" />
              ) : points.length === 0 ? (
                <EmptyState title="Nothing to plot yet" />
              ) : (
                <PassFailChart points={points} height={240} />
              )}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Severity distribution"
              description="How findings are spread across severity levels"
            />
            <div className="p-4">
              {failures.loading ? (
                <Skeleton className="h-[240px]" />
              ) : failures.error ? (
                <ErrorState error={failures.error} onRetry={failures.refresh} />
              ) : (
                <SeverityChart
                  counts={failures.data?.by_severity ?? {}}
                  height={240}
                />
              )}
            </div>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Dimension performance"
              description="Average score per dimension across all stored runs"
            />
            <div className="p-4">
              {failures.loading ? (
                <Skeleton className="h-[280px]" />
              ) : failures.error ? (
                <ErrorState error={failures.error} onRetry={failures.refresh} />
              ) : (failures.data?.by_dimension.length ?? 0) === 0 ? (
                <EmptyState title="No dimension data yet" />
              ) : (
                <DimensionChart
                  data={failures.data?.by_dimension ?? []}
                  height={280}
                />
              )}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Failure distribution"
              description="Which failure categories fire most"
            />
            <div className="p-4">
              {failures.loading ? (
                <Skeleton className="h-[280px]" />
              ) : (failures.data?.by_category.length ?? 0) === 0 ? (
                <EmptyState title="No failures recorded" />
              ) : (
                <CategoryChart
                  data={failures.data?.by_category ?? []}
                  height={280}
                />
              )}
            </div>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader
              title="Dimension pass rates"
              description="Share of runs where each dimension met its threshold"
            />
            <div className="space-y-4 p-5">
              {(failures.data?.by_dimension ?? []).map((row) => (
                <div key={row.dimension}>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-caption font-medium text-forest-ink">
                      {DIMENSION_LABEL[row.dimension as Dimension] ?? row.dimension}
                    </p>
                    <p className="ag-num text-caption text-slate">
                      {formatScore(row.average_score)} avg ·{" "}
                      {formatPercent(row.pass_rate, 1)} pass ·{" "}
                      {row.failure_count} failure(s)
                    </p>
                  </div>
                  <Meter
                    className="mt-1.5"
                    value={row.pass_rate * 100}
                    tone={row.pass_rate >= 0.8 ? "good" : "bad"}
                    thickness={8}
                  />
                </div>
              ))}
              {(failures.data?.by_dimension.length ?? 0) === 0 ? (
                <EmptyState title="No dimension data yet" />
              ) : null}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Top rules"
              description="The most frequently fired rules"
            />
            <div className="p-4">
              {(failures.data?.top_rules.length ?? 0) === 0 ? (
                <EmptyState title="No failing rules recorded" />
              ) : (
                <ul className="space-y-2">
                  {failures.data?.top_rules.map((rule) => (
                    <li
                      key={rule.rule_id}
                      className="flex items-start justify-between gap-3 rounded-card bg-fog/60 px-3 py-2"
                    >
                      <div className="min-w-0">
                        <code className="font-mono text-micro break-all text-forest-ink">
                          {rule.rule_id}
                        </code>
                        <p className="mt-0.5 text-micro text-pebble">
                          {rule.verification} · worst {rule.worst_severity}
                        </p>
                      </div>
                      <span className="ag-num shrink-0 text-caption font-semibold text-forest-ink">
                        {rule.count}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Card>
        </div>

        <Card>
          <CardHeader
            title="Run comparison"
            description="Pick any two stored runs to see the score delta, per-dimension movement, and which rules appeared or resolved."
          />
          <div className="space-y-4 p-5">
            <div className="flex flex-wrap items-end gap-3">
              <label className="min-w-0 flex-1">
                <span className="mb-1.5 block text-micro font-semibold text-slate">
                  Baseline run (A)
                </span>
                <select
                  value={runA}
                  onChange={(event) => setRunA(event.target.value)}
                  className="h-10 w-full rounded-card bg-paper px-3 text-caption text-charcoal shadow-hairline outline-none transition-shadow duration-150 ease-out focus:shadow-hairline-strong"
                >
                  <option value="">Select baseline…</option>
                  {(runs.data?.items ?? []).map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.test_case_name} · {run.overall_score} ·{" "}
                      {run.verdict}
                    </option>
                  ))}
                </select>
              </label>
              <label className="min-w-0 flex-1">
                <span className="mb-1.5 block text-micro font-semibold text-slate">
                  Candidate run (B)
                </span>
                <select
                  value={runB}
                  onChange={(event) => setRunB(event.target.value)}
                  className="h-10 w-full rounded-card bg-paper px-3 text-caption text-charcoal shadow-hairline outline-none transition-shadow duration-150 ease-out focus:shadow-hairline-strong"
                >
                  <option value="">Select candidate…</option>
                  {(runs.data?.items ?? []).map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.test_case_name} · {run.overall_score} ·{" "}
                      {run.verdict}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {!runA || !runB ? (
              <EmptyState
                title="Select two runs to compare"
                description="The comparison is served live by GET /api/v1/analytics/compare/runs."
              />
            ) : runA === runB ? (
              <EmptyState title="Pick two different runs" />
            ) : comparison.loading ? (
              <Skeleton className="h-40" />
            ) : comparison.error ? (
              <ErrorState
                error={comparison.error}
                onRetry={comparison.refresh}
              />
            ) : comparison.data ? (
              <RunComparison delta={comparison.data} />
            ) : null}
          </div>
        </Card>
      </div>
    </AppShell>
  );
}