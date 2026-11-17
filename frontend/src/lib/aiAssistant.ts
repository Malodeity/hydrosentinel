// Wording helpers for the AI assistant tab: plain names for the data the AI looked at, and one place that turns an error into a sentence.

const TOOL_LABELS: Record<string, string> = {
  get_wsas: "authority list",
  count_wsas: "authority count",
  get_overdue_caps: "overdue plans",
  get_open_reports: "open reports",
  get_wsa_detail: "authority detail",
  get_trending_wsas: "risk trends",
  get_report_counts: "report counts",
  get_alerts: "alerts",
  get_audit_summary: "audit log",
  compare_provinces: "province comparison",
};

// "get_open_reports" -> "open reports"; an unknown tool falls back to its own name so nothing is hidden
export function toolLabel(tool: string): string {
  return TOOL_LABELS[tool] ?? tool.replace(/_/g, " ");
}

// the distinct things the AI looked at, in the order it looked, e.g. "authority count, open reports"
export function describeChecked(tools: { tool: string }[]): string {
  return [...new Set(tools.map((t) => toolLabel(t.tool)))].join(", ");
}

// what to tell the admin when an AI call fails; the hourly limit and a missing key are the two they can act on
export function aiErrorMessage(error: unknown, fallback: string): string {
  const status = (error as { response?: { status?: number } })?.response?.status;
  if (status === 429) return "You have used this hour's AI allowance. It frees up gradually, see the meter above.";
  if (status === 503) return "The AI service is not configured (no OpenAI key on the server).";
  return fallback;
}

// the meter turns amber when few calls remain, so the limit is never a surprise
export function usageTone(used: number, limit: number): "ok" | "low" | "empty" {
  if (used >= limit) return "empty";
  return limit - used <= 5 ? "low" : "ok";
}
