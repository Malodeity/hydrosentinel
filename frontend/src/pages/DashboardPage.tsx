import { useEffect, useRef, useState } from "react";

import { fetchAiDigest, fetchProvinceDigest, fetchRiskExplanation, fetchWsaComparison } from "@/api/ai";
import { fetchWsas, type WSA } from "@/api/wsa";
import { AITextBlock } from "@/components/AITextBlock";
import { WSACard } from "@/components/WSACard";
import { WSAMap } from "@/components/WSAMap";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

type AiTab = "national" | "province" | "insight" | "comparison";

const TAB_LABELS: Record<AiTab, string> = {
  national: "National digest",
  province: "Province digest",
  insight: "WSA insight",
  comparison: "Provincial comparison",
};

export function DashboardPage() {
  const [wsas, setWsas] = useState<WSA[]>([]);
  const [selectedWsa, setSelectedWsa] = useState<WSA | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ai section state
  const [activeTab, setActiveTab] = useState<AiTab>("national");
  const [aiLoading, setAiLoading] = useState(false);
  // cache per tab key so we don't re-fetch when switching back
  const aiCache = useRef<Map<string, string>>(new Map());
  const [aiContent, setAiContent] = useState<string | null>(null);

  const lastProvinceRef = useRef<string | null>(null);

  useEffect(() => {
    fetchWsas()
      .then((data) => {
        setWsas(data);
        setSelectedWsa(data[0] ?? null);
      })
      .catch(() => setError("Unable to load WSA data right now."));

    // pre-load national digest into cache
    fetchAiDigest()
      .then((data) => {
        aiCache.current.set("national", data.content);
        setAiContent(data.content);
      })
      .catch(() => {});
  }, []);

  // when province changes, invalidate province cache so it re-fetches
  useEffect(() => {
    const province = selectedWsa?.province ?? null;
    if (!province || province === lastProvinceRef.current) return;
    lastProvinceRef.current = province;
    aiCache.current.delete("province");
    aiCache.current.delete("insight");
    aiCache.current.delete("comparison");
  }, [selectedWsa?.province]);

  // when wsa changes, invalidate wsa-specific cache entries
  useEffect(() => {
    aiCache.current.delete("insight");
    aiCache.current.delete("comparison");
    // if the active tab is wsa-specific and wsa changed, re-fetch
    if (selectedWsa && (activeTab === "insight" || activeTab === "comparison")) {
      loadTab(activeTab);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedWsa?.id]);

  async function loadTab(tab: AiTab) {
    const cached = aiCache.current.get(tab);
    if (cached !== undefined) {
      setAiContent(cached);
      return;
    }

    if ((tab === "insight" || tab === "comparison" || tab === "province") && !selectedWsa) {
      setAiContent(null);
      return;
    }

    setAiLoading(true);
    setAiContent(null);

    try {
      let content = "";
      if (tab === "national") {
        const data = await fetchAiDigest();
        content = data.content;
      } else if (tab === "province" && selectedWsa) {
        const data = await fetchProvinceDigest(selectedWsa.province);
        content = data.content;
      } else if (tab === "insight" && selectedWsa) {
        const data = await fetchRiskExplanation(selectedWsa.id);
        content = data.content;
      } else if (tab === "comparison" && selectedWsa) {
        const data = await fetchWsaComparison(selectedWsa.id);
        content = data.content;
      }
      aiCache.current.set(tab, content);
      setAiContent(content);
    } catch {
      setAiContent(null);
    } finally {
      setAiLoading(false);
    }
  }

  function handleTabClick(tab: AiTab) {
    setActiveTab(tab);
    loadTab(tab);
  }

  const wsaSpecificTabs: AiTab[] = ["province", "insight", "comparison"];

  return (
    <div className="space-y-6">
      {/* AI insights section — between hero and map */}
      <Card>
        <CardHeader className="border-b border-border/60 pb-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>AI insights</CardTitle>
              <CardDescription>
                {selectedWsa
                  ? `Select a topic to generate AI analysis. WSA-specific insights are for ${selectedWsa.name}.`
                  : "Select a WSA on the map to unlock WSA-specific insights."}
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(TAB_LABELS) as AiTab[]).map((tab) => {
                const isDisabled = wsaSpecificTabs.includes(tab) && !selectedWsa;
                return (
                  <Button
                    key={tab}
                    size="sm"
                    variant={activeTab === tab ? "default" : "outline"}
                    disabled={isDisabled}
                    onClick={() => handleTabClick(tab)}
                  >
                    {TAB_LABELS[tab]}
                  </Button>
                );
              })}
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {aiLoading ? (
            <p className="text-sm text-muted-foreground animate-pulse">Generating AI analysis…</p>
          ) : aiContent ? (
            <AITextBlock content={aiContent} label={TAB_LABELS[activeTab]} />
          ) : (
            <p className="text-sm text-muted-foreground">
              {wsaSpecificTabs.includes(activeTab) && !selectedWsa
                ? "Select a WSA on the map first."
                : "Click a button above to generate insights."}
            </p>
          )}
        </CardContent>
      </Card>

      {/* main grid — map + WSA detail */}
      <div className="grid gap-6 xl:grid-cols-[1.7fr_0.95fr]">
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-border/60 bg-card/70">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle>National water services dashboard</CardTitle>
                <CardDescription>Explore risk distribution, service performance indicators, and CAP progress across South African WSAs.</CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge className="border-emerald-200 bg-emerald-100 text-emerald-800" variant="outline">Low</Badge>
                <Badge className="border-amber-200 bg-amber-100 text-amber-800" variant="outline">Medium</Badge>
                <Badge className="border-rose-200 bg-rose-100 text-rose-800" variant="outline">High</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-4">
            {error ? (
              <div className="rounded-3xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>
            ) : (
              <WSAMap wsas={wsas} selectedWsaId={selectedWsa?.id ?? null} onSelect={setSelectedWsa} />
            )}
          </CardContent>
        </Card>

        <ScrollArea className="h-[690px] rounded-[1.5rem]">
          <div className="space-y-4 pr-4">
            <WSACard wsa={selectedWsa} />
            <Card>
              <CardHeader>
                <CardTitle>Snapshot</CardTitle>
                <CardDescription>A quick view of current WSA coverage, risk pressure, and corrective action progress.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                <div className="rounded-3xl bg-secondary/60 p-4">
                  <p className="text-sm text-muted-foreground">Total WSAs</p>
                  <p className="text-3xl font-semibold">{wsas.length}</p>
                </div>
                <div className="rounded-3xl bg-secondary/60 p-4">
                  <p className="text-sm text-muted-foreground">High risk</p>
                  <p className="text-3xl font-semibold">{wsas.filter((item) => item.risk_level === "high").length}</p>
                </div>
                <div className="rounded-3xl bg-secondary/60 p-4">
                  <p className="text-sm text-muted-foreground">CAP completed</p>
                  <p className="text-3xl font-semibold">{wsas.filter((item) => item.cap_status === "completed").length}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </ScrollArea>
      </div>

    </div>
  );
}
