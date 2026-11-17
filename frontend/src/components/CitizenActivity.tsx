import type { PublicReportStats } from "@/api/reports";

// What residents are reporting and how it is going, as three plain numbers. Counts only, from the public stats endpoint.
export function CitizenActivity({ stats }: { stats: PublicReportStats }) {
  const share = stats.total ? Math.round((stats.resolved / stats.total) * 100) : 0;
  const items = [
    { label: "Reports in the past 7 days", value: String(stats.received_7d), hint: `${stats.total} received in total` },
    { label: "Resolved", value: `${share}%`, hint: `${stats.resolved} of ${stats.total} reports` },
    {
      label: "Typical time to resolve",
      value: stats.median_days_to_resolve === null ? "Not yet known" : `${stats.median_days_to_resolve} days`,
      hint: stats.median_days_to_resolve === null ? "No resolved report has a recorded time" : `Median of ${stats.resolved_sample} resolved reports`,
    },
  ];
  return (
    <div className="rounded-2xl bg-card p-4 shadow-soft">
      <p className="text-sm font-medium">What residents are reporting</p>
      <div className="mt-3 grid gap-4 sm:grid-cols-3">
        {items.map((item) => (
          <div key={item.label}>
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className={item.value === "Not yet known" ? "mt-0.5 text-lg font-semibold text-muted-foreground" : "mt-0.5 text-2xl font-semibold"}>{item.value}</p>
            <p className="text-xs text-muted-foreground">{item.hint}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
