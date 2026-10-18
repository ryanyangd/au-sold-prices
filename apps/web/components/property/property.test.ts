import { describe, expect, it } from "vitest";
import type { Comparable } from "@/lib/types";
import { sortComparables } from "./ComparablesTable";
import { mergeTrend } from "./TrendChart";

const comp = (id: string, price: number, land: number | null): Comparable => ({
  property_id: id,
  address: id,
  property_type: "house",
  price,
  contract_date: "2024-01-01",
  land_area_m2: land,
});

describe("sortComparables", () => {
  const rows = [comp("b", 2, null), comp("a", 3, 400), comp("c", 1, 300)];

  it("sorts numerically in both directions", () => {
    expect(sortComparables(rows, "price", "asc").map((r) => r.property_id)).toEqual(["c", "b", "a"]);
    expect(sortComparables(rows, "price", "desc").map((r) => r.property_id)).toEqual(["a", "b", "c"]);
  });

  it("keeps nulls last", () => {
    expect(sortComparables(rows, "land_area_m2", "asc").map((r) => r.property_id)).toEqual(["c", "a", "b"]);
    expect(sortComparables(rows, "land_area_m2", "desc").map((r) => r.property_id)).toEqual(["a", "c", "b"]);
  });
});

describe("mergeTrend", () => {
  it("overlays sale points by month and adds months outside the trend", () => {
    const rows = mergeTrend(
      [
        { month: "2024-01", median: 100, sales_count: 3 },
        { month: "2024-02", median: 110, sales_count: 4 },
      ],
      [
        { contract_date: "2024-02-10", settlement_date: null, price: 120, change_pct: null, years_held: null },
        { contract_date: "2010-06-01", settlement_date: null, price: 50, change_pct: null, years_held: null },
      ],
    );
    expect(rows.map((r) => r.month)).toEqual(["2010-06", "2024-01", "2024-02"]);
    expect(rows[2]).toMatchObject({ median: 110, sale: 120 });
    expect(rows[0]).toMatchObject({ sale: 50 });
  });
});
