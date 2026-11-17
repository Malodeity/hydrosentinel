import { describe, expect, it } from "vitest";

import { paginate } from "@/lib/pagination";

const rows = Array.from({ length: 23 }, (_, index) => index + 1);

describe("paginate", () => {
  it("returns the first page and counts the pages", () => {
    const result = paginate(rows, 1, 10);
    expect(result.items).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    expect(result.pageCount).toBe(3);
    expect([result.start, result.end, result.total]).toEqual([1, 10, 23]);
  });

  it("gives the short last page", () => {
    const result = paginate(rows, 3, 10);
    expect(result.items).toEqual([21, 22, 23]);
    expect([result.start, result.end]).toEqual([21, 23]);
  });

  it("clamps a page past the end, so shrinking a filter never leaves the admin on an empty page", () => {
    expect(paginate(rows, 9, 10).page).toBe(3);
    expect(paginate(rows, 0, 10).page).toBe(1);
  });

  it("handles an empty list as one empty page", () => {
    const result = paginate([], 1, 10);
    expect(result.items).toEqual([]);
    expect([result.page, result.pageCount, result.start, result.end]).toEqual([1, 1, 0, 0]);
  });
});
