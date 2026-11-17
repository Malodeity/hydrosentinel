import type { RiskLevel } from "@/api/wsa";

const LEVEL: Record<RiskLevel, number> = { low: 0, medium: 1, high: 2 };

// Direction of an authority's risk over its scoring history (newest first, as the API returns it).
// It compares risk LEVELS, not probabilities: the model's probability means "chance of high risk" for the fallback
// rule but "confidence in the predicted level" for XGBoost, so plotting it as one line would mislead.
export function riskTrend(newestFirst: { risk_level: RiskLevel }[]) {
  const levels = [...newestFirst].reverse().map((entry) => entry.risk_level);
  if (levels.length < 2) return null;
  const from = levels[0];
  const to = levels[levels.length - 1];
  const direction = LEVEL[to] > LEVEL[from] ? "worse" : LEVEL[to] < LEVEL[from] ? "better" : "unchanged";
  return { direction, from, to, levels, count: levels.length } as const;
}
