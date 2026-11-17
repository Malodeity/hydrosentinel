// The top of the Overview tab: five number tiles (each opens the matching list, already filtered), the 'Do these first' list, the trending-risk list
// with its AI 'Why?', and the risk / Blue Drop / province charts. Numbers: lib/overviewStats.ts, lib/needsAttention.ts, lib/riskByProvince.ts.

import { useState } from "react";
import { ChevronDown } from "lucide-react";

import { fetchTrendExplanation, type RiskTrajectory } from "@/api/ai";
import { AITextBlock } from "@/components/AITextBlock";
import { RiskBadge } from "@/components/RiskBadge";
import type { Alert } from "@/api/alerts";
import type { CitizenReport } from "@/api/reports";
import type { CapStatus, RiskLevel, WSA } from "@/api/wsa";
import { needsAttention, type AttentionItem } from "@/lib/needsAttention";
import { riskByProvince } from "@/lib/riskByProvince";
import type { StatusFilter } from "@/lib/reportFilters";
import { overviewStats, type BlueDropBand } from "@/lib/overviewStats";
import { cn } from "@/lib/utils";

interface Segment { label: string; value: number; color: string }

function StackedBar({ segments }: { segments: Segment[] }) {
  const total = segments.reduce((n, s) => n + s.value, 0);
  return (
    <>
      <div className="flex h-5 w-full overflow-hidden rounded-full bg-secondary" role="img" aria-label={segments.map((s) => `${s.label} ${s.value}`).join(", ")}>
        {segments.filter((s) => s.value > 0).map((s) => (
          <div key={s.label} title={`${s.label}: ${s.value}`} style={{ width: `${(s.value / Math.max(total, 1)) * 100}%`, backgroundColor: s.color }} />
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {segments.map((s) => (
          <span key={s.label} className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} aria-hidden="true" />
            {s.label} <span className="font-semibold text-foreground">{s.value}</span>
          </span>
        ))}
      </div>
    </>
  );
}

function Tile({ label, value, hint, alarm, loading, onClick }: { label: string; value: number; hint: string; alarm?: boolean; loading?: boolean; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="rounded-2xl bg-secondary/60 p-4 text-left transition-colors hover:bg-secondary">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-3xl font-semibold", !loading && alarm && value > 0 ? "text-rose-700" : "")}>{loading ? "…" : value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </button>
  );
}

const BAND_LABEL: Record<BlueDropBand, { label: string; color: string }> = {
  certified: { label: "Certified (95+)", color: "#16a34a" },
  non_certified: { label: "Non-certified (50 to 94)", color: "#f59e0b" },
  poor: { label: "Poor (31 to 49)", color: "#f97316" },
  critical: { label: "Critical (under 31)", color: "#dc2626" },
  unknown: { label: "No score", color: "#cbd5e1" },
};

// where a tile or list item should take the admin, with the filters already set so the list shows exactly what the number counted
export type OverviewTarget =
  | { tab: "reports"; status?: StatusFilter; age?: string; reportId?: string }
  | { tab: "cap"; status?: CapStatus | "all"; risk?: RiskLevel | "all"; overdue?: boolean; query?: string };

const KIND_LABEL: Record<AttentionItem["kind"], { label: string; color: string }> = {
  alert: { label: "Alert", color: "#7c3aed" },
  cap: { label: "Plan overdue", color: "#dc2626" },
  report: { label: "Report waiting", color: "#f97316" },
  uncovered: { label: "No plan", color: "#475569" },
};

// The first thing an admin sees: five numbers that need action (each opens the right list, already filtered), a short ranked "do this first" list, and charts of the whole country
export function OverviewSummary({ wsas, reports, alerts, trending, loading, onNavigate }: { wsas: WSA[]; reports: CitizenReport[]; alerts: Alert[]; trending: RiskTrajectory[]; loading?: boolean; onNavigate: (target: OverviewTarget) => void }) {
  const s = overviewStats(wsas, reports, alerts);
  // which trending row is expanded, and the AI text already fetched for each (so reopening a row costs no second AI call)
  const [openTrend, setOpenTrend] = useState<string | null>(null);
  const [trendText, setTrendText] = useState<Record<string, string>>({});
  const [trendError, setTrendError] = useState<Record<string, string>>({});
  const toggleTrend = (wsaId: string) => {
    setOpenTrend((current) => (current === wsaId ? null : wsaId));
    if (trendText[wsaId] || openTrend === wsaId) return;
    setTrendError((current) => ({ ...current, [wsaId]: "" }));
    fetchTrendExplanation(wsaId)
      .then((result) => setTrendText((current) => ({ ...current, [wsaId]: result.content })))
      .catch((error) =>
        setTrendError((current) => ({
          ...current,
          [wsaId]: error?.response?.status === 429 ? "AI limit reached (20 per hour). Try again later." : "Could not get an explanation right now.",
        })),
      );
  };
  const attention = needsAttention(wsas, reports, alerts);
  const provinces = riskByProvince(wsas);
  const bands = (Object.keys(BAND_LABEL) as BlueDropBand[]).map((b) => ({ ...BAND_LABEL[b], value: s.bands[b] }));
  const risk: Segment[] = [
    { label: "High", value: s.risk.high, color: "#dc2626" },
    { label: "Medium", value: s.risk.medium, color: "#f59e0b" },
    { label: "Low", value: s.risk.low, color: "#16a34a" },
  ];
  const open = (item: AttentionItem) => {
    if (item.kind === "report") onNavigate({ tab: "reports", status: "unresolved", age: "14", reportId: item.reportId });
    else if (item.kind === "cap") onNavigate({ tab: "cap", overdue: true, query: wsas.find((w) => w.id === item.wsaId)?.name });
    else if (item.kind === "uncovered") onNavigate({ tab: "cap", status: "none", risk: "high", query: wsas.find((w) => w.id === item.wsaId)?.name });
    else document.getElementById("system-alerts")?.scrollIntoView();
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Tile loading={loading} label="Unresolved reports" value={s.openReports} hint={`${s.newThisWeek} new in the past 7 days`} onClick={() => onNavigate({ tab: "reports", status: "unresolved", age: "0" })} />
        <Tile loading={loading} label="Waiting 2+ weeks" value={s.waitingTwoWeeks} hint="Unresolved, 14 days or more" alarm onClick={() => onNavigate({ tab: "reports", status: "unresolved", age: "14" })} />
        <Tile loading={loading} label="Overdue plans" value={s.overdueCaps} hint="CAPs past their deadline" alarm onClick={() => onNavigate({ tab: "cap", overdue: true })} />
        <Tile loading={loading} label="High risk, no plan" value={s.highRiskWithoutCap} hint="Authorities with no CAP" alarm onClick={() => onNavigate({ tab: "cap", status: "none", risk: "high" })} />
        <Tile loading={loading} label="Active alerts" value={s.activeAlerts} hint="Listed below" alarm onClick={() => document.getElementById("system-alerts")?.scrollIntoView()} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="rounded-2xl border border-border/70 p-4">
        <p className="text-sm font-medium">Do these first</p>
        <p className="mb-3 text-xs text-muted-foreground">The most pressing problems across alerts, plans and reports. Click one to open it.</p>
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : attention.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing is urgent right now.</p>
        ) : (
          <ul className="divide-y divide-border/60">
            {attention.map((item) => (
              <li key={item.id}>
                <button type="button" onClick={() => open(item)} className="flex w-full items-start gap-3 py-2.5 text-left hover:bg-secondary/40">
                  <span className="mt-0.5 inline-flex w-28 shrink-0 items-center gap-1.5 text-xs font-medium" style={{ color: KIND_LABEL[item.kind].color }}>
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: KIND_LABEL[item.kind].color }} aria-hidden="true" />
                    {KIND_LABEL[item.kind].label}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{item.title}</span>
                    <span className="line-clamp-2 block text-xs text-muted-foreground">{item.detail}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-2xl border border-border/70 p-4">
        <p className="text-sm font-medium">Trending toward higher risk</p>
        <p className="mb-3 text-xs text-muted-foreground">Early warning: authorities whose recent scores point to a worse risk level</p>
        {trending.length === 0 ? (
          <p className="text-sm text-muted-foreground">No authority is trending worse.</p>
        ) : (
          <ul className="divide-y divide-border/60">
            {trending.map((item) => {
              const isOpen = openTrend === item.wsa_id;
              return (
                <li key={item.wsa_id}>
                  <button type="button" aria-expanded={isOpen} onClick={() => toggleTrend(item.wsa_id)} className="flex w-full items-center justify-between gap-3 py-3 text-left hover:bg-secondary/40">
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium">{item.name}</span>
                      <span className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                        {item.current_risk_level ? <RiskBadge riskLevel={item.current_risk_level} compact /> : null}
                        <span aria-hidden="true">→</span>
                        {item.projected_risk_level ? <RiskBadge riskLevel={item.projected_risk_level} compact /> : null}
                        <span>projected {((item.projected_probability ?? 0) * 100).toFixed(0)}%</span>
                      </span>
                    </span>
                    <span className="flex shrink-0 items-center gap-1 text-xs text-primary">
                      {isOpen ? "Hide" : "Why?"}
                      <ChevronDown className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")} />
                    </span>
                  </button>
                  {isOpen ? (
                    <div className="pb-3">
                      {trendError[item.wsa_id] ? (
                        <p className="text-xs text-destructive">{trendError[item.wsa_id]}</p>
                      ) : (
                        <AITextBlock label="AI explanation" content={trendText[item.wsa_id]} loading={!trendText[item.wsa_id]} />
                      )}
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-border/70 p-4">
          <p className="text-sm font-medium">Risk across all authorities</p>
          <p className="mb-3 text-xs text-muted-foreground">{s.total} authorities by risk level</p>
          <StackedBar segments={risk} />
        </div>
        <div className="rounded-2xl border border-border/70 p-4">
          <p className="text-sm font-medium">Blue Drop drinking-water quality</p>
          <p className="mb-3 text-xs text-muted-foreground">Authorities by DWS certification band</p>
          <StackedBar segments={bands} />
        </div>
      </div>

      <div className="rounded-2xl border border-border/70 p-4">
        <p className="text-sm font-medium">Risk by province</p>
        <p className="mb-3 text-xs text-muted-foreground">Provinces with the most high-risk authorities first</p>
        <div className="space-y-2">
          {provinces.map((row) => (
            <div key={row.province} className="grid grid-cols-[8rem_1fr_6rem] items-center gap-3 text-xs sm:grid-cols-[11rem_1fr_6rem]">
              <span className="truncate" title={row.province}>{row.province}</span>
              <div className="flex h-3 overflow-hidden rounded-full bg-secondary" role="img" aria-label={`${row.province}: ${row.high} high, ${row.medium} medium, ${row.low} low`}>
                {[["high", "#dc2626"], ["medium", "#f59e0b"], ["low", "#16a34a"]].map(([level, color]) => {
                  const n = row[level as RiskLevel];
                  return n ? <div key={level} title={`${level}: ${n}`} style={{ width: `${(n / row.total) * 100}%`, backgroundColor: color }} /> : null;
                })}
              </div>
              <span className="text-right text-muted-foreground"><span className="font-semibold text-foreground">{row.high}</span> high of {row.total}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex gap-4 text-xs text-muted-foreground">
          {[["High", "#dc2626"], ["Medium", "#f59e0b"], ["Low", "#16a34a"]].map(([l, c]) => (
            <span key={l} className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: c }} aria-hidden="true" />{l}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
