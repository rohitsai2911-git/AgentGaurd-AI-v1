"use client";

import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Info,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Meter,
  ProgressRing,
  SeverityBadge,
  VerdictBadge,
  VerificationTag,
} from "@/components/ui";
import type {
  ComparisonResponse,
  Dimension,
  DimensionResult,
  EvaluationReport,
  FailureReport,
  Finding,
  LlmEvaluation,
} from "@/lib/api/types";
import {
  categoryLabel,
  cn,
  DIMENSION_BLURB,
  DIMENSION_LABEL,
  formatDuration,
  formatScore,
  formatSigned,
  scoreTone,
  severityTone,
  TONE_CLASSES,
  verdictLabel,
} from "@/lib/format";

/* ------------------------------------------------------------------ */
/* Findings                                                            */
/* ------------------------------------------------------------------ */

export function FindingRow({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false);
  const tone = severityTone(finding.severity);

  return (
    <li className="border-t border-fog first:border-t-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors duration-150 ease-out hover:bg-fog/60"
      >
        <span
          aria-hidden
          className={cn("mt-1.5 size-2 shrink-0 rounded-full", TONE_CLASSES[tone].bar)}
        />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <code className="rounded-sm bg-fog px-1.5 py-0.5 font-mono text-micro text-forest-ink">
              {finding.rule_id}
            </code>
            <SeverityBadge severity={finding.severity} />
            <VerificationTag verification={finding.verification} />
            {finding.response_index !== null &&
            finding.response_index !== undefined ? (
              <span className="ag-num text-micro text-pebble">
                response #{finding.response_index + 1}
              </span>
            ) : null}
          </span>
          <span className="mt-1.5 block text-caption text-charcoal">
            {finding.message}
          </span>
        </span>
        <ChevronDown
          size={16}
          className={cn(
            "mt-1 shrink-0 text-pebble transition-transform duration-200 ease-out",
            open && "rotate-180",
          )}
        />
      </button>

      {open ? (
        <div className="space-y-3 px-4 pb-4 pl-9">
          {finding.evidence ? (
            <div>
              <p className="ag-eyebrow">Evidence</p>
              <pre className="ag-scroll mt-1.5 overflow-x-auto rounded-card bg-fog px-3 py-2 font-mono text-micro whitespace-pre-wrap text-charcoal">
                {finding.evidence}
              </pre>
            </div>
          ) : null}
          <div>
            <p className="ag-eyebrow">Remediation</p>
            <p className="mt-1.5 text-caption text-slate">{finding.remediation}</p>
          </div>
        </div>
      ) : null}
    </li>
  );
}

export function FindingsList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return (
      <p className="flex items-center gap-2 px-4 py-5 text-caption text-slate">
        <CheckCircle2 size={15} className="text-forest-ink" />
        No findings from the rules in this dimension.
      </p>
    );
  }
  return (
    <ul>
      {findings.map((finding, index) => (
        <FindingRow key={`${finding.rule_id}-${index}`} finding={finding} />
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ */
/* Dimension card                                                      */
/* ------------------------------------------------------------------ */

export function DimensionCard({ result }: { result: DimensionResult }) {
  const tone = scoreTone(result.score);
  const threshold = Number(result.details?.threshold ?? 0);

  return (
    <Card className="overflow-hidden">
      <CardHeader
        title={DIMENSION_LABEL[result.dimension as Dimension] ?? result.dimension}
        description={`${result.findings.length} finding(s) · ${
          result.passed ? "met its threshold" : "below threshold"
        }`}
        action={
          <>
            <Badge tone={result.passed ? "good" : "bad"}>
              {result.passed ? "Pass" : "Fail"}
            </Badge>
            <span className="ag-num text-body-lg font-bold text-forest-ink">
              {formatScore(result.score)}
            </span>
          </>
        }
      />

      <div className="px-5 pt-4">
        <Meter value={result.score} tone={tone} thickness={6} />
        <div className="mt-2 flex items-center justify-between text-micro text-pebble">
          <span>0</span>
          <span className="ag-num">
            threshold {threshold > 0 ? threshold : "—"}
          </span>
          <span>100</span>
        </div>

        {result.forced_fail ? (
          <p className="mt-3 flex items-center gap-2 rounded-card bg-forest-ink px-3 py-2 text-micro font-medium text-lime-voltage">
            <ShieldAlert size={14} />
            Forced failure — a blocking rule fired regardless of the numeric score.
          </p>
        ) : null}

        <details className="group mt-3">
          <summary className="cursor-pointer list-none text-micro font-medium text-slate transition-colors duration-150 ease-out hover:text-forest-ink">
            Methodology
          </summary>
          <p className="mt-2 text-micro leading-relaxed text-slate">
            {result.methodology}
          </p>
          <p className="mt-2 text-micro text-pebble">
            {DIMENSION_BLURB[result.dimension as Dimension]}
          </p>
        </details>
      </div>

      <div className="mt-4 border-t border-fog">
        <FindingsList findings={result.findings} />
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Run report                                                          */
/* ------------------------------------------------------------------ */

export function RunReport({
  report,
  onExport,
  exporting,
}: {
  report: EvaluationReport;
  onExport?: () => void;
  exporting?: boolean;
}) {
  const tone = scoreTone(report.overall_score);

  return (
    <div className="space-y-4">
      <Card className="grid gap-6 p-6 lg:grid-cols-[auto_1fr] lg:items-center">
        <div className="flex items-center gap-6">
          <ProgressRing
            value={report.overall_score}
            size={132}
            tone={tone}
            label="overall"
            sublabel="weighted"
          />
          <div>
            <p className="ag-eyebrow">Verdict</p>
            <div className="mt-2">
              <VerdictBadge verdict={report.verdict} />
            </div>
            <p className="ag-eyebrow mt-5">Max severity</p>
            <div className="mt-2">
              <SeverityBadge severity={report.max_severity} />
            </div>
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {report.consistency_mode ? (
              <Badge tone="neutral">{report.consistency_mode} mode</Badge>
            ) : null}
            <Badge tone="neutral">
              {report.responses_submitted} response
              {report.responses_submitted === 1 ? "" : "s"}
            </Badge>
            <Badge tone="neutral">{formatDuration(report.duration_ms)}</Badge>
          </div>

          <p className="mt-4 text-caption leading-relaxed text-charcoal">
            {report.summary}
          </p>

          <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
            <div>
              <dt className="text-micro text-pebble">Test case</dt>
              <dd className="text-caption font-medium text-forest-ink">
                {report.test_case_name}
              </dd>
            </div>
            <div>
              <dt className="text-micro text-pebble">Agent</dt>
              <dd className="text-caption font-medium text-forest-ink">
                {report.agent_name || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-micro text-pebble">Run</dt>
              <dd className="ag-num font-mono text-caption break-all text-forest-ink">
                {report.run_id ?? "not persisted"}
              </dd>
            </div>
          </dl>

          <div className="mt-5">
            <p className="ag-eyebrow">Weights used</p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {Object.entries(report.weights_used).map(([dimension, weight]) => (
                <li
                  key={dimension}
                  className="ag-num rounded-pill bg-fog px-2.5 py-1 text-micro text-charcoal"
                >
                  {dimension.replace(/_/g, " ")} {weight}
                </li>
              ))}
            </ul>
          </div>

          {onExport ? (
            <Button
              variant="secondary"
              size="sm"
              className="mt-5"
              onClick={onExport}
              loading={exporting}
            >
              Export this run as JSON
            </Button>
          ) : null}
        </div>
      </Card>

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="ag-eyebrow">Hallucination assessment</p>
            <p className="mt-1.5 text-body-sm font-semibold text-obsidian">
              {report.hallucination_assessment.verdict.replace(/_/g, " ")}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="neutral">
              {report.hallucination_assessment.contradicted_values.length}{" "}
              contradicted
            </Badge>
            <Badge tone="neutral">
              {report.hallucination_assessment.unsupported_claims.length} unsupported
            </Badge>
          </div>
        </div>

        {report.hallucination_assessment.contradicted_values.length > 0 ? (
          <div className="mt-5">
            <p className="ag-eyebrow">Verified contradictions</p>
            <ul className="mt-2 space-y-1.5">
              {report.hallucination_assessment.contradicted_values.map(
                (claim, index) => (
                  <li
                    key={index}
                    className="rounded-card bg-linen-mist px-3 py-2 text-caption text-forest-ink"
                  >
                    {claim}
                  </li>
                ),
              )}
            </ul>
          </div>
        ) : null}

        {report.hallucination_assessment.unsupported_claims.length > 0 ? (
          <div className="mt-5">
            <p className="ag-eyebrow">Risk indicators · human review required</p>
            <ul className="mt-2 space-y-1.5">
              {report.hallucination_assessment.unsupported_claims
                .slice(0, 8)
                .map((claim, index) => (
                  <li
                    key={index}
                    className="rounded-card bg-fog px-3 py-2 text-caption text-charcoal"
                  >
                    {claim}
                  </li>
                ))}
            </ul>
            {report.hallucination_assessment.unsupported_claims.length > 8 ? (
              <p className="mt-2 text-micro text-pebble">
                +{report.hallucination_assessment.unsupported_claims.length - 8} more
                indicator(s)
              </p>
            ) : null}
          </div>
        ) : null}

        <div className="mt-5">
          <p className="ag-eyebrow">Grounding source</p>
          <ul className="mt-2 space-y-1">
            {report.hallucination_assessment.grounding_sources.map(
              (source, index) => (
                <li key={index} className="text-caption text-slate">
                  {source}
                </li>
              ),
            )}
          </ul>
        </div>

        <p className="mt-5 flex gap-2 rounded-card bg-fog px-3 py-2.5 text-micro leading-relaxed text-slate">
          <Info size={14} className="mt-0.5 shrink-0" />
          {report.disclaimer}
        </p>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Failure intelligence                                                */
/* ------------------------------------------------------------------ */

export function FailureIntelligence({ report }: { report: FailureReport }) {
  if (report.total_failures === 0) {
    return (
      <EmptyState
        title="No failing checks"
        description="Every dimension that ran met its threshold and no blocking rule fired."
        icon={<CheckCircle2 size={20} />}
      />
    );
  }

  const categories = Object.entries(report.by_category).sort(
    (a, b) => b[1] - a[1],
  );
  const severities = Object.entries(report.by_severity).filter(
    ([, count]) => count > 0,
  );

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <p className="ag-eyebrow">Narrative</p>
        <p className="mt-2 text-caption leading-relaxed text-charcoal">
          {report.narrative}
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          <Badge tone="bad">{report.critical_count} critical</Badge>
          <Badge tone="neutral">{report.verified_count} verified</Badge>
          <Badge tone="neutral">{report.risk_count} risk</Badge>
        </div>

        {categories.length > 0 ? (
          <div className="mt-6 space-y-3">
            <p className="ag-eyebrow">By category</p>
            {categories.map(([category, count]) => (
              <div key={category} className="flex items-center gap-3">
                <span className="w-44 shrink-0 text-caption text-charcoal">
                  {categoryLabel(category)}
                </span>
                <Meter
                  value={count}
                  max={report.total_failures}
                  tone="bad"
                  thickness={8}
                />
                <span className="ag-num w-8 shrink-0 text-right text-caption font-semibold text-forest-ink">
                  {count}
                </span>
              </div>
            ))}
          </div>
        ) : null}

        {severities.length > 0 ? (
          <div className="mt-6">
            <p className="ag-eyebrow">By severity</p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {severities.map(([severity, count]) => (
                <li key={severity} className="flex items-center gap-2">
                  <SeverityBadge severity={severity as never} />
                  <span className="ag-num text-caption text-charcoal">
                    {count}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </Card>

      <Card className="overflow-hidden">
        <CardHeader
          title="Explanations and remediation"
          description={`${report.explanations.length} failing check(s), each with the rule that produced it`}
        />
        <ul>
          {report.explanations.map((explanation, index) => (
            <li
              key={`${explanation.rule_id}-${index}`}
              className="border-t border-fog px-4 py-4 first:border-t-0"
            >
              <div className="flex flex-wrap items-center gap-2">
                <code className="rounded-sm bg-fog px-1.5 py-0.5 font-mono text-micro text-forest-ink">
                  {explanation.rule_id}
                </code>
                <Badge tone="neutral">
                  {categoryLabel(explanation.category)}
                </Badge>
                <SeverityBadge severity={explanation.severity} />
                <VerificationTag verification={explanation.verification} />
              </div>
              <p className="mt-2 text-caption text-charcoal">
                {explanation.explanation}
              </p>
              <p className="mt-2 text-caption text-slate">
                <span className="font-medium text-forest-ink">Fix: </span>
                {explanation.remediation}
              </p>
              {explanation.evidence ? (
                <pre className="ag-scroll mt-2 overflow-x-auto rounded-card bg-fog px-3 py-2 font-mono text-micro whitespace-pre-wrap text-charcoal">
                  {explanation.evidence}
                </pre>
              ) : null}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Run comparison                                                      */
/* ------------------------------------------------------------------ */

export function RunComparison({ delta }: { delta: ComparisonResponse }) {
  const isRegression = delta.regression;
  const improved = delta.score_delta > 0;
  const Icon = isRegression ? TrendingDown : improved ? TrendingUp : ArrowRight;

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Icon
              size={22}
              className={isRegression ? "text-obsidian" : "text-forest-ink"}
            />
            <div>
              <p className="ag-eyebrow">
                {delta.a.label} vs {delta.b.label}
              </p>
              <p className="mt-1 text-body-sm font-semibold text-obsidian">
                {isRegression ? "Regression detected" : improved ? "Improvement" : "No change"}
              </p>
            </div>
          </div>
          <div className="ag-num flex items-center gap-4">
            <span className="text-subheading font-bold text-charcoal">
              {delta.a.overall_score.toFixed(1)}
            </span>
            <ArrowRight size={16} className="text-pebble" />
            <span className="text-subheading font-bold text-forest-ink">
              {delta.b.overall_score.toFixed(1)}
            </span>
            <Badge tone={isRegression ? "bad" : improved ? "good" : "neutral"}>
              {formatSigned(delta.score_delta)}
            </Badge>
          </div>
        </div>

        {delta.verdict_changed ? (
          <p className="mt-4 flex gap-2 rounded-card bg-fog px-3 py-2 text-caption text-charcoal">
            <ShieldAlert size={14} className="mt-0.5 shrink-0" />
            Verdict flipped from {verdictLabel(delta.a.verdict)} to{" "}
            {verdictLabel(delta.b.verdict)}.
          </p>
        ) : null}

        {Object.keys(delta.per_dimension_delta).length > 0 ? (
          <div className="mt-6 space-y-3">
            <p className="ag-eyebrow">Per-dimension delta</p>
            {Object.entries(delta.per_dimension_delta).map(([dim, deltaVal]) => (
              <div key={dim} className="flex items-center gap-3">
                <span className="w-44 shrink-0 text-caption text-charcoal">
                  {DIMENSION_LABEL[dim as Dimension] ?? dim}
                </span>
                <Meter
                  value={Math.abs(deltaVal)}
                  max={100}
                  tone={deltaVal < 0 ? "bad" : "good"}
                  thickness={6}
                />
                <span className="ag-num w-12 shrink-0 text-right text-caption font-semibold text-forest-ink">
                  {formatSigned(deltaVal)}
                </span>
              </div>
            ))}
          </div>
        ) : null}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="New rules" description="Rules that fired in B but not A" />
          <div className="p-4">
            {delta.new_rules.length === 0 ? (
              <EmptyState title="No new rules" />
            ) : (
              <ul className="space-y-2">
                {delta.new_rules.map((rule) => (
                  <li
                    key={rule}
                    className="rounded-card bg-forest-ink px-3 py-2 font-mono text-micro text-lime-voltage"
                  >
                    {rule}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Resolved rules"
            description="Rules that fired in A but not B"
          />
          <div className="p-4">
            {delta.resolved_rules.length === 0 ? (
              <EmptyState title="No resolved rules" />
            ) : (
              <ul className="space-y-2">
                {delta.resolved_rules.map((rule) => (
                  <li
                    key={rule}
                    className="rounded-card bg-linen-mist px-3 py-2 font-mono text-micro text-forest-ink"
                  >
                    {rule}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}