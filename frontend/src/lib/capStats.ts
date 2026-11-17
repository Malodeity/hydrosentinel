import type { CapStatus, RiskLevel, WSA } from "@/api/wsa";
import { describeDeadline } from "@/lib/capDeadline";

export const CAP_STATUSES: CapStatus[] = ["none", "submitted", "in_progress", "completed"];
export const RISK_LEVELS: RiskLevel[] = ["high", "medium", "low"];

// the numbers behind the CAP charts, for whichever authorities are currently in view
export function capStats(wsas: WSA[], today: Date = new Date()) {
  const byStatus = Object.fromEntries(CAP_STATUSES.map((s) => [s, 0])) as Record<CapStatus, number>;
  const riskByCap = Object.fromEntries(RISK_LEVELS.map((r) => [r, { ...byStatus }])) as Record<RiskLevel, Record<CapStatus, number>>;
  const deadlines = { overdue: 0, soon: 0, ok: 0, noDate: 0 };

  for (const wsa of wsas) {
    byStatus[wsa.cap_status] += 1;
    riskByCap[wsa.risk_level][wsa.cap_status] += 1;
    // deadlines only matter for plans that exist and are not finished
    if (wsa.cap_status === "none" || wsa.cap_status === "completed") continue;
    const { tone } = describeDeadline(wsa.cap_status, wsa.cap_due_date, today);
    if (tone === "overdue") deadlines.overdue += 1;
    else if (tone === "soon") deadlines.soon += 1;
    else if (tone === "ok") deadlines.ok += 1;
    else deadlines.noDate += 1;
  }
  return { byStatus, riskByCap, deadlines, highRiskWithoutCap: riskByCap.high.none };
}
