import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  FileJson,
  FlaskConical,
  LayoutDashboard,
  Layers,
  Settings2,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  description: string;
}

/** The five-step pipeline: cases live inside suites, results inside reports. */
export const PIPELINE_NAV: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    description: "Quality score, pass rate, critical failures and recent activity",
  },
  {
    href: "/test-suites",
    label: "Test suites",
    icon: Layers,
    description: "Group test cases, manage criteria and execute runs",
  },
  {
    href: "/evaluations",
    label: "Evaluations",
    icon: FlaskConical,
    description: "Run an evaluation and inspect all five dimensions",
  },
  {
    href: "/analytics",
    label: "Analytics",
    icon: BarChart3,
    description: "Trends, failure distribution and run-to-run comparison",
  },
  {
    href: "/reports",
    label: "Reports",
    icon: FileJson,
    description: "Stored runs, execution history and JSON exports",
  },
];

export const SECONDARY_NAV: NavItem[] = [
  {
    href: "/settings",
    label: "Settings",
    icon: Settings2,
    description: "Thresholds, evaluation preferences and workspace configuration",
  },
];

export const ALL_NAV: NavItem[] = [...PIPELINE_NAV, ...SECONDARY_NAV];

export function navItemFor(pathname: string): NavItem | undefined {
  return ALL_NAV.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
  );
}