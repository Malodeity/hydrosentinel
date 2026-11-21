// Contractors and repair tickets API (backend/app/routes/assignments.py, plus GET /ai/reports/{id}/work-order).

import { apiClient } from "@/api/client";
import type { IssueType } from "@/api/reports";

export type TicketStatus = "assigned" | "accepted" | "in_progress" | "fixed" | "sent_back" | "rejected" | "cancelled" | "closed";

export interface Coverage {
  wsa_id: string;
  wsa_name: string;
  issue_types: IssueType[];
}

export interface Contractor {
  id: string;
  name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  coverage: Coverage[];
  open_tickets: number;
}

export interface TicketSummary {
  id: string;
  status: TicketStatus;
  contractor_id: string;
  contractor_name: string;
  due_at: string | null;
  overdue: boolean;
  contractor_note: string | null;
  rejected_reason: string | null;
}

export interface Ticket extends TicketSummary {
  report_id: string;
  wsa_id: string;
  wsa_name: string;
  reference_code: string;
  issue_type: IssueType;
  description: string | null;
  lat: number;
  lng: number;
  photo_urls: string[];
  repair_photo_urls: string[]; // the contractor's "after" photos
  instructions: string | null;
  admin_note: string | null;
  created_at: string;
  accepted_at: string | null;
  started_at: string | null;
  fixed_at: string | null;
  closed_at: string | null;
}

export interface ContractorPerformance {
  contractor_id: string;
  name: string;
  total: number;
  open: number;
  overdue: number;
  fixed: number;
  rejected: number;
  fixed_on_time_pct: number | null;
  avg_hours_to_fix: number | null;
}

export interface AppNotification {
  id: string;
  title: string;
  body: string | null;
  assignment_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface WorkOrderDraft {
  instructions: string;
  suggested_contractor_id: string | null;
  suggested_contractor_name: string | null;
  reason: string;
  due_at: string;
}

export interface ContractorInput {
  name: string;
  contact_name?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active: boolean;
}

export type TicketAction = "accept" | "reject" | "start" | "fix";
export type ReviewAction = "verify" | "send_back" | "cancel";

// ---- admin ----
export const fetchContractors = async () => (await apiClient.get<Contractor[]>("/contractors")).data;
export const createContractor = async (input: ContractorInput) => (await apiClient.post<Contractor>("/contractors", input)).data;
export const updateContractor = async (id: string, input: ContractorInput) => (await apiClient.patch<Contractor>(`/contractors/${id}`, input)).data;
export const setCoverage = async (id: string, wsaId: string, issueTypes: IssueType[]) =>
  (await apiClient.put<Contractor>(`/contractors/${id}/coverage`, { wsa_id: wsaId, issue_types: issueTypes })).data;
export const removeCoverage = async (id: string, wsaId: string) => (await apiClient.delete<Contractor>(`/contractors/${id}/coverage/${wsaId}`)).data;
export const fetchContractorPerformance = async () => (await apiClient.get<ContractorPerformance[]>("/contractors/performance")).data;
export const fetchAssignments = async () => (await apiClient.get<Ticket[]>("/assignments")).data;
export const fetchReportAssignments = async (reportId: string) => (await apiClient.get<Ticket[]>(`/reports/${reportId}/assignments`)).data;
export const assignReport = async (reportId: string, body: { contractor_id: string; instructions?: string; due_at?: string | null }) =>
  (await apiClient.post<Ticket>(`/reports/${reportId}/assign`, body)).data;
export const assignReportsBulk = async (body: { report_ids: string[]; contractor_id: string; instructions?: string; due_at?: string | null }) =>
  (await apiClient.post<Ticket[]>("/reports/assign-bulk", body)).data;
export const reviewTicket = async (id: string, action: ReviewAction, note?: string) =>
  (await apiClient.patch<Ticket>(`/assignments/${id}/review`, { action, note })).data;
export const fetchWorkOrderDraft = async (reportId: string) => (await apiClient.get<WorkOrderDraft>(`/ai/reports/${reportId}/work-order`)).data;

// ---- contractor ----
export const fetchMyTickets = async () => (await apiClient.get<Ticket[]>("/my/tickets")).data;
export const actOnTicket = async (id: string, action: TicketAction, note?: string) =>
  (await apiClient.patch<Ticket>(`/my/tickets/${id}`, { action, note })).data;

export const uploadRepairPhotos = async (id: string, files: File[]) => {
  const form = new FormData();
  files.forEach((file) => form.append("photos", file));
  return (await apiClient.post<Ticket>(`/my/tickets/${id}/photos`, form)).data;
};

// ---- contractor AI helpers (only drafts: the contractor checks and decides) ----
export interface JobBrief {
  summary: string;
  steps: string[];
  safety: string[];
  ai: boolean; // false = a plain standard checklist because the AI was unavailable
}
export const fetchJobBrief = async (ticketId: string) => (await apiClient.get<JobBrief>(`/ai/my/tickets/${ticketId}/brief`)).data;
export const draftFixNote = async (ticketId: string, rough: string) =>
  (await apiClient.post<{ note: string; ai: boolean }>(`/ai/my/tickets/${ticketId}/fix-note`, { rough })).data;
export const fetchMySummary = async (days: 7 | 30 | 90) => (await apiClient.get<{ text: string; days: number; ai: boolean }>("/ai/my/summary", { params: { days } })).data;

// ---- everyone ----
export const fetchNotifications = async () => (await apiClient.get<AppNotification[]>("/notifications")).data;
export const markNotificationRead = async (id: string) => (await apiClient.patch<AppNotification>(`/notifications/${id}/read`)).data;
export const markAllNotificationsRead = async () => {
  await apiClient.post("/notifications/read-all");
};

// the readable reason from a failed call (FastAPI sends {detail: "..."} or a list for bulk problems)
export function apiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => (typeof item === "string" ? item : (item as { reason?: string; msg?: string }).reason ?? (item as { msg?: string }).msg ?? "")).filter(Boolean).join("; ") || fallback;
  }
  return fallback;
}
