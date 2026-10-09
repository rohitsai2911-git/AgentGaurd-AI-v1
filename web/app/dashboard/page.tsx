"use client";

import {
  Activity,
  ArrowRight,
  CircleAlert,
  Gauge,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { PassFailChart, TrendChart } from "@/components/charts";
import { AppShell } from "@/components/shell";
import { useToast } from "@/components/toast";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  Skeleton,
  StatTile,
  VerdictBadge,
} from "@/components/ui";
import { endpoints } from "@/lib/api/endpoints";
import {
  formatNumber,
  formatPercent,
  formatRelative,
  formatScore,
  scoreTone,
  shortId,
} from "@/lib/format";
import { useAction, useResource } from "@/lib/hooks";

export default function DashboardPage() {
  const toast = useToast();
  const overview = useResource(() => endpoints.overview(), [], { pollMs: 20_000 });
  const trends = useResource(() =>
    endpoints.trends({ days: 14, granularity: "day" }),
  );
  const failures = useResource(() => endpoints.failures(6));
  const runs = useResource(() => endpoints.listRuns({ limit: 8 }));

  const seedCases = useAction(() => endpoints.seed());
  const seedRuns = useAction(() => endpoints.seedDemoRuns());

  const stats = overview.data;
  const points = trends.data?.points ?? [];
  const hasActivity =
    (stats?.total_runs ?? 0) > 0 || (stats?.total_suite_executions ?? 0) > 0;

  function refreshAll() {
    overview.refresh();
    trends.refresh();
    runs.refresh();
    failures.refresh();
  }

  async function loadDemoWorkspace() {
    const seeded = await seedCases.run();
    if (!seeded) {
      toast.push("Could not seed the workspace.", "error", "Seed failed");
      return;
    }
    const demo = await seedRuns.run();
    if (!demo) {
      toast.push("Test cases seeded, but producing demo runs failed.", "error");
      return;
    }
    toast.push(
      `Seeded ${seeded.test_cases_created ?? 0} test case(s) and produced ${
        demo.runs_created ?? 0
      } run(s) with the real engine.`,
      "success",
      "Demo workspace ready",
    );
    refreshAll();
  }

  return (
    <AppShell
      eyebrow="Dashboard"
      title="Quality posture"
      description="Aggregate agent quality across every stored evaluation run and suite execution in this workspace."
      actions={
        <>
          <Button
            variant="secondary"
            size="sm"
            icon={<RefreshCw size={14} />}
            onClick={refreshAll}
            loading={overview.refreshing}
          >
            Refresh
          </Button>
          <Link href="/evaluations">
            <Button variant="primary" size="sm" iconRight={<ArrowRight size={14} />}>
              Run evaluation
            </Button>
          </Link>
        </>
      }
    >
      <div className="space-y-4">
        {overview.error ? (
          <ErrorState error={overview.error} onRetry={overview.refresh} />
        ) : null}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Average quality score"
            value={stats ? formatScore(stats.average_overall_score) : "—"}
            hint={
              stats
                ? `best ${stats.best_overall_score} · worst ${stats.worst_overall_score}`
                : undefined
            }
            tone={stats ? scoreTone(stats.average_overall_score) : "neutral"}
            icon={<Gauge size={16} />}
          />
          <StatTile
            label="Evaluation pass rate"
            value={stats ? formatPercent(stats.pass_rate, 1) : "—"}
            hint={stats ? `${stats.total_runs} stored run(s)` : undefined}
            icon={<Activity size={16} />}
          />
          <StatTile
            label="Test executions"
            value={
              stats
                ? formatNumber(stats.total_runs + stats.total_suite_executions)
                : "—"
            }
            hint={
              stats
                ? `${stats.total_runs} direct · ${stats.total_suite_executions} suite`
                : undefined
            }
            icon={<Sparkles size={16} />}
          />
          <StatTile
            label="Critical failures"
            value={failures.data ? formatNumber(failures.data.critical_findings) : "—"}
            hint={
              failures.data
                ? `${failures.data.verified_findings} verified · ${failures.data.risk_findings} risk`
                : undefined
            }
            tone={(failures.data?.critical_findings ?? 0) > 0 ? "bad" : "good"}
            icon={<CircleAlert size={16} />}
          />
        </div>

        {!hasActivity && !overview.loading ? (
          <Card className="p-6">
            <EmptyState
              icon={<Sparkles size={20} />}
              title="This workspace has no evaluations yet"
              description="Load the six customer-support seed test cases and produce real evaluation history from their known-good responses. Runs are computed by the engine, never fabricated."
              action={
                <Button
                  variant="primary"
                  onClick={loadDemoWorkspace}
                  loading={seedCases.pending || seedRuns.pending}
                >
                  Load demo workspace
                </Button>
              }
            />
          </Card>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader
              title="Quality trend"
              description="Average score and pass rate per day over the last 14 days"
              action={
                <Badge tone="neutral">
                  {trends.data?.total_points ?? 0} bucket(s)
                </Badge>
              }
            />
            <div className="p-4">
              {trends.loading ? (
                <Skeleton className="h-[260px]" />
              ) : trends.error ? (
                <ErrorState error={trends.error} onRetry={trends.refresh} />
              ) : points.length === 0 ? (
                <EmptyState
                  title="No runs in the last 14 days"
                  description="Trend buckets appear as soon as evaluations are stored."
                />
              ) : (
                <TrendChart points={points} />
              )}
            </div>
          </Card>

          <Card>
            <CardHeader title="Pass / fail volume" description="Daily outcome mix" />
            <div className="p-4">
              {trends.loading ? (
                <Skeleton className="h-[220px]" />
              ) : points.length === 0 ? (
                <EmptyState title="Nothing to plot yet" />
              ) : (
                <PassFailChart points={points} />
              )}
            </div>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="overflow-hidden lg:col-span-2">
            <CardHeader
              title="Recent activity"
              description="Most recent stored evaluation runs"
              action={
                <Link href="/reports" className="ag-link text-caption">
                  All reports
                </Link>
              }
            />
            {runs.loading ? (
              <div className="space-y-2 p-4">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-12" />
                ))}
              </div>
            ) : runs.error ? (
              <div className="p-4">
                <ErrorState error={runs.error} onRetry={runs.refresh} />
              </div>
            ) : (runs.data?.items.length ?? 0) === 0 ? (
              <div className="p-4">
                <EmptyState title="No runs recorded" />
              </div>
            ) : (
              <div className="ag-scroll overflow-x-auto">
                <table className="w-full min-w-[620px] text-left">
                  <thead>
                    <tr className="border-b border-fog">
                      {["Verdict", "Test case", "Score", "Severity", "When"].map(
                        (heading) => (
                          <th
                            key={heading}
                            className="px-4 py-2 text-micro font-semibold text-slate"
                          >
                            {heading}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {runs.data?.items.map((run) => (
                      <tr
                        key={run.id}
                        className="border-b border-fog transition-colors duration-150 ease-out last:border-b-0 hover:bg-fog/50"
                      >
                        <td className="px-4 py-3">
                          <VerdictBadge verdict={run.verdict} size="sm" />
                        </td>
                        <td className="px-4 py-3">
                          <Link
                            href={`/reports?run=${run.id}`}
                            className="text-caption font-medium text-forest-ink hover:underline"
                          >
                            {run.test_case_name}
                          </Link>
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
                          {formatRelative(run.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card>
            <CardHeader
              title="Top failing rules"
              description="Most frequent rules across all runs"
            />
            <div className="p-4">
              {failures.loading ? (
                <Skeleton className="h-40" />
              ) : (failures.data?.top_rules.length ?? 0) === 0 ? (
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
      </div>
    </AppShell>
  );
}