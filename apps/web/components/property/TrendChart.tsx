"use client";

import { useMemo } from "react";
import { CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatCompact, formatCurrency, formatMonth } from "@/lib/format";
import type { SaleRecord, TrendPoint } from "@/lib/types";
import { Section } from "./Section";

interface Row {
  month: string;
  t: number; // decimal year, keeps the time axis proportional
  median?: number;
  sale?: number;
}

function decimalYear(ym: string): number {
  const [y, m] = ym.split("-").map(Number);
  return (y ?? 0) + ((m ?? 1) - 1) / 12;
}

/** Merges the suburb median series with this property's sale points (by month). */
export function mergeTrend(trend: TrendPoint[], sales: SaleRecord[] | null): Row[] {
  const rows = new Map<string, Row>(trend.map((p) => [p.month, { month: p.month, t: decimalYear(p.month), median: p.median }]));
  for (const s of sales ?? []) {
    const month = s.contract_date.slice(0, 7);
    const row = rows.get(month) ?? { month, t: decimalYear(month) };
    // One marker per month: the highest sale wins.
    row.sale = Math.max(row.sale ?? 0, s.price);
    rows.set(month, row);
  }
  return [...rows.values()].sort((a, b) => a.month.localeCompare(b.month));
}

const tooltipStyle = {
  backgroundColor: "var(--surface)",
  border: "1px solid var(--line)",
  borderRadius: 8,
  color: "var(--fg)",
};

export function TrendChart({ trend, sales, suburb }: { trend: TrendPoint[]; sales: SaleRecord[] | null; suburb: string }) {
  const data = useMemo(() => mergeTrend(trend, sales), [trend, sales]);
  const ticks = useMemo(() => {
    const first = Math.ceil(data[0]?.t ?? 0);
    const last = Math.floor(data[data.length - 1]?.t ?? 0);
    const step = Math.max(1, Math.ceil((last - first + 1) / 8));
    const out: number[] = [];
    for (let y = first; y <= last; y += step) out.push(y);
    return out;
  }, [data]);
  const summary = `Line chart of the ${suburb} monthly median price from ${formatMonth(data[0]?.month ?? "")} to ${formatMonth(
    data[data.length - 1]?.month ?? "",
  )}, with this property's sales marked.`;

  return (
    <Section title="Price trend" subtitle={`${suburb} median price by month`}>
      <div className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted" aria-hidden="true">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-0.5 w-5 bg-brand" /> Suburb median
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full border-2 border-white bg-rose-500 ring-1 ring-rose-500" /> This property’s sales
        </span>
      </div>
      <div role="img" aria-label={summary} className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="t"
              type="number"
              domain={["dataMin", "dataMax"]}
              ticks={ticks}
              tickFormatter={(v: number) => String(Math.round(v))}
              stroke="var(--muted)"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              tickFormatter={(v: number) => formatCompact(v)}
              width={56}
              domain={["auto", "auto"]}
              stroke="var(--muted)"
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={(_, payload) => formatMonth(String(payload?.[0]?.payload?.month ?? ""))}
              formatter={(value, name) => [formatCurrency(Number(value)), name === "sale" ? "This property" : "Suburb median"]}
            />
            <Line
              type="monotone"
              dataKey="median"
              name="median"
              stroke="var(--brand)"
              strokeWidth={2.5}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
            <Line
              dataKey="sale"
              name="sale"
              stroke="none"
              dot={{ r: 6, fill: "#f43f5e", stroke: "#ffffff", strokeWidth: 2 }}
              activeDot={{ r: 7 }}
              isAnimationActive={false}
              legendType="none"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Section>
  );
}
