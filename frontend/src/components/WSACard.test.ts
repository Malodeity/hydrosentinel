import { describe, expect, it } from "vitest";

import type { WSA } from "@/api/wsa";
import { dataCompleteness } from "@/components/WSACard";

function makeWsa(overrides: Partial<WSA> = {}): WSA {
  return {
    id: "1",
    name: "Test WSA",
    province: "Gauteng",
    blue_drop_score: null,
    green_drop_score: null,
    nrw_percent: null,
    cap_status: "none",
    cap_due_date: null,
    maint_pct: null,
    risk_level: "low",
    lat: 0,
    lng: 0,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("dataCompleteness", () => {
  it("counts zero filled fields when all four are null", () => {
    const result = dataCompleteness(makeWsa());
    expect(result).toEqual({ filled: 0, total: 4 });
  });

  it("counts all four filled when every field is present", () => {
    const result = dataCompleteness(
      makeWsa({ blue_drop_score: 80, green_drop_score: 70, nrw_percent: 30, maint_pct: 8 }),
    );
    expect(result).toEqual({ filled: 4, total: 4 });
  });

  it("counts a partial mix correctly", () => {
    const result = dataCompleteness(makeWsa({ blue_drop_score: 80, maint_pct: 8 }));
    expect(result.filled).toBe(2);
    expect(result.total).toBe(4);
  });

  it("treats zero as a present value, not missing", () => {
    // a real risk: `value === null` must be the check, not falsy-check,
    // since 0 is a legitimate score (e.g. nrw_percent: 0)
    const result = dataCompleteness(makeWsa({ nrw_percent: 0 }));
    expect(result.filled).toBe(1);
  });
});
