import { describe, expect, it } from "vitest";

import type { Alert } from "@/api/alerts";
import type { CitizenReport } from "@/api/reports";
import type { WSA } from "@/api/wsa";
import { buildManagementStats } from "@/lib/managementReport";

const NOW = new Date("2026-11-10T12:00:00Z").getTime();
const daysAgo = (days: number) => new Date(NOW - days * 86_400_000 - 1000).toISOString();

const wsa = (overrides: Partial<WSA>): WSA => ({
  id: "w", name: "WSA", province: "Gauteng", blue_drop_score: 50, green_drop_score: null, nrw_percent: null, cap_status: "none",
  cap_due_date: null, maint_pct: null, risk_level: "low", lat: 0, lng: 0, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", ...overrides,
});
const report = (overrides: Partial<CitizenReport>): CitizenReport => ({
  id: "r", wsa_id: "g1", issue_type: "leak", description: "d", reference_code: "HS-1", case_status: "open", admin_comment: null, reviewed_by: null,
  resolved_by: null, reviewed_at: null, resolved_at: null, lat: 0, lng: 0, created_at: daysAgo(1), photo_urls: [], ...overrides,
});
const alert = (overrides: Partial<Alert>): Alert => ({
  id: "a", wsa_id: "g1", wsa_name: "G1", alert_type: "risk_level_high", message: "m", acknowledged_by: null, acknowledged_at: null, created_at: daysAgo(1), ...overrides,
});

const wsas = [
  wsa({ id: "g1", name: "G1", province: "Gauteng", risk_level: "high", blue_drop_score: 20, cap_status: "submitted", cap_due_date: "2026-11-01" }),
  wsa({ id: "g2", name: "G2", province: "Gauteng", risk_level: "low", blue_drop_score: 80, cap_status: "completed", cap_due_date: "2026-10-01" }),
  wsa({ id: "f1", name: "F1", province: "Free State", risk_level: "medium", blue_drop_score: null }),
];
const scopeAll = { province: "", periodDays: 0 };

describe("buildManagementStats", () => {
  it("counts authorities by risk and averages Blue Drop over the ones that have a score", () => {
    const stats = buildManagementStats({ reports: [], wsas, alerts: [], scope: scopeAll, now: NOW });
    expect(stats.authorities).toEqual({ total: 3, high: 1, medium: 1, low: 1, avgBlueDrop: 50 });
    expect(stats.byProvince.map((row) => [row.province, row.total, row.avgBlueDrop])).toEqual([["Free State", 1, null], ["Gauteng", 2, 50]]);
  });

  it("ranks the riskiest authorities first, lowest Blue Drop breaking ties", () => {
    const stats = buildManagementStats({ reports: [], wsas, alerts: [], scope: scopeAll, now: NOW });
    expect(stats.topRisk.map((item) => item.id)).toEqual(["g1", "f1", "g2"]);
  });

  it("limits everything to one province when a province is chosen", () => {
    const reports = [report({ id: "in", wsa_id: "g1" }), report({ id: "out", wsa_id: "f1" })];
    const alerts = [alert({ wsa_id: "g1" }), alert({ id: "b", wsa_id: "f1" })];
    const stats = buildManagementStats({ reports, wsas, alerts, scope: { province: "Gauteng", periodDays: 0 }, now: NOW });
    expect(stats.authorities.total).toBe(2);
    expect(stats.reports.inPeriod).toBe(1);
    expect(stats.alerts.total).toBe(1);
  });

  it("counts a CAP as overdue only when its due date has passed and it is not completed", () => {
    const stats = buildManagementStats({ reports: [], wsas, alerts: [], scope: scopeAll, now: NOW });
    expect(stats.cap.overdue.map((item) => item.id)).toEqual(["g1"]); // g2 is past due but completed
    expect(stats.cap.completed).toBe(1);
  });

  it("never counts an authority with no plan as overdue, so the PDF agrees with the Overview and CAP tabs", () => {
    const withLeftoverDate = [...wsas, wsa({ id: "n1", name: "N1", cap_status: "none", cap_due_date: "2026-01-01" })];
    const stats = buildManagementStats({ reports: [], wsas: withLeftoverDate, alerts: [], scope: scopeAll, now: NOW });
    expect(stats.cap.overdue.map((item) => item.id)).toEqual(["g1"]);
  });

  it("applies the period to report counts and averages but not to the unresolved backlog", () => {
    const reports = [
      report({ id: "recent-resolved", case_status: "resolved", created_at: daysAgo(6), resolved_at: daysAgo(4) }),
      report({ id: "old-open", created_at: daysAgo(60) }),
    ];
    const stats = buildManagementStats({ reports, wsas, alerts: [], scope: { province: "", periodDays: 30 }, now: NOW });
    expect(stats.reports.inPeriod).toBe(1);
    expect(stats.reports.byStatus.resolved).toBe(1);
    expect(stats.reports.avgDaysToResolve).toBe(2);
    expect(stats.ageing.unresolved).toBe(1); // the 60-day-old report is still waiting, so management must see it
    expect(stats.ageing.counts.escalate).toBe(1);
  });

  it("sorts the unresolved backlog into the age hierarchy and counts 14+ days as escalated", () => {
    const reports = [
      report({ id: "a", created_at: daysAgo(1) }),
      report({ id: "b", created_at: daysAgo(4) }),
      report({ id: "c", created_at: daysAgo(9), case_status: "in_review" }),
      report({ id: "d", created_at: daysAgo(15) }),
      report({ id: "e", created_at: daysAgo(40) }),
      report({ id: "f", created_at: daysAgo(200), case_status: "resolved" }),
    ];
    const stats = buildManagementStats({ reports, wsas, alerts: [], scope: scopeAll, now: NOW });
    expect(stats.ageing.counts).toEqual({ ontrack: 1, attention: 1, overdue: 1, critical: 1, escalate: 1 });
    expect(stats.ageing.escalated).toBe(2);
    expect(stats.ageing.oldest[0].id).toBe("e");
  });

  it("writes plain findings from the numbers", () => {
    const reports = [report({ created_at: daysAgo(20) })];
    const stats = buildManagementStats({ reports, wsas, alerts: [alert({})], scope: scopeAll, now: NOW });
    expect(stats.findings).toContain("1 of 3 authorities are rated high risk (33%).");
    expect(stats.findings).toContain("1 citizen report is unresolved and has waited 14 days or more.");
    expect(stats.findings).toContain("1 corrective action plan is past its due date.");
    expect(stats.findings).toContain("1 alert is waiting to be acknowledged.");
  });

  it("uses plural grammar when there is more than one", () => {
    const reports = [report({ id: "x", created_at: daysAgo(20) }), report({ id: "y", created_at: daysAgo(25) }), report({ id: "z", created_at: daysAgo(2) })];
    const stats = buildManagementStats({ reports, wsas, alerts: [alert({ id: "1" }), alert({ id: "2" })], scope: scopeAll, now: NOW });
    expect(stats.findings).toContain("3 citizen reports are unresolved, and 2 of them have waited 14 days or more.");
    expect(stats.findings).toContain("2 alerts are waiting to be acknowledged.");
  });

  it("lists the high-risk authorities that have no corrective action plan, the most urgent gap", () => {
    const extra = [wsa({ id: "h1", name: "H1", risk_level: "high", cap_status: "none", blue_drop_score: 10 }), wsa({ id: "h2", name: "H2", risk_level: "high", cap_status: "in_progress" })];
    const stats = buildManagementStats({ reports: [], wsas: [...wsas, ...extra], alerts: [], scope: scopeAll, now: NOW });
    expect(stats.cap.highRiskWithoutPlan.map((item) => item.id)).toEqual(["h1"]);
    expect(stats.findings).toContain("1 high-risk authority has no corrective action plan.");
  });

  it("lists CAP deadlines in the next 30 days, soonest first, and ignores completed or already-late ones", () => {
    const extra = [
      wsa({ id: "d1", name: "D1", cap_status: "submitted", cap_due_date: "2026-11-25" }),
      wsa({ id: "d2", name: "D2", cap_status: "in_progress", cap_due_date: "2026-11-12" }),
      wsa({ id: "d3", name: "D3", cap_status: "completed", cap_due_date: "2026-11-15" }),
      wsa({ id: "d4", name: "D4", cap_status: "submitted", cap_due_date: "2027-03-01" }),
    ];
    const stats = buildManagementStats({ reports: [], wsas: [...wsas, ...extra], alerts: [], scope: scopeAll, now: NOW });
    expect(stats.cap.dueSoon.map((item) => item.id)).toEqual(["d2", "d1"]);
  });

  it("counts only unacknowledged alerts as waiting", () => {
    const alerts = [alert({ id: "1" }), alert({ id: "2", acknowledged_at: daysAgo(0) })];
    const stats = buildManagementStats({ reports: [], wsas, alerts, scope: scopeAll, now: NOW });
    expect(stats.alerts).toMatchObject({ total: 2, unacknowledged: 1 });
  });
});
