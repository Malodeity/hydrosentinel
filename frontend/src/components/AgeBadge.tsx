import type { CitizenReport } from "@/api/reports";
import { ageInDays, formatAge, reportAgeLevel } from "@/lib/reportAge";
import { cn } from "@/lib/utils";

// Shows how long an unresolved report has waited. Calm by design: plain text with a small coloured dot, and the
// text only gets heavier once the report is overdue, so a long list does not turn into a wall of red. Resolved reports show nothing.
export function AgeBadge({ report }: { report: Pick<CitizenReport, "case_status" | "created_at"> }) {
  const level = reportAgeLevel(report);
  if (!level) return null;
  const days = ageInDays(report.created_at);
  const urgent = level.minDays >= 7;
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 whitespace-nowrap text-xs", urgent ? "font-semibold text-foreground" : "text-muted-foreground")}
      title={`${level.label}: ${level.description}`}
    >
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: level.color }} aria-hidden="true" />
      {formatAge(days)}
      {level.minDays > 0 ? ` · ${level.label}` : ""}
    </span>
  );
}
