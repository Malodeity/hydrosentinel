// The Contractors tab: the companies that do repairs, where each one works, how they are doing, every ticket, and a quick way to hand
// several waiting reports to one contractor. Assigning a single report is done on the Citizen reports tab (ReportTicketPanel).

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

import {
  apiErrorMessage,
  assignReportsBulk,
  createContractor,
  fetchAssignments,
  fetchContractorPerformance,
  fetchContractors,
  removeCoverage,
  setCoverage,
  updateContractor,
  type Contractor,
  type ContractorPerformance,
  type Ticket,
} from "@/api/assignments";
import type { CitizenReport, IssueType } from "@/api/reports";
import { createUser } from "@/api/users";
import type { WSA } from "@/api/wsa";
import { TicketStatus } from "@/components/TicketStatus";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { summarizeCoverage } from "@/lib/coverageSummary";
import { cn } from "@/lib/utils";
import { describeDue, issueList, isActiveTicket } from "@/lib/tickets";

const ISSUES: IssueType[] = ["leak", "outage", "quality", "billing"];

interface Props {
  wsas: WSA[];
  reports: CitizenReport[];
  isNational: boolean;
  onChanged: () => void | Promise<void>;
}

// the small form that says "this contractor works in this authority on these issue types"
function CoverageForm({ contractor, wsas, onSaved, onError }: { contractor: Contractor; wsas: WSA[]; onSaved: (c: Contractor) => void; onError: (m: string) => void }) {
  const [wsaId, setWsaId] = useState("");
  const [issues, setIssues] = useState<IssueType[]>(["leak", "outage"]);
  const toggle = (issue: IssueType) => setIssues((current) => (current.includes(issue) ? current.filter((item) => item !== issue) : [...current, issue]));
  return (
    <div className="mt-3 space-y-2 rounded-xl border border-dashed border-border p-3">
      <p className="text-xs font-medium text-muted-foreground">Pick an authority and the issue types this contractor handles there</p>
      <Select value={wsaId} onValueChange={setWsaId}>
        <SelectTrigger>
          <SelectValue placeholder="Choose an authority" />
        </SelectTrigger>
        <SelectContent>
          {wsas.map((wsa) => (
            <SelectItem key={wsa.id} value={wsa.id}>
              {wsa.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div className="flex flex-wrap gap-3">
        {ISSUES.map((issue) => (
          <label key={issue} className="flex items-center gap-1.5 text-sm capitalize">
            <input type="checkbox" checked={issues.includes(issue)} onChange={() => toggle(issue)} />
            {issue}
          </label>
        ))}
      </div>
      <Button
        size="sm"
        disabled={!wsaId || issues.length === 0}
        onClick={async () => {
          try {
            onSaved(await setCoverage(contractor.id, wsaId, issues));
            setWsaId("");
          } catch (failure) {
            onError(apiErrorMessage(failure, "Could not save where this contractor works."));
          }
        }}
      >
        Save area
      </Button>
      <ProvinceButtons contractor={contractor} wsas={wsas} issues={issues} onSaved={onSaved} onError={onError} />
    </div>
  );
}

// one click for a whole province: "add all authorities" or "remove all" (an authority where the contractor still holds open tickets is kept and reported)
function ProvinceButtons({ contractor, wsas, issues, onSaved, onError }: { contractor: Contractor; wsas: WSA[]; issues: IssueType[]; onSaved: (c: Contractor) => void; onError: (m: string) => void }) {
  const [province, setProvince] = useState("");
  const [working, setWorking] = useState(false);
  const provinces = [...new Set(wsas.map((w) => w.province))].sort((a, b) => a.localeCompare(b));
  const inProvince = wsas.filter((w) => w.province === province);

  async function run(kind: "add" | "remove") {
    setWorking(true);
    let latest = contractor;
    let kept = 0;
    try {
      for (const wsa of inProvince) {
        try {
          latest = kind === "add" ? await setCoverage(contractor.id, wsa.id, issues) : latest.coverage.some((r) => r.wsa_id === wsa.id) ? await removeCoverage(contractor.id, wsa.id) : latest;
        } catch (failure) {
          if (kind === "remove") kept += 1;
          else throw failure;
        }
      }
      onSaved(latest);
      onError(kept ? `${kept} authorit${kept === 1 ? "y was" : "ies were"} kept because open tickets are still there.` : "");
    } catch (failure) {
      onSaved(latest);
      onError(apiErrorMessage(failure, "Could not finish the province."));
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-border/60 pt-2">
      <div className="w-48">
        <Select value={province} onValueChange={setProvince}>
          <SelectTrigger>
            <SelectValue placeholder="Whole province" />
          </SelectTrigger>
          <SelectContent>
            {provinces.map((name) => (
              <SelectItem key={name} value={name}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button size="sm" variant="outline" disabled={!province || issues.length === 0 || working} onClick={() => run("add")}>
        Add all {province ? `(${inProvince.length})` : ""}
      </Button>
      <Button size="sm" variant="ghost" disabled={!province || working} onClick={() => run("remove")}>
        Remove all
      </Button>
    </div>
  );
}

// edit a contractor's name and contact details (the switch on the card handles on / off)
function EditDetails({ contractor, onSaved, onError }: { contractor: Contractor; onSaved: (c: Contractor) => void; onError: (m: string) => void }) {
  const [name, setName] = useState(contractor.name);
  const [contact, setContact] = useState(contractor.contact_name ?? "");
  const [phone, setPhone] = useState(contractor.phone ?? "");
  const [email, setEmail] = useState(contractor.email ?? "");
  return (
    <div className="mt-2 grid gap-2 sm:grid-cols-2">
      <Input aria-label="Company name" value={name} onChange={(e) => setName(e.target.value)} />
      <Input aria-label="Contact person" placeholder="Contact person" value={contact} onChange={(e) => setContact(e.target.value)} />
      <Input aria-label="Phone" placeholder="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
      <Input aria-label="Email" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Button
        size="sm"
        className="sm:col-span-2"
        disabled={!name.trim()}
        onClick={async () => {
          try {
            onSaved(await updateContractor(contractor.id, { name, contact_name: contact || null, phone: phone || null, email: email || null, is_active: contractor.is_active }));
            onError("");
          } catch (failure) {
            onError(apiErrorMessage(failure, "Could not save the details."));
          }
        }}
      >
        Save details
      </Button>
    </div>
  );
}

export function ContractorsTab({ wsas, reports, isNational, onChanged }: Props) {
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [performance, setPerformance] = useState<ContractorPerformance[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [ticketFilter, setTicketFilter] = useState("active");
  const [provinceFilter, setProvinceFilter] = useState("all");
  const [bulkIds, setBulkIds] = useState<string[]>([]);
  const [bulkContractor, setBulkContractor] = useState("");
  const [busy, setBusy] = useState(false);
  const [loginFor, setLoginFor] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  const reload = useCallback(async () => {
    try {
      const [c, p, t] = await Promise.all([fetchContractors(), fetchContractorPerformance(), fetchAssignments()]);
      setContractors(c);
      setPerformance(p);
      setTickets(t);
    } catch {
      setError("Could not load contractors.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const wsaName = useMemo(() => Object.fromEntries(wsas.map((w) => [w.id, w.name])), [wsas]);
  const saved = (updated: Contractor) => {
    setContractors((current) => current.map((c) => (c.id === updated.id ? updated : c)));
    setError(null);
  };

  // reports nobody is working on yet: not resolved, and no ticket still with a contractor
  const waiting = useMemo(
    () => reports.filter((r) => r.case_status !== "resolved" && !(r.assignment && isActiveTicket(r.assignment.status))),
    [reports],
  );
  const [bulkProvince, setBulkProvince] = useState("all");
  const [bulkInstructions, setBulkInstructions] = useState("");
  const wsaProvinceById = useMemo(() => Object.fromEntries(wsas.map((w) => [w.id, w.province])), [wsas]);
  const waitingShown = waiting.filter((r) => bulkProvince === "all" || wsaProvinceById[r.wsa_id] === bulkProvince);
  const ticked = waiting.filter((r) => bulkIds.includes(r.id));
  // a contractor is offered only if it is switched on and can serve EVERY ticked report (same rule the server enforces)
  const servesAll = (c: Contractor) =>
    ticked.every((r) => c.coverage.some((row) => row.wsa_id === r.wsa_id && row.issue_types.includes(r.issue_type)));
  const bulkEligible = contractors.filter((c) => c.is_active && servesAll(c));

  // contractors grouped by the provinces they work in (one that spans provinces shows under each); ones with no area yet go last
  const wsaProvince = useMemo(() => Object.fromEntries(wsas.map((w) => [w.id, w.province])), [wsas]);
  const provinces = useMemo(() => [...new Set(wsas.map((w) => w.province))].sort((a, b) => a.localeCompare(b)), [wsas]);
  const groups = useMemo(() => {
    const map = new Map<string, Contractor[]>();
    for (const c of contractors) {
      const places = [...new Set(summarizeCoverage(c.coverage, wsas).map((p) => p.province))];
      for (const place of places.length ? places : ["Not set up yet"]) map.set(place, [...(map.get(place) ?? []), c]);
    }
    return [...map.entries()]
      .filter(([place]) => provinceFilter === "all" || place === provinceFilter)
      .sort(([a], [b]) => (a === "Not set up yet" ? 1 : b === "Not set up yet" ? -1 : a.localeCompare(b)));
  }, [contractors, provinceFilter, wsas]);

  const shownTickets = tickets.filter((t) =>
    ticketFilter === "all" ? true : ticketFilter === "active" ? isActiveTicket(t.status) : ticketFilter === "overdue" ? t.overdue : t.status === ticketFilter,
  );

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading contractors...
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {error ? <p className="rounded-2xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p> : null}
      {message ? <p className="rounded-2xl border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p> : null}

      {/* the same tiles as the CAP tab: click one to show those tickets in the table at the bottom */}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4" role="group" aria-label="Ticket summary">
        {(
          [
            ["none", "Active contractors", contractors.filter((c) => c.is_active).length],
            ["active", "Open tickets", tickets.filter((t) => isActiveTicket(t.status)).length],
            ["fixed", "Waiting for your check", tickets.filter((t) => t.status === "fixed").length],
            ["overdue", "Overdue", tickets.filter((t) => t.overdue).length],
          ] as [string, string, number][]
        ).map(([value, label, count]) => (
          <button
            key={value}
            type="button"
            disabled={value === "none"}
            aria-pressed={ticketFilter === value}
            onClick={() => {
              setTicketFilter(value);
              document.getElementById("contractor-tickets")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
            className={cn(
              "rounded-2xl p-3 text-left transition-colors sm:p-4",
              ticketFilter === value ? "bg-primary text-primary-foreground" : "bg-secondary/60 enabled:hover:bg-secondary",
            )}
          >
            <p className={cn("text-sm", ticketFilter === value ? "text-primary-foreground/80" : "text-muted-foreground")}>{label}</p>
            <p className={cn("mt-1 text-2xl font-semibold", value === "overdue" && count > 0 && ticketFilter !== value ? "text-rose-700" : "")}>{count}</p>
          </button>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Contractors</CardTitle>
          <CardDescription>The companies your authority uses for repairs. Add one, say where it works, and give its staff a login.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[1.4fr_1fr_1fr_1.2fr_auto]">
            <Input placeholder="Company name" value={name} onChange={(e) => setName(e.target.value)} />
            <Input placeholder="Contact person" value={contact} onChange={(e) => setContact(e.target.value)} />
            <Input placeholder="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
            <Input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Button
              disabled={name.trim().length < 2 || busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await createContractor({ name: name.trim(), contact_name: contact || null, phone: phone || null, email: email || null, is_active: true });
                  setName("");
                  setContact("");
                  setPhone("");
                  setEmail("");
                  setMessage("Contractor added. Now say where it works.");
                  await reload();
                } catch (failure) {
                  setError(apiErrorMessage(failure, "Could not add that contractor."));
                } finally {
                  setBusy(false);
                }
              }}
            >
              Add contractor
            </Button>
          </div>

          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by province">
            {(["all", ...provinces] as string[]).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={provinceFilter === value}
                onClick={() => setProvinceFilter(value)}
                className={cn(
                  "rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                  provinceFilter === value ? "border-primary bg-primary text-primary-foreground" : "border-border bg-background hover:bg-secondary",
                )}
              >
                {value === "all" ? "All provinces" : value}{" "}
                <span className="opacity-70">
                  {value === "all"
                    ? contractors.length
                    : contractors.filter((c) => c.coverage.some((row) => wsaProvince[row.wsa_id] === value)).length}
                </span>
              </button>
            ))}
          </div>
          {contractors.length === 0 ? <p className="text-sm text-muted-foreground">No contractors yet.</p> : null}
          {groups.map(([place, members]) => (
            <section key={place} className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {place} <span className="font-normal normal-case">({members.length} contractor{members.length === 1 ? "" : "s"})</span>
              </h3>
              <div className="grid gap-4 lg:grid-cols-2">
                {members.map((c) => (
              <div key={`${place}-${c.id}`} className="rounded-2xl border border-border/70 bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold">{c.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {[c.contact_name, c.phone, c.email].filter(Boolean).join(" · ") || "No contact details"}
                    </p>
                    <p className="mt-1.5 inline-flex items-center gap-1.5 whitespace-nowrap text-sm font-medium">
                      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: !c.is_active ? "#94a3b8" : c.open_tickets > 0 ? "#f59e0b" : "#16a34a" }} aria-hidden="true" />
                      {!c.is_active ? "Switched off" : c.open_tickets > 0 ? `${c.open_tickets} open ticket${c.open_tickets === 1 ? "" : "s"}` : "Available"}
                    </p>
                  </div>
                  <Button
                    className="shrink-0"
                    size="sm"
                    variant="outline"
                    onClick={async () => {
                      try {
                        saved(await updateContractor(c.id, { name: c.name, contact_name: c.contact_name, phone: c.phone, email: c.email, is_active: !c.is_active }));
                      } catch (failure) {
                        setError(apiErrorMessage(failure, "Could not change that contractor."));
                      }
                    }}
                  >
                    {c.is_active ? "Switch off" : "Switch on"}
                  </Button>
                </div>
                {!c.is_active ? <p className="mt-2 text-xs text-muted-foreground">No new tickets while switched off.</p> : null}
                <ul className="mt-3 space-y-1 text-sm">
                  {c.coverage.length === 0 ? <li className="text-muted-foreground">Not set up for any authority yet.</li> : null}
                  {summarizeCoverage(c.coverage, wsas).map((p) => (
                    <li key={p.province}>
                      <span className="font-medium">{p.province}:</span>{" "}
                      {p.allInProvince ? `all ${p.total} authorities` : p.authorities.join(", ")}{" "}
                      <span className="text-muted-foreground">({issueList(p.issueTypes)})</span>
                    </li>
                  ))}
                </ul>
                <details className="mt-1 text-xs text-muted-foreground">
                  <summary className="cursor-pointer">Authorities ({c.coverage.length}) and remove</summary>
                  <ul className="mt-1 max-h-32 space-y-1 overflow-y-auto">
                    {c.coverage.map((row) => (
                      <li key={row.wsa_id} className="flex items-center justify-between gap-2">
                        <span>
                          {row.wsa_name} ({issueList(row.issue_types)})
                        </span>
                        <button
                          type="button"
                          className="underline underline-offset-2 hover:text-foreground"
                          onClick={async () => {
                            try {
                              saved(await removeCoverage(c.id, row.wsa_id));
                            } catch (failure) {
                              setError(apiErrorMessage(failure, "Could not remove that area."));
                            }
                          }}
                        >
                          Remove
                        </button>
                      </li>
                    ))}
                  </ul>
                </details>
                <details className="mt-2 text-sm">
                  <summary className="cursor-pointer font-medium text-primary">Edit name and contact details</summary>
                  <EditDetails contractor={c} onSaved={saved} onError={(m) => setError(m || null)} />
                </details>
                <details className="mt-2 text-sm">
                  <summary className="cursor-pointer font-medium text-primary">Add or change where it works</summary>
                  <CoverageForm contractor={c} wsas={wsas} onSaved={saved} onError={(m) => setError(m || null)} />
                </details>
                {isNational ? (
                  loginFor === c.id ? (
                    <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
                      <Input type="email" placeholder="Login email" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} />
                      <Input type="password" placeholder="Password (min 8)" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} />
                      <Button
                        size="sm"
                        disabled={!loginEmail || loginPassword.length < 8}
                        onClick={async () => {
                          try {
                            await createUser({ email: loginEmail, password: loginPassword, role: "contractor", contractor_id: c.id });
                            setMessage(`Login created for ${loginEmail}.`);
                            setLoginFor(null);
                            setLoginEmail("");
                            setLoginPassword("");
                          } catch (failure) {
                            setError(apiErrorMessage(failure, "Could not create that login. Is the email already used?"));
                          }
                        }}
                      >
                        Create login
                      </Button>
                    </div>
                  ) : (
                    <Button className="mt-3" size="sm" variant="ghost" onClick={() => setLoginFor(c.id)}>
                      Create a login for this contractor
                    </Button>
                  )
                ) : null}
              </div>
                ))}
              </div>
            </section>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Hand waiting reports to one contractor</CardTitle>
          <CardDescription>{waiting.length} report(s) have nobody working on them. Tick the ones you want, choose a contractor, and send.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="w-56">
              <Select value={bulkProvince} onValueChange={setBulkProvince}>
                <SelectTrigger aria-label="Province filter">
                  <SelectValue placeholder="All provinces" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All provinces</SelectItem>
                  {provinces.map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button size="sm" variant="outline" disabled={waitingShown.length === 0} onClick={() => setBulkIds([...new Set([...bulkIds, ...waitingShown.slice(0, 100).map((r) => r.id)])])}>
              Select all shown ({Math.min(waitingShown.length, 100)})
            </Button>
            <Button size="sm" variant="ghost" disabled={bulkIds.length === 0} onClick={() => setBulkIds([])}>
              Clear
            </Button>
          </div>
          <div className="max-h-56 space-y-1 overflow-y-auto rounded-xl border border-border/60 p-2">
            {waiting.length === 0 ? <p className="p-2 text-sm text-muted-foreground">Every open report already has a contractor.</p> : null}
            {waitingShown.slice(0, 100).map((r) => (
              <label key={r.id} className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm hover:bg-secondary/40">
                <input
                  type="checkbox"
                  checked={bulkIds.includes(r.id)}
                  onChange={() => setBulkIds((current) => (current.includes(r.id) ? current.filter((id) => id !== r.id) : [...current, r.id]))}
                />
                <span className="font-mono text-xs">{r.reference_code}</span>
                <span className="capitalize">{r.issue_type}</span>
                <span className="text-muted-foreground">· {wsaName[r.wsa_id] ?? "Unknown"}</span>
              </label>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="w-72">
              <Select value={bulkContractor} onValueChange={setBulkContractor}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a contractor" />
                </SelectTrigger>
                <SelectContent>
                  {bulkEligible.length === 0 ? <p className="p-2 text-xs text-muted-foreground">No contractor can serve every ticked report. Untick some.</p> : null}
                  {bulkEligible.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Input className="w-72" aria-label="Instructions for the contractor" placeholder="Instructions (optional)" value={bulkInstructions} onChange={(e) => setBulkInstructions(e.target.value)} />
            <Button
              disabled={bulkIds.length === 0 || !bulkContractor || !bulkEligible.some((c) => c.id === bulkContractor) || busy}
              onClick={async () => {
                setBusy(true);
                setError(null);
                try {
                  const made = await assignReportsBulk({ report_ids: bulkIds, contractor_id: bulkContractor, instructions: bulkInstructions || undefined });
                  setMessage(`${made.length} ticket(s) sent.`);
                  setBulkIds([]);
                  setBulkInstructions("");
                  await reload();
                  await onChanged();
                } catch (failure) {
                  setError(apiErrorMessage(failure, "Nothing was sent: at least one report cannot go to that contractor."));
                } finally {
                  setBusy(false);
                }
              }}
            >
              Send {bulkIds.length || ""} ticket{bulkIds.length === 1 ? "" : "s"}
            </Button>
            <p className="text-xs text-muted-foreground">Only contractors that can serve every ticked report are offered.</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>How contractors are doing</CardTitle>
          <CardDescription>For your information only. This does not change any authority's risk score.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Contractor</TableHead>
                <TableHead>Tickets</TableHead>
                <TableHead>Open</TableHead>
                <TableHead>Overdue</TableHead>
                <TableHead>Fixed on time</TableHead>
                <TableHead>Avg time to fix</TableHead>
                <TableHead>Rejected</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {performance.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-muted-foreground">
                    No tickets yet.
                  </TableCell>
                </TableRow>
              ) : null}
              {performance.map((p) => (
                <TableRow key={p.contractor_id}>
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell>{p.total}</TableCell>
                  <TableCell>{p.open}</TableCell>
                  <TableCell className={p.overdue ? "font-semibold text-rose-700" : ""}>{p.overdue}</TableCell>
                  <TableCell>{p.fixed_on_time_pct === null ? "—" : `${p.fixed_on_time_pct}%`}</TableCell>
                  <TableCell>{p.avg_hours_to_fix === null ? "—" : `${p.avg_hours_to_fix} h`}</TableCell>
                  <TableCell>{p.rejected}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card id="contractor-tickets">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>All tickets</CardTitle>
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter tickets">
            {(
              [
                ["active", "Still open"],
                ["fixed", "Waiting for your check"],
                ["overdue", "Overdue"],
                ["rejected", "Rejected"],
                ["closed", "Verified"],
                ["all", "Everything"],
              ] as [string, string][]
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={ticketFilter === value}
                onClick={() => setTicketFilter(value)}
                className={cn(
                  "rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                  ticketFilter === value ? "border-primary bg-primary text-primary-foreground" : "border-border bg-background hover:bg-secondary",
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <CardDescription>To verify, send back or reassign a ticket, open its report on the Citizen reports tab.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Report</TableHead>
                <TableHead>Contractor</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Due</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shownTickets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-muted-foreground">
                    No tickets here.
                  </TableCell>
                </TableRow>
              ) : null}
              {shownTickets.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>
                    <span className="font-mono text-xs">{t.reference_code}</span> <span className="capitalize">{t.issue_type}</span>
                    <p className="text-xs text-muted-foreground">{t.wsa_name}</p>
                  </TableCell>
                  <TableCell>{t.contractor_name}</TableCell>
                  <TableCell>
                    <TicketStatus status={t.status} overdue={t.overdue} />
                  </TableCell>
                  <TableCell className={t.overdue ? "text-rose-700" : "text-muted-foreground"}>{isActiveTicket(t.status) ? describeDue(t.due_at).text : "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
