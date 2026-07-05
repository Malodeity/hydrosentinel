import { apiClient } from "./client";

export type AlertType = "risk_level_high" | "risk_level_increased" | "report_volume_spike" | "cap_overdue";

export interface Alert {
  id: string;
  wsa_id: string;
  wsa_name: string;
  alert_type: AlertType;
  message: string;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

export async function fetchAlerts(unacknowledgedOnly = false): Promise<Alert[]> {
  const { data } = await apiClient.get<Alert[]>("/alerts", {
    params: unacknowledgedOnly ? { unacknowledged_only: true } : {},
  });
  return data;
}

export async function acknowledgeAlert(alertId: string): Promise<Alert> {
  const { data } = await apiClient.patch<Alert>(`/alerts/${alertId}/acknowledge`);
  return data;
}
