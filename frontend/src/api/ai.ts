// Calls to the AI endpoints (backend/app/routes/ai.py). Each function is one endpoint; the interfaces describe what comes back.
// Admin-only ones (briefing, question box, CAP draft, photo check...) count against the hourly allowance shown on the AI assistant tab.

import { apiClient } from "@/api/client";
import type { PhotoAnalysis } from "@/api/reports";
import type { MapBounds } from "@/lib/mapBounds";

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

// caseStatus is the status the admin has selected, saved or not, so the note matches the change they are about to make
export async function generateReportComment(reportId: string, caseStatus?: "open" | "in_review" | "resolved") {
  const { data } = await apiClient.get<AITextResponse>(`/ai/reports/${reportId}/comment`, { params: caseStatus ? { case_status: caseStatus } : {} });
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

export interface MapViewStats {
  total: number;
  high: number;
  medium: number;
  low: number;
  open_reports: number;
}

export interface MapViewSummary {
  stats: MapViewStats;
  content: string | null;
}

export async function fetchMapViewSummary(bounds: MapBounds) {
  const { data } = await apiClient.get<MapViewSummary>("/ai/map-view-summary", { params: bounds });
  return data;
}

// admin only: asks GPT-4o to look at one of the report's photos (it costs an OpenAI call and counts towards the hourly AI limit)
export async function analyzeReportPhoto(reportId: string, photoIndex = 0) {
  const { data } = await apiClient.post<PhotoAnalysis>(`/ai/reports/${reportId}/analyze-photo`, null, { params: { photo_index: photoIndex } });
  return data;
}

// admin only: a short AI explanation of why an authority is on the "trending toward higher risk" list (one OpenAI call)
export async function fetchTrendExplanation(wsaId: string) {
  const { data } = await apiClient.get<AITextResponse>(`/ai/wsa/${wsaId}/trend-explanation`);
  return data;
}

// how much of this admin's 20-per-hour AI allowance is used (reading it costs nothing)
export interface AiUsage {
  used: number;
  limit: number;
  resets_in_minutes: number;
}

export async function fetchAiUsage() {
  const { data } = await apiClient.get<AiUsage>("/ai/usage");
  return data;
}

// a short start-of-day note. `facts` are the database numbers it was written from, so they can be checked against the text
export interface AdminBriefing {
  content: string;
  facts: Record<string, number>;
}

export async function fetchAdminBriefing() {
  const { data } = await apiClient.get<AdminBriefing>("/ai/admin-briefing");
  return data;
}
