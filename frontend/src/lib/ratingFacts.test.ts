import { describe, expect, it } from "vitest";

import type { WSA } from "@/api/wsa";
import { ratingFacts } from "@/lib/ratingFacts";

const wsa = (o: Partial<WSA>) => ({ blue_drop_score: null, green_drop_score: null, nrw_percent: null, maint_pct: null, cap_status: "none", ...o }) as WSA;

describe("ratingFacts", () => {
  it("states the Blue Drop band and the 95 certification line, so a score is never shown without meaning", () => {
    expect(ratingFacts(wsa({ blue_drop_score: 18.73 }))[0]).toBe("Blue Drop score 18.7 is in the critical band (certification needs 95).");
  });

  it("says plainly when there is no score or no plan, instead of staying silent", () => {
    const facts = ratingFacts(wsa({}));
    expect(facts[0]).toContain("No Blue Drop");
    expect(facts).toContain("No corrective action plan has been submitted.");
  });

  it("reports missing data only when something is missing, and quotes NRW only when it exists", () => {
    const full = ratingFacts(wsa({ blue_drop_score: 96, green_drop_score: 80, nrw_percent: 20, maint_pct: 5, cap_status: "completed" }));
    expect(full.some((f) => f.startsWith("Only"))).toBe(false);
    expect(full.some((f) => f.includes("20%"))).toBe(true);
    expect(ratingFacts(wsa({ blue_drop_score: 50 })).some((f) => f.includes("non-revenue"))).toBe(false);
  });
});
