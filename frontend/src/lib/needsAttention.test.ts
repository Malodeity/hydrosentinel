import { describe, expect, it } from "vitest";

import type { Alert } from "@/api/alerts";
import type { CitizenReport } from "@/api/reports";
import type { WSA } from "@/api/wsa";
import { needsAttention } from "@/lib/needsAttention";

const now = new Date(2026, 10, 6, 12).getTime();
const day = 86_400_000;
const wsa = (id: string, o: Partial<WSA> = {}) => ({ id, name: `WSA ${id}`, risk_level: "low", cap_status: "none", cap_due_date: null, blue_drop_score: 50, ...o }) as WSA;
const report = (id: string, wsa_id: string, daysAgo: number, case_status = "open") => ({ id, wsa_id, issue_type: "leak", case_status, created_at: new Date(now - daysAgo * day).toISOString() }) as CitizenReport;

describe("needsAttention", () => {
  it("puts live alerts first, then overdue plans, then old reports, then uncovered high risk", () => {
    const items = needsAttention(
      [wsa("a", { risk_level: "high" }), wsa("b", { cap_status: "submitted", cap_due_date: "2026-10-20" })],
      [report("r1", "a", 25)],
      [{ id: "al", wsa_id: "a", wsa_name: "WSA a", alert_type: "geo_cluster_incident", message: "cluster", acknowledged_at: null } as Alert],
      now,
    );
    expect(items.map((i) => i.kind)).toEqual(["alert", "cap", "report", "uncovered"]);
  });

  it("does not list CAP-overdue alerts, handled alerts, resolved reports or reports under two weeks old", () => {
    const items = needsAttention(
      [wsa("a")],
      [report("old-resolved", "a", 40, "resolved"), report("new", "a", 3)],
      [{ id: "1", wsa_id: "a", wsa_name: "x", alert_type: "cap_overdue", message: "m", acknowledged_at: null } as Alert, { id: "2", wsa_id: "a", wsa_name: "x", alert_type: "risk_level_high", message: "m", acknowledged_at: "2026-11-01" } as Alert],
      now,
    );
    expect(items).toEqual([]);
  });

  it("caps each kind at two so one long backlog cannot hide the other problems", () => {
    const reports = [1, 2, 3, 4, 5].map((n) => report(`r${n}`, "a", 20 + n));
    const items = needsAttention([wsa("a", { risk_level: "high" })], reports, [], now);
    expect(items.filter((i) => i.kind === "report")).toHaveLength(2);
    expect(items.some((i) => i.kind === "uncovered")).toBe(true);
  });

  it("puts the longest-waiting report first even when several have waited a long time", () => {
    // a cap on the score used to make a 65-day and a 156-day report tie, hiding the one that has waited longest
    const items = needsAttention([wsa("a")], [report("r65", "a", 65), report("r156", "a", 156)], [], now);
    expect(items.map((i) => i.reportId)).toEqual(["r156", "r65"]);
  });
});
