import { apiClient } from "@/api/client";

export interface AITextResponse {
  content: string;
}

export interface AIRecommendationsResponse {
  content: string;
  items: string[];
}

export async function fetchAiDigest() {
  const { data } = await apiClient.get<AITextResponse>("/ai/digest");
  return data;
}

export async function fetchWsaSummary(wsaId: string) {
  const { data } = await apiClient.get<AITextResponse>(`/ai/wsa/${wsaId}/summary`);
  return data;
}

export async function fetchWsaRecommendations(wsaId: string) {
  const { data } = await apiClient.get<AIRecommendationsResponse>(`/ai/wsa/${wsaId}/recommendations`);
  return data;
}

export async function generateReportComment(reportId: string) {
  const { data } = await apiClient.get<AITextResponse>(`/ai/reports/${reportId}/comment`);
  return data;
}

export async function fetchRiskExplanation(wsaId: string) {
  const { data } = await apiClient.get<AITextResponse>(`/ai/wsa/${wsaId}/risk-explanation`);
  return data;
}

export async function fetchWsaComparison(wsaId: string) {
  const { data } = await apiClient.get<AITextResponse>(`/ai/wsa/${wsaId}/comparison`);
  return data;
}

export async function fetchProvinceDigest(province: string) {
  const { data } = await apiClient.get<AITextResponse>(`/ai/province/${encodeURIComponent(province)}/digest`);
  return data;
}

export async function fetchReportsSummary(wsaId: string) {
  const { data } = await apiClient.get<AITextResponse>(`/ai/wsa/${wsaId}/reports-summary`);
  return data;
}

export async function fetchWsaReportContext(wsaId: string, issueType: string) {
  const { data } = await apiClient.get<AITextResponse>(`/ai/wsa/${wsaId}/report-context`, {
    params: { issue_type: issueType },
  });
  return data;
}
