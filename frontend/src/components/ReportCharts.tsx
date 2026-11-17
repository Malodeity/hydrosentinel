import type { CitizenReport, IssueType } from "@/api/reports";
import { AGE_LEVELS } from "@/lib/reportAge";
import { ISSUE_TYPES, reportStats } from "@/lib/reportStats";

// same colours as IssueLabel
const ISSUE_COLOR: Record<IssueType, string> = { leak: "#0284c7", outage: "#475569", quality: "#0d9488", billing: "#a16207" };

interface Segment { label: string; value: number; color: string }

function StackedBar({ segments }: { segments: Segment[] }) {
  const total = segments.reduce((n, s) => n + s.value, 0);
  return (
    <div className="flex h-5 w-full overflow-hidden rounded-full bg-secondary" role="img" aria-label={segments.map((s) => `${s.label} ${s.value}`).join(", ")}>
      {segments.filter((s) => s.value > 0).map((s) => (
        <div key={s.label} title={`${s.label}: ${s.value}`} style={{ width: `${(s.value / Math.max(total, 1)) * 100}%`, backgroundColor: s.color }} />
      ))}
    </div>
  );
}

function Legend({ segments }: { segments: Segment[] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {segments.map((s) => (
        <span key={s.label} className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} aria-hidden="true" />
          {s.label} <span className="font-semibold text-foreground">{s.value}</span>
        </span>
      ))}
    </div>
  );
}

function Panel({ title, note, children }: { title: string; note: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border/70 p-4">
      <p className="text-sm font-medium">{title}</p>
      <p className="mb-3 text-xs text-muted-foreground">{note}</p>
      {children}
    </div>
  );
}

// Four small charts of the reports in the chosen place and date range: what kind, how long they have waited, how many arrive each day, and where
export function ReportCharts({ reports, authorityName }: { reports: CitizenReport[]; authorityName: (wsaId: string) => string }) {
  const stats = reportStats(reports);
  const issueSegments = ISSUE_TYPES.map((t) => ({ label: t[0].toUpperCase() + t.slice(1), value: stats.issues[t], color: ISSUE_COLOR[t] }));
  const waitingSegments = AGE_LEVELS.map((l) => ({ label: l.label, value: stats.waiting[l.id], color: l.color }));
  const maxDay = Math.max(1, ...stats.perDay.map((d) => d.count));
  const maxAuthority = Math.max(1, ...stats.topAuthorities.map((a) => a.count));
  const weekTotal = stats.perDay.slice(-7).reduce((n, d) => n + d.count, 0);

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Panel title="What residents report" note={`${reports.length} reports by issue type`}>
        <StackedBar segments={issueSegments} />
        <Legend segments={issueSegments} />
      </Panel>

      <Panel title="How long open reports have waited" note={`${stats.open} unresolved reports`}>
        {stats.open > 0 ? (
          <>
            <StackedBar segments={waitingSegments} />
            <Legend segments={waitingSegments} />
          </>
        ) : (
          <p className="text-sm text-muted-foreground">Nothing is waiting.</p>
        )}
      </Panel>

      <Panel title="New reports per day" note={`Last 14 days: ${weekTotal} in the past week`}>
        <div className="flex h-24 items-end gap-1" role="img" aria-label="Reports received per day over the last 14 days">
          {stats.perDay.map((d) => (
            <div key={d.key} className="flex flex-1 flex-col items-center justify-end gap-1" title={`${d.date.toLocaleDateString("en-ZA", { day: "numeric", month: "short" })}: ${d.count}`}>
              <div className="w-full rounded-sm" style={{ height: `${(d.count / maxDay) * 100}%`, minHeight: d.count ? 3 : 1, backgroundColor: d.count ? "#0284c7" : "#e2e8f0" }} />
            </div>
          ))}
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
          <span>{stats.perDay[0].date.toLocaleDateString("en-ZA", { day: "numeric", month: "short" })}</span>
          <span>Today</span>
        </div>
      </Panel>

      <Panel title="Where the open reports are" note="Authorities with the most unresolved reports">
        {stats.topAuthorities.length > 0 ? (
          <div className="space-y-2">
            {stats.topAuthorities.map((a) => (
              <div key={a.wsaId} className="grid grid-cols-[minmax(0,9rem)_1fr_1.5rem] items-center gap-2 text-xs">
                <span className="truncate" title={authorityName(a.wsaId)}>{authorityName(a.wsaId)}</span>
                <div className="h-3 overflow-hidden rounded-full bg-secondary">
                  <div className="h-full rounded-full bg-sky-600" style={{ width: `${(a.count / maxAuthority) * 100}%` }} />
                </div>
                <span className="text-right font-semibold">{a.count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No unresolved reports.</p>
        )}
      </Panel>
    </div>
  );
}
