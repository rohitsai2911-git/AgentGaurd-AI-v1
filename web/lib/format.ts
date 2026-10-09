import type { Dimension, RunVerdict, Severity } from "./api/types";

export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ */
/* Domain vocabularies                                                 */
/* ------------------------------------------------------------------ */

export const DIMENSION_ORDER: Dimension[] = [
  "accuracy",
  "hallucination_risk",
  "safety",
  "instruction_compliance",
  "consistency",
];

export const DIMENSION_LABEL: Record<Dimension, string> = {
  accuracy: "Accuracy",
  hallucination_risk: "Hallucination risk",
  safety: "Safety",
  instruction_compliance: "Instruction compliance",
  consistency: "Consistency",
};

export const DIMENSION_BLURB: Record<Dimension, string> = {
  accuracy:
    "Token overlap with the expected answer, required-keyword coverage and expected numeric values.",
  hallucination_risk:
    "Claims in the response tested against the grounding source. Risk findings are indicators; verified ones are provable.",
  safety:
    "Policy catalogue applied to the response, including PII and unsafe-promise rules.",
  instruction_compliance:
    "Declarative constraints on the test case, one validator per constraint type.",
  consistency:
    "Internal self-contradiction for a single response, or cross-response contradiction for many.",
};

export const SEVERITY_ORDER: Severity[] = [
  "none",
  "info",
  "low",
  "medium",
  "high",
  "critical",
];

export const SEVERITY_LABEL: Record<Severity, string> = {
  none: "None",
  info: "Info",
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export function severityRank(severity: Severity): number {
  const index = SEVERITY_ORDER.indexOf(severity);
  return index === -1 ? 0 : index;
}

/** Failure categories emitted by app/evaluation/failure_intel.py */
export const CATEGORY_LABEL: Record<string, string> = {
  policy_violation: "Policy violation",
  hallucination_risk: "Hallucination risk",
  accuracy_deviation: "Accuracy deviation",
  instruction_violation: "Instruction violation",
  consistency_defect: "Consistency defect",
  other: "Other",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABEL[category] ?? category.replace(/_/g, " ");
}

export function dimensionsLabel(dimensions: Dimension[] | undefined): string {
  if (!dimensions || dimensions.length === 0) return "all dimensions";
  return dimensions.map((d) => DIMENSION_LABEL[d]).join(", ");
}

export function verdictLabel(verdict: RunVerdict | string): string {
  return verdict === "pass" ? "Pass" : "Fail";
}

/* ------------------------------------------------------------------ */
/* Tones — flat fills from the palette, never gradients                */
/* ------------------------------------------------------------------ */

export type Tone = "good" | "watch" | "bad" | "neutral";

export function scoreTone(score: number): Tone {
  if (score >= 80) return "good";
  if (score >= 60) return "watch";
  return "bad";
}

export const TONE_CLASSES: Record<
  Tone,
  { chip: string; bar: string; text: string }
> = {
  good: {
    chip: "bg-linen-mist text-forest-ink",
    bar: "bg-forest-ink",
    text: "text-forest-ink",
  },
  watch: {
    chip: "bg-fog text-charcoal",
    bar: "bg-slate",
    text: "text-slate",
  },
  bad: {
    chip: "bg-forest-ink text-lime-voltage",
    bar: "bg-obsidian",
    text: "text-obsidian",
  },
  neutral: {
    chip: "bg-fog text-slate",
    bar: "bg-pebble",
    text: "text-slate",
  },
};

export function severityTone(severity: Severity): Tone {
  if (severity === "critical" || severity === "high") return "bad";
  if (severity === "medium") return "watch";
  if (severity === "low" || severity === "info") return "good";
  return "neutral";
}

/* ------------------------------------------------------------------ */
/* Formatting                                                          */
/* ------------------------------------------------------------------ */

/**
 * The backend stores naive UTC datetimes in SQLite. Browsers would parse
 * "2026-10-02T16:16:49" as local time and show the wrong hour, so an
 * explicit UTC offset is attached when the string carries none.
 */
export function normalizeTimestamp(value: string): string {
  if (/(?:Z|[+-]\d{2}:?\d{2})$/.test(value)) return value;
  return `${value}Z`;
}

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(normalizeTimestamp(value));
  return Number.isNaN(date.getTime()) ? "—" : dateTimeFormatter.format(date);
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(normalizeTimestamp(value));
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

export function formatRelative(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(normalizeTimestamp(value));
  if (Number.isNaN(date.getTime())) return "—";
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (seconds < 45) return "just now";
  const units: Array<[number, Intl.RelativeTimeFormatUnit]> = [
    [60, "second"],
    [60, "minute"],
    [24, "hour"],
    [7, "day"],
    [4.348, "week"],
    [12, "month"],
    [Number.POSITIVE_INFINITY, "year"],
  ];
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  let amount = seconds;
  for (const [step, unit] of units) {
    if (Math.abs(amount) < step) {
      return formatter.format(-Math.round(amount), unit);
    }
    amount /= step;
  }
  return formatter.format(-Math.round(amount), "year");
}

/** Backend ratios are 0–1 fractions. */
export function formatPercent(
  ratio: number | null | undefined,
  digits = 1,
): string {
  if (ratio === null || ratio === undefined || Number.isNaN(ratio)) return "—";
  return `${(ratio * 100).toFixed(digits)}%`;
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return "—";
  return Number.isInteger(score) ? String(score) : score.toFixed(1);
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat().format(value);
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(ms < 10_000 ? 2 : 1)} s`;
  const minutes = Math.floor(ms / 60_000);
  return `${minutes}m ${Math.round((ms % 60_000) / 1000)}s`;
}

export function formatSigned(value: number, digits = 1): string {
  const rounded = Number(value.toFixed(digits));
  return `${rounded > 0 ? "+" : ""}${rounded}`;
}

export function shortId(id?: string | null, length = 8): string {
  if (!id) return "—";
  return id.length <= length ? id : id.slice(0, length);
}

/** "a, b , c" -> ["a","b","c"] — used by every tag/keyword field. */
export function parseListInput(value: string): string[] {
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function parseNumberListInput(value: string): number[] {
  return parseListInput(value)
    .map((entry) => Number(entry))
    .filter((entry) => Number.isFinite(entry));
}

export function displayList(
  values: string[] | number[] | undefined | null,
): string {
  if (!values || values.length === 0) return "—";
  return values.join(", ");
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}