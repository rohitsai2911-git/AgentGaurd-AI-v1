"use client";

import { Loader2, RefreshCw } from "lucide-react";
import {
  forwardRef,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";

import { API_BASE_URL, ApiError } from "@/lib/api/client";
import type { RunVerdict, Severity } from "@/lib/api/types";
import {
  cn,
  SEVERITY_LABEL,
  severityTone,
  TONE_CLASSES,
  type Tone,
} from "@/lib/format";

/* ------------------------------------------------------------------ */
/* Buttons — pills, always. Exact properties, never `transition: all`  */
/* ------------------------------------------------------------------ */

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const BUTTON_BASE =
  "inline-flex select-none items-center justify-center gap-2 rounded-pill font-medium whitespace-nowrap " +
  "transition-[transform,background-color,color,box-shadow,filter] duration-150 ease-out " +
  "active:scale-[0.97] disabled:pointer-events-none disabled:opacity-40";

const BUTTON_VARIANT: Record<ButtonVariant, string> = {
  primary: "bg-lime-voltage text-forest-ink hover:brightness-95",
  secondary: "bg-paper text-forest-ink shadow-hairline hover:shadow-hairline-strong",
  ghost: "text-forest-ink hover:bg-fog",
  danger: "bg-forest-ink text-lime-voltage hover:brightness-115",
};

const BUTTON_SIZE: Record<ButtonSize, string> = {
  sm: "h-9 px-4 text-caption",
  md: "h-11 px-6 text-body-sm",
  lg: "h-12 px-7 text-body-sm",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  iconRight?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "secondary",
      size = "md",
      loading = false,
      icon,
      iconRight,
      className,
      children,
      disabled,
      type = "button",
      ...rest
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        className={cn(
          BUTTON_BASE,
          BUTTON_VARIANT[variant],
          BUTTON_SIZE[size],
          className,
        )}
        {...rest}
      >
        {loading ? <Loader2 size={15} className="animate-spin" /> : icon}
        {children}
        {iconRight}
      </button>
    );
  },
);

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  tone?: "default" | "danger";
  size?: "sm" | "md";
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton(
    { label, tone = "default", size = "md", className, children, ...rest },
    ref,
  ) {
    return (
      <button
        ref={ref}
        type="button"
        aria-label={label}
        title={label}
        className={cn(
          "inline-flex items-center justify-center rounded-full text-slate",
          "transition-[transform,background-color,color] duration-150 ease-out",
          "active:scale-[0.94] disabled:pointer-events-none disabled:opacity-40",
          tone === "danger"
            ? "hover:bg-forest-ink hover:text-lime-voltage"
            : "hover:bg-fog hover:text-forest-ink",
          size === "sm" ? "size-7" : "size-9",
          className,
        )}
        {...rest}
      >
        {children}
      </button>
    );
  },
);

/* ------------------------------------------------------------------ */
/* Badges — flat fills, no status red                                 */
/* ------------------------------------------------------------------ */

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-pill px-3 py-1 text-micro font-medium tracking-normal",
        TONE_CLASSES[tone].chip,
        className,
      )}
    >
      {children}
    </span>
  );
}

export function VerdictBadge({
  verdict,
  size = "md",
}: {
  verdict: RunVerdict | string;
  size?: "sm" | "md";
}) {
  const pass = verdict === "pass";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-pill font-semibold tracking-normal",
        pass
          ? "bg-lime-voltage text-forest-ink"
          : "bg-forest-ink text-lime-voltage",
        size === "sm" ? "px-2.5 py-0.5 text-micro" : "px-3 py-1 text-micro",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "size-1.5 rounded-full",
          pass ? "bg-forest-ink" : "bg-lime-voltage",
        )}
      />
      {pass ? "Pass" : "Fail"}
    </span>
  );
}

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-pill px-2.5 py-0.5 text-micro font-medium tracking-normal",
        TONE_CLASSES[severityTone(severity)].chip,
        className,
      )}
    >
      {SEVERITY_LABEL[severity] ?? severity}
    </span>
  );
}

/** Distinguishes provable findings from heuristic indicators. */
export function VerificationTag({ verification }: { verification: string }) {
  const verified = verification === "verified";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-pill px-2.5 py-0.5 text-micro font-medium tracking-normal",
        verified
          ? "bg-linen-mist text-forest-ink"
          : "bg-fog text-slate",
      )}
      title={
        verified
          ? "Provable against the test case grounding source"
          : "Heuristic indicator requiring human review"
      }
    >
      {verified ? "verified" : "risk"}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Surfaces                                                            */
/* ------------------------------------------------------------------ */

export function Card({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("ag-card", className)} {...rest}>
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  description,
  action,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-start justify-between gap-3 border-b border-fog px-5 py-4",
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-body-sm font-semibold text-obsidian">{title}</h2>
        {description ? (
          <p className="mt-0.5 text-caption text-slate">{description}</p>
        ) : null}
      </div>
      {action ? (
        <div className="flex shrink-0 items-center gap-2">{action}</div>
      ) : null}
    </div>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
  className,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0 max-w-2xl">
        {eyebrow ? <p className="ag-eyebrow">{eyebrow}</p> : null}
        <h1 className="ag-display-sm mt-2">{title}</h1>
        {description ? (
          <p className="mt-3 text-body-sm text-slate">{description}</p>
        ) : null}
      </div>
      {action ? (
        <div className="flex shrink-0 items-center gap-2">{action}</div>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Metrics                                                             */
/* ------------------------------------------------------------------ */

export function StatTile({
  label,
  value,
  hint,
  tone = "neutral",
  icon,
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("ag-card p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <p className="ag-eyebrow">{label}</p>
        {icon ? <span className="text-pebble">{icon}</span> : null}
      </div>
      <p
        className={cn(
          "ag-num mt-4 text-heading-sm font-bold leading-none tracking-tight",
          tone === "bad" ? "text-obsidian" : "text-forest-ink",
        )}
      >
        {value}
      </p>
      {hint ? <p className="mt-2 text-caption text-slate">{hint}</p> : null}
    </div>
  );
}

export function Meter({
  value,
  max = 100,
  tone = "good",
  className,
  thickness = 6,
}: {
  value: number;
  max?: number;
  tone?: Tone;
  className?: string;
  thickness?: number;
}) {
  const ratio = max <= 0 ? 0 : Math.min(1, Math.max(0, value / max));
  return (
    <div
      className={cn("w-full overflow-hidden rounded-pill bg-fog", className)}
      style={{ height: thickness }}
      role="meter"
      aria-valuenow={Math.round(value)}
      aria-valuemin={0}
      aria-valuemax={max}
    >
      <div
        className={cn("h-full rounded-pill", TONE_CLASSES[tone].bar)}
        style={{
          width: `${ratio * 100}%`,
          transition: "width 500ms var(--ease-out-quint)",
        }}
      />
    </div>
  );
}

export function ProgressRing({
  value,
  max = 100,
  size = 120,
  thickness = 9,
  tone = "good",
  label,
  sublabel,
}: {
  value: number;
  max?: number;
  size?: number;
  thickness?: number;
  tone?: Tone;
  label?: string;
  sublabel?: string;
}) {
  const ratio = max <= 0 ? 0 : Math.min(1, Math.max(0, value / max));
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
        aria-hidden
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={thickness}
          className="stroke-fog"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={thickness}
          strokeLinecap="round"
          stroke="currentColor"
          className={TONE_CLASSES[tone].text}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - ratio)}
          style={{ transition: "stroke-dashoffset 700ms var(--ease-out-quint)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="ag-num text-body-lg font-bold text-forest-ink">
          {Math.round(value)}
        </span>
        {label ? (
          <span className="text-micro font-medium text-slate">{label}</span>
        ) : null}
        {sublabel ? (
          <span className="mt-0.5 text-micro text-pebble">{sublabel}</span>
        ) : null}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Placeholders                                                        */
/* ------------------------------------------------------------------ */

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("ag-skeleton", className)} aria-hidden />;
}

export function Spinner({
  label = "Loading",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-slate", className)}>
      <Loader2 size={15} className="animate-spin" />
      <span className="text-caption">{label}</span>
    </span>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-card border border-dashed border-fog bg-paper px-6 py-14 text-center">
      {icon ? <span className="text-pebble">{icon}</span> : null}
      <p className="text-body-sm font-semibold text-obsidian">{title}</p>
      {description ? (
        <p className="max-w-md text-caption text-slate">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const apiError = error instanceof ApiError ? error : null;
  const offline = apiError?.isOffline ?? false;

  return (
    <div
      className={cn(
        "rounded-card bg-paper px-6 py-8 shadow-hairline-strong",
        className,
      )}
      role="alert"
    >
      <p className="ag-eyebrow">
        {offline ? "Backend unreachable" : `Error · ${apiError?.code ?? "UNKNOWN"}`}
      </p>
      <p className="mt-3 text-body-sm font-semibold text-obsidian">
        {apiError?.message ?? "Something went wrong while loading this view."}
      </p>
      {offline ? (
        <p className="mt-3 text-caption text-slate">
          The frontend is pointing at{" "}
          <code className="rounded-sm bg-fog px-1.5 py-0.5 font-mono text-micro text-forest-ink">
            {API_BASE_URL}
          </code>
          . Start the backend from the project root with{" "}
          <code className="rounded-sm bg-fog px-1.5 py-0.5 font-mono text-micro text-forest-ink">
            uvicorn app.main:app --port 8077
          </code>
          , or repoint{" "}
          <code className="rounded-sm bg-fog px-1.5 py-0.5 font-mono text-micro text-forest-ink">
            NEXT_PUBLIC_API_BASE_URL
          </code>
          .
        </p>
      ) : null}
      {apiError?.requestId ? (
        <p className="mt-2 font-mono text-micro text-pebble">
          request_id: {apiError.requestId}
        </p>
      ) : null}
      {onRetry ? (
        <Button
          variant="secondary"
          size="sm"
          className="mt-5"
          onClick={onRetry}
          icon={<RefreshCw size={14} />}
        >
          Try again
        </Button>
      ) : null}
    </div>
  );
}