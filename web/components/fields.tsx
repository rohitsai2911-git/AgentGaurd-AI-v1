"use client";

import {
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  forwardRef,
} from "react";

import { cn } from "@/lib/format";

const CONTROL =
  "w-full rounded-card bg-paper text-charcoal shadow-hairline outline-none " +
  "transition-shadow duration-150 ease-out placeholder:text-pebble " +
  "focus:shadow-hairline-strong disabled:opacity-50";

export function Field({
  label,
  hint,
  error,
  children,
  className,
  htmlFor,
}: {
  label: string;
  hint?: ReactNode;
  error?: string;
  children: ReactNode;
  className?: string;
  htmlFor?: string;
}) {
  return (
    <div className={cn("min-w-0", className)}>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 block text-micro font-semibold text-slate"
      >
        {label}
      </label>
      {children}
      {error ? (
        <p className="mt-1 text-micro text-obsidian">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-micro text-pebble">{hint}</p>
      ) : null}
    </div>
  );
}

export const TextInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function TextInput({ className, ...rest }, ref) {
    return (
      <input
        ref={ref}
        className={cn(CONTROL, "h-11 px-3 text-body-sm", className)}
        {...rest}
      />
    );
  },
);

export const TextArea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function TextArea({ className, rows = 4, ...rest }, ref) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={cn(
        CONTROL,
        "ag-scroll resize-y px-3 py-2.5 text-caption",
        className,
      )}
      {...rest}
    />
  );
});

export const SelectInput = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(function SelectInput({ className, children, ...rest }, ref) {
  return (
    <select
      ref={ref}
      className={cn(CONTROL, "h-11 px-3 text-body-sm", className)}
      {...rest}
    >
      {children}
    </select>
  );
});

export function Checkbox({
  label,
  checked,
  onChange,
  hint,
  disabled,
}: {
  label: ReactNode;
  checked: boolean;
  onChange: (next: boolean) => void;
  hint?: ReactNode;
  disabled?: boolean;
}) {
  return (
    <label
      className={cn(
        "flex items-start gap-2.5 text-caption text-charcoal",
        disabled && "opacity-50",
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 size-4 shrink-0 accent-[#163300]"
      />
      <span className="min-w-0">
        <span className="block">{label}</span>
        {hint ? (
          <span className="mt-0.5 block text-micro text-pebble">{hint}</span>
        ) : null}
      </span>
    </label>
  );
}

export function FormGrid({
  children,
  columns = 2,
}: {
  children: ReactNode;
  columns?: 1 | 2 | 3;
}) {
  return (
    <div
      className={cn(
        "grid gap-4",
        columns === 1
          ? "grid-cols-1"
          : columns === 2
            ? "grid-cols-1 sm:grid-cols-2"
            : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
      )}
    >
      {children}
    </div>
  );
}

export function FormSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4 border-t border-fog pt-5 first:border-t-0 first:pt-0">
      <div>
        <h3 className="text-caption font-semibold text-obsidian">{title}</h3>
        {description ? (
          <p className="mt-0.5 text-micro text-pebble">{description}</p>
        ) : null}
      </div>
      {children}
    </section>
  );
}