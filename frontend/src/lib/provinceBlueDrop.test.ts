import { describe, expect, it } from "vitest";

import type { WSA } from "@/api/wsa";
import { provinceBlueDrop } from "@/lib/provinceBlueDrop";

const w = (province: string, blue_drop_score: number | null) => ({ province, blue_drop_score }) as WSA;

describe("provinceBlueDrop", () => {
  it("averages only authorities that have a score and says how many it used", () => {
    const rows = provinceBlueDrop([w("A", 80), w("A", 40), w("A", null), w("B", 90)]);
    expect(rows.find((r) => r.province === "A")).toEqual({ province: "A", average: 60, count: 2 });
  });
  it("lists the best province first and leaves out a province with no scores", () => {
    expect(provinceBlueDrop([w("A", 10), w("B", 90), w("C", null)]).map((r) => r.province)).toEqual(["B", "A"]);
  });
});
