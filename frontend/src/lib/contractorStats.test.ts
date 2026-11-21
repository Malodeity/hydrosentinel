import { describe, expect, it } from "vitest";

import type { Ticket } from "@/api/assignments";
import { chartBars, dashboardNumbers, filterTickets, formatHours } from "@/lib/contractorStats";

const NOW = new Date("2026-11-20T12:00:00Z");
const ago = (days: number, hours = 0) => new Date(NOW.getTime() - days * 86_400_000 - hours * 3_600_000).toISOString();

let n = 0;
const ticket = (over: Partial<Ticket>): Ticket => ({
  id: String(++n), status: "assigned", contractor_id: "c", contractor_name: "C", due_at: null, overdue: false, contractor_note: null, rejected_reason: null,
  report_id: "r", wsa_id: "w", wsa_name: "W", reference_code: "HS-1", issue_type: "leak", description: null, lat: 0, lng: 0, photo_urls: [], repair_photo_urls: [],
  instructions: null, admin_note: null, created_at: ago(1), accepted_at: null, started_at: null, fixed_at: null, closed_at: null, ...over,
});

describe("dashboardNumbers", () => {
  it("counts what is open and what needs the contractor to act, so nothing waiting for them is hidden", () => {
    const list = [ticket({ status: "assigned" }), ticket({ status: "sent_back" }), ticket({ status: "in_progress", overdue: true }), ticket({ status: "fixed" }), ticket({ status: "closed", closed_at: ago(2) })];
    const d = dashboardNumbers(list, "month", NOW);
    expect(d.open).toBe(3); // a fixed ticket is no longer with the contractor
    expect(d.needsAction).toBe(2);
    expect(d.overdue).toBe(1);
    expect(d.awaitingCheck).toBe(1);
  });

  it("counts only the tickets inside the chosen period, so switching week, month and 3 months changes the numbers", () => {
    const list = [ticket({ created_at: ago(3), fixed_at: ago(2), status: "fixed" }), ticket({ created_at: ago(20), fixed_at: ago(15), status: "fixed" }), ticket({ created_at: ago(60), fixed_at: ago(50), status: "closed", closed_at: ago(49) })];
    expect(dashboardNumbers(list, "week", NOW)).toMatchObject({ opened: 1, fixed: 1, verified: 0 });
    expect(dashboardNumbers(list, "month", NOW)).toMatchObject({ opened: 2, fixed: 2, verified: 0 });
    expect(dashboardNumbers(list, "quarter", NOW)).toMatchObject({ opened: 3, fixed: 3, verified: 1 });
  });

  it("averages the time from arriving to being marked fixed, and says nothing rather than zero when nothing was fixed", () => {
    const list = [ticket({ created_at: ago(2, 0), fixed_at: ago(1, 0), status: "fixed" }), ticket({ created_at: ago(3, 0), fixed_at: ago(2, 0), status: "fixed" })];
    expect(dashboardNumbers(list, "week", NOW).avgHoursToFix).toBeCloseTo(24);
    expect(dashboardNumbers([ticket({})], "week", NOW).avgHoursToFix).toBeNull();
  });

  it("measures fixed-on-time against each ticket's own due time and ignores tickets that had none", () => {
    const onTime = ticket({ created_at: ago(3), due_at: ago(1), fixed_at: ago(2), status: "fixed" });
    const late = ticket({ created_at: ago(3), due_at: ago(2), fixed_at: ago(1), status: "fixed" });
    const noDue = ticket({ created_at: ago(3), fixed_at: ago(1), status: "fixed" });
    expect(dashboardNumbers([onTime, late, noDue], "week", NOW).onTimePct).toBe(50);
    expect(dashboardNumbers([noDue], "week", NOW).onTimePct).toBeNull();
  });
});

describe("filterTickets", () => {
  const list = [ticket({ status: "assigned" }), ticket({ status: "accepted", overdue: true }), ticket({ status: "fixed" }), ticket({ status: "closed", closed_at: ago(2) }), ticket({ status: "closed", closed_at: ago(40) }), ticket({ status: "rejected" })];
  it("shows exactly what each number counted, so clicking a tile never disagrees with it", () => {
    expect(filterTickets(list, "open", "month", NOW)).toHaveLength(2);
    expect(filterTickets(list, "action", "month", NOW)).toHaveLength(1);
    expect(filterTickets(list, "overdue", "month", NOW)).toHaveLength(1);
    expect(filterTickets(list, "awaiting", "month", NOW)).toHaveLength(1);
    expect(filterTickets(list, "other", "month", NOW)).toHaveLength(1);
    expect(filterTickets(list, "all", "month", NOW)).toHaveLength(6);
  });
  it("lists closed tickets only from the chosen period, newest first", () => {
    expect(filterTickets(list, "closed", "week", NOW)).toHaveLength(1);
    expect(filterTickets(list, "closed", "quarter", NOW).map((t) => t.closed_at)).toEqual([ago(2), ago(40)]);
  });
});

describe("chartBars", () => {
  it("puts every ticket of the period into exactly one slice, so the chart adds up to the numbers above it", () => {
    const list = [ticket({ created_at: ago(0, 2) }), ticket({ created_at: ago(3), fixed_at: ago(1), status: "fixed" }), ticket({ created_at: ago(100) })];
    const bars = chartBars(list, "week", NOW);
    expect(bars).toHaveLength(7);
    expect(bars.reduce((s, b) => s + b.opened, 0)).toBe(2);
    expect(bars.reduce((s, b) => s + b.fixed, 0)).toBe(1);
  });
});

describe("formatHours", () => {
  it("writes a duration the way a person would say it", () => {
    expect(formatHours(null)).toBe("No data yet");
    expect(formatHours(0.4)).toBe("under 1 h");
    expect(formatHours(6.2)).toBe("6 h");
    expect(formatHours(72)).toBe("3 days");
  });
});
