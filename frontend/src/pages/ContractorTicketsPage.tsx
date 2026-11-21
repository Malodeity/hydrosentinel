// The contractor's own page: only their tickets. Accept or reject a new one, start, and mark fixed with a note. They can never resolve a report:
// the authority checks the work and does that.

import { useCallback, useEffect, useState } from "react";
import { Camera, CheckCircle2, ClipboardList, ExternalLink, Loader2, Sparkles } from "lucide-react";

import { actOnTicket, apiErrorMessage, draftFixNote, fetchJobBrief, fetchMySummary, fetchMyTickets, uploadRepairPhotos, type JobBrief, type Ticket, type TicketAction } from "@/api/assignments";
import { AITextBlock } from "@/components/AITextBlock";
import { photoUrl, RepairPhotos } from "@/components/RepairPhotos";
import { TicketStatus } from "@/components/TicketStatus";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { chartBars, dashboardNumbers, filterTickets, formatHours, PERIODS, type ListFilter, type Period } from "@/lib/contractorStats";
import { cn } from "@/lib/utils";
import { ACTION_LABEL, ACTION_NEEDS_NOTE, contractorActions, describeDue, isActiveTicket } from "@/lib/tickets";

function TicketCard({ ticket, onChanged }: { ticket: Ticket; onChanged: (t: Ticket) => void }) {
  const [pending, setPending] = useState<TicketAction | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [brief, setBrief] = useState<JobBrief | null>(null);
  const [briefOpen, setBriefOpen] = useState(false);
  const [briefLoading, setBriefLoading] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [noteBefore, setNoteBefore] = useState<string | null>(null); // what the contractor had typed before the AI rewrote it, so it can be put back
  const [noteAi, setNoteAi] = useState<boolean | null>(null);
  const due = describeDue(ticket.due_at);
  const actions = contractorActions(ticket.status);

  const submit = async (action: TicketAction) => {
    setBusy(true);
    setError(null);
    try {
      onChanged(await actOnTicket(ticket.id, action, note.trim() || undefined));
      setPending(null);
      setNote("");
      setNoteBefore(null);
      setNoteAi(null);
    } catch (failure) {
      setError(apiErrorMessage(failure, "That did not work. Try again."));
    } finally {
      setBusy(false);
    }
  };

  // the job brief: fetched once when opened, then kept. The AI only prepares; nothing is saved
  const toggleBrief = async () => {
    if (briefOpen) return setBriefOpen(false);
    setBriefOpen(true);
    if (brief || briefLoading) return;
    setBriefLoading(true);
    try {
      setBrief(await fetchJobBrief(ticket.id));
    } catch (failure) {
      setBriefOpen(false);
      setError(apiErrorMessage(failure, "The job brief is not available right now."));
    } finally {
      setBriefLoading(false);
    }
  };

  // "Help me write it": the contractor's few words become a clear note. The original is kept so Undo restores it, and the contractor still presses Confirm
  const helpWithNote = async () => {
    setDrafting(true);
    setError(null);
    try {
      const draft = await draftFixNote(ticket.id, note.trim());
      setNoteBefore(note);
      setNote(draft.note);
      setNoteAi(draft.ai);
    } catch (failure) {
      setError(apiErrorMessage(failure, "Could not tidy the note right now. You can send your own words."));
    } finally {
      setDrafting(false);
    }
  };
  const canBrief = ["assigned", "accepted", "in_progress", "sent_back"].includes(ticket.status);

  // "after" photos can be added while the job is the contractor's or waiting for the check
  const canAddPhotos = ["accepted", "in_progress", "sent_back", "fixed"].includes(ticket.status);
  const addPhotos = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      onChanged(await uploadRepairPhotos(ticket.id, [...files]));
    } catch (failure) {
      setError(apiErrorMessage(failure, "The photos could not be added. Try again."));
    } finally {
      setUploading(false);
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
        {canBrief ? (
          <div>
            <Button size="sm" variant="outline" onClick={() => void toggleBrief()} aria-expanded={briefOpen}>
              {briefLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardList className="h-4 w-4" />}
              {briefOpen ? "Hide job brief" : "Job brief"}
            </Button>
            {briefOpen ? (
              briefLoading || !brief ? (
                <div className="mt-3 space-y-2" aria-busy="true">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-11/12" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
              ) : (
                <div className="mt-3 space-y-2 rounded-xl border border-[#CECBF6] bg-[#F7F6FF] p-3">
                  <span className="inline-flex rounded-[4px] bg-[#EEEDFE] px-[6px] py-[2px] text-[11px] font-medium text-[#534AB7]">{brief.ai ? "AI job brief" : "Standard checklist"}</span>
                  <p>{brief.summary}</p>
                  <ol className="list-decimal space-y-1 pl-5">{brief.steps.map((step) => <li key={step}>{step}</li>)}</ol>
                  {brief.safety.length > 0 ? (
                    <div>
                      <p className="font-medium text-amber-800">Safety</p>
                      <ul className="list-disc space-y-1 pl-5">{brief.safety.map((point) => <li key={point}>{point}</li>)}</ul>
                    </div>
                  ) : null}
                  <p className="text-xs text-muted-foreground">{brief.ai ? "Written by AI from this ticket only. Check it against what you find on site." : "The AI was not available, so this is the standard checklist for this kind of job."}</p>
                </div>
              )
            ) : null}
          </div>
        ) : null}
        {ticket.photo_urls.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {ticket.photo_urls.map((url) => (
              <a key={url} href={photoUrl(url)} target="_blank" rel="noreferrer">
                <img src={photoUrl(url)} alt="Resident's photo" className="h-24 w-32 rounded-xl object-cover" />
              </a>
            ))}
          </div>
        ) : null}
        {ticket.repair_photo_urls.length > 0 ? (
          <div className="space-y-1">
            <p className="font-medium">Your repair photos</p>
            <RepairPhotos urls={ticket.repair_photo_urls} label="Your repair photo" />
          </div>
        ) : null}
        {canAddPhotos ? (
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-border px-3 py-1.5 text-sm font-medium hover:bg-secondary">
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
            {uploading ? "Adding photos..." : ticket.repair_photo_urls.length > 0 ? "Add more repair photos" : "Add repair photos (shows the authority the work)"}
            <input type="file" accept="image/*" multiple className="sr-only" disabled={uploading} onChange={(event) => { void addPhotos(event.target.files); event.target.value = ""; }} />
          </label>
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
                  onChange={(event) => { setNote(event.target.value); setNoteAi(null); }}
                />
                {pending === "fix" ? (
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Button type="button" size="sm" variant="outline" disabled={drafting || note.trim().length < 3} onClick={() => void helpWithNote()}>
                        {drafting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                        Help me write it
                      </Button>
                      {noteBefore !== null ? (
                        <Button type="button" size="sm" variant="ghost" onClick={() => { setNote(noteBefore); setNoteBefore(null); setNoteAi(null); }}>
                          Undo, use my words
                        </Button>
                      ) : null}
                    </div>
                    {noteAi !== null ? (
                      <p className="text-xs text-muted-foreground">
                        {noteAi ? "Tidied by AI from your words. Check it says only what you really did, then confirm." : "The AI was not available, so your words were only tidied. Check them, then confirm."}
                      </p>
                    ) : null}
                  </div>
                ) : null}
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

// one number that opens the list it counted (same idea as the tiles on the admin overview)
function Tile({ label, value, hint, alarm, active, onClick }: { label: string; value: number | string; hint: string; alarm?: boolean; active?: boolean; onClick?: () => void }) {
  const body = (
    <>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={cn("mt-1 font-semibold", typeof value === "string" ? "text-2xl" : "text-3xl", alarm && Number(value) > 0 ? "text-rose-700" : "")}>{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </>
  );
  if (!onClick) return <div className="rounded-2xl bg-secondary/60 p-4 text-left">{body}</div>;
  return (
    <button type="button" aria-pressed={active} onClick={onClick} className={cn("rounded-2xl p-4 text-left ring-2 ring-transparent transition", active ? "bg-primary/10 ring-primary" : "bg-secondary/60 hover:bg-secondary")}>
      {body}
    </button>
  );
}

// small bar chart: for each slice of the period, how many tickets arrived (blue) and how many were marked fixed (green)
function Chart({ tickets, period }: { tickets: Ticket[]; period: Period }) {
  const bars = chartBars(tickets, period);
  const max = Math.max(1, ...bars.flatMap((b) => [b.opened, b.fixed]));
  return (
    <div>
      <div className="flex h-28 items-end gap-2" role="img" aria-label="Tickets arrived and fixed over the period">
        {bars.map((b) => (
          <div key={b.label} className="flex h-full flex-1 flex-col justify-end" title={`${b.label}: ${b.opened} arrived, ${b.fixed} fixed`}>
            <div className="flex h-full items-end justify-center gap-1">
              <div className="w-1/3 rounded-t bg-sky-400 transition-all duration-500" style={{ height: `${(b.opened / max) * 100}%`, minHeight: b.opened ? 4 : 0 }} />
              <div className="w-1/3 rounded-t bg-emerald-500 transition-all duration-500" style={{ height: `${(b.fixed / max) * 100}%`, minHeight: b.fixed ? 4 : 0 }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-2">
        {bars.map((b) => (
          <span key={b.label} className="flex-1 text-center text-[10px] text-muted-foreground">{b.label}</span>
        ))}
      </div>
      <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-sm bg-sky-400" /> Arrived</span>
        <span className="flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-sm bg-emerald-500" /> Marked fixed</span>
      </div>
    </div>
  );
}

const FILTER_LABEL: Record<ListFilter, string> = { open: "Open", action: "Needs your action", overdue: "Overdue", awaiting: "Awaiting check", closed: "Closed", other: "Rejected or cancelled", all: "All" };
const EMPTY: Record<ListFilter, string> = {
  open: "Nothing open right now.", action: "Nothing is waiting for you to act on.", overdue: "Nothing is overdue. Well done.", awaiting: "Nothing is waiting for the authority to check.",
  closed: "No tickets were closed in this period.", other: "No rejected or cancelled tickets.", all: "No tickets yet.",
};
const SHOW_FIRST = 6;

export function ContractorTicketsPage() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>("month");
  const [filter, setFilter] = useState<ListFilter>("open");
  const [showAll, setShowAll] = useState(false);
  const [summary, setSummary] = useState<{ text: string; ai: boolean } | null>(null);
  const [summarising, setSummarising] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

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

  useEffect(() => setShowAll(false), [filter, period]);
  useEffect(() => { setSummary(null); setSummaryError(null); }, [period]); // a summary belongs to the period it was written for

  if (error) return <p className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</p>;
  if (!tickets) {
    return (
      <div className="space-y-6" aria-busy="true" aria-live="polite">
        <span className="sr-only">Loading your tickets</span>
        <Skeleton className="h-9 w-48" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">{[0, 1, 2, 3, 4].map((n) => <Skeleton key={n} className="h-[104px]" />)}</div>
        <Skeleton className="h-48 w-full" />
        <div className="grid gap-4 lg:grid-cols-2"><Skeleton className="h-56" /><Skeleton className="h-56" /></div>
      </div>
    );
  }

  const replace = (updated: Ticket) => setTickets((current) => (current ?? []).map((t) => (t.id === updated.id ? updated : t)));
  const d = dashboardNumbers(tickets, period);
  const periodLabel = PERIODS.find((p) => p.id === period)!.label.toLowerCase();
  const counts: Record<ListFilter, number> = Object.fromEntries((Object.keys(FILTER_LABEL) as ListFilter[]).map((f) => [f, filterTickets(tickets, f, period).length])) as Record<ListFilter, number>;
  const list = filterTickets(tickets, filter, period);
  const shown = showAll ? list : list.slice(0, SHOW_FIRST);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight">My tickets</h2>
          <p className="mt-1 text-sm text-muted-foreground">Repairs the authority has given you. Accept a job, do the work, then mark it fixed with a note on what you did.</p>
        </div>
        <div className="flex gap-2" role="group" aria-label="Period">
          {PERIODS.map((p) => (
            <button key={p.id} type="button" aria-pressed={period === p.id} onClick={() => setPeriod(p.id)}
              className={cn("rounded-full border px-4 py-1.5 text-sm font-medium transition-colors", period === p.id ? "border-primary bg-primary text-primary-foreground" : "border-border bg-background hover:bg-secondary")}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Tile label="Open now" value={d.open} hint="With you, not yet fixed" active={filter === "open"} onClick={() => setFilter("open")} />
        <Tile label="Needs your action" value={d.needsAction} hint="New, or sent back" alarm active={filter === "action"} onClick={() => setFilter("action")} />
        <Tile label="Overdue" value={d.overdue} hint="Past the due time" alarm active={filter === "overdue"} onClick={() => setFilter("overdue")} />
        <Tile label="Awaiting check" value={d.awaitingCheck} hint="You marked them fixed" active={filter === "awaiting"} onClick={() => setFilter("awaiting")} />
        <Tile label="Closed" value={d.verified} hint={`Verified, ${periodLabel}`} active={filter === "closed"} onClick={() => setFilter("closed")} />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">How you are doing, {periodLabel}</CardTitle>
          <CardDescription>Tickets that arrived, were fixed and were checked in this period.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
          <div className="grid grid-cols-2 gap-3">
            <Tile label="Arrived" value={d.opened} hint="New tickets" />
            <Tile label="Marked fixed" value={d.fixed} hint="By you" />
            <Tile label="Average time to fix" value={formatHours(d.avgHoursToFix)} hint="From arriving to fixed" />
            <Tile label="Fixed on time" value={d.onTimePct === null ? "No data yet" : `${d.onTimePct}%`} hint="By the due time" />
          </div>
          <Chart tickets={tickets} period={period} />
        </CardContent>
        <CardContent className="space-y-3 pt-0">
          <Button size="sm" variant="outline" disabled={summarising} onClick={async () => {
            setSummarising(true);
            setSummaryError(null);
            try {
              setSummary(await fetchMySummary(PERIODS.find((p) => p.id === period)!.days as 7 | 30 | 90));
            } catch (failure) {
              setSummaryError(apiErrorMessage(failure, "The summary is not available right now."));
            } finally {
              setSummarising(false);
            }
          }}>
            {summarising ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Summarise my {periodLabel}
          </Button>
          {summarising || summary ? <AITextBlock label={summary && !summary.ai ? "Summary" : "AI summary"} content={summary?.text ?? null} loading={summarising} /> : null}
          {summaryError ? <p className="text-sm text-destructive">{summaryError}</p> : null}
        </CardContent>
      </Card>

      <div className="space-y-3">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Show tickets">
          {(Object.keys(FILTER_LABEL) as ListFilter[]).map((f) => (
            <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}
              className={cn("rounded-full border px-4 py-1.5 text-sm font-medium transition-colors", filter === f ? "border-primary bg-primary text-primary-foreground" : "border-border bg-background hover:bg-secondary")}>
              {FILTER_LABEL[f]} <span className="opacity-70">{counts[f]}</span>
            </button>
          ))}
        </div>
        {list.length === 0 ? (
          <p className="flex items-center gap-2 rounded-2xl border border-border/70 p-6 text-sm text-muted-foreground">
            {filter === "overdue" || filter === "action" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : null}
            {EMPTY[filter]}
          </p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {shown.map((t) => (
              <TicketCard key={t.id} ticket={t} onChanged={replace} />
            ))}
          </div>
        )}
        {list.length > SHOW_FIRST ? (
          <Button variant="outline" size="sm" onClick={() => setShowAll((v) => !v)}>
            {showAll ? "Show fewer" : `Show all ${list.length}`}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
