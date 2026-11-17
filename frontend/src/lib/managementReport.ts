import type { Alert, AlertType } from "@/api/alerts";
import type { CaseStatus, CitizenReport, IssueType } from "@/api/reports";
import type { CapStatus, RiskLevel, WSA } from "@/api/wsa";
import { AGE_LEVELS, ageInDays, ageLevel, isUnresolved, type AgeLevelId } from "@/lib/reportAge";
import { sortOldestFirst } from "@/lib/reportFilters";

// Turns the live admin data into the numbers on the management report. Kept free of React so every figure is unit-tested:
// a document that goes to management must not contain a wrong count.

export interface ReportScope {
  province: string; // "" = all provinces
  periodDays: number; // 0 = all time
}

export interface ProvinceRow {
  province: string;
  total: number;
  high: number;
  medium: number;
  low: number;
  avgBlueDrop: number | null;
}

export interface ManagementStats {
  scope: ReportScope;
  authorities: { total: number; high: number; medium: number; low: number; avgBlueDrop: number | null };
  byProvince: ProvinceRow[];
  topRisk: WSA[];
  cap: Record<CapStatus, number> & { overdue: WSA[]; dueSoon: WSA[]; highRiskWithoutPlan: WSA[] };
  reports: {
    inPeriod: number;
    byStatus: Record<CaseStatus, number>;
    byIssue: Record<IssueType, number>;
    avgDaysToResolve: number | null;
    avgDaysToReview: number | null;
  };
  ageing: {
    unresolved: number;
    counts: Record<AgeLevelId, number>;
    escalated: number; // 14 days or more
    oldest: CitizenReport[];
  };
  alerts: { total: number; unacknowledged: number; byType: Partial<Record<AlertType, number>>; latestUnacknowledged: Alert[] };
  findings: string[];
}

const MS_PER_DAY = 86_400_000;
const riskRank: Record<RiskLevel, number> = { high: 0, medium: 1, low: 2 };

function average(values: number[]): number | null {
  return values.length === 0 ? null : values.reduce((sum, value) => sum + value, 0) / values.length;
}

const round1 = (value: number) => Math.round(value * 10) / 10;

export function buildManagementStats(input: { reports: CitizenReport[]; wsas: WSA[]; alerts: Alert[]; scope: ReportScope; now?: number }): ManagementStats {
  const now = input.now ?? Date.now();
  const { scope } = input;
  const wsas = scope.province ? input.wsas.filter((wsa) => wsa.province === scope.province) : input.wsas;
  const wsaIds = new Set(wsas.map((wsa) => wsa.id));
  const scopedReports = input.reports.filter((report) => wsaIds.has(report.wsa_id));
  const periodStart = scope.periodDays > 0 ? now - scope.periodDays * MS_PER_DAY : -Infinity;
  const reportsInPeriod = scopedReports.filter((report) => new Date(report.created_at).getTime() >= periodStart);

  const countRisk = (level: RiskLevel, list: WSA[]) => list.filter((wsa) => wsa.risk_level === level).length;
  const blueDrop = (list: WSA[]) => average(list.flatMap((wsa) => (wsa.blue_drop_score === null ? [] : [wsa.blue_drop_score])));

  const provinceNames = [...new Set(wsas.map((wsa) => wsa.province))].sort((a, b) => a.localeCompare(b));
  const byProvince: ProvinceRow[] = provinceNames.map((province) => {
    const inProvince = wsas.filter((wsa) => wsa.province === province);
    const avg = blueDrop(inProvince);
    return {
      province,
      total: inProvince.length,
      high: countRisk("high", inProvince),
      medium: countRisk("medium", inProvince),
      low: countRisk("low", inProvince),
      avgBlueDrop: avg === null ? null : round1(avg),
    };
  });

  const today = new Date(now).toISOString().slice(0, 10);
  const capCount = (status: CapStatus) => wsas.filter((wsa) => wsa.cap_status === status).length;
  const overdueCaps = wsas
    .filter((wsa) => wsa.cap_due_date && wsa.cap_status !== "completed" && wsa.cap_status !== "none" && wsa.cap_due_date < today) // no plan, no deadline: same rule as the admin screens
    .sort((a, b) => (a.cap_due_date ?? "").localeCompare(b.cap_due_date ?? ""));

  const soonLimit = new Date(now + 30 * MS_PER_DAY).toISOString().slice(0, 10);
  const dueSoon = wsas
    .filter((wsa) => wsa.cap_due_date && wsa.cap_status !== "completed" && wsa.cap_status !== "none" && wsa.cap_due_date >= today && wsa.cap_due_date <= soonLimit)
    .sort((a, b) => (a.cap_due_date ?? "").localeCompare(b.cap_due_date ?? ""));
  const highRiskWithoutPlan = wsas
    .filter((wsa) => wsa.risk_level === "high" && wsa.cap_status === "none")
    .sort((a, b) => (a.blue_drop_score ?? 101) - (b.blue_drop_score ?? 101) || a.name.localeCompare(b.name));

  const byStatus: Record<CaseStatus, number> = { open: 0, in_review: 0, resolved: 0 };
  const byIssue: Record<IssueType, number> = { leak: 0, outage: 0, quality: 0, billing: 0 };
  for (const report of reportsInPeriod) {
    byStatus[report.case_status] += 1;
    byIssue[report.issue_type] += 1;
  }
  const daysBetween = (from: string, to: string) => (new Date(to).getTime() - new Date(from).getTime()) / MS_PER_DAY;
  const avgResolve = average(reportsInPeriod.flatMap((report) => (report.resolved_at ? [daysBetween(report.created_at, report.resolved_at)] : [])));
  const avgReview = average(reportsInPeriod.flatMap((report) => (report.reviewed_at ? [daysBetween(report.created_at, report.reviewed_at)] : [])));

  // the backlog is every unresolved report, whatever its age, so a report from before the period still shows up
  const backlog = scopedReports.filter(isUnresolved);
  const counts = Object.fromEntries(AGE_LEVELS.map((level) => [level.id, 0])) as Record<AgeLevelId, number>;
  for (const report of backlog) counts[ageLevel(ageInDays(report.created_at, now)).id] += 1;
  const escalated = backlog.filter((report) => ageInDays(report.created_at, now) >= 14).length;

  const alerts = input.alerts.filter((alert) => wsaIds.has(alert.wsa_id));
  const unacknowledged = alerts.filter((alert) => !alert.acknowledged_at);
  const alertsByType: Partial<Record<AlertType, number>> = {};
  for (const alert of alerts) alertsByType[alert.alert_type] = (alertsByType[alert.alert_type] ?? 0) + 1;

  const authorities = {
    total: wsas.length,
    high: countRisk("high", wsas),
    medium: countRisk("medium", wsas),
    low: countRisk("low", wsas),
    avgBlueDrop: (() => {
      const avg = blueDrop(wsas);
      return avg === null ? null : round1(avg);
    })(),
  };

  const findings: string[] = [];
  const where = scope.province ? ` in ${scope.province}` : "";
  if (authorities.total > 0) {
    findings.push(`${authorities.high} of ${authorities.total} authorities${where} are rated high risk (${Math.round((authorities.high / authorities.total) * 100)}%).`);
  }
  const many = (count: number, one: string, other: string) => (count === 1 ? one : other);
  if (backlog.length === 0) {
    findings.push("No citizen reports are waiting for action.");
  } else if (backlog.length === 1) {
    findings.push(escalated > 0 ? "1 citizen report is unresolved and has waited 14 days or more." : "1 citizen report is unresolved, for less than 14 days.");
  } else {
    findings.push(
      escalated > 0
        ? `${backlog.length} citizen reports are unresolved, and ${escalated} of them ${many(escalated, "has", "have")} waited 14 days or more.`
        : `${backlog.length} citizen reports are unresolved, none for 14 days or more.`,
    );
  }
  if (avgResolve !== null) findings.push(`Resolved reports took ${round1(avgResolve)} days on average to close.`);
  findings.push(
    overdueCaps.length > 0
      ? `${overdueCaps.length} corrective action ${many(overdueCaps.length, "plan is", "plans are")} past ${many(overdueCaps.length, "its", "their")} due date.`
      : "No corrective action plan is past its due date.",
  );
  if (highRiskWithoutPlan.length > 0) {
    findings.push(`${highRiskWithoutPlan.length} high-risk ${many(highRiskWithoutPlan.length, "authority has", "authorities have")} no corrective action plan.`);
  }
  if (unacknowledged.length > 0) findings.push(`${unacknowledged.length} ${many(unacknowledged.length, "alert is", "alerts are")} waiting to be acknowledged.`);

  return {
    scope,
    authorities,
    byProvince,
    topRisk: [...wsas]
      .sort((a, b) => riskRank[a.risk_level] - riskRank[b.risk_level] || (a.blue_drop_score ?? 101) - (b.blue_drop_score ?? 101) || a.name.localeCompare(b.name))
      .slice(0, 10),
    cap: { none: capCount("none"), submitted: capCount("submitted"), in_progress: capCount("in_progress"), completed: capCount("completed"), overdue: overdueCaps, dueSoon, highRiskWithoutPlan },
    reports: {
      inPeriod: reportsInPeriod.length,
      byStatus,
      byIssue,
      avgDaysToResolve: avgResolve === null ? null : round1(avgResolve),
      avgDaysToReview: avgReview === null ? null : round1(avgReview),
    },
    ageing: { unresolved: backlog.length, counts, escalated, oldest: sortOldestFirst(backlog).slice(0, 15) },
    alerts: {
      total: alerts.length,
      unacknowledged: unacknowledged.length,
      byType: alertsByType,
      latestUnacknowledged: [...unacknowledged].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 6),
    },
    findings,
  };
}
