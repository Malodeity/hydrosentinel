import { useEffect, useState } from "react";

import { fetchWsaReportContext } from "@/api/ai";
import { createCitizenReport } from "@/api/reports";
import { fetchWsas, type WSA } from "@/api/wsa";
import { AITextBlock } from "@/components/AITextBlock";
import { ReportForm } from "@/components/ReportForm";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ReportPage() {
  const [wsas, setWsas] = useState<WSA[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
            <div className="rounded-3xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">{statusMessage}</div>
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
          setAiResponse(null);
          setErrorMessage(null);
          try {
            await createCitizenReport(payload, photos);
            setStatusMessage("Report submitted successfully. Thank you for contributing to accountability tracking.");
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
    </div>
  );
}
