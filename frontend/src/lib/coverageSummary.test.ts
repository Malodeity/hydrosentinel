import { describe, expect, it } from "vitest";

import type { Coverage } from "@/api/assignments";
import { summarizeCoverage } from "@/lib/coverageSummary";

const wsas = [
  { id: "a", name: "Alpha", province: "Gauteng" },
  { id: "b", name: "Beta", province: "Gauteng" },
  { id: "c", name: "Gamma", province: "Free State" },
];
const row = (wsa_id: string, wsa_name: string, issue_types: Coverage["issue_types"]): Coverage => ({ wsa_id, wsa_name, issue_types });

describe("summarizeCoverage", () => {
  // "all authorities in the province" is only true when every one is covered with the same issues: a managing admin relies on that wording
  it("says all-in-province only when every authority is covered with the same issue types", () => {
    const full = summarizeCoverage([row("a", "Alpha", ["leak"]), row("b", "Beta", ["leak"])], wsas);
    expect(full).toEqual([{ province: "Gauteng", issueTypes: ["leak"], allInProvince: true, authorities: ["Alpha", "Beta"], total: 2 }]);

    const partial = summarizeCoverage([row("a", "Alpha", ["leak"])], wsas);
    expect(partial[0].allInProvince).toBe(false);

    const mixed = summarizeCoverage([row("a", "Alpha", ["leak"]), row("b", "Beta", ["leak", "outage"])], wsas);
    expect(mixed[0].allInProvince).toBe(false);
  });

  it("groups by province, sorted, across provinces", () => {
    const out = summarizeCoverage([row("c", "Gamma", ["quality"]), row("a", "Alpha", ["leak"])], wsas);
    expect(out.map((p) => p.province)).toEqual(["Free State", "Gauteng"]);
  });
});
