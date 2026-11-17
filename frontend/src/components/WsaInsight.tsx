import { useState } from "react";
import { Sparkles } from "lucide-react";

import { fetchRiskExplanation } from "@/api/ai";
import { AITextBlock } from "@/components/AITextBlock";
import { Button } from "@/components/ui/button";

// "Explain this rating" for one authority, shown inside its card. It only calls the AI when the visitor asks, and keeps each answer
// so reopening the same authority is free. (This used to be a separate "WSA insight" tab far from the authority it described.)
export function WsaInsight({ wsaId }: { wsaId: string }) {
  const [texts, setTexts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  const ask = async () => {
    setLoading(true);
    setFailed(false);
    try {
      const result = await fetchRiskExplanation(wsaId);
      setTexts((current) => ({ ...current, [wsaId]: result.content }));
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  };

  if (texts[wsaId] || loading) return <AITextBlock label="AI explanation" content={texts[wsaId]} loading={loading} />;
  return (
    <div>
      <Button variant="outline" size="sm" onClick={ask}>
        <Sparkles className="h-4 w-4" />
        Explain this rating with AI
      </Button>
      {failed ? <p className="mt-2 text-xs text-destructive">Could not get an explanation right now.</p> : null}
    </div>
  );
}
