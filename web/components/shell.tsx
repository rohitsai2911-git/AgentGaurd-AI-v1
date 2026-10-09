"use client";

import {
  ChevronsUpDown,
  ExternalLink,
  LogOut,
  Settings2,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { Spinner } from "@/components/ui";
import { API_BASE_URL } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { cn, shortId } from "@/lib/format";
import { useResource } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import { PIPELINE_NAV, SECONDARY_NAV } from "@/lib/nav";

/* ------------------------------------------------------------------ */
/* Mark — shield + check, lime on forest ink                           */
/* ------------------------------------------------------------------ */

export function AgentGuardMark({ size = 30 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="AgentGuard AI"
      className="shrink-0"
    >
      <rect width="64" height="64" rx="15" fill="#163300" />
      <path
        d="M32 11 50 18.2v14.4c0 10.3-7.5 17.6-18 21.4-10.5-3.8-18-11.1-18-21.4V18.2Z"
        fill="#9fe870"
      />
      <path
        d="m23.4 32.6 6.2 6.2 11.4-12.6"
        fill="none"
        stroke="#163300"
        strokeWidth="5.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <AgentGuardMark size={30} />
      <span className="flex flex-col leading-none">
        <span className="text-body-sm font-bold tracking-tight text-forest-ink">
          AgentGuard
        </span>
        <span className="mt-0.5 text-micro font-medium tracking-[0.14em] text-pebble uppercase">
          AI
        </span>
      </span>
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Product switcher — the segmented pill switcher                      */
/* ------------------------------------------------------------------ */

function ProductSwitcher() {
  return (
    <nav
      aria-label="Product areas"
      className="hidden items-center gap-0.5 rounded-pill bg-fog p-1 lg:flex"
    >
      {PIPELINE_NAV.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="rounded-pill px-3.5 py-1.5 text-micro font-medium text-charcoal transition-colors duration-150 ease-out hover:bg-paper"
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

export function TopBar() {
  const health = useResource(() => endpoints.health(), [], { pollMs: 30_000 });
  const { user, workspace, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const online = health.data?.database_ok === true && !health.error;
  const offline = Boolean(health.error);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <header className="sticky top-0 z-50 border-b border-fog bg-paper/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-[1560px] items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="shrink-0" aria-label="AgentGuard AI home">
          <Wordmark />
        </Link>

        <ProductSwitcher />

        <div className="ml-auto flex items-center gap-2">
          <a
            href={`${API_BASE_URL}/docs`}
            target="_blank"
            rel="noreferrer"
            className="hidden items-center gap-1.5 rounded-pill px-3 py-1.5 text-micro font-medium text-charcoal transition-colors duration-150 ease-out hover:bg-fog md:inline-flex"
          >
            API reference
            <ExternalLink size={13} strokeWidth={2} />
          </a>

          <div ref={menuRef} className="relative">
            <button
              type="button"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              aria-haspopup="menu"
              className="flex items-center gap-2 rounded-pill py-1 pr-2.5 pl-1 text-left transition-colors duration-150 ease-out hover:bg-fog"
            >
              <span className="flex size-8 items-center justify-center rounded-full bg-forest-ink text-micro font-bold text-lime-voltage">
                {(user?.name ?? user?.email ?? "AG").trim().charAt(0).toUpperCase()}
              </span>
              <span className="hidden leading-tight sm:block">
                <span className="block max-w-[160px] truncate text-micro font-semibold text-forest-ink">
                  {workspace?.name ?? "Workspace"}
                </span>
                <span className="block max-w-[160px] truncate text-micro text-pebble">
                  {user?.email ?? ""}
                </span>
              </span>
              <ChevronsUpDown size={14} className="text-pebble" />
            </button>

            <AnimatePresence>
              {open ? (
                <motion.div
                  role="menu"
                  initial={{ opacity: 0, scale: 0.96, y: -4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98, y: -2 }}
                  transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
                  style={{ transformOrigin: "top right" }}
                  className="absolute right-0 mt-2 w-72 overflow-hidden rounded-card bg-paper shadow-overlay"
                >
                  <div className="border-b border-fog px-4 py-3">
                    <p className="ag-eyebrow">Workspace</p>
                    <p className="mt-1 text-caption font-semibold text-obsidian">
                      {workspace?.name ?? "Workspace"}
                    </p>
                    <p className="mt-0.5 truncate text-micro text-pebble">
                      {user?.email ?? ""}
                    </p>
                  </div>

                  <dl className="grid grid-cols-3 gap-2 px-4 py-3">
                    {[
                      ["Test cases", health.data?.test_cases],
                      ["Runs", health.data?.runs],
                      ["Suites", health.data?.suites],
                    ].map(([label, value]) => (
                      <div key={String(label)}>
                        <dt className="text-micro text-pebble">{label}</dt>
                        <dd className="ag-num text-caption font-semibold text-forest-ink">
                          {typeof value === "number" ? value : "—"}
                        </dd>
                      </div>
                    ))}
                  </dl>

                  <div className="flex items-center justify-between border-t border-fog px-4 py-3">
                    <span className="inline-flex items-center gap-2 text-micro text-slate">
                      <span
                        aria-hidden
                        className={cn(
                          "size-2 rounded-full",
                          offline
                            ? "bg-obsidian"
                            : online
                              ? "bg-lime-voltage"
                              : "bg-pebble",
                        )}
                      />
                      {offline
                        ? "Backend offline"
                        : online
                          ? "Backend connected"
                          : "Checking…"}
                    </span>
                    <span className="font-mono text-micro text-pebble">
                      {health.data?.stage
                        ? `stage ${health.data.stage}`
                        : shortId(null)}
                    </span>
                  </div>

                  <Link
                    href="/settings"
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-2 border-t border-fog px-4 py-3 text-caption font-medium text-forest-ink transition-colors duration-150 ease-out hover:bg-fog"
                  >
                    <Settings2 size={14} />
                    Workspace settings
                  </Link>
                  <button
                    type="button"
                    onClick={() => {
                      setOpen(false);
                      logout();
                      router.push("/login");
                    }}
                    className="flex w-full items-center gap-2 border-t border-fog px-4 py-3 text-left text-caption font-medium text-forest-ink transition-colors duration-150 ease-out hover:bg-fog"
                  >
                    <LogOut size={14} />
                    Log out
                  </button>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </header>
  );
}

/* ------------------------------------------------------------------ */
/* Sidebar — quiet rail on desktop, horizontal pills on mobile          */
/* ------------------------------------------------------------------ */

function SideNav() {
  const pathname = usePathname();

  const items = [...PIPELINE_NAV, ...SECONDARY_NAV];

  const renderLink = (item: (typeof items)[number], compact: boolean) => {
    const active =
      pathname === item.href || pathname.startsWith(`${item.href}/`);
    const Icon = item.icon;
    return (
      <Link
        key={item.href}
        href={item.href}
        aria-current={active ? "page" : undefined}
        title={item.description}
        className={cn(
          "group flex items-center gap-2.5 rounded-pill font-medium",
          "transition-[background-color,color] duration-150 ease-out",
          compact ? "shrink-0 px-3.5 py-2" : "px-3.5 py-2.5",
          active
            ? "bg-lime-voltage text-forest-ink"
            : "text-charcoal hover:bg-forest-ink hover:text-lime-voltage",
        )}
      >
        <Icon
          size={compact ? 15 : 16}
          strokeWidth={2}
          className={active ? "text-forest-ink" : "text-pebble group-hover:text-lime-voltage"}
        />
        <span className="text-caption whitespace-nowrap">{item.label}</span>
      </Link>
    );
  };

  return (
    <>
      {/* Mobile: single scrollable pill row */}
      <nav
        aria-label="Sections"
        className="ag-scroll -mx-1 flex items-center gap-1.5 overflow-x-auto px-1 pb-1 lg:hidden"
      >
        {items.map((item) => renderLink(item, true))}
      </nav>

      {/* Desktop: vertical rail */}
      <nav
        aria-label="Sections"
        className="sticky top-24 hidden w-60 shrink-0 flex-col gap-1 lg:flex"
      >
        <p className="ag-eyebrow px-3.5 pb-2">Pipeline</p>
        {PIPELINE_NAV.map((item) => renderLink(item, false))}
        <div className="my-3 h-px bg-fog" />
        {SECONDARY_NAV.map((item) => renderLink(item, false))}

        <div className="mt-6 rounded-card bg-fog p-4">
          <p className="ag-eyebrow">Honesty contract</p>
          <p className="mt-2 text-micro leading-relaxed text-slate">
            Findings are <span className="font-semibold text-forest-ink">verified</span>{" "}
            only when provable against the test case grounding source. Everything else
            is a <span className="font-semibold text-forest-ink">risk</span> indicator
            for human review. Absence of findings is not proof of correctness.
          </p>
        </div>
      </nav>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* App shell                                                           */
/* ------------------------------------------------------------------ */

export function AppShell({
  children,
  title,
  description,
  actions,
  eyebrow,
}: {
  children: React.ReactNode;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  eyebrow?: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, ready } = useAuth();
  const health = useResource(() => endpoints.health(), [], { pollMs: 30_000 });

  // Every app page lives behind auth. No token -> back to the login screen.
  useEffect(() => {
    if (ready && !isAuthenticated) router.replace("/login");
  }, [ready, isAuthenticated, router]);

  if (!ready || !isAuthenticated) {
    return (
      <div className="flex min-h-full flex-1 items-center justify-center bg-paper">
        <Spinner label="Loading workspace…" />
      </div>
    );
  }

  return (
    <div className="flex min-h-full flex-col bg-paper">
      <TopBar />
      <div className="mx-auto flex w-full max-w-[1560px] flex-1 gap-8 px-4 py-6 sm:px-6 lg:py-8">
        <SideNav />
        <main className="min-w-0 flex-1">
          <motion.div
            key={pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="flex flex-col gap-4 border-b border-fog pb-6 sm:flex-row sm:items-end sm:justify-between">
              <div className="min-w-0 max-w-3xl">
                <p className="ag-eyebrow">
                  {eyebrow ?? "AgentGuard AI"}
                  {health.data?.database_ok ? (
                    <span className="ml-2 font-mono tracking-normal normal-case">
                      · db ok
                    </span>
                  ) : null}
                </p>
                <h1 className="ag-display-sm mt-2">{title}</h1>
                {description ? (
                  <p className="mt-3 text-body-sm text-slate">{description}</p>
                ) : null}
              </div>
              {actions ? (
                <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
              ) : null}
            </div>
            <div className="pt-6 pb-16">{children}</div>
          </motion.div>
        </main>
      </div>
    </div>
  );
}