"use client";

import {
  ArrowRight,
  Ban,
  CircleAlert,
  Gauge,
  Layers,
  Repeat2,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

import { AgentGuardMark, Wordmark } from "@/components/shell";
import { Badge, Button } from "@/components/ui";
import { API_BASE_URL } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import {
  DIMENSION_BLURB,
  DIMENSION_LABEL,
  DIMENSION_ORDER,
  formatNumber,
  formatPercent,
  formatScore,
} from "@/lib/format";
import { useResource } from "@/lib/hooks";
import type { Dimension } from "@/lib/api/types";

const DIMENSION_ICON: Record<Dimension, typeof Target> = {
  accuracy: Target,
  hallucination_risk: ScanSearch,
  safety: ShieldCheck,
  instruction_compliance: Ban,
  consistency: Repeat2,
};

const STEPS = [
  {
    n: "01",
    title: "Encode the expectation",
    body: "The prompt, expected answer, referenced facts, keywords, expected numbers and declarative constraints.",
  },
  {
    n: "02",
    title: "Submit agent responses",
    body: "One response reads internal consistency. Several unlock cross-response contradiction detection.",
  },
  {
    n: "03",
    title: "Read a gated verdict",
    body: "Each dimension scores against its own rule and threshold. A critical finding fails the run regardless of score.",
  },
];

const PRINCIPLES = [
  {
    icon: Gauge,
    title: "Deterministic",
    body: "Same input, same score. No randomness, no network calls inside the engine, no per-evaluation cost.",
  },
  {
    icon: Sparkles,
    title: "Named rules",
    body: "Every score points at the rule that produced it, with evidence and a remediation line attached.",
  },
  {
    icon: CircleAlert,
    title: "Honest about limits",
    body: "Heuristic indicators are labelled risk. Only contradictions provable against the grounding source are verified.",
  },
];

export default function LandingPage() {
  const reduceMotion = useReducedMotion();
  const overview = useResource(() => endpoints.overview());
  const meta = useResource(() => endpoints.dimensions());
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const stats = overview.data;
  const live = Boolean(stats) && !overview.error;

  return (
    <div className="flex min-h-full flex-col bg-paper">
      <header
        className={
          "sticky top-0 z-50 border-b bg-paper/90 backdrop-blur-sm transition-colors duration-200 ease-out " +
          (scrolled ? "border-fog" : "border-transparent")
        }
      >
        <div className="mx-auto flex h-16 max-w-[1200px] items-center gap-4 px-4 sm:px-6">
          <Link href="/" aria-label="AgentGuard AI home">
            <Wordmark />
          </Link>
          <nav className="ml-2 hidden items-center gap-0.5 rounded-pill bg-fog p-1 md:flex">
            {[
              ["Dimensions", "#dimensions"],
              ["Principles", "#principles"],
              ["How it works", "#how"],
            ].map(([label, href]) => (
              <a
                key={href}
                href={href}
                className="rounded-pill px-3.5 py-1.5 text-micro font-medium text-charcoal transition-colors duration-150 ease-out hover:bg-paper"
              >
                {label}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="hidden text-caption font-medium text-forest-ink underline decoration-forest-ink/30 underline-offset-4 transition-colors duration-150 ease-out hover:decoration-forest-ink sm:inline"
            >
              API reference
            </a>
            <Link href="/dashboard">
              <Button variant="primary" size="sm">
                Open dashboard
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <section className="mx-auto w-full max-w-[1200px] px-4 pt-14 pb-10 sm:px-6 sm:pt-20">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="max-w-4xl"
        >
          <Badge tone="good" className="mb-6">
            <span className="size-1.5 rounded-full bg-forest-ink" aria-hidden />
            Deterministic engine · live backend
          </Badge>

          <h1 className="ag-display">
            Don&apos;t ship an
            <br />
            agent you
            <br />
            can&apos;t prove.
          </h1>

          <p className="mt-7 max-w-2xl text-body text-slate">
            AgentGuard scores five dimensions of agent quality against criteria you
            write, with a verdict a critical safety failure can never outvote. Local,
            offline, and reproducible run to run.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3">
            <Link href="/dashboard">
              <Button variant="primary" size="lg" iconRight={<ArrowRight size={16} />}>
                Open the dashboard
              </Button>
            </Link>
            <Link href="/evaluations" className="ag-link text-body-sm">
              Run your first evaluation
            </Link>
          </div>
        </motion.div>

        <div className="mt-14 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ["Test cases", live ? formatNumber(stats?.total_test_cases) : "—"],
            ["Evaluation runs", live ? formatNumber(stats?.total_runs) : "—"],
            ["Average score", live ? formatScore(stats?.average_overall_score) : "—"],
            ["Pass rate", live ? formatPercent(stats?.pass_rate, 0) : "—"],
          ].map(([label, value], index) => (
            <motion.div
              key={label}
              initial={reduceMotion ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.42,
                delay: reduceMotion ? 0 : 0.1 + index * 0.06,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="ag-card p-5"
            >
              <p className="ag-eyebrow">{label}</p>
              <p className="ag-num mt-3 text-subheading font-bold leading-none text-forest-ink">
                {value}
              </p>
            </motion.div>
          ))}
        </div>
        <p className="mt-3 text-micro text-pebble">
          {live
            ? "Read live from the local SQLite store via GET /api/v1/analytics/overview."
            : "Backend not reachable — start it with uvicorn app.main:app --port 8077 to populate these figures."}
        </p>
      </section>

      <section id="dimensions" className="border-y border-fog bg-fog/40 py-16 sm:py-20">
        <div className="mx-auto w-full max-w-[1200px] px-4 sm:px-6">
          <p className="ag-eyebrow">Five dimensions</p>
          <h2 className="ag-display-sm mt-3 max-w-2xl">
            Every score names the rule that produced it.
          </h2>

          <ul className="mt-10 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {DIMENSION_ORDER.map((dimension) => {
              const Icon = DIMENSION_ICON[dimension];
              const info = meta.data?.dimensions.find(
                (entry) => entry.dimension === dimension,
              );
              return (
                <li key={dimension} className="ag-card flex flex-col p-5">
                  <div className="flex items-center justify-between gap-3">
                    <Icon size={20} strokeWidth={2} className="text-forest-ink" />
                    {info ? (
                      <span className="ag-num text-micro text-pebble">
                        weight {info.default_weight} · threshold{" "}
                        {info.default_threshold}
                      </span>
                    ) : null}
                  </div>
                  <h3 className="mt-5 text-body-sm font-semibold text-obsidian">
                    {DIMENSION_LABEL[dimension]}
                  </h3>
                  <p className="mt-2 text-caption text-slate">
                    {DIMENSION_BLURB[dimension]}
                  </p>
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      <section
        id="principles"
        className="mx-auto w-full max-w-[1200px] px-4 py-16 sm:px-6 sm:py-20"
      >
        <div className="grid gap-10 lg:grid-cols-3">
          {PRINCIPLES.map((principle) => {
            const Icon = principle.icon;
            return (
              <div key={principle.title}>
                <Icon size={24} strokeWidth={2} className="text-charcoal" />
                <h3 className="mt-6 text-body-sm font-bold text-obsidian">
                  {principle.title}
                </h3>
                <p className="mt-2 text-caption text-pebble">{principle.body}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section id="how" className="mx-auto w-full max-w-[1200px] px-4 pb-16 sm:px-6">
        <p className="ag-eyebrow">How it works</p>
        <div className="mt-8 grid gap-3 lg:grid-cols-3">
          {STEPS.map((step) => (
            <div key={step.n} className="ag-card p-6">
              <span className="ag-num text-body-lg font-bold text-lime-voltage">
                {step.n}
              </span>
              <h3 className="mt-5 text-body-sm font-semibold text-obsidian">
                {step.title}
              </h3>
              <p className="mt-2 text-caption text-slate">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-[1200px] px-4 pb-20 sm:px-6">
        <div className="ag-panel flex flex-col gap-8 p-8 sm:p-12 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-xl">
            <Layers size={22} className="text-lime-voltage" />
            <h2 className="mt-6 text-subheading font-bold text-lime-voltage">
              Suites turn one-off checks into a release gate.
            </h2>
            <p className="mt-4 text-body-sm text-linen-mist/80">
              Group test cases, execute the whole suite, and read a single aggregated
              verdict with failure intelligence attached to every case.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-x-6 gap-y-3">
            <Link href="/test-suites">
              <Button variant="primary" size="lg">
                Manage test suites
              </Button>
            </Link>
            <Link
              href="/analytics"
              className="text-body-sm font-medium text-lime-voltage underline underline-offset-4"
            >
              See analytics
            </Link>
          </div>
        </div>
      </section>

      <footer className="mt-auto border-t border-fog">
        <div className="mx-auto flex max-w-[1200px] flex-col gap-4 px-4 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-3">
            <AgentGuardMark size={26} />
            <p className="text-micro text-pebble">
              AgentGuard AI · v0.2.0 · FastAPI + Next.js
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-5 text-micro text-slate">
            <Link href="/dashboard" className="ag-link">
              Dashboard
            </Link>
            <Link href="/reports" className="ag-link">
              Reports
            </Link>
            <Link href="/settings" className="ag-link">
              Settings
            </Link>
            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="ag-link"
            >
              API docs
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}