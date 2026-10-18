"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createCheckout } from "@/lib/api";
import { useAuth, setReturnTo } from "@/lib/auth/context";
import { ANNUAL_PER_MONTH, ANNUAL_SAVING, PRICING, PRICING_PLAN_IDS } from "@/lib/config";
import { btnPrimary, btnSecondary, card } from "@/lib/ui";

type Interval = "monthly" | "annual";

const FREE_FEATURES = [
  "Address search across NSW",
  "Last sale price and date",
  "Key growth and holding metrics",
  "Suburb median and recent change",
];
const PRO_FEATURES = [
  "Everything in Free",
  "Full sale history for every property",
  "Suburb price trend charts",
  "Price distribution histograms",
  "Comparable sales tables",
];

function Check() {
  return (
    <svg className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600 dark:text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <path d="M5 13l4 4L19 7" />
    </svg>
  );
}

export function PricingTable() {
  const { user, token, loading, getToken } = useAuth();
  const router = useRouter();
  const [period, setPeriod] = useState<Interval>("annual");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const price = period === "monthly" ? PRICING.proMonthly : PRICING.proAnnual;

  async function upgrade() {
    setError(null);
    if (!user) {
      setReturnTo("/pricing");
      router.push("/login?next=/pricing");
      return;
    }
    setBusy(true);
    try {
      const fresh = (await getToken()) ?? token;
      if (!fresh) throw new Error("Please sign in again.");
      const { url } = await createCheckout(PRICING_PLAN_IDS[period], fresh);
      window.location.assign(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn’t start checkout.");
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="flex justify-center">
        <div role="group" aria-label="Billing interval" className="inline-flex rounded-xl border border-line bg-surface p-1">
          {(["monthly", "annual"] as const).map((i) => (
            <button
              key={i}
              type="button"
              aria-pressed={period === i}
              onClick={() => setPeriod(i)}
              className={`rounded-lg px-4 py-2 text-sm font-semibold ${
                period === i ? "bg-btn text-white" : "text-muted hover:text-fg"
              }`}
            >
              {i === "monthly" ? "Monthly" : "Annual"}
              {i === "annual" && (
                <span className={`ml-2 text-xs ${period === i ? "text-indigo-100" : "text-emerald-600 dark:text-emerald-400"}`}>
                  Save {PRICING.currencyLabel}
                  {ANNUAL_SAVING}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="mx-auto mt-10 grid max-w-4xl gap-6 md:grid-cols-2">
        <section aria-labelledby="plan-free" className={`${card} flex flex-col p-6`}>
          <h2 id="plan-free" className="text-xl font-bold">Free</h2>
          <p className="mt-1 text-sm text-muted">Quick checks on any address.</p>
          <p className="mt-6 text-4xl font-bold">
            {PRICING.currencyLabel}0<span className="text-base font-normal text-muted"> / forever</span>
          </p>
          <ul className="mt-6 flex-1 space-y-3 text-sm">
            {FREE_FEATURES.map((f) => (
              <li key={f} className="flex gap-2"><Check />{f}</li>
            ))}
          </ul>
          <Link href="/" className={`${btnSecondary} mt-8`}>Search an address</Link>
        </section>

        <section aria-labelledby="plan-pro" className="flex flex-col rounded-xl border-2 border-brand bg-surface p-6 shadow-md">
          <h2 id="plan-pro" className="text-xl font-bold">Pro</h2>
          <p className="mt-1 text-sm text-muted">Full analytics for buyers, investors and agents.</p>
          <p className="mt-6 text-4xl font-bold">
            {PRICING.currencyLabel}
            {price}
            <span className="text-base font-normal text-muted"> / {period === "monthly" ? "month" : "year"}</span>
          </p>
          <p className="mt-1 h-5 text-sm text-muted">
            {period === "annual" && `Just ${PRICING.currencyLabel}${ANNUAL_PER_MONTH.toFixed(0)} per month, billed annually`}
          </p>
          <ul className="mt-5 flex-1 space-y-3 text-sm">
            {PRO_FEATURES.map((f) => (
              <li key={f} className="flex gap-2"><Check />{f}</li>
            ))}
          </ul>
          {error && <p role="alert" className="mt-4 text-sm text-rose-600 dark:text-rose-400">{error}</p>}
          <button type="button" onClick={upgrade} disabled={busy || loading} className={`${btnPrimary} mt-6`}>
            {busy ? "Redirecting…" : user ? "Upgrade to Pro" : "Sign in to upgrade"}
          </button>
        </section>
      </div>
    </div>
  );
}
