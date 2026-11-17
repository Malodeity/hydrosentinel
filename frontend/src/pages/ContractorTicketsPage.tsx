// The contractor's own page: only their tickets. Accept or reject a new one, start, and mark fixed with a note. They can never resolve a report:
// the authority checks the work and does that.

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, Loader2 } from "lucide-react";

import { actOnTicket, apiErrorMessage, fetchMyTickets, type Ticket, type TicketAction } from "@/api/assignments";
import { TicketStatus } from "@/components/TicketStatus";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ACTION_LABEL, ACTION_NEEDS_NOTE, contractorActions, describeDue, isActiveTicket } from "@/lib/tickets";

const apiBaseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const photoUrl = (url: string) => (url.startsWith("http") ? url : `${apiBaseUrl}${url}`);

function TicketCard({ ticket, onChanged }: { ticket: Ticket; onChanged: (t: Ticket) => void }) {
  const [pending, setPending] = useState<TicketAction | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const due = describeDue(ticket.due_at);
  const actions = contractorActions(ticket.status);

  const submit = async (action: TicketAction) => {
    setBusy(true);
    setError(null);
    try {
      onChanged(await actOnTicket(ticket.id, action, note.trim() || undefined));
      setPending(null);
      setNote("");
    } catch (failure) {
      setError(apiErrorMessage(failure, "That did not work. Try again."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-lg">
            <span className="capitalize">{ticket.issue_type}</span> · {ticket.wsa_name}
          </CardTitle>
          <TicketStatus status={ticket.status} overdue={ticket.overdue} />
        </div>
        <CardDescription>
          <span className="font-mono">{ticket.reference_code}</span> · {isActiveTicket(ticket.status) && ticket.status !== "fixed" ? due.text : `received ${new Date(ticket.created_at).toLocaleString()}`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {ticket.instructions ? (
          <p>
            <span className="font-medium">Instructions:</span> {ticket.instructions}
          </p>
        ) : null}
        <p>
          <span className="font-medium">Resident says:</span> {ticket.description ?? "No description"}
        </p>
        <p>
          <a
            className="inline-flex items-center gap-1 underline underline-offset-2"
            href={`https://www.openstreetmap.org/?mlat=${ticket.lat}&mlon=${ticket.lng}#map=17/${ticket.lat}/${ticket.lng}`}
            target="_blank"
            rel="noreferrer"
          >
            Open location on a map <ExternalLink className="h-3.5 w-3.5" />
          </a>{" "}
          <span className="text-muted-foreground">
            ({ticket.lat.toFixed(5)}, {ticket.lng.toFixed(5)})
          </span>
        </p>
        {ticket.photo_urls.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {ticket.photo_urls.map((url) => (
              <a key={url} href={photoUrl(url)} target="_blank" rel="noreferrer">
                <img src={photoUrl(url)} alt="Resident's photo" className="h-24 w-32 rounded-xl object-cover" />
              </a>
            ))}
          </div>
        ) : null}
        {ticket.status === "sent_back" && ticket.admin_note ? (
          <p className="rounded-xl border border-rose-200 bg-rose-50 p-2 text-rose-800">
            <span className="font-medium">Sent back by the authority:</span> {ticket.admin_note}
          </p>
        ) : null}
        {ticket.status === "fixed" ? <p className="text-muted-foreground">You marked this fixed ({ticket.contractor_note}). The authority will check it.</p> : null}
        {ticket.status === "rejected" ? <p className="text-muted-foreground">You rejected this: {ticket.rejected_reason}</p> : null}
        {ticket.status === "closed" ? <p className="text-emerald-700">The authority verified this repair. Thank you.</p> : null}
        {ticket.status === "cancelled" ? <p className="text-muted-foreground">The authority cancelled this ticket{ticket.admin_note ? `: ${ticket.admin_note}` : "."}</p> : null}

        {actions.length > 0 ? (
          <div className="space-y-2 border-t border-border/60 pt-3">
            {pending && ACTION_NEEDS_NOTE[pending] ? (
              <>
                <Textarea
                  className="min-h-[72px]"
                  autoFocus
                  placeholder={pending === "reject" ? "Why can you not do this job?" : "What did you do? e.g. replaced 2 m of pipe and tested the pressure"}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
                <div className="flex gap-2">
                  <Button size="sm" disabled={busy || !note.trim()} onClick={() => void submit(pending)}>
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Confirm: {ACTION_LABEL[pending]}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setPending(null)}>
                    Back
                  </Button>
                </div>
              </>
            ) : (
              <div className="flex flex-wrap gap-2">
                {actions.map((action) => (
                  <Button
                    key={action}
                    size="sm"
                    variant={action === "reject" ? "outline" : "default"}
                    disabled={busy}
                    onClick={() => (ACTION_NEEDS_NOTE[action] ? setPending(action) : void submit(action))}
                  >
                    {busy && !ACTION_NEEDS_NOTE[action] ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    {ACTION_LABEL[action]}
                  </Button>
                ))}
              </div>
            )}
          </div>
        ) : null}
        {error ? <p className="text-destructive">{error}</p> : null}
      </CardContent>
    </Card>
  );
}

export function ContractorTicketsPage() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDone, setShowDone] = useState(false);

  const load = useCallback(async () => {
    try {
      setTickets(await fetchMyTickets());
      setError(null);
    } catch (failure) {
      setError(apiErrorMessage(failure, "Could not load your tickets."));
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(timer);
  }, [load]);

  if (error) return <p className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</p>;
  if (!tickets) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading your tickets...
      </p>
    );
  }

  const active = tickets.filter((t) => isActiveTicket(t.status));
  const finished = tickets.filter((t) => !isActiveTicket(t.status));
  const replace = (updated: Ticket) => setTickets((current) => (current ?? []).map((t) => (t.id === updated.id ? updated : t)));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-semibold tracking-tight">My tickets</h2>
        <p className="mt-1 text-sm text-muted-foreground">Repairs the authority has given you. Accept a job, do the work, then mark it fixed with a note on what you did.</p>
      </div>
      {active.length === 0 ? <p className="rounded-2xl border border-border/70 p-6 text-sm text-muted-foreground">No open tickets right now.</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {active.map((t) => (
          <TicketCard key={t.id} ticket={t} onChanged={replace} />
        ))}
      </div>
      {finished.length > 0 ? (
        <div className="space-y-3">
          <Button variant="outline" size="sm" onClick={() => setShowDone((v) => !v)}>
            {showDone ? "Hide" : "Show"} finished tickets ({finished.length})
          </Button>
          {showDone ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {finished.map((t) => (
                <TicketCard key={t.id} ticket={t} onChanged={replace} />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
