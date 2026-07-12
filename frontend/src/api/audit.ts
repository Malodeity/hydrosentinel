import { apiClient } from "@/api/client";

export type AuditAction =
  | "cap_status_updated"
  | "report_status_updated"
  | "report_comment_updated"
  | "risk_score_run"
  | "wsa_updated"
  | "user_created"
  | "summary_generated";

export interface AuditLogEntry {
  id: string;
  user_id: string;
  action: AuditAction;
  table_name: string;
  record_id: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export async function fetchAuditLog(limit = 200): Promise<AuditLogEntry[]> {
  const { data } = await apiClient.get<AuditLogEntry[]>("/audit-log", {
    params: { limit },
  });
  return data;
}
