import { useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { fetchAiDigest, fetchProvinceDigest, fetchRiskExplanation, fetchWsaComparison } from "@/api/ai";
import { fetchWsas, type WSA } from "@/api/wsa";
import { AITextBlock } from "@/components/AITextBlock";
import { WSACard } from "@/components/WSACard";
import { WSAMap } from "@/components/WSAMap";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { pickDefaultWsa } from "@/lib/wsaSelection";

type AiTab = "national" | "province" | "insight" | "comparison";

const TAB_LABELS: Record<AiTab, string> = {
  national: "National digest",
  province: "Province digest",
  insight: "WSA insight",
  comparison: "Provincial comparison",
};

export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [wsas, setWsas] = useState<WSA[]>([]);
  const [selectedWsa, setSelectedWsaState] = useState<WSA | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingWsas, setIsLoadingWsas] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  // keeps ?wsa=<id> in the URL in sync so a selected WSA is shareable/bookmarkable
  function setSelectedWsa(wsa: WSA | null) {
    setSelectedWsaState(wsa);
    setSearchParams(wsa ? { wsa: wsa.id } : {}, { replace: true });
  }

  const searchMatches = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return [];
    return wsas.filter((wsa) => wsa.name.toLowerCase().includes(query)).slice(0, 8);
  }, [searchQuery, wsas]);

  const provinceAverages = useMemo(() => {
    const byProvince = new Map<string, number[]>();
    for (const wsa of wsas) {
      if (wsa.blue_drop_score === null) continue;
      const scores = byProvince.get(wsa.province) ?? [];
      scores.push(wsa.blue_drop_score);
      byProvince.set(wsa.province, scores);
    }
    return Array.from(byProvince.entries())
      .map(([province, scores]) => ({
        province,
        average: scores.reduce((sum, score) => sum + score, 0) / scores.length,
      }))
      .sort((a, b) => b.average - a.average);
  }, [wsas]);

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
        const requestedId = searchParams.get("wsa");
        const requested = requestedId ? data.find((wsa) => wsa.id === requestedId) : undefined;
        setSelectedWsaState(requested ?? pickDefaultWsa(data));
      })
      .catch(() => setError("Unable to load WSA data right now."))
      .finally(() => setIsLoadingWsas(false));
    // only ever runs once on mount — the URL param is read as the initial value only
    // eslint-disable-next-line react-hooks/exhaustive-deps

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
              <CardDescription>{selectedWsa ? selectedWsa.name : "Select a WSA on the map"}</CardDescription>
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
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-11/12" />
              <Skeleton className="h-4 w-3/4" />
            </div>
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
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle>Risk map</CardTitle>
              <div className="relative w-full sm:w-64">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search a WSA"
                  className="pl-9"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
                {searchMatches.length > 0 ? (
                  <div className="absolute z-[1000] mt-2 w-full overflow-hidden rounded-2xl border border-border bg-white shadow-soft">
                    {searchMatches.map((wsa) => (
                      <button
                        key={wsa.id}
                        type="button"
                        className="block w-full border-b border-border/60 px-4 py-2.5 text-left text-sm last:border-b-0 hover:bg-secondary/60"
                        onClick={() => {
                          setSelectedWsa(wsa);
                          setSearchQuery("");
                        }}
                      >
                        <span className="font-medium">{wsa.name}</span>
                        <span className="ml-2 text-muted-foreground">{wsa.province}</span>
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-4">
            {error ? (
              <div className="rounded-3xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>
            ) : isLoadingWsas ? (
              <Skeleton className="h-[580px] w-full" />
            ) : (
              <WSAMap wsas={wsas} selectedWsaId={selectedWsa?.id ?? null} onSelect={setSelectedWsa} showDataGaps />
            )}
          </CardContent>
        </Card>

        <ScrollArea className="h-[690px] rounded-[1.5rem]">
          <div className="space-y-4 pr-4">
            <WSACard wsa={selectedWsa} />
            <Card>
              <CardHeader>
                <CardTitle>Snapshot</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                {isLoadingWsas ? (
                  <>
                    <Skeleton className="h-[76px]" />
                    <Skeleton className="h-[76px]" />
                    <Skeleton className="h-[76px]" />
                  </>
                ) : (
                  <>
                    <div className="rounded-3xl border border-primary/15 bg-primary/5 p-4">
                      <p className="text-sm text-muted-foreground">Total WSAs</p>
                      <p className="text-3xl font-semibold text-primary">{wsas.length}</p>
                    </div>
                    <div className="rounded-3xl border border-rose-200 bg-rose-50 p-4">
                      <p className="text-sm text-muted-foreground">High risk</p>
                      <p className="text-3xl font-semibold text-rose-700">{wsas.filter((item) => item.risk_level === "high").length}</p>
                    </div>
                    <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-4">
                      <p className="text-sm text-muted-foreground">CAP completed</p>
                      <p className="text-3xl font-semibold text-emerald-700">{wsas.filter((item) => item.cap_status === "completed").length}</p>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {!isLoadingWsas && provinceAverages.length > 0 ? (
              <Card>
                <CardHeader>
                  <CardTitle>Blue Drop by province</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {provinceAverages.map(({ province, average }) => (
                    <div key={province}>
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="text-foreground">{province}</span>
                        <span className="font-medium text-muted-foreground">{average.toFixed(0)}%</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-secondary/60">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${average}%` }} />
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : null}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
