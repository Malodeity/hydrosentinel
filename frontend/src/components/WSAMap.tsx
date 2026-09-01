import { useEffect } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";

import type { RiskLevel, WSA } from "@/api/wsa";
import { RiskBadge } from "@/components/RiskBadge";
import { dataCompleteness } from "@/components/WSACard";

interface WSAMapProps {
  wsas: WSA[];
  selectedWsaId: string | null;
  onSelect: (wsa: WSA) => void;
  showDataGaps?: boolean;
}

function FlyToSelected({ wsa }: { wsa: WSA | null }) {
  const map = useMap();

  useEffect(() => {
    if (!wsa) return;
    map.flyTo([wsa.lat, wsa.lng], Math.max(map.getZoom(), 9), { duration: 0.8 });
  }, [wsa, map]);

  return null;
}

const riskColorMap: Record<RiskLevel, string> = {
  low: "#16a34a",
  medium: "#f59e0b",
  high: "#dc2626",
};

const LEGEND_ITEMS: { level: RiskLevel; label: string }[] = [
  { level: "low", label: "Low" },
  { level: "medium", label: "Medium" },
  { level: "high", label: "High" },
];

export function WSAMap({ wsas, selectedWsaId, onSelect, showDataGaps }: WSAMapProps) {
  const selectedWsa = wsas.find((wsa) => wsa.id === selectedWsaId) ?? null;

  return (
    <div className="relative">
      <MapContainer center={[-29.0, 24.0]} zoom={5} scrollWheelZoom className="h-[580px] w-full rounded-[1.5rem]">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FlyToSelected wsa={selectedWsa} />
        <MarkerClusterGroup chunkedLoading spiderfyOnMaxZoom disableClusteringAtZoom={14}>
          {wsas.map((wsa) => {
            const isSelected = wsa.id === selectedWsaId;
            const isDataGap = showDataGaps && dataCompleteness(wsa).filled < 2;
            return (
              <CircleMarker
                key={wsa.id}
                center={[wsa.lat, wsa.lng]}
                radius={isSelected ? 11 : 7}
                pathOptions={{
                  color: isSelected ? "#111827" : riskColorMap[wsa.risk_level],
                  fillColor: riskColorMap[wsa.risk_level],
                  fillOpacity: isDataGap ? 0.25 : 0.85,
                  weight: isSelected ? 4 : isDataGap ? 1 : 2,
                  dashArray: isDataGap ? "2,2" : undefined,
                  className: isSelected ? "wsa-marker-selected" : undefined,
                }}
                eventHandlers={{ click: () => onSelect(wsa) }}
              >
                <Popup>
                  <div className="space-y-2">
                    <p className="font-semibold">{wsa.name}</p>
                    <p className="text-sm text-slate-600">{wsa.province}</p>
                    <RiskBadge riskLevel={wsa.risk_level} />
                    {isDataGap ? <p className="text-xs text-muted-foreground">Limited data available</p> : null}
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MarkerClusterGroup>
      </MapContainer>

      <div className="pointer-events-none absolute bottom-4 left-4 z-[1000] flex gap-3 rounded-full border border-border/70 bg-white/95 px-4 py-2 shadow-soft backdrop-blur-sm">
        {LEGEND_ITEMS.map(({ level, label }) => (
          <span key={level} className="flex items-center gap-1.5 text-xs font-medium text-foreground">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: riskColorMap[level] }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
