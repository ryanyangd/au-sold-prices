import { describe, expect, it } from "vitest";
import { highlightSegments } from "./highlight";

describe("highlightSegments", () => {
  it("returns a single unmatched segment for an empty query", () => {
    expect(highlightSegments("12 Example St", "")).toEqual([{ text: "12 Example St", match: false }]);
  });

  it("marks case-insensitive matches and preserves original casing", () => {
    expect(highlightSegments("12 Example St", "exam")).toEqual([
      { text: "12 ", match: false },
      { text: "Exam", match: true },
      { text: "ple St", match: false },
    ]);
  });

  it("handles multiple tokens and overlapping ranges", () => {
    const segs = highlightSegments("12 Example St", "12 ex exam");
    expect(segs.filter((s) => s.match).map((s) => s.text)).toEqual(["12", "Exam"]);
    expect(segs.map((s) => s.text).join("")).toBe("12 Example St");
  });

  it("matches repeated occurrences", () => {
    expect(highlightSegments("Sample Sam", "sam").filter((s) => s.match)).toHaveLength(2);
  });
});
