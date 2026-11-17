import type { WSA } from "@/api/wsa";

// how many of the four indicators we actually have for an authority. shown as a '3/4 data' badge so people can see when the data is thin
export function dataCompleteness(wsa: WSA): { filled: number; total: number } {
  const fields = [wsa.blue_drop_score, wsa.green_drop_score, wsa.nrw_percent, wsa.maint_pct];
  return { filled: fields.filter((v) => v !== null).length, total: fields.length };
}
