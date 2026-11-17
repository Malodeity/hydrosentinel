import { describe, expect, it } from "vitest";

import { formatAuditAction, formatAuditValue } from "@/lib/auditFormat";

describe("formatAuditAction", () => {
  it("makes snake_case readable and keeps the CAP acronym", () => {
    expect(formatAuditAction("cap_status_updated")).toBe("CAP status updated");
    expect(formatAuditAction("report_status_updated")).toBe("Report status updated");
  });
});

describe("formatAuditValue", () => {
  it("lists each changed field instead of a raw JSON blob", () => {
    expect(formatAuditValue({ case_status: "open", admin_comment: null })).toBe("case_status: open · admin_comment: none");
  });

  it("shows a dash when there was no previous or new value", () => {
    expect(formatAuditValue(null)).toBe("—");
    expect(formatAuditValue({})).toBe("—");
  });

  it("cuts a long note so one entry cannot take over the table, and can still give the full text for a tooltip", () => {
    const note = "x".repeat(200);
    expect(formatAuditValue({ admin_comment: note })).toBe(`admin_comment: ${"x".repeat(80)}…`);
    expect(formatAuditValue({ admin_comment: note }, Infinity)).toBe(`admin_comment: ${note}`);
  });

  it("keeps numbers and nested values legible", () => {
    expect(formatAuditValue({ probability: 0.8263, detail: { a: 1 } })).toBe('probability: 0.8263 · detail: {"a":1}');
  });
});
