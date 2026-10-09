"use client";

import {
  Database,
  Layers,
  Play,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";

import { AppShell } from "@/components/shell";
import { useToast } from "@/components/toast";
import { Checkbox } from "@/components/fields";
import { ConfirmDialog } from "@/components/modal";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  ErrorState,
  Skeleton,
} from "@/components/ui";
import { endpoints } from "@/lib/api/endpoints";
import {
  categoryLabel,
  DIMENSION_LABEL,
  formatPercent,
  SEVERITY_LABEL,
} from "@/lib/format";
import { useAction, useLocalStorage, useResource } from "@/lib/hooks";
import type { Dimension } from "@/lib/api/types";
import { useState } from "react";

export default function SettingsPage() {
  const toast = useToast();
  const [confirmClear, setConfirmClear] = useState(false);

  const health = useResource(() => endpoints.health(), [], { pollMs: 20_000 });
  const meta = useResource(() => endpoints.dimensions());
  const safety = useResource(() => endpoints.safetyRules());
  const constraintTypes = useResource(() => endpoints.constraintTypes());
  const consistency = useResource(() => endpoints.consistencyModes());
  const disclaimer = useResource(() => endpoints.disclaimer());
  const llm = useResource(() => endpoints.metaLlmStatus());

  const seedCases = useAction(() => endpoints.seed());
  const seedRuns = useAction(() => endpoints.seedDemoRuns());
  const clearSeed = useAction(() => endpoints.removeSeed());

  const prefs = useLocalStorage("agentguard.prefs", {
    defaultPersist: true,
    dashboardPollSeconds: 20,
  });

  function refreshAll() {
    health.refresh();
    meta.refresh();
    safety.refresh();
    constraintTypes.refresh();
    consistency.refresh();
    disclaimer.refresh();
    llm.refresh();
  }

  async function seedDemoWorkspace() {
    const seeded = await seedCases.run();
    if (!seeded) {
      toast.push("Could not seed the workspace.", "error", "Seed failed");
      return;
    }
    const demo = await seedRuns.run();
    toast.push(
      demo
        ? `Seeded ${seeded.test_cases_created ?? 0} case(s), produced ${
            demo.runs_created ?? 0
          } run(s).`
        : "Cases seeded; demo runs failed to produce.",
      demo ? "success" : "error",
      "Demo workspace",
    );
    health.refresh();
  }

  async function removeSeedData() {
    const result = await clearSeed.run();
    if (result === null && clearSeed.error) {
      toast.push(clearSeed.error.message, "error", "Remove failed");
      setConfirmClear(false);
      return;
    }
    toast.push("Seed data removed.", "success");
    setConfirmClear(false);
    health.refresh();
  }

  return (
    <AppShell
      eyebrow="Settings"
      title="Workspace settings"
      description="Engine configuration, evaluation preferences and the honesty contract, exactly as the backend serves them."
      actions={
        <Button
          variant="secondary"
          size="sm"
          icon={<RefreshCw size={14} />}
          onClick={refreshAll}
          loading={health.refreshing}
        >
          Refresh
        </Button>
      }
    >
      <div className="space-y-4">
        <Card>
          <CardHeader
            title="Workspace"
            description="Live connection state and stored counts, straight from GET /health."
            action={
              health.data ? (
                <Badge tone={health.data.database_ok ? "good" : "bad"}>
                  {health.data.database_ok ? "connected" : "degraded"}
                </Badge>
              ) : null
            }
          />
          {health.loading ? (
            <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-16" />
              ))}
            </div>
          ) : health.error ? (
            <div className="p-4">
              <ErrorState error={health.error} onRetry={health.refresh} />
            </div>
          ) : (
            <dl className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["Product", health.data?.name ?? "—"],
                ["Version", health.data ? `v${health.data.version}` : "—"],
                ["Stage", health.data?.stage ?? "—"],
                ["Database", health.data?.database_ok ? "SQLite · OK" : "unavailable"],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="ag-eyebrow">{label}</dt>
                  <dd className="mt-1.5 text-caption font-medium text-obsidian">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          )}
          <div className="grid gap-4 border-t border-fog p-5 sm:grid-cols-3">
            {[
              ["Test cases", health.data?.test_cases],
              ["Evaluation runs", health.data?.runs],
              ["Test suites", health.data?.suites],
            ].map(([label, value]) => (
              <div key={String(label)}>
                <dt className="ag-eyebrow">{String(label)}</dt>
                <dd className="ag-num mt-1.5 text-subheading font-bold text-forest-ink">
                  {typeof value === "number" ? value : "—"}
                </dd>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Evaluation dimensions"
            description="Default weights and thresholds applied when a test case does not override them."
          />
          {meta.loading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-10" />
              ))}
            </div>
          ) : meta.error ? (
            <div className="p-4">
              <ErrorState error={meta.error} onRetry={meta.refresh} />
            </div>
          ) : (
            <div className="ag-scroll overflow-x-auto">
              <table className="w-full min-w-[620px] text-left">
                <thead>
                  <tr className="border-b border-fog">
                    {["Dimension", "Weight", "Threshold", "Methodology"].map(
                      (heading) => (
                        <th
                          key={heading}
                          className="px-4 py-2.5 text-micro font-semibold text-slate"
                        >
                          {heading}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {(meta.data?.dimensions ?? []).map((row) => (
                    <tr
                      key={row.dimension}
                      className="border-b border-fog last:border-b-0"
                    >
                      <td className="px-4 py-3 text-caption font-medium text-forest-ink">
                        {DIMENSION_LABEL[row.dimension] ?? row.dimension}
                      </td>
                      <td className="ag-num px-4 py-3 text-caption text-charcoal">
                        {row.default_weight}
                      </td>
                      <td className="ag-num px-4 py-3 text-caption text-charcoal">
                        {row.default_threshold}
                      </td>
                      <td className="px-4 py-3 text-caption text-slate">
                        {row.methodology}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {meta.data?.scoring_rule ? (
            <p className="border-t border-fog px-5 py-4 text-caption leading-relaxed text-slate">
              {meta.data.scoring_rule}
            </p>
          ) : null}
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Advisory LLM judge"
              description="OpenRouter is optional and additive; it never changes deterministic scores."
              action={
                llm.data ? (
                  <Badge tone={llm.data.configured ? "good" : "neutral"}>
                    {llm.data.configured ? "configured" : "no key"}
                  </Badge>
                ) : null
              }
            />
            {llm.loading ? (
              <div className="p-5">
                <Skeleton className="h-20" />
              </div>
            ) : llm.data ? (
              <dl className="grid gap-3 p-5 sm:grid-cols-2">
                {[
                  ["Provider", llm.data.provider],
                  ["Model", llm.data.model],
                  ["Key hint", llm.data.key_hint || "—"],
                  ["Timeout", `${llm.data.timeout_seconds}s`],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="ag-eyebrow">{label}</dt>
                    <dd className="mt-1 break-all font-mono text-caption text-obsidian">
                      {value}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </Card>

          <Card>
            <CardHeader
              title="Consistency modes"
              description="Which mode runs depends on how many responses you submit."
            />
            <div className="space-y-3 p-5">
              {(consistency.data?.modes ?? []).map((mode) => (
                <div key={mode.mode} className="rounded-card bg-fog/60 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-caption font-semibold text-forest-ink">
                      {mode.mode.replace(/_/g, " ")}
                    </p>
                    <Badge tone="neutral">{mode.trigger}</Badge>
                  </div>
                  <p className="mt-1.5 text-micro text-slate">{mode.methodology}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Safety rule catalogue"
              description={`${safety.data?.count ?? 0} policy rule(s) applied to every response.`}
            />
            <div className="ag-scroll max-h-80 space-y-2 overflow-y-auto p-4">
              {(safety.data?.rules ?? []).map((rule) => (
                <div
                  key={rule.rule_id}
                  className="flex items-start justify-between gap-3 rounded-card bg-fog/60 px-3 py-2"
                >
                  <div className="min-w-0">
                    <code className="font-mono text-micro text-forest-ink">
                      {rule.rule_id}
                    </code>
                    <p className="mt-0.5 text-micro text-slate">{rule.message}</p>
                  </div>
                  <Badge
                    tone={
                      rule.severity === "critical" || rule.severity === "high"
                        ? "bad"
                        : "neutral"
                    }
                  >
                    {SEVERITY_LABEL[rule.severity] ?? rule.severity}
                  </Badge>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Constraint types"
              description={`${constraintTypes.data?.count ?? 0} validator(s) drive the instruction-compliance dimension.`}
            />
            <div className="ag-scroll max-h-80 space-y-2 overflow-y-auto p-4">
              {(constraintTypes.data?.constraint_types ?? []).map((entry) => (
                <div
                  key={entry.type}
                  className="flex items-center justify-between gap-3 rounded-card bg-fog/60 px-3 py-2"
                >
                  <code className="font-mono text-micro text-forest-ink">
                    {entry.type.replace(/_/g, " ")}
                  </code>
                  <span className="shrink-0 text-micro text-pebble">
                    {entry.requires_value
                      ? "needs value"
                      : entry.requires_phrases
                        ? "needs phrases"
                        : "no argument"}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card className="p-6">
          <p className="ag-eyebrow">Honesty contract</p>
          <p className="mt-3 text-caption leading-relaxed text-charcoal">
            {disclaimer.data?.disclaimer ??
              "Findings are labelled verified or risk; heuristic detection cannot find every hallucination."}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-card bg-linen-mist px-3 py-2.5">
              <p className="text-caption font-semibold text-forest-ink">verified</p>
              <p className="mt-1 text-micro text-forest-ink/80">
                {disclaimer.data?.verified_means ?? "Provable against the grounding source."}
              </p>
            </div>
            <div className="rounded-card bg-fog px-3 py-2.5">
              <p className="text-caption font-semibold text-charcoal">risk</p>
              <p className="mt-1 text-micro text-slate">
                {disclaimer.data?.risk_means ??
                  "A heuristic indicator that requires human review."}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Preferences"
            description="Stored in this browser only. The backend owns per-test-case thresholds and weights."
          />
          <div className="space-y-4 p-5">
            <Checkbox
              label="Persist runs by default"
              hint="Pre-selects the persistence toggle on the Evaluations page."
              checked={prefs.value.defaultPersist}
              onChange={(next) =>
                prefs.update({ ...prefs.value, defaultPersist: next })
              }
            />
          </div>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader
            title="Demo data"
            description="Seed the six customer-support test cases, or remove them along with the runs generated from them."
          />
          <div className="flex flex-wrap items-center gap-3 p-5">
            <Button
              variant="primary"
              icon={<Sparkles size={14} />}
              onClick={seedDemoWorkspace}
              loading={seedCases.pending || seedRuns.pending}
            >
              Load demo workspace
            </Button>
            <Button
              variant="ghost"
              icon={<Trash2 size={14} />}
              onClick={() => setConfirmClear(true)}
            >
              Remove seed data
            </Button>
          </div>
        </Card>
      </div>

      <ConfirmDialog
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        onConfirm={removeSeedData}
        pending={clearSeed.pending}
        title="Remove seed data?"
        message="The six seeded test cases and every run generated from them will be deleted. Test cases you created yourself are untouched."
        confirmLabel="Remove seed data"
      />
    </AppShell>
  );
}