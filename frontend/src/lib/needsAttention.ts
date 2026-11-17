// Builds the 'Do these first' list on the Overview tab from alerts, overdue plans, old reports and uncovered high-risk authorities.

import type { Alert } from "@/api/alerts";
import type { CitizenReport } from "@/api/reports";
import type { WSA } from "@/api/wsa";
import { describeDeadline } from "@/lib/capDeadline";
import { AGE_LEVELS, ageInDays, formatAge, isUnresolved } from "@/lib/reportAge";

export type AttentionKind = "alert" | "report" | "cap" | "uncovered";

export interface AttentionItem {
  id: string;
  kind: AttentionKind;
  title: string; // the authority
  detail: string; // what is wrong, in a sentence
  score: number; // for ranking only
  reportId?: string;
  wsaId?: string;
}

const PER_KIND = 2; // so one long backlog can never push every other kind of problem off the list
const MAX_ITEMS = 6;

// Scores rise strictly with age (n / (n + 30)) but saturate, so the longest-waiting item is first without ever outranking a live alert.
// One ranked "what to do first" list drawn from all the places a problem can show up. It does not repeat the CAP-overdue alerts,
// because overdue plans are listed here directly. Ranking: live alerts, then the longest overdue plans and oldest reports, then uncovered high risk.
export function needsAttention(wsas: WSA[], reports: CitizenReport[], alerts: Alert[], now: number = Date.now()): AttentionItem[] {
  const name = new Map(wsas.map((w) => [w.id, w.name]));
  const criticalDays = AGE_LEVELS.find((l) => l.id === "critical")!.minDays;
  const items: AttentionItem[] = [];
  const take = (kind: AttentionKind, list: AttentionItem[]) => items.push(...list.sort((a, b) => b.score - a.score).slice(0, PER_KIND));

  take("alert", alerts.filter((a) => !a.acknowledged_at && a.alert_type !== "cap_overdue").map((a) => ({
    id: `alert-${a.id}`, kind: "alert" as const, title: a.wsa_name, detail: a.message, score: 100, wsaId: a.wsa_id,
  })));

  take("cap", wsas.flatMap((w) => {
    const d = describeDeadline(w.cap_status, w.cap_due_date, new Date(now));
    if (d.tone !== "overdue") return [];
    const late = Number(/(\d+) days? overdue/.exec(d.text)?.[1] ?? 0);
    return [{ id: `cap-${w.id}`, kind: "cap" as const, title: w.name, detail: `Corrective action plan is ${late} day${late === 1 ? "" : "s"} past its deadline`, score: 60 + (20 * late) / (late + 30) + (w.risk_level === "high" ? 10 : 0), wsaId: w.id }];
  }));

  take("report", reports.filter((r) => isUnresolved(r) && ageInDays(r.created_at, now) >= criticalDays).map((r) => {
    const days = ageInDays(r.created_at, now);
    return { id: `report-${r.id}`, kind: "report" as const, title: name.get(r.wsa_id) ?? "Unknown authority", detail: `${r.issue_type[0].toUpperCase() + r.issue_type.slice(1)} report waiting ${formatAge(days)}`, score: 50 + (30 * days) / (days + 30), reportId: r.id, wsaId: r.wsa_id };
  }));

  take("uncovered", wsas.filter((w) => w.risk_level === "high" && w.cap_status === "none").map((w) => ({
    id: `uncovered-${w.id}`, kind: "uncovered" as const, title: w.name, detail: "High risk and no corrective action plan", score: 40 + (100 - (w.blue_drop_score ?? 0)) / 10, wsaId: w.id,
  })));

  return items.sort((a, b) => b.score - a.score).slice(0, MAX_ITEMS);
}
