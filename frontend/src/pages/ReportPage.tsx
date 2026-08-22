import { useEffect, useState } from "react";

import { fetchWsaReportContext } from "@/api/ai";
import { createCitizenReport, trackCitizenReport, type CitizenReportTrackStatus } from "@/api/reports";
import { fetchWsas, type WSA } from "@/api/wsa";
import { AITextBlock } from "@/components/AITextBlock";
import { ReportForm } from "@/components/ReportForm";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function ReportPage() {
  const [wsas, setWsas] = useState<WSA[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [referenceCode, setReferenceCode] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [trackInput, setTrackInput] = useState("");
  const [trackResult, setTrackResult] = useState<CitizenReportTrackStatus | null>(null);
  const [trackError, setTrackError] = useState<string | null>(null);

  useEffect(() => {
    fetchWsas().then(setWsas).catch(() => setErrorMessage("Unable to load WSA options."));
  }, []);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Citizen issue reporting</CardTitle>
          <CardDescription>Residents can log leaks, outages, water quality problems, or billing issues with a precise map location.</CardDescription>
        </CardHeader>
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
          <AITextBlock content={aiResponse} label="AI response" />
          {errorMessage ? (
            <div className="rounded-3xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{errorMessage}</div>
          ) : null}
        </CardContent>
      </Card>

      <ReportForm
        wsas={wsas}
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
            try {
              // targeted context uses the actual issue type for a relevant response
              const context = await fetchWsaReportContext(payload.wsa_id, payload.issue_type);
              setAiResponse(context.content);
            } catch {
              setAiResponse(null);
            }
          } catch {
            setErrorMessage("We could not submit the report right now. Please try again.");
          } finally {
            setIsSubmitting(false);
          }
        }}
      />

      <Card>
        <CardHeader>
          <CardTitle>Track a report</CardTitle>
          <CardDescription>Enter your reference code to check the status of a report you submitted.</CardDescription>
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
                try {
                  const result = await trackCitizenReport(trackInput.trim());
                  setTrackResult(result);
                } catch {
                  setTrackError("No report found with that reference code.");
                }
              }}
              disabled={!trackInput.trim()}
            >
              Check status
            </Button>
          </div>
          {trackError ? <p className="text-sm text-destructive">{trackError}</p> : null}
          {trackResult ? (
            <div className="rounded-2xl bg-secondary/60 p-4 text-sm">
              <p>
                <span className="font-medium capitalize">{trackResult.issue_type}</span> report — status:{" "}
                <span className="font-medium capitalize">{trackResult.case_status.replace("_", " ")}</span>
              </p>
              <p className="mt-1 text-muted-foreground">Submitted {new Date(trackResult.created_at).toLocaleString()}</p>
              {trackResult.admin_comment ? <p className="mt-2">{trackResult.admin_comment}</p> : null}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
