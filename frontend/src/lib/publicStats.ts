import type { WSA } from "@/api/wsa";
import { blueDropBand } from "@/lib/overviewStats";

// the four headline numbers on the public dashboard. deliberately no "last updated" date: updated_at moves whenever an admin edits a CAP,
// which says nothing about how fresh the audit data is (the page header states the audit year instead)
export function publicStats(wsas: WSA[]) {
  return {
    total: wsas.length,
    high: wsas.filter((w) => w.risk_level === "high").length,
    criticalWater: wsas.filter((w) => blueDropBand(w.blue_drop_score) === "critical").length,
    capCompleted: wsas.filter((w) => w.cap_status === "completed").length,
  };
}
