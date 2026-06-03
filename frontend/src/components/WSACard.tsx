import { Droplets, Gauge, MapPin, ShieldCheck, Wrench } from "lucide-react";

import type { WSA } from "@/api/wsa";
import { RiskBadge } from "@/components/RiskBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface WSACardProps {
  wsa: WSA | null;
}

function formatValue(value: number | null, suffix = "%") {
  return value === null ? "Not available" : `${value}${suffix}`;
}

export function WSACard({ wsa }: WSACardProps) {
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

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{wsa.name}</CardTitle>
            <CardDescription>{wsa.province}</CardDescription>
          </div>
          <RiskBadge riskLevel={wsa.risk_level} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-3xl bg-secondary/60 p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Droplets className="h-4 w-4 text-primary" />
              Blue Drop
            </div>
            <p className="mt-2 text-2xl font-semibold">{formatValue(wsa.blue_drop_score)}</p>
          </div>
          <div className="rounded-3xl bg-secondary/60 p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Gauge className="h-4 w-4 text-primary" />
              NRW
            </div>
            <p className="mt-2 text-2xl font-semibold">{formatValue(wsa.nrw_percent)}</p>
          </div>
          <div className="rounded-3xl bg-secondary/60 p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Wrench className="h-4 w-4 text-primary" />
              Maintenance
            </div>
            <p className="mt-2 text-2xl font-semibold">{formatValue(wsa.maint_pct)}</p>
          </div>
          <div className="rounded-3xl bg-secondary/60 p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <MapPin className="h-4 w-4 text-primary" />
              Location
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {wsa.lat.toFixed(4)}, {wsa.lng.toFixed(4)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-3xl border border-border/80 bg-background/70 p-4">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <div className="space-y-1">
            <p className="text-sm font-medium">Corrective Action Plan</p>
            <Badge variant="secondary" className="capitalize">
              {wsa.cap_status.replace("_", " ")}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
