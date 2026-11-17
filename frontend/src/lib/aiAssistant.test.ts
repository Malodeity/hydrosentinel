import { describe, expect, it } from "vitest";

import { aiErrorMessage, describeChecked, toolLabel, usageTone } from "@/lib/aiAssistant";

describe("aiAssistant helpers", () => {
  it("names the data the AI looked at in plain words, once each, and never hides an unknown tool", () => {
    expect(describeChecked([{ tool: "count_wsas" }, { tool: "get_open_reports" }, { tool: "count_wsas" }])).toBe("authority count, open reports");
    expect(toolLabel("some_new_tool")).toBe("some new tool");
  });

  it("explains the two failures an admin can act on, and falls back for the rest", () => {
    expect(aiErrorMessage({ response: { status: 429 } }, "x")).toContain("allowance");
    expect(aiErrorMessage({ response: { status: 503 } }, "x")).toContain("not configured");
    expect(aiErrorMessage(new Error("boom"), "Could not answer.")).toBe("Could not answer.");
  });

  it("warns with five calls left and again when none are left", () => {
    expect(usageTone(10, 20)).toBe("ok");
    expect(usageTone(15, 20)).toBe("low");
    expect(usageTone(20, 20)).toBe("empty");
  });
});
