import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { ToastProvider } from "@/components/toast";
import { APP_NAME } from "@/lib/api/client";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: `${APP_NAME} · Deterministic agent quality testing`,
    template: `%s · ${APP_NAME}`,
  },
  description:
    "Deterministic quality and reliability testing for AI agents. Five evaluation dimensions — accuracy, hallucination risk, safety, instruction compliance, consistency. Every score names the rule that produced it.",
  applicationName: APP_NAME,
  keywords: [
    "AI agent evaluation",
    "hallucination detection",
    "LLM quality assurance",
    "agent reliability",
    "deterministic evaluation",
  ],
  openGraph: {
    title: `${APP_NAME} · Deterministic agent quality testing`,
    description:
      "Five evaluation dimensions. Severity-gated verdicts. A report that separates provable findings from heuristic risk.",
    siteName: APP_NAME,
    type: "website",
  },
  twitter: {
    card: "summary",
    title: `${APP_NAME} · Deterministic agent quality testing`,
    description:
      "Five evaluation dimensions. Severity-gated verdicts. Provable findings separated from heuristic risk.",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#163300",
  colorScheme: "light",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-paper">
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
