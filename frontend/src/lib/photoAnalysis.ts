// Turns the server's photo verdict (matches / mismatch / inconclusive) into the sentence an admin reads.

import type { IssueType, PhotoAnalysis } from "@/api/reports";

export type VerdictTone = "good" | "warn" | "neutral";

const WHAT_IT_SHOWS: Record<PhotoAnalysis["issue_type"], string> = {
  leak: "a leak",
  quality: "a water quality problem",
  outage: "an outage (a dry tap or empty infrastructure)",
  not_water_related: "no water service problem",
  unclear: "something unclear",
};

const WHAT_WAS_REPORTED: Record<IssueType, string> = {
  leak: "a leak",
  outage: "an outage",
  quality: "a water quality problem",
  billing: "a billing problem",
};

export function describeIssue(issue: PhotoAnalysis["issue_type"]): string {
  return WHAT_IT_SHOWS[issue];
}

// Turns the server's verdict into the sentence an admin reads. The wording matters: a photo can only support or contradict a report,
// it can never prove a report false, and a billing report cannot be checked from a photo at all.
export function describeVerdict(analysis: PhotoAnalysis, reported: IssueType): { tone: VerdictTone; title: string; detail: string } {
  if (analysis.verdict === "matches") {
    return { tone: "good", title: "The photo agrees with the report", detail: `It shows ${describeIssue(analysis.issue_type)}, as the resident reported.` };
  }
  if (analysis.verdict === "mismatch") {
    return {
      tone: "warn",
      title: "The photo does not match the report",
      detail: `It shows ${describeIssue(analysis.issue_type)}, but the resident reported ${WHAT_WAS_REPORTED[reported]}. Look at the photo before acting.`,
    };
  }
  return {
    tone: "neutral",
    title: "The photo cannot confirm or contradict the report",
    detail: reported === "billing" ? "Billing problems cannot be checked from a photo." : "The photo is too unclear to say what it shows.",
  };
}
