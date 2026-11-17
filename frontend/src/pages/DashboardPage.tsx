// The public dashboard, top to bottom: headline numbers, what residents are reporting, AI insights tabs, the risk map with search and 'Find my area',
// the selected authority's card, and Blue Drop by province. Public data only: nothing here needs a login.

import { useEffect, useMemo, useRef, useState } from "react";
import { LocateFixed, Search } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { fetchAiDigest, fetchProvinceDigest, fetchWsaComparison } from "@/api/ai";
import { fetchPublicReportStats, type PublicReportStats } from "@/api/reports";
import { fetchWsas, type WSA } from "@/api/wsa";
import { AITextBlock } from "@/components/AITextBlock";
import { BlueDropByProvince } from "@/components/BlueDropByProvince";
import { CitizenActivity } from "@/components/CitizenActivity";
import { WSACard } from "@/components/WSACard";
import { WSAMap } from "@/components/WSAMap";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { nearestAuthority } from "@/lib/nearestAuthority";
import { provinceBlueDrop } from "@/lib/provinceBlueDrop";
import { publicStats } from "@/lib/publicStats";
import { pickDefaultWsa } from "@/lib/wsaSelection";

// the authority-level explanation now lives in the authority card ("Explain this rating"), so there is no separate tab for it
type AiTab = "national" | "province" | "comparison";

const TAB_LABELS: Record<AiTab, string> = {
  national: "National digest",
  province: "Province digest",
  comparison: "Provincial comparison",
};

// the public dashboard: the risk map, the selected authority's card, and the AI insight tabs (national, province, authority, comparison).
// results are cached per tab so switching back does not call the AI again
export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [wsas, setWsas] = useState<WSA[]>([]);
  const [selectedWsa, setSelectedWsaState] = useState<WSA | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingWsas, setIsLoadingWsas] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [reportStats, setReportStats] = useState<PublicReportStats | null>(null);
  const [locateMessage, setLocateMessage] = useState<string | null>(null);

  // keeps ?wsa=<id> in the URL in sync so a selected WSA is shareable/bookmarkable
  function setSelectedWsa(wsa: WSA | null) {
    setSelectedWsaState(wsa);
    setSearchParams(wsa ? { wsa: wsa.id } : {}, { replace: true });
  }

  const stats = useMemo(() => publicStats(wsas), [wsas]);

  const searchMatches = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return [];
    return wsas.filter((wsa) => wsa.name.toLowerCase().includes(query) || wsa.province.toLowerCase().includes(query)).slice(0, 8);
  }, [searchQuery, wsas]);

  const provinceAverages = useMemo(() => provinceBlueDrop(wsas), [wsas]);

  // ai section state
  const [activeTab, setActiveTab] = useState<AiTab>("national");
  const [aiLoading, setAiLoading] = useState(false);
  // cache per tab key so we don't re-fetch when switching back
  const aiCache = useRef<Map<string, string>>(new Map());
  const [aiContent, setAiContent] = useState<string | null>(null);

  const lastProvinceRef = useRef<string | null>(null);

  useEffect(() => {
    // resident-report numbers are a bonus: if they fail to load the rest of the page is unaffected
    fetchPublicReportStats().then(setReportStats).catch(() => setReportStats(null));
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
    aiCache.current.delete("comparison");
  }, [selectedWsa?.province]);

  // when wsa changes, invalidate wsa-specific cache entries
  useEffect(() => {
    aiCache.current.delete("comparison");
    // if the active tab is wsa-specific and wsa changed, re-fetch
    if (selectedWsa && activeTab === "comparison") {
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

    if ((tab === "comparison" || tab === "province") && !selectedWsa) {
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

  // "find my area": uses the browser's location (only when the visitor clicks) and selects the nearest authority on the map
  function locateMe() {
    if (!navigator.geolocation) {
      setLocateMessage("Your browser cannot share its location. Search for your municipality instead.");
      return;
    }
    setLocateMessage("Finding your location...");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const nearest = nearestAuthority(wsas, coords.latitude, coords.longitude);
        if (!nearest) return setLocateMessage("No authorities are loaded yet.");
        setSelectedWsa(nearest.wsa);
        setLocateMessage(`Nearest authority to you: ${nearest.wsa.name}, about ${Math.round(nearest.km)} km away. Boundaries are not mapped, so check the name is right.`);
      },
      () => setLocateMessage("Location was blocked. Search for your municipality instead."),
      { timeout: 10000 },
    );
  }

  const wsaSpecificTabs: AiTab[] = ["province", "comparison"];

  return (
    <div className="space-y-6">
      {/* headline numbers: the first thing a visitor sees, before any AI text */}
      <div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {isLoadingWsas
            ? [0, 1, 2, 3].map((n) => <Skeleton key={n} className="h-[92px] rounded-2xl" />)
            : [
                { label: "Authorities tracked", value: stats.total, hint: "Water service authorities", color: "" },
                { label: "High risk", value: stats.high, hint: `${stats.total ? Math.round((stats.high / stats.total) * 100) : 0}% of all authorities`, color: "text-rose-700" },
                { label: "Critical drinking water", value: stats.criticalWater, hint: "Blue Drop score under 31", color: "text-rose-700" },
                { label: "Plans completed", value: stats.capCompleted, hint: "Corrective action plans", color: "text-emerald-700" },
              ].map((tile) => (
                <div key={tile.label} className="rounded-2xl bg-card p-4 shadow-soft">
                  <p className="text-sm text-muted-foreground">{tile.label}</p>
                  <p className={`mt-1 text-3xl font-semibold ${tile.color}`}>{tile.value}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{tile.hint}</p>
                </div>
              ))}
        </div>
      </div>

      {reportStats ? <CitizenActivity stats={reportStats} /> : null}

      {/* AI insights section */}
      <Card>
        <CardHeader className="border-b border-border/60 pb-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>AI insights</CardTitle>
              <CardDescription>{activeTab === "national" ? "A plain-language summary of the whole country" : selectedWsa ? selectedWsa.name : "Select a WSA on the map"}</CardDescription>
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
              <div className="flex w-full items-center gap-2 sm:w-auto">
              <Button type="button" variant="outline" size="sm" onClick={locateMe} className="shrink-0">
                <LocateFixed className="h-4 w-4" />
                Find my area
              </Button>
              <div className="relative w-full sm:w-64">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search name or province"
                  className="pl-9"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
                {searchMatches.length > 0 ? (
                  <div className="absolute z-[1100] mt-2 w-full overflow-hidden rounded-2xl border border-border bg-white shadow-soft">
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
            </div>
            {locateMessage ? <p className="mt-2 text-xs text-muted-foreground">{locateMessage}</p> : null}
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
            <WSACard wsa={selectedWsa} reportCounts={selectedWsa ? reportStats?.by_wsa[selectedWsa.id] ?? { open: 0, resolved: 0 } : undefined} />
            {!isLoadingWsas && provinceAverages.length > 0 ? <BlueDropByProvince rows={provinceAverages} /> : null}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
