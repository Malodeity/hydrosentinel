import { describe, expect, it } from "vitest";

import { ageInDays, ageLevel, formatAge, reportAgeLevel } from "@/lib/reportAge";

const NOW = new Date("2026-11-10T12:00:00Z").getTime();
const daysAgo = (days: number) => new Date(NOW - days * 86_400_000 - 1000).toISOString();

describe("ageLevel", () => {
  it.each([
    [0, "ontrack"],
    [2, "ontrack"],
    [3, "attention"],
    [6, "attention"],
    [7, "overdue"],
    [13, "overdue"],
    [14, "critical"],
    [29, "critical"],
    [30, "escalate"],
    [400, "escalate"],
  ])("a report waiting %i days is %s", (days, expected) => {
    expect(ageLevel(days).id).toBe(expected);
  });
});

describe("ageInDays", () => {
  it("counts whole days", () => {
    expect(ageInDays(daysAgo(0), NOW)).toBe(0);
    expect(ageInDays(daysAgo(3), NOW)).toBe(3);
  });

  it("treats a bad or future date as 0 days instead of breaking the list", () => {
    expect(ageInDays("not a date", NOW)).toBe(0);
    expect(ageInDays(new Date(NOW + 5 * 86_400_000).toISOString(), NOW)).toBe(0);
  });
});

describe("reportAgeLevel", () => {
  it("flags an unresolved report by how long it has waited", () => {
    expect(reportAgeLevel({ case_status: "open", created_at: daysAgo(9) }, NOW)?.id).toBe("overdue");
    expect(reportAgeLevel({ case_status: "in_review", created_at: daysAgo(31) }, NOW)?.id).toBe("escalate");
  });

  it("does not flag a resolved report, however old it is", () => {
    expect(reportAgeLevel({ case_status: "resolved", created_at: daysAgo(200) }, NOW)).toBeNull();
  });
});

describe("formatAge", () => {
  it("reads naturally", () => {
    expect(formatAge(0)).toBe("Today");
    expect(formatAge(1)).toBe("1 day");
    expect(formatAge(12)).toBe("12 days");
  });
});
