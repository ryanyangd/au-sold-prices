import type { Metadata } from "next";
import { PricingTable } from "@/components/PricingTable";
import { container } from "@/lib/ui";

export const metadata: Metadata = { title: "Pricing" };

export default function PricingPage() {
  return (
    <div className={`${container} py-14`}>
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Simple pricing</h1>
        <p className="mt-3 text-lg text-muted">Start free. Upgrade when you need the full picture.</p>
      </div>
      <div className="mt-10">
        <PricingTable />
      </div>
      <p className="mx-auto mt-10 max-w-xl text-center text-xs text-muted">
        Prices in Australian dollars. Cancel any time from your account. Not valuation advice. Data may be incomplete.
      </p>
    </div>
  );
}
