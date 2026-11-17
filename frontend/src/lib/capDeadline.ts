import type { CapStatus } from "@/api/wsa";

export type DeadlineTone = "overdue" | "soon" | "ok" | "none";

const DAY_MS = 86400000;
const parseDay = (iso: string) => {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
};
const fmt = (iso: string) => parseDay(iso).toLocaleDateString("en-ZA", { day: "numeric", month: "short", year: "numeric" });

// Turns a CAP's due date into words an official can act on ("12 Dec 2026 · in 36 days"), instead of a bare date.
// A completed plan is never overdue; a plan that was never submitted has no deadline to speak of.
export function describeDeadline(status: CapStatus, dueDate: string | null, today: Date = new Date()): { tone: DeadlineTone; text: string } {
  if (status === "none" && !dueDate) return { tone: "none", text: "No plan submitted" };
  if (!dueDate) return { tone: "none", text: "No due date set" };
  if (status === "completed") return { tone: "ok", text: `Done · was due ${fmt(dueDate)}` };
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((parseDay(dueDate).getTime() - startOfToday.getTime()) / DAY_MS);
  if (days < 0) return { tone: "overdue", text: `${fmt(dueDate)} · ${-days} day${days === -1 ? "" : "s"} overdue` };
  if (days === 0) return { tone: "soon", text: `${fmt(dueDate)} · due today` };
  return { tone: days <= 14 ? "soon" : "ok", text: `${fmt(dueDate)} · in ${days} day${days === 1 ? "" : "s"}` };
}
