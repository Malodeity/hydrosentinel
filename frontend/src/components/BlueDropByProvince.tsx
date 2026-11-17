import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { blueDropBand } from "@/lib/overviewStats";
import type { ProvinceBlueDrop } from "@/lib/provinceBlueDrop";

const BAND_COLOR = { certified: "#16a34a", non_certified: "#f59e0b", poor: "#f97316", critical: "#dc2626", unknown: "#94a3b8" } as const;

// Average Blue Drop score per province. Bars take the colour of the DWS band their average falls in, and a line marks 95, the score needed for certification
export function BlueDropByProvince({ rows }: { rows: ProvinceBlueDrop[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Drinking water quality by province</CardTitle>
        <CardDescription>Average Blue Drop score. 95 or more is certified, below 31 is critical.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map(({ province, average, count }) => (
          <div key={province}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="text-foreground">{province}</span>
              <span className="font-medium text-foreground">
                {average.toFixed(0)}% <span className="text-xs font-normal text-muted-foreground">from {count} authorities</span>
              </span>
            </div>
            <div className="relative h-2.5 overflow-hidden rounded-full bg-secondary/70" role="img" aria-label={`${province}: ${average.toFixed(0)} percent`}>
              <div className="h-full rounded-full" style={{ width: `${average}%`, backgroundColor: BAND_COLOR[blueDropBand(average)] }} />
              <div className="absolute inset-y-0 w-px bg-foreground/60" style={{ left: "95%" }} aria-hidden="true" />
            </div>
          </div>
        ))}
        <div className="flex flex-wrap gap-x-3 gap-y-1 pt-1 text-xs text-muted-foreground">
          {[["Certified", "certified"], ["Non-certified", "non_certified"], ["Poor", "poor"], ["Critical", "critical"]].map(([label, band]) => (
            <span key={band} className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: BAND_COLOR[band as keyof typeof BAND_COLOR] }} aria-hidden="true" />
              {label}
            </span>
          ))}
          <span>| line = 95</span>
        </div>
      </CardContent>
    </Card>
  );
}
