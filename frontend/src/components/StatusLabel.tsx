import type { CaseStatus } from "@/api/reports";

const DOT: Record<CaseStatus, string> = { open: "#f59e0b", in_review: "#0ea5e9", resolved: "#16a34a" };

// Case status as a coloured dot plus plain text, instead of a filled pill, so tables stay quiet.
export function StatusLabel({ status }: { status: CaseStatus }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-sm font-medium capitalize">
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: DOT[status] }} aria-hidden="true" />
      {status.replace("_", " ")}
    </span>
  );
}
