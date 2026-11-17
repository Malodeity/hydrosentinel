// The printable four-page management report (/admin/report). It is a normal page styled for A4; the browser's Print > Save as PDF makes the file.
// All numbers are computed in lib/managementReport.ts, so this file is layout only.

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Loader2, Printer } from "lucide-react";

import { fetchAiDigest, fetchProvinceDigest } from "@/api/ai";
import { fetchAlerts, type Alert, type AlertType } from "@/api/alerts";
import { fetchAuditLog, type AuditLogEntry } from "@/api/audit";
import { authStorage } from "@/api/client";
import { fetchCitizenReports, type CitizenReport, type IssueType } from "@/api/reports";
import { fetchWsas, type CapStatus, type RiskLevel, type WSA } from "@/api/wsa";
import { Button } from "@/components/ui/button";
import { formatAuditAction, formatAuditValue } from "@/lib/auditFormat";
import { buildManagementStats } from "@/lib/managementReport";
import { AGE_LEVELS, ageInDays, formatAge, reportAgeLevel } from "@/lib/reportAge";

// The management report is a normal page that prints to a four-page A4 PDF. Colours match the app.
const NAVY = "#14283e";
const BLUE = "#0f77c7";
const MUTED = "#566881";
const BORDER = "#d3e0ee";
const TINT = "#eef5fe";
const RISK_COLOR: Record<RiskLevel, string> = { low: "#16a34a", medium: "#f59e0b", high: "#dc2626" };
const CAP_COLOR: Record<CapStatus, string> = { none: "#94a3b8", submitted: "#38bdf8", in_progress: "#0f77c7", completed: "#16a34a" };
const CAP_LABEL: Record<CapStatus, string> = { none: "No CAP", submitted: "Submitted", in_progress: "In progress", completed: "Completed" };
const ISSUE_COLOR: Record<IssueType, string> = { leak: "#0ea5e9", outage: "#dc2626", quality: "#f59e0b", billing: "#6366f1" };
const ISSUE_LABEL: Record<IssueType, string> = { leak: "Leaks", outage: "Outages", quality: "Water quality", billing: "Billing" };
const ALERT_LABEL: Record<AlertType, string> = {
  risk_level_high: "High risk",
  risk_level_increased: "Risk increased",
  report_volume_spike: "Report spike",
  cap_overdue: "CAP overdue",
  geo_cluster_incident: "Localized incident",
  assignment_overdue: "Repair overdue",
};
const PERIODS = [
  { value: 7, label: "Last 7 days" },
  { value: 30, label: "Last 30 days" },
  { value: 90, label: "Last 90 days" },
  { value: 0, label: "All time" },
];
const TOTAL_PAGES = 4;
// one date format everywhere in the document, e.g. "3 Nov 2026"
const shortDate = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

const printCss = `
.report-sheet { width: 210mm; height: 297mm; position: relative; overflow: hidden; background: #fff; box-sizing: border-box;
  -webkit-print-color-adjust: exact; print-color-adjust: exact; font-feature-settings: "tnum"; }
@media print {
  @page { size: A4; margin: 0; }
  html, body { background: #fff !important; }
  .report-sheet { margin: 0 !important; box-shadow: none !important; break-after: page; page-break-after: always; }
  .report-sheet:last-child { break-after: auto; page-break-after: auto; }
}`;

function Pill({ color, children }: { color: string; children: ReactNode }) {
  return (
    <span className="inline-block whitespace-nowrap rounded-full px-2 py-[1px] text-[8.5px] font-bold uppercase tracking-wide" style={{ color, backgroundColor: `${color}1f`, border: `1px solid ${color}55` }}>
      {children}
    </span>
  );
}

function Card({ title, children, accent = BLUE, className = "" }: { title?: string; children: ReactNode; accent?: string; className?: string }) {
  return (
    <div className={`rounded-xl bg-white ${className}`} style={{ border: `1px solid ${BORDER}`, borderTop: `3px solid ${accent}` }}>
      {title ? <p className="px-4 pt-3 text-[9px] font-bold uppercase tracking-[0.14em]" style={{ color: accent }}>{title}</p> : null}
      <div className="px-4 pb-3 pt-1.5">{children}</div>
    </div>
  );
}

function Kpi({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="rounded-xl bg-white px-4 py-3" style={{ border: `1px solid ${BORDER}`, borderLeft: `5px solid ${color}` }}>
      <p className="text-[8.5px] font-bold uppercase tracking-[0.12em]" style={{ color: MUTED }}>{label}</p>
      <p className="mt-0.5 text-[26px] font-bold leading-none tracking-tight" style={{ color }}>{value}</p>
      <p className="mt-1 text-[9px] leading-tight" style={{ color: MUTED }}>{sub}</p>
    </div>
  );
}

function Stacked({ parts }: { parts: { value: number; color: string }[] }) {
  const total = parts.reduce((sum, part) => sum + part.value, 0);
  return (
    <div className="flex h-3 w-full overflow-hidden rounded-full" style={{ backgroundColor: TINT }}>
      {total > 0 ? parts.map((part, index) => (part.value > 0 ? <div key={index} style={{ width: `${(part.value / total) * 100}%`, backgroundColor: part.color }} /> : null)) : null}
    </div>
  );
}

function Legend({ items }: { items: { label: string; value: number; color: string }[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
      {items.map((item) => (
        <span key={item.label} className="inline-flex items-center gap-1.5 text-[9.5px]" style={{ color: NAVY }}>
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
          {item.label} <strong>{item.value}</strong>
        </span>
      ))}
    </div>
  );
}

function Donut({ parts, centre }: { parts: { value: number; color: string }[]; centre: string }) {
  const total = parts.reduce((sum, part) => sum + part.value, 0);
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;
  return (
    <svg viewBox="0 0 100 100" className="h-[88px] w-[88px] shrink-0">
      <circle cx="50" cy="50" r={radius} fill="none" stroke={TINT} strokeWidth="14" />
      {total > 0
        ? parts.map((part, index) => {
            const length = (part.value / total) * circumference;
            const circle = (
              <circle key={index} cx="50" cy="50" r={radius} fill="none" stroke={part.color} strokeWidth="14" strokeDasharray={`${length} ${circumference - length}`} strokeDashoffset={-offset} transform="rotate(-90 50 50)" />
            );
            offset += length;
            return circle;
          })
        : null}
      <text x="50" y="49" textAnchor="middle" fontSize="19" fontWeight="700" fill={NAVY}>{centre}</text>
      <text x="50" y="62" textAnchor="middle" fontSize="7" fill={MUTED}>reports</text>
    </svg>
  );
}

function Th({ children, className = "" }: { children?: ReactNode; className?: string }) {
  return <th className={`px-2 py-1.5 text-left text-[8px] font-bold uppercase tracking-[0.1em] ${className}`} style={{ color: MUTED, borderBottom: `1.5px solid ${BORDER}` }}>{children}</th>;
}
function Td({ children, className = "" }: { children?: ReactNode; className?: string }) {
  return <td className={`px-2 py-[5px] align-middle text-[9.5px] ${className}`} style={{ color: NAVY, borderBottom: `1px solid ${BORDER}66` }}>{children}</td>;
}

function Sheet({ page, title, subtitle, children, scope, generated }: { page: number; title: string; subtitle: string; children: ReactNode; scope: string; generated: string }) {
  return (
    <section className="report-sheet mx-auto mb-8 shadow-[0_18px_50px_-20px_rgba(20,40,62,0.35)] print:mb-0">
      {page > 1 ? (
        <header className="flex items-end justify-between px-[14mm] pb-3 pt-[11mm]" style={{ borderBottom: `3px solid ${BLUE}`, background: `linear-gradient(180deg, ${TINT}, #fff)` }}>
          <div>
            <p className="text-[8.5px] font-bold uppercase tracking-[0.16em]" style={{ color: BLUE }}>{subtitle}</p>
            <h2 className="mt-0.5 text-[20px] font-bold leading-none tracking-tight" style={{ color: NAVY }}>{title}</h2>
          </div>
          <Wordmark small />
        </header>
      ) : null}
      <div className="px-[14mm]" style={{ paddingTop: page > 1 ? "6mm" : 0 }}>{children}</div>
      <footer className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-[14mm] pb-[7mm] text-[8px]" style={{ color: MUTED }}>
        <span>HydroSentinel &middot; Management report &middot; {scope} &middot; {generated}</span>
        <span className="font-bold">Page {page} of {TOTAL_PAGES}</span>
      </footer>
    </section>
  );
}

function Wordmark({ small = false, light = false }: { small?: boolean; light?: boolean }) {
  const colour = light ? "#fff" : NAVY;
  return (
    <span className="inline-flex items-center gap-2">
      <svg viewBox="0 0 24 24" className={small ? "h-5 w-5" : "h-8 w-8"} aria-hidden="true">
        <path d="M12 2C12 2 5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13z" fill={light ? "#38bdf8" : BLUE} />
        <path d="M9 15a3 3 0 0 0 3 3" stroke="#fff" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      </svg>
      <span className={`${small ? "text-[13px]" : "text-[20px]"} font-bold tracking-tight`} style={{ color: colour }}>HydroSentinel</span>
    </span>
  );
}

export function ManagementReportPage() {
  const user = authStorage.getUser();
  const [province, setProvince] = useState("");
  const [periodDays, setPeriodDays] = useState(30);
  const [reports, setReports] = useState<CitizenReport[]>([]);
  const [wsas, setWsas] = useState<WSA[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [audit, setAudit] = useState<AuditLogEntry[]>([]);
  const [digest, setDigest] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const generatedAt = useMemo(() => new Date(), []);

  useEffect(() => {
    Promise.all([fetchCitizenReports(), fetchWsas(), fetchAlerts(), fetchAuditLog(10)])
      .then(([reportData, wsaData, alertData, auditData]) => {
        setReports(reportData);
        setWsas(wsaData);
        setAlerts(alertData);
        setAudit(auditData);
      })
      .catch(() => setError("Could not load the data for the report. Make sure you are signed in as an admin."))
      .finally(() => setLoading(false));
  }, []);

  // the AI overview follows the chosen scope; if the AI is unavailable the report is still complete without it
  useEffect(() => {
    let current = true;
    setDigest(null);
    (province ? fetchProvinceDigest(province) : fetchAiDigest())
      .then((data) => current && setDigest(data.content))
      .catch(() => current && setDigest(null));
    return () => {
      current = false;
    };
  }, [province]);

  // the browser uses the page title as the suggested PDF file name
  useEffect(() => {
    const previous = document.title;
    document.title = `HydroSentinel Management Report ${generatedAt.toISOString().slice(0, 10)}${province ? ` ${province}` : ""}`;
    return () => {
      document.title = previous;
    };
  }, [generatedAt, province]);

  const stats = useMemo(() => buildManagementStats({ reports, wsas, alerts, scope: { province, periodDays } }), [reports, wsas, alerts, province, periodDays]);
  const wsaById = useMemo(() => Object.fromEntries(wsas.map((wsa) => [wsa.id, wsa])) as Record<string, WSA>, [wsas]);
  const provinces = useMemo(() => [...new Set(wsas.map((wsa) => wsa.province))].sort((a, b) => a.localeCompare(b)), [wsas]);

  const scopeLabel = `${province || "All provinces"} · ${PERIODS.find((period) => period.value === periodDays)?.label ?? ""}`;
  const generatedLabel = generatedAt.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const a = stats.authorities;
  const maxAlerts = Math.max(1, ...Object.values(stats.alerts.byType));
  const maxIssue = Math.max(1, ...Object.values(stats.reports.byIssue));
  const sheetProps = { scope: scopeLabel, generated: generatedLabel };

  return (
    <div className="-mx-4 -my-8 bg-[#e8eff7] px-4 py-8 print:m-0 print:bg-white print:p-0">
      <style>{printCss}</style>

      <div className="mx-auto mb-6 flex w-[210mm] max-w-full flex-wrap items-end justify-between gap-4 print:hidden">
        <div className="space-y-1">
          <Button asChild variant="ghost" size="sm" className="-ml-3">
            <Link to="/admin">
              <ArrowLeft className="h-4 w-4" />
              Back to admin
            </Link>
          </Button>
          <h1 className="text-2xl font-semibold tracking-tight">Management report</h1>
          <p className="text-sm text-muted-foreground">Choose the scope, then download. In the print window pick &ldquo;Save as PDF&rdquo;.</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="space-y-1 text-xs font-medium text-muted-foreground">
            Province
            <select className="block h-10 rounded-full border border-border bg-white px-4 text-sm text-foreground" value={province} onChange={(event) => setProvince(event.target.value)}>
              <option value="">All provinces</option>
              {provinces.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-xs font-medium text-muted-foreground">
            Period
            <select className="block h-10 rounded-full border border-border bg-white px-4 text-sm text-foreground" value={periodDays} onChange={(event) => setPeriodDays(Number(event.target.value))}>
              {PERIODS.map((period) => (
                <option key={period.value} value={period.value}>{period.label}</option>
              ))}
            </select>
          </label>
          <Button onClick={() => window.print()} disabled={loading || Boolean(error)}>
            <Printer className="h-4 w-4" />
            Download PDF
          </Button>
        </div>
      </div>

      {loading ? (
        <p className="flex items-center justify-center gap-2 py-24 text-sm text-muted-foreground print:hidden">
          <Loader2 className="h-4 w-4 animate-spin" /> Gathering the data...
        </p>
      ) : error ? (
        <p className="mx-auto max-w-xl rounded-2xl border border-destructive/30 bg-white p-6 text-sm text-destructive print:hidden">{error}</p>
      ) : (
        <>
          {/* PAGE 1: overview */}
          <Sheet page={1} title="Overview" subtitle="Overview" {...sheetProps}>
            <div className="-mx-[14mm] px-[14mm] pb-7 pt-[13mm] text-white" style={{ background: "linear-gradient(135deg, #0e1f33 0%, #0f4f86 55%, #0f77c7 100%)", position: "relative", overflow: "hidden" }}>
              <svg viewBox="0 0 800 120" className="absolute bottom-0 left-0 w-full" preserveAspectRatio="none" aria-hidden="true">
                <path d="M0 70 C120 30 240 110 400 70 S680 30 800 70 V120 H0 Z" fill="rgba(255,255,255,0.08)" />
                <path d="M0 95 C140 60 260 120 420 90 S690 60 800 95 V120 H0 Z" fill="rgba(56,189,248,0.18)" />
              </svg>
              <div className="relative">
                <Wordmark light />
                <p className="mt-6 text-[9px] font-bold uppercase tracking-[0.2em]" style={{ color: "#7dd3fc" }}>Management report</p>
                <h1 className="mt-1 max-w-[150mm] text-[30px] font-bold leading-[1.05] tracking-tight">Water service risk and citizen response</h1>
                <div className="mt-4 flex flex-wrap gap-2">
                  {[province || "All provinces", PERIODS.find((period) => period.value === periodDays)?.label ?? "", `${a.total} authorities`].map((chip) => (
                    <span key={chip} className="rounded-full bg-white/15 px-3 py-1 text-[9.5px] font-semibold">{chip}</span>
                  ))}
                </div>
                <p className="mt-3 text-[9.5px] text-white/75">
                  Prepared {generatedLabel}{user ? ` by ${user.email}` : ""}
                </p>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-[1.15fr_1fr] gap-3">
              <Card title="Key findings" accent={BLUE}>
                <ul className="space-y-1.5">
                  {stats.findings.map((finding) => (
                    <li key={finding} className="flex gap-2 text-[10px] leading-snug" style={{ color: NAVY }}>
                      <span className="mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: BLUE }} />
                      {finding}
                    </li>
                  ))}
                </ul>
              </Card>
              <Card title="AI overview" accent="#7F77DD">
                <p className="text-[9.5px] leading-[1.45]" style={{ color: NAVY }}>
                  {digest ?? "The AI overview is not available for this report. All figures in this document come directly from the HydroSentinel database."}
                </p>
              </Card>
            </div>

            <div className="mt-3 grid grid-cols-3 gap-3">
              <Kpi label="Authorities monitored" value={String(a.total)} sub={a.avgBlueDrop === null ? "No Blue Drop data" : `Average Blue Drop score ${a.avgBlueDrop}%`} color={BLUE} />
              <Kpi label="High-risk authorities" value={String(a.high)} sub={a.total ? `${Math.round((a.high / a.total) * 100)}% of those monitored` : "—"} color={RISK_COLOR.high} />
              <Kpi label="Unresolved reports" value={String(stats.ageing.unresolved)} sub={`${stats.ageing.escalated} waiting 14 days or more`} color="#f97316" />
              <Kpi label="Reports received" value={String(stats.reports.inPeriod)} sub={`${stats.reports.byStatus.resolved} resolved in this period`} color="#0ea5e9" />
              <Kpi label="Average time to resolve" value={stats.reports.avgDaysToResolve === null ? "—" : `${stats.reports.avgDaysToResolve} d`} sub={stats.reports.avgDaysToReview === null ? "No reviewed reports yet" : `${stats.reports.avgDaysToReview} days to first review`} color={RISK_COLOR.low} />
              <Kpi label="CAPs past due date" value={String(stats.cap.overdue.length)} sub={`${stats.cap.completed} completed, ${stats.cap.in_progress + stats.cap.submitted} under way`} color="#7c3aed" />
            </div>

            <div className="mt-3 grid grid-cols-1 gap-3">
              <Card title="Risk level of authorities" accent={RISK_COLOR.high}>
                <Stacked parts={[{ value: a.high, color: RISK_COLOR.high }, { value: a.medium, color: RISK_COLOR.medium }, { value: a.low, color: RISK_COLOR.low }]} />
                <Legend items={[{ label: "High", value: a.high, color: RISK_COLOR.high }, { label: "Medium", value: a.medium, color: RISK_COLOR.medium }, { label: "Low", value: a.low, color: RISK_COLOR.low }]} />
                <table className="mt-2 w-full border-collapse">
                  <thead>
                    <tr><Th>Province</Th><Th className="text-right">Authorities</Th><Th className="w-[44mm]">Risk mix</Th><Th className="text-right">High</Th><Th className="text-right">Avg Blue Drop</Th></tr>
                  </thead>
                  <tbody>
                    {stats.byProvince.map((row) => (
                      <tr key={row.province}>
                        <Td className="font-semibold">{row.province}</Td>
                        <Td className="text-right">{row.total}</Td>
                        <Td><Stacked parts={[{ value: row.high, color: RISK_COLOR.high }, { value: row.medium, color: RISK_COLOR.medium }, { value: row.low, color: RISK_COLOR.low }]} /></Td>
                        <Td className="text-right font-semibold" >{row.high}</Td>
                        <Td className="text-right">{row.avgBlueDrop === null ? "—" : `${row.avgBlueDrop}%`}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          </Sheet>

          {/* PAGE 2: citizen reports and the age hierarchy */}
          <Sheet page={2} title="Citizen reports" subtitle={`${stats.reports.inPeriod} received in the period`} {...sheetProps}>
            <div className="grid grid-cols-2 gap-3">
              <Card title="Case status" accent={BLUE}>
                <div className="flex items-center gap-4">
                  <Donut centre={String(stats.reports.inPeriod)} parts={[{ value: stats.reports.byStatus.open, color: "#f59e0b" }, { value: stats.reports.byStatus.in_review, color: "#38bdf8" }, { value: stats.reports.byStatus.resolved, color: "#16a34a" }]} />
                  <div className="space-y-1.5 text-[10px]" style={{ color: NAVY }}>
                    <p className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-[#f59e0b]" />Open <strong>{stats.reports.byStatus.open}</strong></p>
                    <p className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-[#38bdf8]" />In review <strong>{stats.reports.byStatus.in_review}</strong></p>
                    <p className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-[#16a34a]" />Resolved <strong>{stats.reports.byStatus.resolved}</strong></p>
                  </div>
                </div>
              </Card>
              <Card title="What residents report" accent="#0ea5e9">
                <div className="space-y-2">
                  {(Object.keys(ISSUE_LABEL) as IssueType[]).map((issue) => (
                    <div key={issue} className="flex items-center gap-2 text-[9.5px]" style={{ color: NAVY }}>
                      <span className="w-[22mm]">{ISSUE_LABEL[issue]}</span>
                      <div className="h-2.5 flex-1 rounded-full" style={{ backgroundColor: TINT }}>
                        <div className="h-full rounded-full" style={{ width: `${(stats.reports.byIssue[issue] / maxIssue) * 100}%`, backgroundColor: ISSUE_COLOR[issue] }} />
                      </div>
                      <strong className="w-5 text-right">{stats.reports.byIssue[issue]}</strong>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <div className="mt-3">
              <Card title="How long unresolved reports have waited" accent="#dc2626">
                <div className="grid grid-cols-5 gap-2">
                  {AGE_LEVELS.map((level) => (
                    <div key={level.id} className="overflow-hidden rounded-lg text-center" style={{ border: `1px solid ${level.color}55` }}>
                      <p className="py-1 text-[8.5px] font-bold uppercase tracking-wide text-white" style={{ backgroundColor: level.color }}>{level.label}</p>
                      <p className="pt-1.5 text-[24px] font-bold leading-none" style={{ color: level.color }}>{stats.ageing.counts[level.id]}</p>
                      <p className="px-1 pb-1.5 pt-1 text-[8px] leading-tight" style={{ color: MUTED }}>{level.minDays === 0 ? "under 3 days" : `${level.minDays}+ days`}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-2 text-[8.5px] leading-snug" style={{ color: MUTED }}>
                  Every report that is not yet resolved is counted, whenever it was received. Flags rise at 3, 7, 14 and 30 days; reports at 30 days or more should be escalated to management.
                </p>
              </Card>
            </div>

            <div className="mt-3">
              <Card title="Reports waiting longest" accent="#f97316">
                {stats.ageing.oldest.length === 0 ? (
                  <p className="py-4 text-center text-[10px]" style={{ color: MUTED }}>No reports are waiting for action.</p>
                ) : (
                  <table className="w-full border-collapse">
                    <thead>
                      <tr><Th>Waiting</Th><Th>Authority</Th><Th>Issue</Th><Th>Status</Th><Th>Reference</Th></tr>
                    </thead>
                    <tbody>
                      {stats.ageing.oldest.map((report) => {
                        const level = reportAgeLevel(report);
                        return (
                          <tr key={report.id}>
                            <Td>{level ? <Pill color={level.color}>{formatAge(ageInDays(report.created_at))}</Pill> : null}</Td>
                            <Td className="font-semibold">{wsaById[report.wsa_id]?.name ?? "—"}</Td>
                            <Td className="capitalize">{report.issue_type}</Td>
                            <Td className="capitalize">{report.case_status.replace("_", " ")}</Td>
                            <Td><span className="font-mono text-[9px]">{report.reference_code}</span></Td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </Card>
            </div>
          </Sheet>

          {/* PAGE 3: authorities and corrective action plans */}
          <Sheet page={3} title="Authorities and corrective actions" subtitle="Where to focus" {...sheetProps}>
            <Card title="Ten authorities needing most attention" accent={RISK_COLOR.high}>
              <table className="w-full border-collapse">
                <thead>
                  <tr><Th>#</Th><Th>Authority</Th><Th>Province</Th><Th>Risk</Th><Th className="w-[34mm]">Blue Drop</Th><Th>CAP</Th></tr>
                </thead>
                <tbody>
                  {stats.topRisk.map((wsa, index) => (
                    <tr key={wsa.id}>
                      <Td className="font-bold" >{index + 1}</Td>
                      <Td className="font-semibold">{wsa.name}</Td>
                      <Td>{wsa.province}</Td>
                      <Td><Pill color={RISK_COLOR[wsa.risk_level]}>{wsa.risk_level}</Pill></Td>
                      <Td>
                        <div className="flex items-center gap-1.5">
                          <div className="h-2 flex-1 rounded-full" style={{ backgroundColor: TINT }}>
                            <div className="h-full rounded-full" style={{ width: `${wsa.blue_drop_score ?? 0}%`, backgroundColor: wsa.blue_drop_score === null ? "transparent" : BLUE }} />
                          </div>
                          <span className="w-8 text-right text-[9px]">{wsa.blue_drop_score === null ? "—" : `${wsa.blue_drop_score}%`}</span>
                        </div>
                      </Td>
                      <Td>{CAP_LABEL[wsa.cap_status]}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            <div className="mt-3">
              <Card title="Corrective action plans (CAPs)" accent="#7c3aed">
                <Stacked parts={(Object.keys(CAP_LABEL) as CapStatus[]).map((status) => ({ value: stats.cap[status], color: CAP_COLOR[status] }))} />
                <Legend items={(Object.keys(CAP_LABEL) as CapStatus[]).map((status) => ({ label: CAP_LABEL[status], value: stats.cap[status], color: CAP_COLOR[status] }))} />
              </Card>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-3">
              <Card title="High risk and no plan in place" accent={RISK_COLOR.high}>
                <p className="text-[10px]" style={{ color: NAVY }}>
                  <strong className="text-[22px] leading-none" style={{ color: RISK_COLOR.high }}>{stats.cap.highRiskWithoutPlan.length}</strong> high-risk {stats.cap.highRiskWithoutPlan.length === 1 ? "authority has" : "authorities have"} no CAP
                </p>
                <ul className="mt-2 space-y-1">
                  {stats.cap.highRiskWithoutPlan.slice(0, 7).map((wsa) => (
                    <li key={wsa.id} className="flex items-baseline justify-between gap-2 text-[9px]" style={{ color: NAVY }}>
                      <span className="font-semibold">{wsa.name}</span>
                      <span style={{ color: MUTED }}>{wsa.province}</span>
                    </li>
                  ))}
                </ul>
                {stats.cap.highRiskWithoutPlan.length > 7 ? <p className="pt-1.5 text-[8.5px]" style={{ color: MUTED }}>and {stats.cap.highRiskWithoutPlan.length - 7} more</p> : null}
              </Card>
              <Card title="CAP deadlines in the next 30 days" accent={BLUE}>
                {stats.cap.dueSoon.length === 0 ? (
                  <p className="py-4 text-center text-[10px]" style={{ color: MUTED }}>No CAP deadline falls in the next 30 days.</p>
                ) : (
                  <ul className="space-y-1">
                    {stats.cap.dueSoon.slice(0, 8).map((wsa) => (
                      <li key={wsa.id} className="flex items-baseline justify-between gap-2 text-[9px]" style={{ color: NAVY }}>
                        <span className="font-semibold">{wsa.name}</span>
                        <span style={{ color: MUTED }}>{wsa.cap_due_date ? shortDate(wsa.cap_due_date) : ""}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>

            <div className="mt-3">
              <Card title="CAPs past their due date" accent="#dc2626">
                {stats.cap.overdue.length === 0 ? (
                  <p className="py-3 text-center text-[10px]" style={{ color: MUTED }}>No corrective action plan is past its due date.</p>
                ) : (
                  <table className="w-full border-collapse">
                    <thead>
                      <tr><Th>Authority</Th><Th>Province</Th><Th>CAP status</Th><Th>Due</Th><Th className="text-right">Days late</Th></tr>
                    </thead>
                    <tbody>
                      {stats.cap.overdue.slice(0, 8).map((wsa) => (
                        <tr key={wsa.id}>
                          <Td className="font-semibold">{wsa.name}</Td>
                          <Td>{wsa.province}</Td>
                          <Td>{CAP_LABEL[wsa.cap_status]}</Td>
                          <Td>{wsa.cap_due_date ? shortDate(wsa.cap_due_date) : "—"}</Td>
                          <Td className="text-right font-semibold" >{wsa.cap_due_date ? ageInDays(wsa.cap_due_date) : "—"}</Td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {stats.cap.overdue.length > 8 ? <p className="pt-2 text-[8.5px]" style={{ color: MUTED }}>and {stats.cap.overdue.length - 8} more</p> : null}
              </Card>
            </div>
          </Sheet>

          {/* PAGE 4: alerts, activity and method */}
          <Sheet page={4} title="Alerts, activity and method" subtitle="Monitoring" {...sheetProps}>
            <div className="grid grid-cols-2 gap-3">
              <Card title="System alerts" accent="#f59e0b">
                <p className="text-[10px]" style={{ color: NAVY }}>
                  <strong className="text-[22px] leading-none" style={{ color: "#f59e0b" }}>{stats.alerts.unacknowledged}</strong> waiting to be acknowledged, {stats.alerts.total} in total
                </p>
                <div className="mt-2 space-y-1.5">
                  {(Object.keys(ALERT_LABEL) as AlertType[]).map((type) => (
                    <div key={type} className="flex items-center gap-2 text-[9.5px]" style={{ color: NAVY }}>
                      <span className="w-[27mm]">{ALERT_LABEL[type]}</span>
                      <div className="h-2.5 flex-1 rounded-full" style={{ backgroundColor: TINT }}>
                        <div className="h-full rounded-full" style={{ width: `${((stats.alerts.byType[type] ?? 0) / maxAlerts) * 100}%`, backgroundColor: "#f59e0b" }} />
                      </div>
                      <strong className="w-5 text-right">{stats.alerts.byType[type] ?? 0}</strong>
                    </div>
                  ))}
                </div>
              </Card>
              <Card title="Latest alerts not yet acknowledged" accent="#dc2626">
                {stats.alerts.latestUnacknowledged.length === 0 ? (
                  <p className="py-4 text-center text-[10px]" style={{ color: MUTED }}>Every alert has been acknowledged.</p>
                ) : (
                  <ul className="space-y-2">
                    {stats.alerts.latestUnacknowledged.map((alert) => (
                      <li key={alert.id} className="text-[9px] leading-snug" style={{ color: NAVY }}>
                        <Pill color="#f59e0b">{ALERT_LABEL[alert.alert_type]}</Pill> <strong>{alert.wsa_name}</strong>
                        <span className="block" style={{ color: MUTED }}>{shortDate(alert.created_at)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>

            <div className="mt-3">
              <Card title="Recent administrative activity" accent={BLUE}>
                {audit.length === 0 ? (
                  <p className="py-3 text-center text-[10px]" style={{ color: MUTED }}>No activity has been recorded yet.</p>
                ) : (
                  <table className="w-full border-collapse">
                    <thead>
                      <tr><Th>When</Th><Th>Action</Th><Th>Change</Th></tr>
                    </thead>
                    <tbody>
                      {audit.slice(0, 9).map((entry) => (
                        <tr key={entry.id}>
                          <Td className="whitespace-nowrap">{shortDate(entry.created_at)}</Td>
                          <Td className="whitespace-nowrap font-semibold">{formatAuditAction(entry.action)}</Td>
                          <Td className="text-[8.5px]">{formatAuditValue(entry.new_value, 46)}</Td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </Card>
            </div>

            <div className="mt-3">
              <Card title="Definitions and method" accent={MUTED}>
                <div className="grid grid-cols-2 gap-5 text-[8.5px] leading-snug" style={{ color: NAVY }}>
                  <div className="space-y-1.5">
                    <p><strong>Risk level.</strong> Low, medium or high for each authority, from a machine-learning model trained on audited Blue Drop Risk Rating data, with a rule-based fallback when the model cannot score an authority.</p>
                    <p><strong>CAP.</strong> A corrective action plan an authority must carry out. A CAP is past due when its due date has passed and it is not completed.</p>
                    <p><strong>Period.</strong> Report counts and averages cover reports received in the chosen period. The unresolved backlog always includes every unresolved report.</p>
                  </div>
                  <div className="space-y-1.5">
                    <p><strong>Waiting time flags.</strong> Counted from the day a report was received, until it is resolved.</p>
                    {AGE_LEVELS.map((level) => (
                      <p key={level.id} className="flex items-center gap-2">
                        <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: level.color }} />
                        <span><strong>{level.label}</strong>, {level.minDays === 0 ? "under 3 days" : `${level.minDays} days or more`}: {level.description.toLowerCase()}</span>
                      </p>
                    ))}
                  </div>
                </div>
                <p className="mt-3 pt-2 text-[8px]" style={{ color: MUTED, borderTop: `1px solid ${BORDER}` }}>
                  Source: HydroSentinel database, DWS Blue Drop, Green Drop and No Drop reports, and National Treasury Municipal Money data. Generated {generatedAt.toLocaleString("en-GB", { dateStyle: "long", timeStyle: "short" })}.
                </p>
              </Card>
            </div>
          </Sheet>
        </>
      )}
    </div>
  );
}
