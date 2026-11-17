import type { WSA } from "@/api/wsa";

export interface ProvinceRisk { province: string; high: number; medium: number; low: number; total: number }

// authorities per province split by risk level, the province with the most high-risk authorities first
export function riskByProvince(wsas: WSA[]): ProvinceRisk[] {
  const map = new Map<string, ProvinceRisk>();
  for (const w of wsas) {
    const row = map.get(w.province) ?? { province: w.province, high: 0, medium: 0, low: 0, total: 0 };
    row[w.risk_level] += 1;
    row.total += 1;
    map.set(w.province, row);
  }
  return [...map.values()].sort((a, b) => b.high - a.high || b.medium - a.medium || a.province.localeCompare(b.province));
}
