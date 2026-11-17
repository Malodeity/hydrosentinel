import type { CaseStatus, CitizenReport, IssueType } from "@/api/reports";
import { ageInDays, isUnresolved } from "@/lib/reportAge";

// "unresolved" = open + in review: everything still waiting on someone
export type StatusFilter = CaseStatus | "all" | "unresolved";
export type IssueFilter = IssueType | "all";

export interface ReportFilters {
  status: StatusFilter;
  issue: IssueFilter;
  query: string;
  minAgeDays: number; // 0 = any age; otherwise only unresolved reports at least this old
}

export function matchesReportFilters(report: CitizenReport, filters: ReportFilters, wsaName: string, now: number = Date.now()): boolean {
  if (filters.status === "unresolved" ? !isUnresolved(report) : filters.status !== "all" && report.case_status !== filters.status) return false;
  if (filters.issue !== "all" && report.issue_type !== filters.issue) return false;
  if (filters.minAgeDays > 0 && (!isUnresolved(report) || ageInDays(report.created_at, now) < filters.minAgeDays)) return false;
  const query = filters.query.trim().toLowerCase();
  if (!query) return true;
  return [report.description ?? "", report.reference_code, wsaName, report.admin_comment ?? ""].some((field) =>
    field.toLowerCase().includes(query),
  );
}

export function countByStatus(reports: CitizenReport[]): Record<StatusFilter, number> {
  const counts: Record<StatusFilter, number> = { all: reports.length, unresolved: 0, open: 0, in_review: 0, resolved: 0 };
  for (const report of reports) {
    counts[report.case_status] += 1;
    if (isUnresolved(report)) counts.unresolved += 1;
  }
  return counts;
}

// Oldest first, so the reports that have waited longest are at the top of the list.
export function sortOldestFirst(reports: CitizenReport[]): CitizenReport[] {
  return [...reports].sort((left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime());
}
