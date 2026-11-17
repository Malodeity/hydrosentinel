import { describe, expect, it } from "vitest";

import type { WSA } from "@/api/wsa";
import { riskByProvince } from "@/lib/riskByProvince";

const w = (province: string, risk_level: WSA["risk_level"]) => ({ province, risk_level }) as WSA;

describe("riskByProvince", () => {
  it("counts risk levels per province and lists the province with the most high-risk authorities first", () => {
    const rows = riskByProvince([w("A", "low"), w("B", "high"), w("B", "high"), w("A", "high"), w("B", "low")]);
    expect(rows.map((r) => r.province)).toEqual(["B", "A"]);
    expect(rows[0]).toMatchObject({ high: 2, low: 1, total: 3 });
  });
});
