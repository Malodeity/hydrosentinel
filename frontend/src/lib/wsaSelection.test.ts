import { describe, expect, it } from "vitest";

import type { WSA } from "@/api/wsa";
import { pickDefaultWsa } from "@/lib/wsaSelection";

function makeWsa(overrides: Partial<WSA> = {}): WSA {
  return {
    id: "1",
    name: "Z WSA",
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

describe("pickDefaultWsa", () => {
  it("returns null for an empty list", () => {
    expect(pickDefaultWsa([])).toBeNull();
  });

  it("picks the high-risk WSA over one that merely sorts first alphabetically", () => {
    // the actual bug this guards against: "!Kai! Garib LM" sorts before
    // every letter, so a plain wsas[0] pick always won regardless of risk
    const punctuationNamed = makeWsa({ id: "1", name: "!Kai! Garib LM", risk_level: "low" });
    const highRisk = makeWsa({ id: "2", name: "Albert Luthuli LM", risk_level: "high" });

    const picked = pickDefaultWsa([punctuationNamed, highRisk]);

    expect(picked?.id).toBe("2");
  });

  it("breaks ties within the same risk tier alphabetically", () => {
    const b = makeWsa({ id: "1", name: "Bravo WSA", risk_level: "high" });
    const a = makeWsa({ id: "2", name: "Alpha WSA", risk_level: "high" });

    const picked = pickDefaultWsa([b, a]);

    expect(picked?.name).toBe("Alpha WSA");
  });

  it("prefers medium risk over low when no high-risk WSA exists", () => {
    const low = makeWsa({ id: "1", name: "Low WSA", risk_level: "low" });
    const medium = makeWsa({ id: "2", name: "Medium WSA", risk_level: "medium" });

    const picked = pickDefaultWsa([low, medium]);

    expect(picked?.id).toBe("2");
  });
});
