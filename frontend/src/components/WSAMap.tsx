import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

import type { RiskLevel, WSA } from "@/api/wsa";
import { RiskBadge } from "@/components/RiskBadge";

interface WSAMapProps {
  wsas: WSA[];
  selectedWsaId: string | null;
  onSelect: (wsa: WSA) => void;
}

const riskColorMap: Record<RiskLevel, string> = {
  low: "#16a34a",
  medium: "#f59e0b",
  high: "#dc2626",
};

export function WSAMap({ wsas, selectedWsaId, onSelect }: WSAMapProps) {
  return (
    <MapContainer center={[-29.0, 24.0]} zoom={5} scrollWheelZoom className="h-[580px] w-full rounded-[1.5rem]">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {wsas.map((wsa) => {
        const isSelected = wsa.id === selectedWsaId;
        return (
          <CircleMarker
            key={wsa.id}
            center={[wsa.lat, wsa.lng]}
            radius={isSelected ? 10 : 7}
            pathOptions={{
              color: riskColorMap[wsa.risk_level],
              fillColor: riskColorMap[wsa.risk_level],
              fillOpacity: 0.85,
              weight: isSelected ? 4 : 2,
            }}
            eventHandlers={{ click: () => onSelect(wsa) }}
          >
            <Popup>
              <div className="space-y-2">
                <p className="font-semibold">{wsa.name}</p>
                <p className="text-sm text-slate-600">{wsa.province}</p>
                <RiskBadge riskLevel={wsa.risk_level} />
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
