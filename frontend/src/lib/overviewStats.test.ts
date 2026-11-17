import { describe, expect, it } from "vitest";

import type { Alert } from "@/api/alerts";
import type { CitizenReport } from "@/api/reports";
import type { WSA } from "@/api/wsa";
import { blueDropBand, overviewStats } from "@/lib/overviewStats";

const now = new Date(2026, 10, 6, 12).getTime();
const wsa = (o: Partial<WSA>) => ({ risk_level: "low", cap_status: "none", cap_due_date: null, blue_drop_score: null, ...o }) as WSA;
const report = (daysAgo: number, case_status = "open") => ({ case_status, created_at: new Date(now - daysAgo * 86_400_000).toISOString() }) as CitizenReport;

describe("blueDropBand", () => {
  it("uses the DWS bands: 95 certified, 50 non-certified, 31 poor, below that critical", () => {
    expect([95, 94.9, 50, 49, 31, 30.9].map(blueDropBand)).toEqual(["certified", "non_certified", "non_certified", "poor", "poor", "critical"]);
  });
  it("says unknown, not critical, when there is no score", () => {
    expect(blueDropBand(null)).toBe("unknown");
  });
});

describe("overviewStats", () => {
  it("counts what needs action: unresolved reports, those waiting two weeks, overdue plans, uncovered high risk, unhandled alerts", () => {
    const s = overviewStats(
      [wsa({ risk_level: "high" }), wsa({ risk_level: "high", cap_status: "submitted", cap_due_date: "2026-11-01" }), wsa({})],
      [report(20), report(2), report(30, "resolved")],
      [{ acknowledged_at: null }, { acknowledged_at: "2026-11-01" }] as Alert[],
      now,
    );
    expect(s).toMatchObject({ openReports: 2, waitingTwoWeeks: 1, overdueCaps: 1, highRiskWithoutCap: 1, activeAlerts: 1, total: 3 });
    expect(s.risk.high).toBe(2);
    expect(s.newThisWeek).toBe(1); // only the 2-day-old report is from the past 7 days
  });
});
