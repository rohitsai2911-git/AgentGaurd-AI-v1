"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";

import { Field, TextInput } from "@/components/fields";
import { AgentGuardMark, Wordmark } from "@/components/shell";
import { useToast } from "@/components/toast";
import { Button } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { endpoints } from "@/lib/api/endpoints";
import { toApiError } from "@/lib/hooks";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const toast = useToast();
  const { login } = useAuth();
  const reduceMotion = useReducedMotion();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const result =
        mode === "login"
          ? await endpoints.login({ email, password })
          : await endpoints.register({
              email,
              password,
              name,
              workspace_name: workspaceName,
            });
      login(result.access_token, result.user, result.workspace);
      toast.push(
        `Signed in to ${result.workspace.name}.`,
        "success",
        `Welcome, ${result.user.name || result.user.email}`,
      );
      router.push("/dashboard");
    } catch (caught) {
      setError(toApiError(caught).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="grid min-h-full flex-1 lg:grid-cols-2">
      <div className="ag-panel hidden flex-col justify-between p-12 lg:flex">
        <Link href="/" className="inline-flex">
          <span className="flex items-center gap-3">
            <AgentGuardMark size={34} />
            <span className="text-body-sm font-bold text-lime-voltage">
              AgentGuard AI
            </span>
          </span>
        </Link>
        <div>
          <h1 className="text-heading-sm font-bold text-lime-voltage">
            Prove your agent before you ship it.
          </h1>
          <p className="mt-5 max-w-md text-body-sm text-linen-mist/80">
            Deterministic quality testing across five dimensions. Every score names
            the rule that produced it — and your workspace keeps it all private.
          </p>
        </div>
        <p className="text-micro text-linen-mist/50">
          Accuracy · Hallucination risk · Safety · Compliance · Consistency
        </p>
      </div>

      <div className="flex flex-col justify-center px-6 py-12 sm:px-12">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="mx-auto w-full max-w-sm"
        >
          <div className="lg:hidden">
            <Wordmark />
          </div>

          <div
            role="tablist"
            aria-label="Auth mode"
            className="mt-6 inline-flex rounded-pill bg-fog p-1"
          >
            {(["login", "register"] as Mode[]).map((value) => (
              <button
                key={value}
                role="tab"
                type="button"
                aria-selected={mode === value}
                onClick={() => {
                  setMode(value);
                  setError(null);
                }}
                className={
                  "rounded-pill px-4 py-1.5 text-caption font-medium transition-colors duration-150 ease-out " +
                  (mode === value
                    ? "bg-lime-voltage text-forest-ink"
                    : "text-charcoal hover:bg-paper")
                }
              >
                {value === "login" ? "Log in" : "Sign up"}
              </button>
            ))}
          </div>

          <h2 className="ag-display-sm mt-6">
            {mode === "login" ? "Welcome back." : "Create your workspace."}
          </h2>
          <p className="mt-2 text-caption text-slate">
            {mode === "login"
              ? "Log in to your AgentGuard workspace."
              : "One workspace per account. Your test cases and runs stay private."}
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            {mode === "register" ? (
              <>
                <Field label="Your name">
                  <TextInput
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Rohit"
                    autoComplete="name"
                  />
                </Field>
                <Field label="Workspace name">
                  <TextInput
                    value={workspaceName}
                    onChange={(event) => setWorkspaceName(event.target.value)}
                    placeholder="Acme Support"
                  />
                </Field>
              </>
            ) : null}

            <Field label="Email">
              <TextInput
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
                autoComplete="email"
              />
            </Field>

            <Field
              label="Password"
              hint={mode === "register" ? "At least 8 characters." : undefined}
            >
              <TextInput
                type="password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
              />
            </Field>

            {error ? (
              <p className="rounded-card bg-fog px-3 py-2 text-caption text-charcoal">
                {error}
              </p>
            ) : null}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              loading={pending}
              iconRight={<ArrowRight size={16} />}
            >
              {mode === "login" ? "Log in" : "Create workspace"}
            </Button>
          </form>

          {mode === "login" ? (
            <div className="mt-6 rounded-card bg-fog/60 px-3 py-2.5">
              <p className="text-micro text-slate">
                Demo account (auto-seeded):{" "}
                <code className="font-mono text-forest-ink">
                  demo@agentguard.local
                </code>{" "}
                / <code className="font-mono text-forest-ink">demo1234</code>
              </p>
            </div>
          ) : null}
        </motion.div>
      </div>
    </div>
  );
}