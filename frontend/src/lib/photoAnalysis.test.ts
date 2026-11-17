import { describe, expect, it } from "vitest";

import type { PhotoAnalysis } from "@/api/reports";
import { describeVerdict } from "@/lib/photoAnalysis";

const analysis = (overrides: Partial<PhotoAnalysis>): PhotoAnalysis => ({
  issue_type: "leak", severity: "medium", confidence: "high", summary: "Water from a pipe.", verdict: "matches", photo: "a.png", analysed_at: "2026-11-06T10:00:00Z", ...overrides,
});

describe("describeVerdict", () => {
  it("says the photo agrees when the server's verdict is matches", () => {
    const result = describeVerdict(analysis({ verdict: "matches" }), "leak");
    expect(result.tone).toBe("good");
    expect(result.detail).toContain("a leak");
  });

  it("warns on a mismatch and names both what the photo shows and what was reported, so the admin looks before acting", () => {
    const result = describeVerdict(analysis({ verdict: "mismatch", issue_type: "leak" }), "outage");
    expect(result.tone).toBe("warn");
    expect(result.detail).toContain("shows a leak");
    expect(result.detail).toContain("reported an outage");
  });

  it("explains a photo of nothing wrong as no water service problem", () => {
    const result = describeVerdict(analysis({ verdict: "mismatch", issue_type: "not_water_related" }), "leak");
    expect(result.detail).toContain("no water service problem");
  });

  it("is neutral, not alarming, when the photo cannot decide, and explains that billing cannot be checked from a photo", () => {
    expect(describeVerdict(analysis({ verdict: "inconclusive", issue_type: "unclear" }), "leak").tone).toBe("neutral");
    expect(describeVerdict(analysis({ verdict: "inconclusive" }), "billing").detail).toContain("Billing");
  });
});
