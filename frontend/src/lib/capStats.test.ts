import { describe, expect, it } from "vitest";

import type { WSA } from "@/api/wsa";
import { capStats } from "@/lib/capStats";

const today = new Date(2026, 10, 6);
const wsa = (risk_level: WSA["risk_level"], cap_status: WSA["cap_status"], cap_due_date: string | null = null) =>
  ({ risk_level, cap_status, cap_due_date }) as WSA;

describe("capStats", () => {
  it("counts high-risk authorities with no CAP, the gap an official most needs to see", () => {
    const stats = capStats([wsa("high", "none"), wsa("high", "none"), wsa("high", "submitted"), wsa("low", "none")], today);
    expect(stats.highRiskWithoutCap).toBe(2);
    expect(stats.riskByCap.high.submitted).toBe(1);
  });

  it("buckets deadlines only for unfinished plans", () => {
    const stats = capStats(
      [wsa("medium", "in_progress", "2026-11-01"), wsa("medium", "submitted", "2026-11-10"), wsa("medium", "submitted", "2027-05-01"), wsa("medium", "submitted"), wsa("medium", "completed", "2020-01-01"), wsa("medium", "none")],
      today,
    );
    expect(stats.deadlines).toEqual({ overdue: 1, soon: 1, ok: 1, noDate: 1 });
  });
});
