import { describe, expect, it } from "vitest";

import type { WSA } from "@/api/wsa";
import { publicStats } from "@/lib/publicStats";

const w = (o: Partial<WSA>) => ({ risk_level: "low", blue_drop_score: null, cap_status: "none", updated_at: "2026-01-01T00:00:00Z", ...o }) as WSA;

describe("publicStats", () => {
  it("counts critical drinking water only for real scores under 31, not for authorities with no score", () => {
    const s = publicStats([w({ blue_drop_score: 20 }), w({ blue_drop_score: 31 }), w({ blue_drop_score: null }), w({ risk_level: "high", cap_status: "completed" })]);
    expect(s).toMatchObject({ total: 4, high: 1, criticalWater: 1, capCompleted: 1 });
  });
});
