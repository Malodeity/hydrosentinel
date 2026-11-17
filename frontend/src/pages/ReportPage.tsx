// The resident page: submit a report (components/ReportForm.tsx), see the reference code and a short AI reply, and look up a report's status by code.
// Only the status and the admin's note are shown back: never the description, photos or location.

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { fetchWsaReportContext } from "@/api/ai";
import { createCitizenReport, trackCitizenReport, type CaseStatus, type CitizenReportTrackStatus } from "@/api/reports";
import { fetchWsas, type WSA } from "@/api/wsa";
import { AITextBlock } from "@/components/AITextBlock";
import { ReportForm } from "@/components/ReportForm";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

const caseStatusClassMap: Record<CaseStatus, string> = {
  open: "border-amber-200 bg-amber-100 text-amber-800",
  in_review: "border-sky-200 bg-sky-100 text-sky-800",
  resolved: "border-emerald-200 bg-emerald-100 text-emerald-800",
};

// the public citizen page: submit a report, get a reference code and a short AI reply, and track a report by its code. no login needed
export function ReportPage() {
  const [searchParams] = useSearchParams();
  const [wsas, setWsas] = useState<WSA[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [referenceCode, setReferenceCode] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // true while the authority list loads and while the AI reply is being written, so the page never looks frozen
  const [isLoadingWsas, setIsLoadingWsas] = useState(true);
  const [isAiLoading, setIsAiLoading] = useState(false);

  const [trackInput, setTrackInput] = useState("");
  const [trackResult, setTrackResult] = useState<CitizenReportTrackStatus | null>(null);
  const [trackError, setTrackError] = useState<string | null>(null);
  const [isTracking, setIsTracking] = useState(false);

  const hasStatusContent = Boolean(statusMessage || aiResponse || errorMessage || isAiLoading);

  useEffect(() => {
    // load the authorities once, for the province and authority dropdowns
    fetchWsas()
      .then(setWsas)
      .catch(() => setErrorMessage("Unable to load WSA options."))
      .finally(() => setIsLoadingWsas(false));
  }, []);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Report an issue</CardTitle>
          <CardDescription>Leaks, outages, water quality, or billing</CardDescription>
        </CardHeader>
        {hasStatusContent ? (
          <CardContent className="space-y-4">
            {statusMessage ? (
              <div className="rounded-3xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">
                <p>{statusMessage}</p>
                {referenceCode ? (
                  <p className="mt-2">
                    Your reference code: <span className="font-mono font-semibold">{referenceCode}</span> — save it to check your report's status below.
                  </p>
                ) : null}
              </div>
            ) : null}
            <AITextBlock content={aiResponse} label="AI response" loading={isAiLoading} />
            {errorMessage ? (
              <div className="rounded-3xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{errorMessage}</div>
            ) : null}
          </CardContent>
        ) : null}
      </Card>

      {/* the form validates itself; on submit we save the report first, then ask the AI for a short reply. if the AI fails the report is still saved */}
      {isLoadingWsas ? (
        <Card aria-busy="true">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              Loading the report form...
            </CardTitle>
            <CardDescription>Getting the list of water authorities</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-11 w-full" />
            <Skeleton className="h-11 w-full" />
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
      ) : (
      <ReportForm
        wsas={wsas}
        initialWsaId={searchParams.get("wsa") ?? undefined}
        isSubmitting={isSubmitting}
        onSubmit={async (payload, photos) => {
          setIsSubmitting(true);
          setStatusMessage(null);
          setReferenceCode(null);
          setAiResponse(null);
          setErrorMessage(null);
          try {
            const report = await createCitizenReport(payload, photos);
            setStatusMessage("Report submitted successfully. Thank you for contributing to accountability tracking.");
            setReferenceCode(report.reference_code);
            // the confirmation sits at the top of the page, so bring it into view (plain scroll: smooth is unreliable)
            window.scrollTo(0, 0);
            setIsAiLoading(true);
            try {
              // targeted context uses the actual issue type for a relevant response
              const context = await fetchWsaReportContext(payload.wsa_id, payload.issue_type);
              setAiResponse(context.content);
            } catch {
              setAiResponse(null);
            } finally {
              setIsAiLoading(false);
            }
          } catch {
            setErrorMessage("We could not submit the report right now. Please try again.");
          } finally {
            setIsSubmitting(false);
          }
        }}
      />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Track a report</CardTitle>
          <CardDescription>Enter your reference code</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row">
            <Input
              placeholder="HS-XXXXXXXX"
              value={trackInput}
              onChange={(event) => setTrackInput(event.target.value.toUpperCase())}
              className="font-mono"
            />
            <Button
              onClick={async () => {
                setTrackError(null);
                setTrackResult(null);
                setIsTracking(true);
                try {
                  const result = await trackCitizenReport(trackInput.trim());
                  setTrackResult(result);
                } catch {
                  setTrackError("No report found with that reference code.");
                } finally {
                  setIsTracking(false);
                }
              }}
              disabled={!trackInput.trim() || isTracking}
            >
              {isTracking ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Checking...
                </>
              ) : (
                "Check status"
              )}
            </Button>
          </div>
          {trackError ? <p className="text-sm text-destructive">{trackError}</p> : null}
          {trackResult ? (
            <div className="rounded-2xl bg-secondary/60 p-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium capitalize">{trackResult.issue_type}</span>
                <Badge className={caseStatusClassMap[trackResult.case_status]} variant="outline">
                  {trackResult.case_status.replace("_", " ")}
                </Badge>
              </div>
              <p className="mt-2 text-muted-foreground">Submitted {new Date(trackResult.created_at).toLocaleString()}</p>
              {trackResult.admin_comment ? <p className="mt-2">{trackResult.admin_comment}</p> : null}
              {trackResult.repair_status ? (
                <p className="mt-2 font-medium">
                  {trackResult.repair_status === "awaiting_check"
                    ? "A repair team says the work is done. The authority is checking it."
                    : trackResult.repair_status === "in_progress"
                      ? "A repair team is working on this."
                      : "A repair team has been assigned."}
                  {trackResult.repair_due_at && trackResult.repair_status !== "awaiting_check" ? (
                    <span className="font-normal text-muted-foreground"> Aim: {new Date(trackResult.repair_due_at).toLocaleDateString("en-ZA", { day: "numeric", month: "short" })}.</span>
                  ) : null}
                </p>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
