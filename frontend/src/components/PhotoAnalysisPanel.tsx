// The 'AI photo check' box in a report's detail: a button, the saved result, and the wording of the verdict (lib/photoAnalysis.ts).
// The verdict itself is decided by the server (backend routes/ai.py), not by the AI.

import { useState } from "react";
import { Loader2, ScanSearch } from "lucide-react";

import { analyzeReportPhoto } from "@/api/ai";
import type { CitizenReport, PhotoAnalysis } from "@/api/reports";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { describeIssue, describeVerdict, type VerdictTone } from "@/lib/photoAnalysis";
import { cn } from "@/lib/utils";

const TONE_STYLES: Record<VerdictTone, { border: string; badge: string }> = {
  good: { border: "#16a34a", badge: "border-emerald-200 bg-emerald-100 text-emerald-800" },
  warn: { border: "#f59e0b", badge: "border-amber-200 bg-amber-100 text-amber-900" },
  neutral: { border: "#94a3b8", badge: "border-slate-200 bg-slate-100 text-slate-700" },
};

interface PhotoAnalysisPanelProps {
  report: CitizenReport;
  onAnalysed: (analysis: PhotoAnalysis) => void;
  onError: (message: string) => void;
}

// The "AI photo check" box in a report's detail. It is a button, not automatic, because each check sends the photo to OpenAI,
// costs an AI call and counts towards the hourly limit. The saved result is shown again whenever the report is opened.
export function PhotoAnalysisPanel({ report, onAnalysed, onError }: PhotoAnalysisPanelProps) {
  const [photoIndex, setPhotoIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const analysis = report.photo_analysis ?? null;
  const photoCount = report.photo_urls.length;

  const analyse = async () => {
    setLoading(true);
    try {
      onAnalysed(await analyzeReportPhoto(report.id, photoIndex));
    } catch (error) {
      const status = (error as { response?: { status?: number } }).response?.status;
      onError(
        status === 429
          ? "AI limit reached (20 per hour). Try again later."
          : status === 413
            ? "That photo is too large to analyse."
            : "The photo could not be analysed right now.",
      );
    } finally {
      setLoading(false);
    }
  };

  const verdict = analysis ? describeVerdict(analysis, report.issue_type) : null;

  return (
    <div className="space-y-3 rounded-2xl border border-border/70 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-md">
          <p className="text-sm font-medium">AI photo check</p>
          <p className="text-xs text-muted-foreground">Sends the photo to OpenAI to see what it shows. It can be wrong, so always look at the photo yourself.</p>
        </div>
        <div className="flex items-center gap-2">
          {photoCount > 1 ? (
            <select
              aria-label="Photo to analyse"
              className="h-9 rounded-full border border-border bg-white px-3 text-sm"
              value={photoIndex}
              onChange={(event) => setPhotoIndex(Number(event.target.value))}
            >
              {report.photo_urls.map((url, index) => (
                <option key={url} value={index}>
                  Photo {index + 1}
                </option>
              ))}
            </select>
          ) : null}
          <Button size="sm" variant="outline" disabled={loading} onClick={analyse}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
            {analysis ? "Analyse again" : "Analyse photo"}
          </Button>
        </div>
      </div>

      {analysis && verdict ? (
        <div className="rounded-2xl border-l-4 bg-secondary/50 p-4 text-sm" style={{ borderLeftColor: TONE_STYLES[verdict.tone].border }}>
          <p className="font-semibold">{verdict.title}</p>
          <p className="mt-0.5 text-muted-foreground">{verdict.detail}</p>
          {analysis.summary ? <p className="mt-2 text-foreground">{analysis.summary}</p> : null}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant="outline" className={cn("first-letter:uppercase", TONE_STYLES[verdict.tone].badge)}>
              Looks like: {describeIssue(analysis.issue_type).replace(/^an? /, "")}
            </Badge>
            <Badge variant="outline">Severity: {analysis.severity}</Badge>
            <Badge variant="outline">Confidence: {analysis.confidence}</Badge>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Checked {analysis.photo} on {new Date(analysis.analysed_at).toLocaleString()}
          </p>
        </div>
      ) : null}
    </div>
  );
}
