// How long an unresolved citizen report has been waiting, and how loudly it should be flagged.
// The thresholds live here, in one place, so the admin page, the filters and the management PDF always agree.

export type AgeLevelId = "ontrack" | "attention" | "overdue" | "critical" | "escalate";

export interface AgeLevel {
  id: AgeLevelId;
  label: string;
  minDays: number; // the first whole day at which this level applies
  description: string;
  badgeClass: string; // Tailwind classes for the on-screen badge
  color: string; // solid colour for charts and the PDF
}

export const AGE_LEVELS: AgeLevel[] = [
  { id: "ontrack", label: "On track", minDays: 0, description: "Recently reported", badgeClass: "border-emerald-200 bg-emerald-50 text-emerald-800", color: "#16a34a" },
  { id: "attention", label: "Attention", minDays: 3, description: "Should be picked up", badgeClass: "border-amber-200 bg-amber-100 text-amber-900", color: "#f59e0b" },
  { id: "overdue", label: "Overdue", minDays: 7, description: "Past the one-week mark", badgeClass: "border-orange-200 bg-orange-100 text-orange-900", color: "#f97316" },
  { id: "critical", label: "Critical", minDays: 14, description: "Residents have waited two weeks", badgeClass: "border-red-200 bg-red-100 text-red-900", color: "#dc2626" },
  { id: "escalate", label: "Escalate", minDays: 30, description: "Needs management attention", badgeClass: "border-purple-300 bg-purple-100 text-purple-900", color: "#7c3aed" },
];

const MS_PER_DAY = 86_400_000;

// Whole days since the report was created. A bad or future date counts as 0 rather than breaking the page.
export function ageInDays(createdAt: string, now: number = Date.now()): number {
  const created = new Date(createdAt).getTime();
  if (Number.isNaN(created) || created > now) return 0;
  return Math.floor((now - created) / MS_PER_DAY);
}

export function ageLevel(days: number): AgeLevel {
  return [...AGE_LEVELS].reverse().find((level) => days >= level.minDays) ?? AGE_LEVELS[0];
}

export function isUnresolved(report: { case_status: string }): boolean {
  return report.case_status !== "resolved";
}

// Resolved reports are not flagged: they are no longer waiting.
export function reportAgeLevel(report: { case_status: string; created_at: string }, now: number = Date.now()): AgeLevel | null {
  return isUnresolved(report) ? ageLevel(ageInDays(report.created_at, now)) : null;
}

export function formatAge(days: number): string {
  if (days <= 0) return "Today";
  return days === 1 ? "1 day" : `${days} days`;
}
