import type { PropertyType } from "./types";

const aud = new Intl.NumberFormat("en-AU", {
  style: "currency",
  currency: "AUD",
  maximumFractionDigits: 0,
});

export function formatCurrency(n: number | null | undefined): string {
  return n == null ? "—" : aud.format(n);
}

/** e.g. 1250000 -> $1.25M, 437000 -> $437k */
export function formatCompact(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `$${trim(n / 1_000_000)}M`;
  if (n >= 1_000) return `$${trim(n / 1_000)}k`;
  return `$${Math.round(n)}`;
}

function trim(n: number): string {
  return n.toFixed(2).replace(/\.?0+$/, "");
}

export function formatPct(n: number | null | undefined, digits = 1): string {
  if (n == null) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Formats YYYY-MM-DD as "4 Dec 2018" without timezone drift. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  const month = MONTHS[Number(m) - 1];
  if (!y || !month || !d) return iso;
  return `${Number(d)} ${month} ${y}`;
}

/** Formats YYYY-MM as "Dec 2018". */
export function formatMonth(ym: string): string {
  const [y, m] = ym.split("-");
  const month = MONTHS[Number(m) - 1];
  return y && month ? `${month} ${y}` : ym;
}

export function formatYears(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${n.toFixed(1)} yrs`;
}

export function formatArea(n: number | null | undefined): string {
  return n == null ? "—" : `${new Intl.NumberFormat("en-AU").format(n)} m²`;
}

export function formatPropertyType(t: PropertyType): string {
  return t === "vacant land" ? "Vacant land" : t.charAt(0).toUpperCase() + t.slice(1);
}

/** Tailwind text color for positive/negative change. */
export function changeClass(n: number | null | undefined): string {
  if (n == null || n === 0) return "text-muted";
  return n > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400";
}
