import type { Alert } from "@/api/alerts";
import type { CitizenReport } from "@/api/reports";

// matches the backend's geo-cluster window (app/alert_helpers.py _CLUSTER_WINDOW_HOURS)
export const CLUSTER_WINDOW_HOURS = 6;

// "3 leak reports within 2.0km of each other ..." -> "leak"
export function clusterIssueType(message: string): string | null {
  return message.match(/^\d+\s+(\w+)\s+reports?\b/)?.[1] ?? null;
}

// The reports that caused a "localized incident" alert: same authority, same issue, in the 6 hours before the alert was raised.
// The window is measured from when the ALERT was raised, not from now, so the map still works days later.
export function clusterReportsForAlert(alert: Pick<Alert, "wsa_id" | "created_at" | "message">, reports: CitizenReport[]): CitizenReport[] {
  const raisedAt = new Date(alert.created_at).getTime();
  const issue = clusterIssueType(alert.message);
  return reports.filter((report) => {
    const created = new Date(report.created_at).getTime();
    return (
      report.wsa_id === alert.wsa_id &&
      (!issue || report.issue_type === issue) &&
      created <= raisedAt + 60_000 &&
      created >= raisedAt - CLUSTER_WINDOW_HOURS * 3_600_000
    );
  });
}

export function reportBounds(reports: Pick<CitizenReport, "lat" | "lng">[]): [[number, number], [number, number]] {
  const lats = reports.map((report) => report.lat);
  const lngs = reports.map((report) => report.lng);
  return [
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)],
  ];
}
