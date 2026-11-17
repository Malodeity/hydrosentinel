// The three charts at the top of the CAP tab: where plans stand, whether they are on time, whether the riskiest authorities are covered.
// Numbers come from lib/capStats.ts.

import type { CapStatus, WSA } from "@/api/wsa";
import { CAP_STATUSES, RISK_LEVELS, capStats } from "@/lib/capStats";

const STATUS: Record<CapStatus, { label: string; color: string }> = {
  none: { label: "No CAP", color: "#cbd5e1" },
  submitted: { label: "Submitted", color: "#0ea5e9" },
  in_progress: { label: "In progress", color: "#f59e0b" },
  completed: { label: "Completed", color: "#16a34a" },
};

interface Segment { label: string; value: number; color: string }

// one horizontal bar split into coloured parts; widths are shares of `total`
function StackedBar({ segments, total }: { segments: Segment[]; total: number }) {
  return (
    <div className="flex h-5 w-full overflow-hidden rounded-full bg-secondary" role="img" aria-label={segments.map((s) => `${s.label} ${s.value}`).join(", ")}>
      {segments.filter((s) => s.value > 0).map((s) => (
        <div key={s.label} title={`${s.label}: ${s.value}`} style={{ width: `${(s.value / Math.max(total, 1)) * 100}%`, backgroundColor: s.color }} />
      ))}
    </div>
  );
}

function Legend({ items }: { items: { label: string; color: string; value?: number }[] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {items.map((item) => (
        <span key={item.label} className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} aria-hidden="true" />
          {item.label}
          {item.value !== undefined ? <span className="font-semibold text-foreground">{item.value}</span> : null}
        </span>
      ))}
    </div>
  );
}

// Three small charts for the authorities in view: where plans stand, whether they are on time, and whether the riskiest authorities are covered
export function CapCharts({ wsas }: { wsas: WSA[] }) {
  const stats = capStats(wsas);
  const total = wsas.length;
  const unfinished = stats.deadlines.overdue + stats.deadlines.soon + stats.deadlines.ok + stats.deadlines.noDate;
  const deadlineSegments: Segment[] = [
    { label: "Overdue", value: stats.deadlines.overdue, color: "#dc2626" },
    { label: "Due within 14 days", value: stats.deadlines.soon, color: "#f59e0b" },
    { label: "On track", value: stats.deadlines.ok, color: "#16a34a" },
    { label: "No deadline set", value: stats.deadlines.noDate, color: "#cbd5e1" },
  ];

  return (
    <div className="space-y-3">
      {stats.highRiskWithoutCap > 0 ? (
        <p className="rounded-2xl border-l-4 bg-secondary/60 p-4 text-sm" style={{ borderLeftColor: "#dc2626" }}>
          <span className="font-semibold">{stats.highRiskWithoutCap} high-risk {stats.highRiskWithoutCap === 1 ? "authority has" : "authorities have"} no corrective action plan.</span>{" "}
          <span className="text-muted-foreground">These are the first to act on.</span>
        </p>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-border/70 p-4">
          <p className="text-sm font-medium">Where the plans stand</p>
          <p className="mb-3 text-xs text-muted-foreground">All {total} authorities in view, by CAP status</p>
          <StackedBar total={total} segments={CAP_STATUSES.map((s) => ({ label: STATUS[s].label, value: stats.byStatus[s], color: STATUS[s].color }))} />
          <Legend items={CAP_STATUSES.map((s) => ({ label: STATUS[s].label, color: STATUS[s].color, value: stats.byStatus[s] }))} />
        </div>

        <div className="rounded-2xl border border-border/70 p-4">
          <p className="text-sm font-medium">Are plans on time?</p>
          <p className="mb-3 text-xs text-muted-foreground">{unfinished} unfinished plans, by deadline</p>
          {unfinished > 0 ? (
            <>
              <StackedBar total={unfinished} segments={deadlineSegments} />
              <Legend items={deadlineSegments.map((s) => ({ label: s.label, color: s.color, value: s.value }))} />
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No unfinished plans.</p>
          )}
        </div>

        <div className="rounded-2xl border border-border/70 p-4">
          <p className="text-sm font-medium">Are the riskiest covered?</p>
          <p className="mb-3 text-xs text-muted-foreground">CAP status within each risk level</p>
          <div className="space-y-2">
            {RISK_LEVELS.map((risk) => {
              const row = stats.riskByCap[risk];
              const rowTotal = CAP_STATUSES.reduce((sum, s) => sum + row[s], 0);
              return (
                <div key={risk} className="grid grid-cols-[4.5rem_1fr_2rem] items-center gap-2 text-xs">
                  <span className="capitalize text-muted-foreground">{risk}</span>
                  <StackedBar total={rowTotal} segments={CAP_STATUSES.map((s) => ({ label: STATUS[s].label, value: row[s], color: STATUS[s].color }))} />
                  <span className="text-right font-semibold">{rowTotal}</span>
                </div>
              );
            })}
          </div>
          <Legend items={CAP_STATUSES.map((s) => ({ label: STATUS[s].label, color: STATUS[s].color }))} />
        </div>
      </div>
    </div>
  );
}
