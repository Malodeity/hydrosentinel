import type { Alert } from "@/api/alerts";
import type { CitizenReport } from "@/api/reports";
import type { RiskLevel, WSA } from "@/api/wsa";
import { capStats } from "@/lib/capStats";
import { AGE_LEVELS, ageInDays, isUnresolved } from "@/lib/reportAge";

export type BlueDropBand = "certified" | "non_certified" | "poor" | "critical" | "unknown";

// DWS Blue Drop bands, the same ones the data import uses (see backend BDCertification)
export function blueDropBand(score: number | null): BlueDropBand {
  if (score === null || score === undefined) return "unknown";
  if (score >= 95) return "certified";
  if (score >= 50) return "non_certified";
  if (score >= 31) return "poor";
  return "critical";
}

// wording for each band, with the score range, for the public authority card
export const BLUE_DROP_BAND_TEXT: Record<BlueDropBand, string> = {
  certified: "Certified",
  non_certified: "Non-certified",
  poor: "Poor",
  critical: "Critical",
  unknown: "No score",
};

// the headline numbers for the Overview tab: what needs action, and how the whole country looks
export function overviewStats(wsas: WSA[], reports: CitizenReport[], alerts: Alert[], now: number = Date.now()) {
  const criticalDays = AGE_LEVELS.find((l) => l.id === "critical")!.minDays;
  const unresolved = reports.filter(isUnresolved);
  const cap = capStats(wsas, new Date(now));

  const risk = { high: 0, medium: 0, low: 0 } as Record<RiskLevel, number>;
  const bands = { certified: 0, non_certified: 0, poor: 0, critical: 0, unknown: 0 } as Record<BlueDropBand, number>;
  for (const wsa of wsas) {
    risk[wsa.risk_level] += 1;
    bands[blueDropBand(wsa.blue_drop_score)] += 1;
  }

  return {
    openReports: unresolved.length,
    newThisWeek: reports.filter((r) => now - new Date(r.created_at).getTime() <= 7 * 86_400_000).length,
    waitingTwoWeeks: unresolved.filter((r) => ageInDays(r.created_at, now) >= criticalDays).length,
    overdueCaps: cap.deadlines.overdue,
    highRiskWithoutCap: cap.highRiskWithoutCap,
    activeAlerts: alerts.filter((a) => !a.acknowledged_at).length,
    risk,
    bands,
    total: wsas.length,
  };
}
