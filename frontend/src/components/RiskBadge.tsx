import { Badge } from "@/components/ui/badge";
import type { RiskLevel } from "@/api/wsa";

const riskLabelMap: Record<RiskLevel, string> = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

const riskClassMap: Record<RiskLevel, string> = {
  low: "border-emerald-200 bg-emerald-100 text-emerald-800",
  medium: "border-amber-200 bg-amber-100 text-amber-800",
  high: "border-rose-200 bg-rose-100 text-rose-800",
};

interface RiskBadgeProps {
  riskLevel: RiskLevel;
}

export function RiskBadge({ riskLevel }: RiskBadgeProps) {
  return <Badge className={riskClassMap[riskLevel]} variant="outline">{riskLabelMap[riskLevel]}</Badge>;
}
