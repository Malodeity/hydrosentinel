import { describe, expect, it } from "vitest";

import type { CitizenReport } from "@/api/reports";
import { reportStats } from "@/lib/reportStats";

const now = new Date(2026, 10, 6, 12).getTime();
const daysAgo = (n: number) => new Date(now - n * 86_400_000).toISOString();
const report = (over: Partial<CitizenReport>) => ({ wsa_id: "a", issue_type: "leak", case_status: "open", created_at: daysAgo(0), ...over }) as CitizenReport;

describe("reportStats", () => {
  it("counts the waiting backlog only for unresolved reports, by how long they have waited", () => {
    const s = reportStats([report({ created_at: daysAgo(20) }), report({ created_at: daysAgo(1) }), report({ case_status: "resolved", created_at: daysAgo(40) })], now);
    expect(s.open).toBe(2);
    expect(s.waiting.critical).toBe(1);
    expect(s.waiting.ontrack).toBe(1);
    expect(s.waiting.escalate).toBe(0);
  });

  it("ranks authorities by open reports so the worst-hit one comes first", () => {
    const s = reportStats([report({ wsa_id: "x" }), report({ wsa_id: "y" }), report({ wsa_id: "y" }), report({ wsa_id: "z", case_status: "resolved" })], now);
    expect(s.topAuthorities[0]).toEqual({ wsaId: "y", count: 2 });
    expect(s.topAuthorities.some((a) => a.wsaId === "z")).toBe(false);
  });

  it("puts today's reports in the last day slot and ignores reports older than the window", () => {
    const s = reportStats([report({ created_at: daysAgo(0) }), report({ created_at: daysAgo(0) }), report({ created_at: daysAgo(30) })], now);
    expect(s.perDay).toHaveLength(14);
    expect(s.perDay[13].count).toBe(2);
    expect(s.perDay.reduce((n, d) => n + d.count, 0)).toBe(2);
  });
});
