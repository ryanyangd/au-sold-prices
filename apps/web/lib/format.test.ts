import { describe, expect, it } from "vitest";
import { formatCompact, formatCurrency, formatDate, formatPct } from "./format";
import { ANNUAL_SAVING, PRICING } from "./config";
import { safePath } from "./auth/context";

describe("format", () => {
  it("formats currency, compact values, dates and percentages", () => {
    expect(formatCurrency(437000)).toBe("$437,000");
    expect(formatCompact(1_250_000)).toBe("$1.25M");
    expect(formatCompact(437_000)).toBe("$437k");
    expect(formatDate("2018-12-04")).toBe("4 Dec 2018");
    expect(formatPct(5.84)).toBe("+5.8%");
    expect(formatPct(-2)).toBe("-2.0%");
    expect(formatPct(null)).toBe("—");
  });
});

describe("config and auth helpers", () => {
  it("derives the annual saving from the price constants", () => {
    expect(PRICING.proMonthly).toBe(15);
    expect(PRICING.proAnnual).toBe(144);
    expect(ANNUAL_SAVING).toBe(36);
  });

  it("only allows same-site relative return paths", () => {
    expect(safePath("/pricing")).toBe("/pricing");
    expect(safePath("//evil.example")).toBeNull();
    expect(safePath("https://evil.example")).toBeNull();
    expect(safePath(null)).toBeNull();
  });
});
