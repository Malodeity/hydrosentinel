// The numbers on a contractor's own dashboard, worked out from its list of tickets: how many are open or need action, and, for the last week, month
// or three months, how many came in, how many were fixed, how long a fix took and how many were fixed on time. Pure functions so they can be tested.

import type { Ticket } from "@/api/assignments";

export type Period = "week" | "month" | "quarter";
export const PERIODS: { id: Period; label: string; days: number }[] = [
  { id: "week", label: "Last 7 days", days: 7 },
  { id: "month", label: "Last 30 days", days: 30 },
  { id: "quarter", label: "Last 3 months", days: 90 },
];
const DAY = 86_400_000;
const HOUR = 3_600_000;

// still with the contractor (the authority has not been asked to check it yet)
const WORKING = ["assigned", "accepted", "in_progress", "sent_back"];
export const isWorking = (t: Ticket) => WORKING.includes(t.status);
// a ticket the contractor has to do something about now: a new one to accept or reject, or one the authority sent back
export const needsAction = (t: Ticket) => t.status === "assigned" || t.status === "sent_back";

export const periodDays = (period: Period) => PERIODS.find((p) => p.id === period)!.days;
const since = (period: Period, now: Date) => now.getTime() - periodDays(period) * DAY;
const inPeriod = (iso: string | null, period: Period, now: Date) => iso !== null && new Date(iso).getTime() >= since(period, now) && new Date(iso).getTime() <= now.getTime();

export interface DashboardNumbers {
  open: number;
  needsAction: number;
  overdue: number;
  awaitingCheck: number; // marked fixed, waiting for the authority to verify
  opened: number; // tickets that arrived in the period
  fixed: number; // tickets the contractor marked fixed in the period
  verified: number; // tickets the authority closed in the period
  avgHoursToFix: number | null; // from the ticket arriving to it being marked fixed
  onTimePct: number | null; // share of the fixed ones that were fixed by their due time
}

export function dashboardNumbers(tickets: Ticket[], period: Period, now: Date = new Date()): DashboardNumbers {
  const fixedNow = tickets.filter((t) => inPeriod(t.fixed_at, period, now));
  const hours = fixedNow.map((t) => (new Date(t.fixed_at!).getTime() - new Date(t.created_at).getTime()) / HOUR);
  const withDue = fixedNow.filter((t) => t.due_at);
  return {
    open: tickets.filter(isWorking).length,
    needsAction: tickets.filter(needsAction).length,
    overdue: tickets.filter((t) => isWorking(t) && t.overdue).length,
    awaitingCheck: tickets.filter((t) => t.status === "fixed").length,
    opened: tickets.filter((t) => inPeriod(t.created_at, period, now)).length,
    fixed: fixedNow.length,
    verified: tickets.filter((t) => t.status === "closed" && inPeriod(t.closed_at, period, now)).length,
    avgHoursToFix: hours.length ? hours.reduce((a, b) => a + b, 0) / hours.length : null,
    onTimePct: withDue.length ? Math.round((withDue.filter((t) => new Date(t.fixed_at!) <= new Date(t.due_at!)).length / withDue.length) * 100) : null,
  };
}

// "under 1 h", "6 h", "3 days": a duration in words that is easy to read at a glance
export function formatHours(hours: number | null): string {
  if (hours === null) return "No data yet";
  if (hours < 1) return "under 1 h";
  if (hours < 48) return `${Math.round(hours)} h`;
  return `${Math.round(hours / 24)} days`;
}

export interface Bar {
  label: string;
  opened: number;
  fixed: number;
}

// the period cut into equal slices, oldest first, with how many tickets arrived and how many were marked fixed in each (for the small chart)
export function chartBars(tickets: Ticket[], period: Period, now: Date = new Date()): Bar[] {
  const slices = period === "week" ? 7 : period === "month" ? 6 : 6;
  const sliceMs = (periodDays(period) * DAY) / slices;
  const start = since(period, now);
  return Array.from({ length: slices }, (_, i) => {
    const from = start + i * sliceMs;
    const to = from + sliceMs;
    const within = (iso: string | null) => iso !== null && new Date(iso).getTime() >= from && new Date(iso).getTime() < to + (i === slices - 1 ? 1 : 0);
    return {
      label: new Date(from).toLocaleDateString("en-ZA", { day: "numeric", month: "short" }),
      opened: tickets.filter((t) => within(t.created_at)).length,
      fixed: tickets.filter((t) => within(t.fixed_at)).length,
    };
  });
}

export type ListFilter = "open" | "action" | "overdue" | "awaiting" | "closed" | "other" | "all";

// which tickets a tile or chip shows. "closed" means verified by the authority within the chosen period
export function filterTickets(tickets: Ticket[], filter: ListFilter, period: Period, now: Date = new Date()): Ticket[] {
  const picked = tickets.filter((t) => {
    switch (filter) {
      case "open": return isWorking(t);
      case "action": return needsAction(t);
      case "overdue": return isWorking(t) && t.overdue;
      case "awaiting": return t.status === "fixed";
      case "closed": return t.status === "closed" && inPeriod(t.closed_at, period, now);
      case "other": return t.status === "rejected" || t.status === "cancelled";
      default: return true;
    }
  });
  const key = (t: Ticket) => new Date(filter === "closed" ? t.closed_at ?? t.created_at : t.created_at).getTime();
  return picked.sort((a, b) => key(b) - key(a));
}
