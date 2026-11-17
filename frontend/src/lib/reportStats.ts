import type { CitizenReport, IssueType } from "@/api/reports";
import { AGE_LEVELS, ageInDays, ageLevel, isUnresolved } from "@/lib/reportAge";

export const ISSUE_TYPES: IssueType[] = ["leak", "outage", "quality", "billing"];
const DAY_MS = 86_400_000;
const dayKey = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

// the numbers behind the citizen-report charts
export function reportStats(reports: CitizenReport[], now: number = Date.now(), days = 14) {
  const issues = Object.fromEntries(ISSUE_TYPES.map((t) => [t, 0])) as Record<IssueType, number>;
  const waiting = Object.fromEntries(AGE_LEVELS.map((l) => [l.id, 0])) as Record<(typeof AGE_LEVELS)[number]["id"], number>;
  const perAuthority = new Map<string, number>();
  let open = 0;

  for (const report of reports) {
    issues[report.issue_type] += 1;
    if (!isUnresolved(report)) continue;
    open += 1;
    waiting[ageLevel(ageInDays(report.created_at, now)).id] += 1;
    perAuthority.set(report.wsa_id, (perAuthority.get(report.wsa_id) ?? 0) + 1);
  }

  // reports received per day, oldest to newest, ending today
  const perDay = Array.from({ length: days }, (_, i) => {
    const date = new Date(now - (days - 1 - i) * DAY_MS);
    return { date, count: 0, key: dayKey(date) };
  });
  for (const report of reports) {
    const slot = perDay.find((d) => d.key === dayKey(new Date(report.created_at)));
    if (slot) slot.count += 1;
  }

  const topAuthorities = [...perAuthority.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([wsaId, count]) => ({ wsaId, count }));
  return { issues, waiting, open, perDay, topAuthorities };
}
