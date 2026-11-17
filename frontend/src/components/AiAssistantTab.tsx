// The whole AI assistant tab (admin). Sections, top to bottom: today's briefing, ask the data (suggestions + short history), ask the regulations,
// and AI tools for one chosen authority. Nothing runs by itself: each button is one OpenAI call, and the meter at the top shows the hourly allowance.
// Backend: app/routes/ai.py and ai/query_agent.py. Wording helpers: lib/aiAssistant.ts.

import { useCallback, useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";

import {
  askAiQuery,
  fetchAdminBriefing,
  fetchAiUsage,
  fetchRegulatoryContext,
  fetchReportsSummary,
  fetchRiskExplanation,
  fetchTrendExplanation,
  fetchWsaRecommendations,
  type AIQueryResponse,
  type AdminBriefing,
  type AiUsage,
  type RegulatoryContextResponse,
} from "@/api/ai";
import type { WSA } from "@/api/wsa";
import { AITextBlock } from "@/components/AITextBlock";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { aiErrorMessage, describeChecked, usageTone } from "@/lib/aiAssistant";
import { cn } from "@/lib/utils";

// Questions worth asking, so an admin who has never used the box can start with one click. Each one is answerable from the data.
const DATA_SUGGESTIONS = [
  "Which high-risk authorities have no corrective action plan?",
  "Which plans are overdue, and by how many days?",
  "What are the oldest unresolved reports?",
  "Which provinces have the weakest drinking water quality?",
  "Which authorities are trending toward higher risk?",
];
const REGULATION_SUGGESTIONS = [
  "What is the Green Drop assessment?",
  "What is non-revenue water and why does it matter?",
  "What is the Blue Drop Risk Rating?",
];

interface DataExchange { id: number; question: string; answer: AIQueryResponse }

const MAX_HISTORY = 8;
const toneStyles = { ok: "bg-secondary text-muted-foreground", low: "bg-amber-100 text-amber-900", empty: "bg-rose-100 text-rose-800" };

// The whole AI assistant tab: a daily briefing, a question box over the live data (with suggestions and a short history), a question box
// over the DWS regulatory reports, and one-click AI tools for a chosen authority. Every AI call costs money and counts against an hourly
// allowance, so nothing runs by itself: each result is asked for, and the meter at the top always shows what is left.
export function AiAssistantTab({ wsas }: { wsas: WSA[] }) {
  const [usage, setUsage] = useState<AiUsage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const refreshUsage = useCallback(() => {
    fetchAiUsage().then(setUsage).catch(() => setUsage(null));
  }, []);
  useEffect(refreshUsage, [refreshUsage]);

  // runs one AI call, then refreshes the meter whether it worked or not (a failed call can still have used an allowance slot)
  async function track<T>(action: () => Promise<T>, failure: string): Promise<T | null> {
    setError(null);
    try {
      return await action();
    } catch (caught) {
      setError(aiErrorMessage(caught, failure));
      return null;
    } finally {
      refreshUsage();
    }
  }

  // ---- briefing
  const [briefing, setBriefing] = useState<AdminBriefing | null>(null);
  const [loadingBriefing, setLoadingBriefing] = useState(false);
  async function runBriefing() {
    setLoadingBriefing(true);
    setBriefing(await track(fetchAdminBriefing, "Could not write the briefing right now."));
    setLoadingBriefing(false);
  }

  // ---- ask the data
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [history, setHistory] = useState<DataExchange[]>([]);
  async function askData(text: string) {
    const asked = text.trim();
    if (asked.length < 3 || asking) return;
    setAsking(true);
    const answer = await track(() => askAiQuery(asked), "Could not answer that question right now.");
    if (answer) {
      setHistory((current) => [{ id: Date.now(), question: asked, answer }, ...current].slice(0, MAX_HISTORY));
      setQuestion("");
    }
    setAsking(false);
  }

  // ---- ask the regulations
  const [regQuestion, setRegQuestion] = useState("");
  const [askingReg, setAskingReg] = useState(false);
  const [regAnswer, setRegAnswer] = useState<RegulatoryContextResponse | null>(null);
  async function askRegulations(text: string) {
    const asked = text.trim();
    if (asked.length < 3 || askingReg) return;
    setAskingReg(true);
    setRegAnswer(await track(() => fetchRegulatoryContext(asked), "No relevant excerpts were found, or the request failed."));
    setAskingReg(false);
  }

  // ---- authority tools
  const sorted = [...wsas].sort((a, b) => a.name.localeCompare(b.name));
  const [wsaId, setWsaId] = useState("");
  const [toolResult, setToolResult] = useState<{ label: string; wsaId: string; content?: string; items?: string[] } | null>(null);
  const [runningTool, setRunningTool] = useState<string | null>(null);
  const chosen = wsas.find((w) => w.id === wsaId) ?? null;

  async function runTool(label: string, call: () => Promise<{ content?: string; items?: string[] }>) {
    if (!chosen) return;
    setRunningTool(label);
    const needsHistory = label === "Why it is trending worse" ? " It needs at least two risk scores for this authority." : "";
    const result = await track(call, `Could not get "${label}" for ${chosen.name}.${needsHistory}`);
    setToolResult(result ? { label, wsaId: chosen.id, ...result } : null);
    setRunningTool(null);
  }
  const tools = chosen
    ? [
        { label: "Recommended actions", call: () => fetchWsaRecommendations(chosen.id).then((r) => ({ items: r.items })) },
        { label: "Open reports summary", call: () => fetchReportsSummary(chosen.id) },
        { label: "Why this risk level", call: () => fetchRiskExplanation(chosen.id) },
        { label: "Why it is trending worse", call: () => fetchTrendExplanation(chosen.id) },
      ]
    : [];

  const tone = usage ? usageTone(usage.used, usage.limit) : "ok";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="border-b border-border/60 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Sparkles className="h-5 w-5 text-primary" />
              <CardTitle>AI assistant</CardTitle>
            </div>
            {usage ? (
              <span className={cn("rounded-full px-3 py-1 text-xs font-medium", toneStyles[tone])} title="Counts questions, briefings, CAP drafts, photo checks and trend explanations. One call frees up an hour after it was used.">
                AI calls this hour: {usage.used} of {usage.limit}
                {usage.used > 0 ? ` · next frees in ${usage.resets_in_minutes} min` : ""}
              </span>
            ) : null}
          </div>
          <CardDescription>It reads the live data and the DWS reports, never guesses a number, and only runs when you ask.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-8 pt-5">
          {error ? <p className="rounded-2xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p> : null}

          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium">Today's briefing</p>
                <p className="text-xs text-muted-foreground">What to look at first, written from the current numbers.</p>
              </div>
              <Button size="sm" variant="outline" disabled={loadingBriefing} onClick={() => void runBriefing()}>
                {loadingBriefing ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {briefing ? "Write again" : "Write briefing"}
              </Button>
            </div>
            {briefing ? (
              <>
                <div className="whitespace-pre-line">
                  <AITextBlock label="Briefing" content={briefing.content} />
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                  {Object.entries(briefing.facts).map(([key, value]) => (
                    <span key={key} className="rounded-full bg-secondary px-2.5 py-1">
                      {key.replace(/_/g, " ")}: <span className="font-semibold text-foreground">{value}</span>
                    </span>
                  ))}
                </div>
              </>
            ) : null}
          </section>

          <section className="space-y-3">
            <div>
              <p className="text-sm font-medium">Ask the data</p>
              <p className="text-xs text-muted-foreground">Authorities, plans, reports, alerts, risk trends and the audit log.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {DATA_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  disabled={asking}
                  onClick={() => void askData(suggestion)}
                  className="rounded-full border border-border bg-background px-3 py-1.5 text-left text-xs transition-colors hover:bg-secondary disabled:opacity-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                placeholder="Or type your own, e.g. which Eastern Cape authorities have no CAP and are high risk?"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void askData(question);
                  }
                }}
              />
              <Button disabled={asking || question.trim().length < 3} onClick={() => void askData(question)}>
                {asking ? <Loader2 className="h-4 w-4 animate-spin" /> : "Ask"}
              </Button>
            </div>
            {asking ? <p className="text-xs text-muted-foreground">Looking through the data...</p> : null}
            <div className="space-y-3">
              {history.map((entry) => (
                <div key={entry.id} className="rounded-2xl bg-secondary/60 p-4 text-sm">
                  <p className="text-xs font-medium text-muted-foreground">{entry.question}</p>
                  <p className="mt-1.5 whitespace-pre-line">{entry.answer.answer}</p>
                  {entry.answer.tool_calls.length > 0 ? (
                    <details className="mt-2 text-xs text-muted-foreground">
                      <summary className="cursor-pointer">Checked: {describeChecked(entry.answer.tool_calls)}</summary>
                      <ul className="mt-1 space-y-0.5 pl-4">
                        {entry.answer.tool_calls.map((call, index) => (
                          <li key={index}>
                            {call.tool}
                            {Object.keys(call.arguments).length ? ` (${Object.entries(call.arguments).map(([k, v]) => `${k}: ${String(v)}`).join(", ")})` : ""}
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </div>
              ))}
              {history.length > 0 ? (
                <button type="button" className="text-xs text-muted-foreground underline underline-offset-2" onClick={() => setHistory([])}>
                  Clear answers
                </button>
              ) : null}
            </div>
          </section>

          <section className="space-y-3">
            <div>
              <p className="text-sm font-medium">Ask the regulations</p>
              <p className="text-xs text-muted-foreground">Answers come from the DWS reports (Blue Drop, Green Drop, No Drop) and name the page they used.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {REGULATION_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  disabled={askingReg}
                  onClick={() => void askRegulations(suggestion)}
                  className="rounded-full border border-border bg-background px-3 py-1.5 text-left text-xs transition-colors hover:bg-secondary disabled:opacity-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                placeholder="Or type your own, e.g. how often must a water safety plan be reviewed?"
                value={regQuestion}
                onChange={(event) => setRegQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void askRegulations(regQuestion);
                  }
                }}
              />
              <Button disabled={askingReg || regQuestion.trim().length < 3} onClick={() => void askRegulations(regQuestion)}>
                {askingReg ? <Loader2 className="h-4 w-4 animate-spin" /> : "Ask"}
              </Button>
            </div>
            {askingReg ? <p className="text-xs text-muted-foreground">Searching the DWS reports... the first question after the server starts can take a minute while they are read.</p> : null}
            {regAnswer ? (
              <div className="rounded-2xl bg-secondary/60 p-4 text-sm">
                <p className="whitespace-pre-line">{regAnswer.answer}</p>
                {regAnswer.sources.length > 0 ? (
                  <p className="mt-2 text-xs text-muted-foreground">Sources: {regAnswer.sources.map((s) => `${s.source} p.${s.page}`).join(", ")}</p>
                ) : null}
              </div>
            ) : null}
          </section>

          <section className="space-y-3">
            <div>
              <p className="text-sm font-medium">Focus on one authority</p>
              <p className="text-xs text-muted-foreground">Pick an authority, then choose what you want the AI to work out.</p>
            </div>
            <Select value={wsaId} onValueChange={(value) => { setWsaId(value); setToolResult(null); }}>
              <SelectTrigger className="sm:max-w-sm">
                <SelectValue placeholder="Choose an authority" />
              </SelectTrigger>
              <SelectContent className="max-h-72">
                {sorted.map((wsa) => (
                  <SelectItem key={wsa.id} value={wsa.id}>
                    {wsa.name} ({wsa.province})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {chosen ? (
              <div className="flex flex-wrap gap-2">
                {tools.map((tool) => (
                  <Button key={tool.label} size="sm" variant="outline" disabled={runningTool !== null} onClick={() => void runTool(tool.label, tool.call)}>
                    {runningTool === tool.label ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    {tool.label}
                  </Button>
                ))}
              </div>
            ) : null}
            {toolResult && chosen && toolResult.wsaId === chosen.id ? <AITextBlock label={`${toolResult.label}: ${chosen.name}`} content={toolResult.content} items={toolResult.items} /> : null}
          </section>
        </CardContent>
      </Card>
    </div>
  );
}
