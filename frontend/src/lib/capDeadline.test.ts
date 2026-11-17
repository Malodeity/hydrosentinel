import { describe, expect, it } from "vitest";

import { describeDeadline } from "@/lib/capDeadline";

const today = new Date(2026, 10, 6); // 6 Nov 2026

describe("describeDeadline", () => {
  it("flags a missed deadline as overdue and says by how many days, so the official knows how late it is", () => {
    const result = describeDeadline("in_progress", "2026-11-01", today);
    expect(result.tone).toBe("overdue");
    expect(result.text).toContain("5 days overdue");
  });

  it("never calls a completed plan overdue, even if its due date has passed", () => {
    expect(describeDeadline("completed", "2026-01-01", today).tone).toBe("ok");
  });

  it("warns when the deadline is within two weeks, and treats a later one as fine", () => {
    expect(describeDeadline("submitted", "2026-11-12", today)).toMatchObject({ tone: "soon" });
    expect(describeDeadline("submitted", "2026-12-31", today).tone).toBe("ok");
  });

  it("treats today as due today, not overdue", () => {
    expect(describeDeadline("submitted", "2026-11-06", today)).toMatchObject({ tone: "soon", text: expect.stringContaining("due today") });
  });

  it("explains a missing date instead of showing a dash", () => {
    expect(describeDeadline("none", null, today).text).toBe("No plan submitted");
    expect(describeDeadline("submitted", null, today).text).toBe("No due date set");
  });
});
