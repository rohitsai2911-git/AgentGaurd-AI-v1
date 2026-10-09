"use client";

import { AgentGuardMark } from "@/components/shell";

/**
 * Last-resort boundary: rendered when the root layout itself fails, so it
 * must carry its own <html> and <body> and cannot rely on any provider.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#ffffff",
          color: "#454745",
          fontFamily:
            "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
          padding: "24px",
        }}
      >
        <main style={{ maxWidth: 560 }}>
          <AgentGuardMark size={34} />
          <h1
            style={{
              margin: "28px 0 0",
              fontSize: 40,
              lineHeight: 0.95,
              letterSpacing: "-0.024em",
              fontWeight: 900,
              color: "#163300",
            }}
          >
            AgentGuard hit a fatal error.
          </h1>
          <p style={{ marginTop: 16, fontSize: 16, lineHeight: 1.5 }}>
            The application shell could not load. Restarting the dev server or the
            backend usually clears this.
          </p>
          <pre
            style={{
              marginTop: 24,
              padding: "12px 16px",
              background: "#e8ebe6",
              borderRadius: 10,
              fontSize: 12,
              overflowX: "auto",
              whiteSpace: "pre-wrap",
            }}
          >
            {error.message || "Unknown error"}
            {error.digest ? `\n\ndigest: ${error.digest}` : ""}
          </pre>
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: 24,
              height: 44,
              padding: "0 24px",
              border: "none",
              borderRadius: 9999,
              background: "#9fe870",
              color: "#163300",
              fontWeight: 500,
              fontSize: 16,
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}