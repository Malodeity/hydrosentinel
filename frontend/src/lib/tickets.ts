// Plain rules for repair tickets on screen: labels, colours, which button a contractor sees at each step, due-time wording. Mirrors the server rules
// in backend/app/assignment_helpers.py (the server is the one that enforces them).

import type { TicketAction, TicketStatus } from "@/api/assignments";

export const TICKET_LABEL: Record<TicketStatus, string> = {
  assigned: "New",
  accepted: "Accepted",
  in_progress: "In progress",
  fixed: "Fixed, awaiting check",
  sent_back: "Sent back",
  rejected: "Rejected",
  cancelled: "Cancelled",
  closed: "Verified",
};

export const TICKET_DOT: Record<TicketStatus, string> = {
  assigned: "#f59e0b",
  accepted: "#0ea5e9",
  in_progress: "#0ea5e9",
  fixed: "#8b5cf6",
  sent_back: "#e11d48",
  rejected: "#94a3b8",
  cancelled: "#94a3b8",
  closed: "#16a34a",
};

const ACTIVE: TicketStatus[] = ["assigned", "accepted", "in_progress", "sent_back", "fixed"];

export const isActiveTicket = (status: TicketStatus) => ACTIVE.includes(status);

// what the contractor can do next from each status, in the order the buttons are shown
export function contractorActions(status: TicketStatus): TicketAction[] {
  switch (status) {
    case "assigned":
      return ["accept", "reject"];
    case "accepted":
      return ["start", "fix"];
    case "in_progress":
    case "sent_back":
      return ["fix"];
    default:
      return [];
  }
}

// actions that need the contractor to write something first (a reason, or what was done)
export const ACTION_NEEDS_NOTE: Record<TicketAction, boolean> = { accept: false, start: false, reject: true, fix: true };

export const ACTION_LABEL: Record<TicketAction, string> = { accept: "Accept", reject: "Reject", start: "Start work", fix: "Mark fixed" };

// "due in 5 h", "due in 2 days", "3 h overdue" for a ticket still with the contractor
export function describeDue(dueAt: string | null, now: Date = new Date()): { text: string; overdue: boolean } {
  if (!dueAt) return { text: "No due time", overdue: false };
  const hours = (new Date(dueAt).getTime() - now.getTime()) / 3_600_000;
  const abs = Math.abs(hours);
  const span = abs < 1 ? "under an hour" : abs < 48 ? `${Math.round(abs)} h` : `${Math.round(abs / 24)} days`;
  return hours < 0 ? { text: `${span} overdue`, overdue: true } : { text: `due in ${span}`, overdue: false };
}

// "leak,outage" style lists to "Leak, outage"
export const issueList = (types: string[]) => (types.length ? types.map((t) => t[0].toUpperCase() + t.slice(1)).join(", ") : "None");
