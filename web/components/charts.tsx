"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type {
  DimensionAggregate,
  FailureCategoryAggregate,
  TrendPoint,
} from "@/lib/api/types";
import { SEVERITY_LABEL, SEVERITY_ORDER, categoryLabel } from "@/lib/format";
import { useHydrated } from "@/lib/hooks";

/* Palette — flat fills only, never gradients */
const INK = "#163300";
const LIME = "#9fe870";
const OBSIDIAN = "#0e0f0c";
const PEBBLE = "#868685";
const SLATE = "#6a6c6a";
const FOG = "#e8ebe6";

const AXIS_TICK = { fill: PEBBLE, fontSize: 12 };
const GRID = { stroke: FOG, strokeDasharray: "0" };

/** "2026-10-02" -> "Oct 02"; "2026-10-02T13" -> "13:00" */
function bucketLabel(bucket: string): string {
  if (bucket.includes("T")) {
    return `${bucket.split("T")[1].padStart(2, "0")}:00`;
  }
  const date = new Date(`${bucket}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return bucket;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "2-digit",
    timeZone: "UTC",
  });
}

interface TooltipRow {
  label: string;
  value: string;
  color: string;
}

function FlatTooltip({ title, rows }: { title: string; rows: TooltipRow[] }) {
  return (
    <div className="rounded-card bg-paper px-3 py-2 shadow-hairline-strong">
      <p className="text-micro font-semibold text-obsidian">{title}</p>
      <ul className="mt-1.5 space-y-0.5">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center gap-2 text-micro">
            <span
              aria-hidden
              className="size-2 shrink-0 rounded-full"
              style={{ background: row.color }}
            />
            <span className="text-slate">{row.label}</span>
            <span className="ag-num ml-auto font-semibold text-obsidian">
              {row.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Recharts measures the DOM, so charts mount only after hydration. */
function ChartFrame({
  height,
  children,
}: {
  height: number;
  children: React.ReactNode;
}) {
  const hydrated = useHydrated();
  if (!hydrated) {
    return <div className="ag-skeleton w-full" style={{ height }} aria-hidden />;
  }
  return (
    <div style={{ height }} className="w-full">
      {children}
    </div>
  );
}

export function TrendChart({
  points,
  height = 260,
}: {
  points: TrendPoint[];
  height?: number;
}) {
  const data = points.map((point) => ({
    ...point,
    label: bucketLabel(point.bucket),
    passRatePct: Number((point.pass_rate * 100).toFixed(1)),
  }));

  return (
    <ChartFrame height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid {...GRID} vertical={false} />
          <XAxis
            dataKey="label"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: FOG }}
            minTickGap={16}
          />
          <YAxis
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
            width={44}
          />
          <Tooltip
            cursor={{ stroke: PEBBLE, strokeDasharray: "3 3" }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const point = payload[0].payload as (typeof data)[number];
              return (
                <FlatTooltip
                  title={String(label)}
                  rows={[
                    {
                      label: "Average score",
                      value: `${point.average_score}`,
                      color: INK,
                    },
                    { label: "Pass rate", value: `${point.passRatePct}%`, color: LIME },
                    {
                      label: "Runs",
                      value: `${point.total} (${point.failed} failed)`,
                      color: OBSIDIAN,
                    },
                  ]}
                />
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="average_score"
            stroke={INK}
            strokeWidth={2}
            fill={INK}
            fillOpacity={0.07}
            activeDot={{ r: 4, fill: INK, stroke: "#ffffff", strokeWidth: 2 }}
          />
          <Line
            type="monotone"
            dataKey="passRatePct"
            stroke={LIME}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: LIME, stroke: INK, strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

export function PassFailChart({
  points,
  height = 220,
}: {
  points: TrendPoint[];
  height?: number;
}) {
  const data = points.map((point) => ({
    label: bucketLabel(point.bucket),
    passed: point.passed,
    failed: point.failed,
  }));

  return (
    <ChartFrame height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -22 }}>
          <CartesianGrid {...GRID} vertical={false} />
          <XAxis
            dataKey="label"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: FOG }}
            minTickGap={16}
          />
          <YAxis
            allowDecimals={false}
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip
            cursor={{ fill: FOG, fillOpacity: 0.5 }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const point = payload[0].payload as (typeof data)[number];
              return (
                <FlatTooltip
                  title={String(label)}
                  rows={[
                    { label: "Passed", value: `${point.passed}`, color: LIME },
                    { label: "Failed", value: `${point.failed}`, color: OBSIDIAN },
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="passed" stackId="runs" fill={LIME} />
          <Bar dataKey="failed" stackId="runs" fill={OBSIDIAN} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

export function DimensionChart({
  data,
  height = 280,
}: {
  data: DimensionAggregate[];
  height?: number;
}) {
  const rows = data.map((row) => ({
    ...row,
    label: row.dimension.replace(/_/g, " "),
  }));

  return (
    <ChartFrame height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 0, left: 8 }}
        >
          <CartesianGrid {...GRID} horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: FOG }}
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ ...AXIS_TICK, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={112}
          />
          <Tooltip
            cursor={{ fill: FOG, fillOpacity: 0.5 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload as (typeof rows)[number];
              return (
                <FlatTooltip
                  title={row.dimension.replace(/_/g, " ")}
                  rows={[
                    {
                      label: "Average score",
                      value: row.average_score.toFixed(1),
                      color: INK,
                    },
                    {
                      label: "Pass rate",
                      value: `${(row.pass_rate * 100).toFixed(1)}%`,
                      color: LIME,
                    },
                    {
                      label: "Failures",
                      value: `${row.failure_count}`,
                      color: OBSIDIAN,
                    },
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="average_score" fill={INK} radius={[0, 3, 3, 0]} barSize={16} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

export function CategoryChart({
  data,
  height = 260,
}: {
  data: FailureCategoryAggregate[];
  height?: number;
}) {
  const rows = data.map((row) => ({
    ...row,
    label: categoryLabel(row.category),
  }));

  return (
    <ChartFrame height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 0, left: 8 }}
        >
          <CartesianGrid {...GRID} horizontal={false} />
          <XAxis
            type="number"
            allowDecimals={false}
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: FOG }}
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ ...AXIS_TICK, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={148}
          />
          <Tooltip
            cursor={{ fill: FOG, fillOpacity: 0.5 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload as (typeof rows)[number];
              return (
                <FlatTooltip
                  title={categoryLabel(row.category)}
                  rows={[
                    { label: "Findings", value: `${row.count}`, color: OBSIDIAN },
                    {
                      label: "Share",
                      value: `${row.percentage.toFixed(1)}%`,
                      color: SLATE,
                    },
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="count" fill={OBSIDIAN} radius={[0, 3, 3, 0]} barSize={16} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

export function SeverityChart({
  counts,
  height = 220,
}: {
  counts: Record<string, number>;
  height?: number;
}) {
  const rows = SEVERITY_ORDER.map((severity) => ({
    label: SEVERITY_LABEL[severity],
    value: counts[severity] ?? 0,
  }));

  return (
    <ChartFrame height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -22 }}>
          <CartesianGrid {...GRID} vertical={false} />
          <XAxis
            dataKey="label"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: FOG }}
          />
          <YAxis
            allowDecimals={false}
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip
            cursor={{ fill: FOG, fillOpacity: 0.5 }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <FlatTooltip
                  title={String(label)}
                  rows={[
                    {
                      label: "Findings",
                      value: `${payload[0].value as number}`,
                      color: INK,
                    },
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="value" radius={[3, 3, 0, 0]} barSize={34}>
            {rows.map((row) => (
              <Cell
                key={row.label}
                fill={
                  row.label === "Critical" || row.label === "High" ? OBSIDIAN : LIME
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

export function ScoreSparkline({
  values,
  height = 48,
}: {
  values: number[];
  height?: number;
}) {
  const data = values.map((value, index) => ({ index, value }));

  return (
    <ChartFrame height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
          <YAxis domain={[0, 100]} hide />
          <Line
            type="monotone"
            dataKey="value"
            stroke={INK}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}