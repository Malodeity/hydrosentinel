import { describe, expect, it } from "vitest";

import type { CitizenReport } from "@/api/reports";
import { clusterIssueType, clusterReportsForAlert, reportBounds } from "@/lib/alertCluster";

const RAISED = new Date("2026-10-19T09:14:30Z").getTime();
const at = (hoursBeforeAlert: number) => new Date(RAISED - hoursBeforeAlert * 3_600_000).toISOString();
const report = (overrides: Partial<CitizenReport>): CitizenReport => ({
  id: "r", wsa_id: "w1", issue_type: "leak", description: null, reference_code: "HS-1", case_status: "open", admin_comment: null,
  reviewed_by: null, resolved_by: null, reviewed_at: null, resolved_at: null, lat: -26.2, lng: 28.0, created_at: at(1), photo_urls: [], ...overrides,
});
const alert = { wsa_id: "w1", created_at: new Date(RAISED).toISOString(), message: "3 leak reports within 2.0km of each other in City of Ekurhuleni in the last 6 hours" };

describe("clusterReportsForAlert", () => {
  it("finds the reports behind an alert even when the alert is days old, so 'View on map' never comes up empty", () => {
    const reports = [report({ id: "a", created_at: at(1) }), report({ id: "b", created_at: at(3) }), report({ id: "c", created_at: at(0.1) })];
    // 'now' is far past the alert: the old code measured from now and found nothing
    expect(clusterReportsForAlert(alert, reports).map((r) => r.id).sort()).toEqual(["a", "b", "c"]);
  });

  it("leaves out reports from another authority, other issue types, and those older than the 6 hour window", () => {
    const reports = [
      report({ id: "other-wsa", wsa_id: "w2" }),
      report({ id: "other-issue", issue_type: "outage" }),
      report({ id: "too-old", created_at: at(7) }),
      report({ id: "after-alert", created_at: at(-3) }),
      report({ id: "match" }),
    ];
    expect(clusterReportsForAlert(alert, reports).map((r) => r.id)).toEqual(["match"]);
  });

  it("includes every issue type when the message does not name one", () => {
    const reports = [report({ id: "a" }), report({ id: "b", issue_type: "outage" })];
    expect(clusterReportsForAlert({ ...alert, message: "Something else" }, reports)).toHaveLength(2);
  });
});

describe("clusterIssueType", () => {
  it("reads the issue type from the alert message", () => {
    expect(clusterIssueType("3 leak reports within 2.0km")).toBe("leak");
    expect(clusterIssueType("5 outage reports within 2.0km")).toBe("outage");
    expect(clusterIssueType("High risk")).toBeNull();
  });
});

describe("reportBounds", () => {
  it("returns the box that fits every report", () => {
    expect(reportBounds([{ lat: -26.2, lng: 28.0 }, { lat: -26.25, lng: 28.1 }])).toEqual([[-26.25, 28.0], [-26.2, 28.1]]);
  });
});
