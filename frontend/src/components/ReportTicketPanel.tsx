// "Repair ticket" box inside the selected report on the Citizen reports tab: who has it, the ticket's status, the assign form (with an AI draft),
// and the check-the-work buttons (verify / send back / cancel). Changes go through onChanged so the page reloads its numbers and audit log.

import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

import {
  apiErrorMessage,
  assignReport,
  fetchContractors,
  fetchReportAssignments,
  fetchWorkOrderDraft,
  reviewTicket,
  type Contractor,
  type ReviewAction,
  type Ticket,
} from "@/api/assignments";
import type { CitizenReport } from "@/api/reports";
import { TicketStatus } from "@/components/TicketStatus";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { describeDue, isActiveTicket } from "@/lib/tickets";

interface Props {
  report: CitizenReport;
  onChanged: () => void | Promise<void>;
}

// a datetime-local value ("2026-11-09T14:30") to an ISO time, or null when empty
const toIso = (value: string) => (value ? new Date(value).toISOString() : null);

export function ReportTicketPanel({ report, onChanged }: Props) {
  const [history, setHistory] = useState<Ticket[]>([]);
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [contractorId, setContractorId] = useState("");
  const [instructions, setInstructions] = useState("");
  const [dueLocal, setDueLocal] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aiReason, setAiReason] = useState<string | null>(null);

  const active = history.find((ticket) => isActiveTicket(ticket.status)) ?? null;
  const last = history[0] ?? null;
  const resolved = report.case_status === "resolved";

  const reload = async () => {
    try {
      const [tickets, people] = await Promise.all([fetchReportAssignments(report.id), fetchContractors()]);
      setHistory(tickets);
      setContractors(people);
    } catch {
      setError("Could not load the repair ticket.");
    }
  };

  // a different report was selected: forget the form and load that report's tickets
  useEffect(() => {
    setShowForm(false);
    setContractorId("");
    setInstructions("");
    setDueLocal("");
    setReviewNote("");
    setMessage(null);
    setError(null);
    setAiReason(null);
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report.id]);

  // only contractors that are switched on and set up for this authority and issue type may be offered
  const eligible = useMemo(
    () => contractors.filter((c) => c.is_active && c.coverage.some((row) => row.wsa_id === report.wsa_id && row.issue_types.includes(report.issue_type))),
    [contractors, report.issue_type, report.wsa_id],
  );

  const run = async (label: string, action: () => Promise<unknown>, done: string) => {
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(done);
      await reload();
      await onChanged();
    } catch (failure) {
      setError(apiErrorMessage(failure, "That did not work. Try again."));
    } finally {
      setBusy(null);
    }
  };

  const draftWithAi = async () => {
    setBusy("draft");
    setError(null);
    try {
      const draft = await fetchWorkOrderDraft(report.id);
      setInstructions(draft.instructions);
      setAiReason(draft.reason);
      if (draft.suggested_contractor_id && eligible.some((c) => c.id === draft.suggested_contractor_id)) setContractorId(draft.suggested_contractor_id);
    } catch (failure) {
      setError(apiErrorMessage(failure, "The AI draft is not available right now. You can still write the instructions yourself."));
    } finally {
      setBusy(null);
    }
  };

  const review = (action: ReviewAction, done: string) => {
    if (!active) return;
    if (action === "send_back" && !reviewNote.trim()) {
      setError("Tell the contractor what is still wrong before sending it back.");
      return;
    }
    void run(action, () => reviewTicket(active.id, action, reviewNote.trim() || undefined), done).then(() => setReviewNote(""));
  };

  return (
    <div className="space-y-3 rounded-2xl border border-border/70 bg-secondary/20 p-4" aria-label="Repair ticket">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold">Repair ticket</p>
        {last ? <TicketStatus status={last.status} overdue={last.overdue} /> : <span className="text-xs text-muted-foreground">Not assigned</span>}
      </div>

      {active ? (
        <div className="space-y-2 text-sm">
          <p>
            <span className="font-medium">{active.contractor_name}</span> · {describeDue(active.due_at).text}
          </p>
          {active.instructions ? <p className="text-muted-foreground">Instructions: {active.instructions}</p> : null}
          {active.status === "sent_back" && active.admin_note ? <p className="text-rose-700">Sent back: {active.admin_note}</p> : null}
          {active.contractor_note ? (
            <p className="rounded-xl bg-background p-2">
              <span className="font-medium">Contractor says:</span> {active.contractor_note}
            </p>
          ) : null}
        </div>
      ) : last && (last.status === "rejected" || last.status === "cancelled") ? (
        <p className="text-sm text-muted-foreground">
          {last.contractor_name} {last.status === "rejected" ? `rejected it: ${last.rejected_reason ?? "no reason given"}` : "was taken off this ticket."}
        </p>
      ) : null}

      {active?.status === "fixed" ? (
        <div className="space-y-2 border-t border-border/60 pt-3">
          <p className="text-sm font-medium">The contractor says this is fixed. Check it on site, then:</p>
          <Textarea className="min-h-[64px]" placeholder="Note (required to send it back)" value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={busy !== null} onClick={() => review("verify", "Verified. The report is now resolved.")}>
              {busy === "verify" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Verify and resolve
            </Button>
            <Button size="sm" variant="outline" disabled={busy !== null} onClick={() => review("send_back", "Sent back to the contractor.")}>
              Send back
            </Button>
          </div>
        </div>
      ) : null}

      {active && active.status !== "fixed" ? (
        <Button size="sm" variant="ghost" disabled={busy !== null} onClick={() => review("cancel", "Ticket cancelled.")}>
          Cancel ticket
        </Button>
      ) : null}

      {!resolved && !showForm ? (
        <Button size="sm" variant={active ? "outline" : "default"} onClick={() => setShowForm(true)}>
          {active ? "Reassign to another contractor" : "Assign to a contractor"}
        </Button>
      ) : null}

      {!resolved && showForm ? (
        <div className="space-y-3 border-t border-border/60 pt-3">
          {eligible.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No active contractor is set up for {report.issue_type} reports in this authority. Add one on the Contractors tab.
            </p>
          ) : (
            <>
              <div className="space-y-1">
                <label className="text-sm font-medium">Contractor</label>
                <Select value={contractorId} onValueChange={setContractorId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a contractor" />
                  </SelectTrigger>
                  <SelectContent>
                    {eligible.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.name} ({c.open_tickets} open)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Instructions</label>
                  <Button type="button" size="sm" variant="outline" disabled={busy !== null} onClick={() => void draftWithAi()}>
                    {busy === "draft" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Draft with AI
                  </Button>
                </div>
                <Textarea className="min-h-[88px]" placeholder="What the contractor should do first" value={instructions} onChange={(event) => setInstructions(event.target.value)} />
                {aiReason ? <p className="text-xs text-muted-foreground">AI draft. Please check it. Suggested contractor: {aiReason}</p> : null}
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor={`due-${report.id}`}>
                  Due (optional, leave empty for the standard time for this issue)
                </label>
                <input
                  id={`due-${report.id}`}
                  type="datetime-local"
                  className="flex h-10 w-full rounded-xl border border-input bg-background px-3 text-sm"
                  value={dueLocal}
                  onChange={(event) => setDueLocal(event.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  disabled={!contractorId || busy !== null}
                  onClick={() =>
                    void run(
                      "assign",
                      () => assignReport(report.id, { contractor_id: contractorId, instructions: instructions.trim() || undefined, due_at: toIso(dueLocal) }),
                      "Ticket sent to the contractor.",
                    ).then(() => setShowForm(false))
                  }
                >
                  {busy === "assign" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  {active ? "Reassign" : "Assign"}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>
                  Close
                </Button>
              </div>
            </>
          )}
        </div>
      ) : null}

      {message ? <p className="text-sm text-emerald-700">{message}</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {history.length > 1 ? (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer">Earlier tickets ({history.length - (active ? 1 : 0)})</summary>
          <ul className="mt-1 space-y-1">
            {history
              .filter((ticket) => ticket.id !== active?.id)
              .map((ticket) => (
                <li key={ticket.id}>
                  {ticket.contractor_name} · {ticket.status.replace("_", " ")} · {new Date(ticket.created_at).toLocaleDateString()}
                </li>
              ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
