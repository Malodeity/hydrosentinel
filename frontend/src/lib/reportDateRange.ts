import type { CitizenReport } from "@/api/reports";

export function isReportInsideRange(report: CitizenReport, range: string) {
  if (range === "all") {
    return true;
  }

  const reportDate = new Date(report.created_at);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  if (range === "today") {
    return reportDate >= startOfToday;
  }

  const days = Number(range);
  const cutoff = new Date(now);
  cutoff.setDate(now.getDate() - days);
  return reportDate >= cutoff;
}
