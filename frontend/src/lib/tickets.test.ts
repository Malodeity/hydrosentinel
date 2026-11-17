import { describe, expect, it } from "vitest";

import { ACTION_NEEDS_NOTE, contractorActions, describeDue, isActiveTicket, issueList } from "@/lib/tickets";

describe("contractorActions", () => {
  // a contractor must accept before starting, and can never resolve the report: the only way out of the work is "fix" (then the authority checks it)
  it("offers accept/reject on a new ticket, then start or fix, and nothing once finished", () => {
    expect(contractorActions("assigned")).toEqual(["accept", "reject"]);
    expect(contractorActions("accepted")).toEqual(["start", "fix"]);
    expect(contractorActions("sent_back")).toEqual(["fix"]);
    for (const done of ["fixed", "rejected", "cancelled", "closed"] as const) expect(contractorActions(done)).toEqual([]);
  });

  it("requires a reason to reject and a note to mark fixed, but not to accept or start", () => {
    expect(ACTION_NEEDS_NOTE).toEqual({ accept: false, start: false, reject: true, fix: true });
  });
});

describe("isActiveTicket", () => {
  it("treats a fixed ticket as still active because the authority has not verified it yet", () => {
    expect(isActiveTicket("fixed")).toBe(true);
    expect(isActiveTicket("closed")).toBe(false);
    expect(isActiveTicket("rejected")).toBe(false);
  });
});

describe("describeDue", () => {
  const now = new Date("2026-11-07T10:00:00Z");
  it("flags a past due time as overdue and a future one as not", () => {
    expect(describeDue("2026-11-07T07:00:00Z", now)).toEqual({ text: "3 h overdue", overdue: true });
    expect(describeDue("2026-11-07T15:00:00Z", now)).toEqual({ text: "due in 5 h", overdue: false });
    expect(describeDue("2026-11-11T10:00:00Z", now)).toEqual({ text: "due in 4 days", overdue: false });
    expect(describeDue(null, now).overdue).toBe(false);
  });
});

describe("issueList", () => {
  it("capitalises each issue and joins them", () => expect(issueList(["leak", "outage"])).toBe("Leak, Outage"));
});
