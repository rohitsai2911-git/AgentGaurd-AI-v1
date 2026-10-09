import Link from "next/link";
import type { Metadata } from "next";

import { AgentGuardMark } from "@/components/shell";
import { Button } from "@/components/ui";
import { PIPELINE_NAV } from "@/lib/nav";

export const metadata: Metadata = {
  title: "Page not found",
};

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1200px] flex-col justify-center px-4 py-16 sm:px-6">
      <div className="flex items-center gap-3">
        <AgentGuardMark size={34} />
        <p className="ag-eyebrow">Error 404</p>
      </div>

      <h1 className="ag-display mt-8">
        No route
        <br />
        here.
      </h1>

      <p className="mt-6 max-w-xl text-body-sm text-slate">
        That path does not exist in this workspace. Everything AgentGuard renders comes
        from one of five areas below.
      </p>

      <ul className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {PIPELINE_NAV.map((item) => {
          const Icon = item.icon;
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className="group flex h-full flex-col gap-2 rounded-card bg-paper p-5 shadow-hairline transition-[box-shadow,transform] duration-200 ease-out hover:shadow-hairline-strong active:scale-[0.99]"
              >
                <Icon size={18} strokeWidth={2} className="text-forest-ink" />
                <span className="text-body-sm font-semibold text-obsidian">
                  {item.label}
                </span>
                <span className="text-caption text-slate">{item.description}</span>
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3">
        <Link href="/">
          <Button variant="primary">Back to the landing page</Button>
        </Link>
        <Link href="/dashboard" className="ag-link text-body-sm">
          Go to the dashboard
        </Link>
      </div>
    </main>
  );
}