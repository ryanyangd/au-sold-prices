"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { formatArea, formatCurrency, formatDate, formatPropertyType } from "@/lib/format";
import type { Comparable } from "@/lib/types";
import { TypeBadge } from "../TypeBadge";
import { Section } from "./Section";

type SortKey = "address" | "property_type" | "price" | "contract_date" | "land_area_m2";

const COLUMNS: { key: SortKey; label: string; align?: "right" }[] = [
  { key: "address", label: "Address" },
  { key: "property_type", label: "Type" },
  { key: "price", label: "Price", align: "right" },
  { key: "contract_date", label: "Sold", align: "right" },
  { key: "land_area_m2", label: "Land", align: "right" },
];

export function sortComparables(rows: Comparable[], key: SortKey, dir: "asc" | "desc"): Comparable[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1; // nulls last in both directions
    if (bv == null) return -1;
    return (typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv))) * sign;
  });
}

export function ComparablesTable({ rows }: { rows: Comparable[] }) {
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "contract_date", dir: "desc" });
  const sorted = useMemo(() => sortComparables(rows, sort.key, sort.dir), [rows, sort]);

  function toggle(key: SortKey) {
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "address" || key === "property_type" ? "asc" : "desc" }));
  }

  return (
    <Section title="Comparable sales" subtitle="Recent sales of similar nearby properties">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] text-left text-sm">
          <caption className="sr-only">Comparable sales. Column headers are sortable buttons.</caption>
          <thead>
            <tr className="border-b border-line text-muted">
              {COLUMNS.map((c) => {
                const active = sort.key === c.key;
                return (
                  <th
                    key={c.key}
                    scope="col"
                    aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                    className={`py-2 pr-4 font-medium ${c.align === "right" ? "text-right" : ""}`}
                  >
                    <button
                      type="button"
                      onClick={() => toggle(c.key)}
                      className={`inline-flex items-center gap-1 rounded hover:text-fg ${active ? "text-fg" : ""}`}
                    >
                      {c.label}
                      <span aria-hidden="true" className="text-xs">
                        {active ? (sort.dir === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </button>
                  </th>
                );
              })}
              <th scope="col" className="py-2 text-right font-medium">
                <span className="sr-only">Link</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.property_id} className="border-b border-line/60 last:border-0">
                <td className="py-3 pr-4 font-medium">{r.address}</td>
                <td className="py-3 pr-4">
                  <TypeBadge type={r.property_type} />
                  <span className="sr-only">{formatPropertyType(r.property_type)}</span>
                </td>
                <td className="py-3 pr-4 text-right font-semibold">{formatCurrency(r.price)}</td>
                <td className="py-3 pr-4 text-right">{formatDate(r.contract_date)}</td>
                <td className="py-3 pr-4 text-right">{formatArea(r.land_area_m2)}</td>
                <td className="py-3 text-right">
                  <Link
                    href={`/property/${encodeURIComponent(r.property_id)}`}
                    className="font-semibold text-brand hover:underline"
                    aria-label={`View ${r.address}`}
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
