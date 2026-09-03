import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CitizenReport } from "@/api/reports";
import { isReportInsideRange } from "@/lib/reportDateRange";

function makeReport(createdAt: string): CitizenReport {
  return {
    id: "1",
    wsa_id: "wsa-1",
    issue_type: "leak",
    description: null,
    reference_code: "HS-TEST0000",
    case_status: "open",
    admin_comment: null,
    reviewed_by: null,
    resolved_by: null,
    reviewed_at: null,
    resolved_at: null,
    lat: 0,
    lng: 0,
    created_at: createdAt,
    photo_urls: [],
  };
}

describe("isReportInsideRange", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-15T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("always includes a report when range is 'all'", () => {
    expect(isReportInsideRange(makeReport("2020-01-01T00:00:00Z"), "all")).toBe(true);
  });

  it("includes a report created today for range 'today'", () => {
    expect(isReportInsideRange(makeReport("2026-06-15T01:00:00Z"), "today")).toBe(true);
  });

  it("excludes a report created yesterday for range 'today'", () => {
    // well clear of the UTC day boundary so this isn't timezone-sensitive
    // (isReportInsideRange correctly uses local-time day boundaries — a
    // timestamp near midnight UTC would flip "today" depending on the
    // runner's timezone, which isn't what this test is checking)
    expect(isReportInsideRange(makeReport("2026-06-13T12:00:00Z"), "today")).toBe(false);
  });

  it("includes a report within the numeric day window", () => {
    expect(isReportInsideRange(makeReport("2026-06-10T12:00:00Z"), "7")).toBe(true);
  });

  it("excludes a report outside the numeric day window", () => {
    expect(isReportInsideRange(makeReport("2026-06-01T12:00:00Z"), "7")).toBe(false);
  });
});
