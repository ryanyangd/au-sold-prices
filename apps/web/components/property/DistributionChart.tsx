"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatCompact, formatCurrency } from "@/lib/format";
import type { DistributionBucket } from "@/lib/types";
import { Section } from "./Section";

export function DistributionChart({
  buckets,
  highlightPrice,
  suburb,
}: {
  buckets: DistributionBucket[];
  highlightPrice: number;
  suburb: string;
}) {
  const data = buckets.map((b) => ({
    label: `${formatCompact(b.bucket_from)}–${formatCompact(b.bucket_to)}`,
    from: b.bucket_from,
    count: b.count,
    mine: highlightPrice >= b.bucket_from && highlightPrice < b.bucket_to,
  }));

  return (
    <Section title="Price distribution" subtitle={`${suburb} sales in the last 12 months. Highlighted bar contains this property’s last sale.`}>
      <div role="img" aria-label={`Histogram of ${suburb} sale prices over the last 12 months`} className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="from"
              tickFormatter={(v: number) => formatCompact(v)}
              interval="preserveStartEnd"
              minTickGap={24}
              stroke="var(--muted)"
              tick={{ fontSize: 12 }}
            />
            <YAxis allowDecimals={false} width={36} stroke="var(--muted)" tick={{ fontSize: 12 }} />
            <Tooltip
              cursor={{ fill: "var(--surface-2)" }}
              contentStyle={{
                backgroundColor: "var(--surface)",
                border: "1px solid var(--line)",
                borderRadius: 8,
                color: "var(--fg)",
              }}
              labelFormatter={(_, payload) => String(payload?.[0]?.payload?.label ?? "")}
              formatter={(value) => [`${value} sales`, "Count"]}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.from} fill={d.mine ? "#f43f5e" : "var(--brand)"} fillOpacity={d.mine ? 1 : 0.65} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="sr-only">Property last sold for {formatCurrency(highlightPrice)}.</p>
    </Section>
  );
}
