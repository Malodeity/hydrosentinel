import { apiClient } from "@/api/client";

export type CapStatus = "none" | "submitted" | "in_progress" | "completed";
export type RiskLevel = "low" | "medium" | "high";

export interface WSA {
  id: string;
  name: string;
  province: string;
  blue_drop_score: number | null;
  nrw_percent: number | null;
  cap_status: CapStatus;
  maint_pct: number | null;
  risk_level: RiskLevel;
  summary?: string | null;
  lat: number;
  lng: number;
  created_at: string;
  updated_at: string;
}

export interface RiskScore {
  wsa_id: string;
  name: string;
  risk_level: RiskLevel;
}

export async function fetchWsas() {
  const { data } = await apiClient.get<WSA[]>("/wsa");
  return data;
}

export async function fetchWsa(wsaId: string) {
  const { data } = await apiClient.get<WSA>(`/wsa/${wsaId}`);
  return data;
}

export async function updateWsaCapStatus(wsaId: string, capStatus: CapStatus) {
  const { data } = await apiClient.patch<WSA>(`/wsa/${wsaId}`, { cap_status: capStatus });
  return data;
}

export async function fetchRiskScores() {
  const { data } = await apiClient.get<RiskScore[]>("/risk/scores");
  return data;
}
