import { describe, expect, it } from "vitest";

import type { CitizenReport } from "@/api/reports";
import { countByStatus, matchesReportFilters, sortOldestFirst, type ReportFilters } from "@/lib/reportFilters";

function makeReport(overrides: Partial<CitizenReport> = {}): CitizenReport {
  return {
    id: "1",
    wsa_id: "w1",
    issue_type: "leak",
    description: "Water main leaking on the corner",
    reference_code: "HS-AB12CD34",
    case_status: "open",
    admin_comment: null,
    reviewed_by: null,
    resolved_by: null,
    reviewed_at: null,
    resolved_at: null,
    lat: 0,
    lng: 0,
    created_at: "2026-01-01T00:00:00Z",
    photo_urls: [],
    ...overrides,
  };
}

const all: ReportFilters = { status: "all", issue: "all", query: "", minAgeDays: 0 };

describe("matchesReportFilters", () => {
  it("keeps everything when no filter is set", () => {
    expect(matchesReportFilters(makeReport(), all, "Ekurhuleni")).toBe(true);
  });

  it("filters by case status and issue type", () => {
    const report = makeReport({ case_status: "in_review", issue_type: "outage" });
    expect(matchesReportFilters(report, { ...all, status: "open" }, "X")).toBe(false);
    expect(matchesReportFilters(report, { ...all, status: "in_review" }, "X")).toBe(true);
    expect(matchesReportFilters(report, { ...all, issue: "leak" }, "X")).toBe(false);
  });

  it("searches description, reference code, authority name and admin note, ignoring case and spaces", () => {
    const report = makeReport({ admin_comment: "Crew dispatched" });
    expect(matchesReportFilters(report, { ...all, query: "  MAIN LEAKING " }, "Ekurhuleni")).toBe(true);
    expect(matchesReportFilters(report, { ...all, query: "hs-ab12" }, "Ekurhuleni")).toBe(true);
    expect(matchesReportFilters(report, { ...all, query: "ekurhuleni" }, "Ekurhuleni")).toBe(true);
    expect(matchesReportFilters(report, { ...all, query: "dispatched" }, "Ekurhuleni")).toBe(true);
    expect(matchesReportFilters(report, { ...all, query: "billing dispute" }, "Ekurhuleni")).toBe(false);
  });

  it("does not crash on a report with no description", () => {
    expect(matchesReportFilters(makeReport({ description: null }), { ...all, query: "leak" }, "Z")).toBe(false);
  });
});

describe("minimum age filter", () => {
  const NOW = new Date("2026-11-10T12:00:00Z").getTime();
  const created = (daysAgo: number) => new Date(NOW - daysAgo * 86_400_000 - 1000).toISOString();

  it("keeps only unresolved reports that have waited at least that long", () => {
    const old = makeReport({ created_at: created(8) });
    const fresh = makeReport({ created_at: created(1) });
    expect(matchesReportFilters(old, { ...all, minAgeDays: 7 }, "X", NOW)).toBe(true);
    expect(matchesReportFilters(fresh, { ...all, minAgeDays: 7 }, "X", NOW)).toBe(false);
  });

  it("drops resolved reports from an age filter, however old, because they are no longer waiting", () => {
    const oldResolved = makeReport({ case_status: "resolved", created_at: created(90) });
    expect(matchesReportFilters(oldResolved, { ...all, minAgeDays: 3 }, "X", NOW)).toBe(false);
  });
});

describe("sortOldestFirst", () => {
  it("puts the longest-waiting report first without changing the original list", () => {
    const newer = makeReport({ id: "new", created_at: "2026-02-01T00:00:00Z" });
    const older = makeReport({ id: "old", created_at: "2026-01-01T00:00:00Z" });
    const list = [newer, older];
    expect(sortOldestFirst(list).map((report) => report.id)).toEqual(["old", "new"]);
    expect(list.map((report) => report.id)).toEqual(["new", "old"]);
  });
});

describe("countByStatus", () => {
  it("counts each status so the filter chips can show them", () => {
    const counts = countByStatus([makeReport(), makeReport({ id: "2", case_status: "resolved" }), makeReport({ id: "3" })]);
    expect(counts).toEqual({ all: 3, unresolved: 2, open: 2, in_review: 0, resolved: 1 });
  });
});

describe("unresolved status filter", () => {
  const mk = (case_status: string) => ({ case_status, issue_type: "leak", created_at: new Date().toISOString(), reference_code: "x", description: "" }) as CitizenReport;
  it("matches open and in-review reports but not resolved ones, and is counted", () => {
    const filters = { status: "unresolved" as const, issue: "all" as const, query: "", minAgeDays: 0 };
    expect(matchesReportFilters(mk("open"), filters, "")).toBe(true);
    expect(matchesReportFilters(mk("in_review"), filters, "")).toBe(true);
    expect(matchesReportFilters(mk("resolved"), filters, "")).toBe(false);
    expect(countByStatus([mk("open"), mk("in_review"), mk("resolved")]).unresolved).toBe(2);
  });
});
