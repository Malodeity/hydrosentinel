import type { WSA } from "@/api/wsa";

const toRad = (deg: number) => (deg * Math.PI) / 180;

// great-circle distance in km (haversine), same maths as the back end's cluster alert
export function distanceKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const a = Math.sin(toRad(lat2 - lat1) / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(toRad(lng2 - lng1) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(a));
}

// The authority whose recorded point is closest to a position. This is an approximation: each authority is stored as one point,
// not as a boundary, so near a border the nearest point may belong to the neighbouring authority. The UI says so.
export function nearestAuthority(wsas: WSA[], lat: number, lng: number): { wsa: WSA; km: number } | null {
  let best: { wsa: WSA; km: number } | null = null;
  for (const wsa of wsas) {
    const km = distanceKm(lat, lng, wsa.lat, wsa.lng);
    if (!best || km < best.km) best = { wsa, km };
  }
  return best;
}
