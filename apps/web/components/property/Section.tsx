import Link from "next/link";
import type { ReactNode } from "react";
import { btnPrimary, card } from "@/lib/ui";

export function Section({
  title,
  subtitle,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section aria-label={title} className={`${card} p-5 ${className}`}>
      <h2 className="text-lg font-semibold">{title}</h2>
      {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function EmptySection({ title, message }: { title: string; message: string }) {
  return (
    <Section title={title}>
      <p className="py-6 text-center text-sm text-muted">{message}</p>
    </Section>
  );
}

export type PlaceholderKind = "chart" | "bars" | "table";

/** Decorative stand-in drawn with static shapes; never contains real data. */
function Placeholder({ kind }: { kind: PlaceholderKind }) {
  if (kind === "table") {
    return (
      <div className="space-y-3" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="grid grid-cols-4 gap-4">
            <div className="h-4 rounded bg-surface-2" />
            <div className="h-4 rounded bg-brand-soft" />
            <div className="h-4 rounded bg-surface-2" />
            <div className="h-4 rounded bg-surface-2" />
          </div>
        ))}
      </div>
    );
  }
  if (kind === "bars") {
    const heights = [20, 35, 55, 80, 100, 85, 60, 40, 25, 15];
    return (
      <div className="flex h-56 items-end gap-2" aria-hidden="true">
        {heights.map((h, i) => (
          <div key={i} className="flex-1 rounded-t bg-brand/50" style={{ height: `${h}%` }} />
        ))}
      </div>
    );
  }
  return (
    <svg viewBox="0 0 400 140" className="h-56 w-full" preserveAspectRatio="none" aria-hidden="true">
      <path d="M0 110 C60 100 90 60 140 70 S230 30 280 45 S350 20 400 15" fill="none" stroke="currentColor" strokeWidth="3" className="text-brand" />
      <path d="M0 125 H400 M0 85 H400 M0 45 H400" stroke="currentColor" strokeWidth="1" className="text-line" />
    </svg>
  );
}

export function LockedSection({
  title,
  description,
  kind,
}: {
  title: string;
  description: string;
  kind: PlaceholderKind;
}) {
  return (
    <section aria-label={`${title} (Pro)`} className={`${card} relative overflow-hidden p-5`}>
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-4 select-none blur-sm" aria-hidden="true">
        <Placeholder kind={kind} />
      </div>
      <div className="absolute inset-x-0 bottom-0 top-14 flex flex-col items-center justify-center gap-3 bg-surface/60 px-4 text-center">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-soft text-brand">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <rect x="4" y="11" width="16" height="10" rx="2" />
            <path d="M8 11V7a4 4 0 0 1 8 0v4" />
          </svg>
        </span>
        <p className="max-w-sm text-sm font-medium">{description}</p>
        <Link href="/pricing" className={btnPrimary}>
          Upgrade to Pro
        </Link>
      </div>
    </section>
  );
}
