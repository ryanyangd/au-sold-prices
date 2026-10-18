import { describe, expect, it } from "vitest";
import { getPropertyMock, searchMock } from "./data";

describe("mock data", () => {
  it("finds addresses by tokens and respects the limit", () => {
    const res = searchMock("example", 3);
    expect(res.length).toBeGreaterThan(0);
    expect(res.length).toBeLessThanOrEqual(3);
    expect(res[0]).toMatchObject({ state: "NSW", postcode: expect.any(String) });
    expect(searchMock("ab", 8)).toEqual([]);
  });

  it("gates sections for the free plan", () => {
    const id = searchMock("example", 1)[0]!.property_id;
    const free = getPropertyMock(id, "free")!;
    expect(free.access).toEqual({
      plan: "free",
      locked_sections: ["sales_history", "trend", "distribution", "comparables"],
    });
    expect(free.sales).toBeNull();
    expect(free.trend).toBeNull();
    expect(free.suburb.median_12m).not.toBeNull();
  });

  it("returns every section for pro and null for unknown ids", () => {
    const id = searchMock("example", 1)[0]!.property_id;
    const pro = getPropertyMock(id, "pro")!;
    expect(pro.access.locked_sections).toEqual([]);
    expect(pro.sales!.length).toBe(pro.property.sale_count);
    expect(pro.trend!.length).toBeGreaterThan(100);
    expect(pro.comparables!.every((c) => c.property_id !== id)).toBe(true);
    expect(getPropertyMock("nope", "pro")).toBeNull();
  });
});
