import type { WSA } from "@/api/wsa";

export interface ProvinceBlueDrop { province: string; average: number; count: number }

// average Blue Drop score per province, using only authorities that have a score, best province first.
// `count` is how many authorities the average rests on, so a province with two scored authorities is not mistaken for a solid figure
export function provinceBlueDrop(wsas: WSA[]): ProvinceBlueDrop[] {
  const scores = new Map<string, number[]>();
  for (const wsa of wsas) {
    if (wsa.blue_drop_score === null) continue;
    scores.set(wsa.province, [...(scores.get(wsa.province) ?? []), wsa.blue_drop_score]);
  }
  return [...scores.entries()]
    .map(([province, list]) => ({ province, average: list.reduce((a, b) => a + b, 0) / list.length, count: list.length }))
    .sort((a, b) => b.average - a.average);
}
