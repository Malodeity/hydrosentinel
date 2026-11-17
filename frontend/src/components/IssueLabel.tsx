import type { IssueType } from "@/api/reports";

// one colour per issue type; square marker (status and age use round dots) so the two are never confused
const ISSUE_COLOR: Record<IssueType, string> = { leak: "#0284c7", outage: "#475569", quality: "#0d9488", billing: "#a16207" };

export function IssueLabel({ type }: { type: IssueType }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-medium capitalize" style={{ color: ISSUE_COLOR[type] }}>
      <span className="h-2 w-2 rounded-[2px]" style={{ backgroundColor: ISSUE_COLOR[type] }} aria-hidden="true" />
      {type}
    </span>
  );
}
