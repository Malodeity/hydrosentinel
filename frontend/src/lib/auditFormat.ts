// "cap_status_updated" -> "CAP status updated"
export function formatAuditAction(action: string): string {
  const words = action.replace(/_/g, " ");
  return (words.charAt(0).toUpperCase() + words.slice(1)).replace(/\bcap\b/gi, "CAP");
}

// {"case_status":"open","admin_comment":null} -> "case_status: open · admin_comment: none", readable without opening a JSON blob
// Long values (an AI-written case note is ~600 characters) are cut at maxLength so one entry never takes over the table;
// pass Infinity to get the full text, e.g. for a hover tooltip.
export function formatAuditValue(value: Record<string, unknown> | null, maxLength = 80): string {
  if (!value) return "—";
  const entries = Object.entries(value);
  if (entries.length === 0) return "—";
  return entries
    .map(([key, item]) => {
      const text = item === null || item === undefined || item === "" ? "none" : typeof item === "object" ? JSON.stringify(item) : String(item);
      return `${key}: ${text.length > maxLength ? `${text.slice(0, maxLength).trimEnd()}…` : text}`;
    })
    .join(" · ");
}
