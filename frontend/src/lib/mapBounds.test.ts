import { describe, expect, it } from "vitest";

import { toSummaryBounds } from "@/lib/mapBounds";

describe("toSummaryBounds", () => {
  it("leaves a normal view untouched", () => {
    const view = { south: -27.2, north: -25.4, west: 27.0, east: 29.2 };
    expect(toSummaryBounds(view)).toEqual(view);
  });

  it("clamps a zoomed-out view that wraps past the antimeridian, which the API would reject with a 422", () => {
    const wrapped = { south: -95, north: 91, west: -280, east: 340 };
    expect(toSummaryBounds(wrapped)).toEqual({ south: -90, north: 90, west: -180, east: 180 });
  });
});
