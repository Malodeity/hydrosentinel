// The 'Summarise this view' button on the dashboard map: sends the visible map area to the AI and shows its short summary.

import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Loader2, Sparkles, X } from "lucide-react";

import { fetchMapViewSummary, type MapViewSummary as MapViewSummaryData } from "@/api/ai";
import { Button } from "@/components/ui/button";
import { toSummaryBounds, type MapBounds } from "@/lib/mapBounds";

interface MapViewSummaryProps {
  getBounds: () => MapBounds | null;
  viewVersion: number; // changes every time the map moves
}

// wait for the map to settle so a drag or a fly-to is one request, not dozens
const SETTLE_MS = 900;

export function MapViewSummary({ getBounds, viewVersion }: MapViewSummaryProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MapViewSummaryData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latestRequest = useRef(0);
  const summarisedVersion = useRef(viewVersion);

  const summarise = async () => {
    const bounds = getBounds();
    if (!bounds) return;
    const requestId = ++latestRequest.current;
    summarisedVersion.current = viewVersion;
    setOpen(true);
    setLoading(true);
    setError(null);
    try {
      const summary = await fetchMapViewSummary(toSummaryBounds(bounds));
      if (requestId !== latestRequest.current) return; // the map moved again; a newer answer is coming
      setResult(summary);
    } catch (err) {
      if (requestId !== latestRequest.current) return;
      setResult(null);
      setError(
        axios.isAxiosError(err) && err.response?.status === 404
          ? "No authorities in this view. Zoom out or pan the map."
          : "Could not summarise this view. Please try again.",
      );
    } finally {
      if (requestId === latestRequest.current) setLoading(false);
    }
  };

  // once the panel is open, follow the map: summarise again whenever the view changes and settles
  useEffect(() => {
    if (!open || viewVersion === summarisedVersion.current) return;
    const timer = setTimeout(summarise, SETTLE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewVersion, open]);

  const stats = result?.stats;

  return (
    <div className="absolute right-4 top-4 z-[1000] flex w-80 max-w-[calc(100%-2rem)] flex-col items-end gap-2">
      <Button size="sm" onClick={summarise} disabled={loading} className="shadow-soft">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        {open ? "Refresh summary" : "Summarise this view"}
      </Button>

      {open ? (
        <div className="w-full rounded-2xl border border-border/70 bg-white/95 p-4 shadow-soft backdrop-blur-sm">
          <div className="mb-2 flex items-center justify-between">
            <span className="rounded-full bg-accent px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-accent-foreground">
              AI summary of this view
            </span>
            <button type="button" aria-label="Close summary" onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>

          {loading && !stats ? <p className="text-sm text-muted-foreground">Reading the map...</p> : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          {stats && !error ? (
            <div className={loading ? "opacity-50 transition-opacity" : "transition-opacity"}>
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                {stats.total} authorities &middot; {stats.high} high &middot; {stats.medium} medium &middot; {stats.low} low &middot; {stats.open_reports} open reports
              </p>
              <p className="text-sm leading-6 text-foreground">
                {result?.content ?? "The AI summary is unavailable right now. The counts above are live."}
              </p>
            </div>
          ) : null}
          {loading && stats ? <p className="mt-2 text-xs font-medium text-muted-foreground">Updating for the new view...</p> : null}
        </div>
      ) : null}
    </div>
  );
}
