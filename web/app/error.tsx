"use client";

import Link from "next/link";
import { useEffect } from "react";

import { AgentGuardMark } from "@/components/shell";
import { Button } from "@/components/ui";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surfaces in the browser console and in the Next.js server log.
    console.error("[AgentGuard] route error:", error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-[70vh] w-full max-w-[1200px] flex-col justify-center px-4 py-16 sm:px-6">
      <div className="flex items-center gap-3">
        <AgentGuardMark size={34} />
        <p className="ag-eyebrow">Runtime error</p>
      </div>

      <h1 className="ag-display-sm mt-8 max-w-2xl">
        This view failed to render.
      </h1>

      <p className="mt-5 max-w-xl text-body-sm text-slate">
        The error was caught by the route boundary, so the rest of the application is
        still usable. Retrying re-mounts the segment and refetches its data.
      </p>

      <pre className="ag-scroll mt-8 max-w-3xl overflow-x-auto rounded-card bg-fog px-4 py-3 font-mono text-micro whitespace-pre-wrap text-charcoal">
        {error.message || "Unknown error"}
        {error.digest ? `\n\ndigest: ${error.digest}` : ""}
      </pre>

      <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
        <Button variant="primary" onClick={reset}>
          Try again
        </Button>
        <Link href="/dashboard" className="ag-link text-body-sm">
          Back to the dashboard
        </Link>
      </div>
    </main>
  );
}