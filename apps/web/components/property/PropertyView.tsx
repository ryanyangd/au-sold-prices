"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { ApiError, getProperty } from "@/lib/api";
import { useAuth } from "@/lib/auth/context";
import type { PropertyResponse, SectionKey } from "@/lib/types";
import { btnPrimary, btnSecondary, card } from "@/lib/ui";
import { AddressSearch } from "../AddressSearch";
import { ComparablesTable } from "./ComparablesTable";
import { DistributionChart } from "./DistributionChart";
import { MetricCards, PropertyHeader } from "./PropertyHeader";
import { PropertySkeleton } from "./PropertySkeleton";
import { SalesHistory, SuburbSnapshotCard } from "./SalesAndSuburb";
import { EmptySection, LockedSection, type PlaceholderKind } from "./Section";
import { TrendChart } from "./TrendChart";

interface Loaded {
  key: string;
  data?: PropertyResponse;
  error?: ApiError;
}

const LOCK_COPY: Record<SectionKey, { title: string; description: string; kind: PlaceholderKind }> = {
  sales_history: {
    title: "Sale history",
    description: "See every past sale, price change and holding period with Pro.",
    kind: "table",
  },
  trend: {
    title: "Price trend",
    description: "Track the suburb median over time with this property’s sales overlaid.",
    kind: "chart",
  },
  distribution: {
    title: "Price distribution",
    description: "See where this property sits among recent suburb sales.",
    kind: "bars",
  },
  comparables: {
    title: "Comparable sales",
    description: "Compare against similar recent sales nearby.",
    kind: "table",
  },
};

function Locked({ k }: { k: SectionKey }) {
  const c = LOCK_COPY[k];
  return <LockedSection title={c.title} description={c.description} kind={c.kind} />;
}

export function PropertyView({ id }: { id: string }) {
  const { token, loading: authLoading } = useAuth();
  const [retry, setRetry] = useState(0);
  const [state, setState] = useState<Loaded | null>(null);
  const key = `${id}|${token ?? ""}|${retry}`;

  useEffect(() => {
    if (authLoading) return;
    const ctrl = new AbortController();
    (async () => {
      try {
        let data: PropertyResponse;
        try {
          data = await getProperty(id, { token, signal: ctrl.signal });
        } catch (e) {
          // Expired/invalid token: fall back to the anonymous (free) view.
          if (token && e instanceof ApiError && e.status === 401) {
            data = await getProperty(id, { signal: ctrl.signal });
          } else {
            throw e;
          }
        }
        if (!ctrl.signal.aborted) setState({ key, data });
      } catch (e) {
        if (ctrl.signal.aborted) return;
        setState({ key, error: e instanceof ApiError ? e : new ApiError(0, "Something went wrong.") });
      }
    })();
    return () => ctrl.abort();
  }, [id, token, authLoading, key]);

  const current = state && state.key === key ? state : null;

  if (authLoading || !current) return <PropertySkeleton />;

  if (current.error) {
    if (current.error.status === 404) {
      return (
        <div className={`${card} mx-auto max-w-xl p-8 text-center`}>
          <h1 className="text-2xl font-bold">Property not found</h1>
          <p className="mt-2 text-muted">We couldn’t find a property with that ID. Try searching by address.</p>
          <div className="mt-6 text-left">
            <AddressSearch />
          </div>
          <Link href="/" className={`${btnSecondary} mt-6`}>
            Back to home
          </Link>
        </div>
      );
    }
    return (
      <div role="alert" className={`${card} mx-auto max-w-xl p-8 text-center`}>
        <h1 className="text-2xl font-bold">Couldn’t load this property</h1>
        <p className="mt-2 text-muted">{current.error.message}</p>
        <button type="button" className={`${btnPrimary} mt-6`} onClick={() => setRetry((r) => r + 1)}>
          Try again
        </button>
      </div>
    );
  }

  const d = current.data!;
  const locked = new Set(d.access.locked_sections);

  function sectionOrEmpty<T>(k: SectionKey, value: T[] | null, render: (v: T[]) => ReactNode) {
    if (locked.has(k)) return <Locked k={k} />;
    if (!value || value.length === 0) {
      return <EmptySection title={LOCK_COPY[k].title} message="Not enough data available for this section." />;
    }
    return render(value);
  }

  return (
    <div className="space-y-6">
      <PropertyHeader property={d.property} dataAsOf={d.data_as_of} />
      <MetricCards metrics={d.metrics} median={d.suburb.median_12m} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {sectionOrEmpty("sales_history", d.sales, (v) => (
            <SalesHistory sales={v} />
          ))}
        </div>
        <SuburbSnapshotCard suburb={d.suburb} />
      </div>

      {sectionOrEmpty("trend", d.trend, (v) => (
        <TrendChart trend={v} sales={d.sales} suburb={d.suburb.name} />
      ))}
      {sectionOrEmpty("distribution", d.distribution, (v) => (
        <DistributionChart buckets={v} highlightPrice={d.metrics.last_sale_price} suburb={d.suburb.name} />
      ))}
      {sectionOrEmpty("comparables", d.comparables, (v) => (
        <ComparablesTable rows={v} />
      ))}
    </div>
  );
}
