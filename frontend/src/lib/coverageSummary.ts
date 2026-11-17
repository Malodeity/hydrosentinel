// Turns a contractor's coverage rows into plain lines grouped by province, so "works in all 5 authorities in Gauteng" reads at a glance
// instead of a list of five names. Used by the Contractors tab (components/ContractorsTab.tsx).

import type { Coverage } from "@/api/assignments";

export interface ProvinceCoverage {
  province: string;
  issueTypes: string[]; // the issue types shared by every row shown
  allInProvince: boolean; // true when the contractor covers every authority in that province
  authorities: string[]; // names, sorted (all of them when allInProvince)
  total: number; // how many authorities the province has
}

// wsas: just the id, name and province of each authority (the public list)
export function summarizeCoverage(coverage: Coverage[], wsas: { id: string; name: string; province: string }[]): ProvinceCoverage[] {
  const byId = new Map(wsas.map((w) => [w.id, w]));
  const totals = new Map<string, number>();
  for (const w of wsas) totals.set(w.province, (totals.get(w.province) ?? 0) + 1);

  const groups = new Map<string, Coverage[]>();
  for (const row of coverage) {
    const province = byId.get(row.wsa_id)?.province ?? "Unknown province";
    groups.set(province, [...(groups.get(province) ?? []), row]);
  }
  return [...groups.entries()]
    .map(([province, rows]) => {
      // only the issue types every row has are called "shared"; a mixed province lists authorities individually
      const shared = rows.map((r) => r.issue_types).reduce((a, b) => a.filter((t) => b.includes(t)));
      const uniform = rows.every((r) => r.issue_types.length === shared.length);
      const total = totals.get(province) ?? rows.length;
      return {
        province,
        issueTypes: shared,
        allInProvince: uniform && rows.length === total,
        authorities: rows.map((r) => r.wsa_name).sort((a, b) => a.localeCompare(b)),
        total,
      };
    })
    .sort((a, b) => a.province.localeCompare(b.province));
}
