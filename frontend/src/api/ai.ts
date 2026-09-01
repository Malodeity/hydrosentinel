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

export interface CapDraftItem {
  action: string;
  priority: "high" | "medium" | "low";
  suggested_due_in_days: number | null;
  justification: string;
}

export interface CapDraftResponse {
  items: CapDraftItem[];
}

export async function fetchCapDraft(wsaId: string) {
  const { data } = await apiClient.get<CapDraftResponse>(`/ai/wsa/${wsaId}/cap-draft`);
  return data;
}

export interface RegulatorySource {
  source: string;
  page: number;
  score: number;
}

export interface RegulatoryContextResponse {
  answer: string;
  sources: RegulatorySource[];
}

export async function fetchRegulatoryContext(query: string) {
  const { data } = await apiClient.get<RegulatoryContextResponse>("/ai/regulatory-context", {
    params: { query },
  });
  return data;
}

export interface AIQueryToolCall {
  tool: string;
  arguments: Record<string, unknown>;
  result: string;
}

export interface AIQueryResponse {
  answer: string;
  tool_calls: AIQueryToolCall[];
}

export async function askAiQuery(question: string) {
  const { data } = await apiClient.post<AIQueryResponse>("/ai/query", { question });
  return data;
}

export interface RiskTrajectory {
  wsa_id: string;
  name: string;
  trend: "insufficient_data" | "improving" | "stable" | "worsening";
  current_probability: number | null;
  current_risk_level: "low" | "medium" | "high" | null;
  projected_probability: number | null;
  projected_risk_level: "low" | "medium" | "high" | null;
  crosses_tier: boolean;
  sample_size: number;
}

export async function fetchTrendingWsas() {
  const { data } = await apiClient.get<RiskTrajectory[]>("/risk/trending");
  return data;
}
