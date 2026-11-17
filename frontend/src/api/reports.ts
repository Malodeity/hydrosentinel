import { apiClient } from "@/api/client";
import type { TicketSummary } from "@/api/assignments";

export type IssueType = "leak" | "outage" | "quality" | "billing";
export type CaseStatus = "open" | "in_review" | "resolved";

// what an admin gets back after asking the AI to look at a report's photo. the verdict is decided by the server
export interface PhotoAnalysis {
  issue_type: "leak" | "quality" | "outage" | "not_water_related" | "unclear";
  severity: "low" | "medium" | "high";
  confidence: "low" | "medium" | "high";
  summary: string;
  verdict: "matches" | "mismatch" | "inconclusive";
  photo: string;
  analysed_at: string;
}

export interface CitizenReport {
  id: string;
  wsa_id: string;
  issue_type: IssueType;
  description: string | null;
  reference_code: string;
  case_status: CaseStatus;
  admin_comment: string | null;
  reviewed_by: string | null;
  resolved_by: string | null;
  reviewed_at: string | null;
  resolved_at: string | null;
  lat: number;
  lng: number;
  created_at: string;
  photo_urls: string[];
  photo_analysis?: PhotoAnalysis | null; // admin view only; the public tracking page never returns it
  assignment?: TicketSummary | null; // admin view only: the newest repair ticket on this report
}

export interface CreateCitizenReportPayload {
  wsa_id: string;
  issue_type: IssueType;
  description: string;
  lat: number;
  lng: number;
}

// a report with photos has to be sent as multipart form data (not json), so the fields and files go into a FormData
export async function createCitizenReport(payload: CreateCitizenReportPayload, photos: File[] = []) {
  const formData = new FormData();
  formData.append("wsa_id", payload.wsa_id);
  formData.append("issue_type", payload.issue_type);
  formData.append("description", payload.description);
  formData.append("lat", String(payload.lat));
  formData.append("lng", String(payload.lng));
  photos.forEach((photo) => formData.append("photos", photo));

  const { data } = await apiClient.post<CitizenReport>("/reports", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return data;
}

// admin only: the token interceptor adds the login, and the backend answers 401 or 403 for anyone else
export async function fetchCitizenReports() {
  const { data } = await apiClient.get<CitizenReport[]>("/reports");
  return data;
}

export async function updateCitizenReport(reportId: string, payload: { case_status: CaseStatus; admin_comment: string }) {
  const { data } = await apiClient.patch<CitizenReport>(`/reports/${reportId}`, payload);
  return data;
}

export interface CitizenReportTrackStatus {
  reference_code: string;
  issue_type: IssueType;
  case_status: CaseStatus;
  admin_comment: string | null;
  created_at: string;
  repair_status?: "assigned" | "in_progress" | "awaiting_check" | null; // progress only: never the company or its contact details
  repair_due_at?: string | null;
}

// public: look up a report's status with its reference code
export async function trackCitizenReport(referenceCode: string) {
  const { data } = await apiClient.get<CitizenReportTrackStatus>(`/reports/track/${referenceCode}`);
  return data;
}

// downloads the csv as a blob, then clicks a temporary link so the browser saves it as a file
export async function downloadReportsCsv() {
  const { data } = await apiClient.get("/reports/export.csv", { responseType: "blob" });
  const url = URL.createObjectURL(new Blob([data], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "reports_export.csv";
  link.click();
  URL.revokeObjectURL(url);
}

// public, aggregate-only numbers for the dashboard (no report text, locations or codes)
export interface PublicReportStats {
  received_7d: number;
  total: number;
  open: number;
  resolved: number;
  median_days_to_resolve: number | null;
  resolved_sample: number;
  by_wsa: Record<string, { open: number; resolved: number }>;
}

export async function fetchPublicReportStats() {
  const { data } = await apiClient.get<PublicReportStats>("/reports/public-stats");
  return data;
}
