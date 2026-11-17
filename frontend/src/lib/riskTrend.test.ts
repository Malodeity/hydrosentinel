import { describe, expect, it } from "vitest";

import { riskTrend } from "@/lib/riskTrend";

const h = (...levels: ("low" | "medium" | "high")[]) => levels.map((risk_level) => ({ risk_level })); // newest first

describe("riskTrend", () => {
  it("says worse when the newest score is a higher risk level than the oldest", () => {
    expect(riskTrend(h("high", "medium", "low"))?.direction).toBe("worse");
  });
  it("says better when risk fell, and unchanged when the level is the same", () => {
    expect(riskTrend(h("low", "medium", "high"))?.direction).toBe("better");
    expect(riskTrend(h("medium", "medium"))?.direction).toBe("unchanged");
  });
  it("needs two scores to have a trend", () => {
    expect(riskTrend(h("high"))).toBeNull();
  });
});
