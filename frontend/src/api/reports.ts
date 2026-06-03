import { apiClient } from "@/api/client";

export type IssueType = "leak" | "outage" | "quality" | "billing";
export type CaseStatus = "open" | "in_review" | "resolved";

export interface CitizenReport {
  id: string;
  wsa_id: string;
  issue_type: IssueType;
  description: string | null;
  case_status: CaseStatus;
  admin_comment: string | null;
  lat: number;
  lng: number;
  created_at: string;
  photo_urls: string[];
}

export interface CreateCitizenReportPayload {
  wsa_id: string;
  issue_type: IssueType;
  description: string;
  lat: number;
  lng: number;
}

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

export async function fetchCitizenReports() {
  const { data } = await apiClient.get<CitizenReport[]>("/reports");
  return data;
}

export async function updateCitizenReport(reportId: string, payload: { case_status: CaseStatus; admin_comment: string }) {
  const { data } = await apiClient.patch<CitizenReport>(`/reports/${reportId}`, payload);
  return data;
}
