// The authority card on the public dashboard: scores with their Blue Drop band, 'what this rating is based on' (lib/ratingFacts.ts), the plan and its deadline,
// resident report counts, the AI 'Explain this rating' button (components/WsaInsight.tsx) and the 'Report a problem' link.

import { Droplets, Gauge, ShieldCheck, Wrench } from "lucide-react";
import { Link } from "react-router-dom";

import type { WSA } from "@/api/wsa";
import { RiskBadge } from "@/components/RiskBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { describeDeadline } from "@/lib/capDeadline";
import { dataCompleteness } from "@/lib/dataCompleteness";
import { BLUE_DROP_BAND_TEXT, blueDropBand, type BlueDropBand } from "@/lib/overviewStats";
import { ratingFacts } from "@/lib/ratingFacts";
import { WsaInsight } from "@/components/WsaInsight";

// kept here so existing imports keep working
export { dataCompleteness };

interface WSACardProps {
  wsa: WSA | null;
  reportCounts?: { open: number; resolved: number }; // residents' reports for this authority (counts only)
}

const BAND_COLOR: Record<BlueDropBand, string> = { certified: "#16a34a", non_certified: "#f59e0b", poor: "#f97316", critical: "#dc2626", unknown: "#94a3b8" };
const CAP_DOT = { none: "#94a3b8", submitted: "#0ea5e9", in_progress: "#f59e0b", completed: "#16a34a" } as const;

function formatValue(value: number | null, suffix = "%") {
  return value === null ? "No data" : `${value}${suffix}`;
}

// the side card on the dashboard: the selected authority's indicators, what its risk level rests on, and its corrective action plan
export function WSACard({ wsa, reportCounts }: WSACardProps) {
  if (!wsa) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle>Select a WSA</CardTitle>
          <CardDescription>Click a marker on the map to inspect service indicators and CAP status.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const band = blueDropBand(wsa.blue_drop_score);
  const deadline = describeDeadline(wsa.cap_status, wsa.cap_due_date);
  const { filled, total } = dataCompleteness(wsa);

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{wsa.name}</CardTitle>
            <CardDescription>{wsa.province}</CardDescription>
          </div>
          <div className="flex flex-col items-end gap-2">
            <RiskBadge riskLevel={wsa.risk_level} />
            {filled < total ? (
              <Badge variant="outline" className="text-xs font-normal text-muted-foreground" title="Some source data is missing for this authority, so its rating is less reliable">
                {filled}/{total} data
              </Badge>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-3xl bg-secondary/60 p-4">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Droplets className="h-4 w-4 text-primary" />
            Blue Drop (drinking water quality)
          </div>
          <p className="mt-2 text-2xl font-semibold">{formatValue(wsa.blue_drop_score)}</p>
          <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: BAND_COLOR[band] }} aria-hidden="true" />
            <span className="font-semibold text-foreground">{BLUE_DROP_BAND_TEXT[band]}</span>
            {band !== "unknown" ? " · certification needs 95" : " · not reported"}
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {[
            { label: "Green Drop", hint: "wastewater", icon: Droplets, value: wsa.green_drop_score },
            // no NRW of its own: show the province average with a ~ and say so, never as if it were this authority's figure
            { label: "NRW", hint: wsa.nrw_percent === null && wsa.nrw_estimate_percent != null ? "province average" : "water lost", icon: Gauge, value: wsa.nrw_percent ?? wsa.nrw_estimate_percent ?? null, approx: wsa.nrw_percent === null && wsa.nrw_estimate_percent != null, note: wsa.nrw_estimate_note ?? undefined },
            { label: "Maintenance", hint: "of spend", icon: Wrench, value: wsa.maint_pct },
          ].map(({ label, hint, icon: Icon, value, approx, note }) => (
            <div key={label} className="rounded-3xl bg-secondary/60 p-3" title={approx ? note : undefined}>
              <div className="flex items-center gap-1.5 text-xs font-medium">
                <Icon className="h-3.5 w-3.5 text-primary" />
                {label}
              </div>
              <p className={value === null ? "mt-1.5 text-sm text-muted-foreground" : "mt-1.5 text-lg font-semibold"}>{approx && value !== null ? `~${value}%` : formatValue(value)}</p>
              <p className="text-[11px] text-muted-foreground">{hint}</p>
            </div>
          ))}
        </div>

        <div>
          <p className="mb-1.5 text-sm font-medium">What this rating is based on</p>
          <ul className="space-y-1 text-sm text-muted-foreground">
            {ratingFacts(wsa).map((fact) => (
              <li key={fact} className="flex gap-2">
                <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted-foreground" aria-hidden="true" />
                {fact}
              </li>
            ))}
          </ul>
        </div>

        <WsaInsight wsaId={wsa.id} />

        <div className="flex items-start gap-3 rounded-3xl border border-border/80 bg-background/70 p-4">
          <ShieldCheck className="mt-0.5 h-5 w-5 text-primary" />
          <div className="space-y-0.5">
            <p className="text-sm font-medium">Corrective action plan</p>
            <p className="inline-flex items-center gap-1.5 text-sm first-letter:uppercase">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: CAP_DOT[wsa.cap_status] }} aria-hidden="true" />
              {wsa.cap_status === "none" ? "No plan submitted" : wsa.cap_status.replace("_", " ")}
            </p>
            {wsa.cap_status !== "none" ? <p className={deadline.tone === "overdue" ? "text-xs font-semibold text-rose-700" : "text-xs text-muted-foreground"}>{deadline.text}</p> : null}
          </div>
        </div>

        {reportCounts ? (
          <p className="text-sm text-muted-foreground">
            Reports from residents: <span className="font-semibold text-foreground">{reportCounts.open} open</span>, {reportCounts.resolved} resolved
          </p>
        ) : null}

        <Button asChild variant="outline" className="w-full">
          <Link to={`/reports?wsa=${wsa.id}`}>Report a problem in {wsa.name}</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
