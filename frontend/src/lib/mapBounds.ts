export interface MapBounds {
  south: number;
  north: number;
  west: number;
  east: number;
}

// Leaflet reports longitudes past +/-180 when the map is zoomed out and wraps the world; the API rejects those,
// so clamp the view to the real world before asking for a summary.
export function toSummaryBounds(bounds: MapBounds): MapBounds {
  const clamp = (value: number, limit: number) => Math.min(limit, Math.max(-limit, value));
  return {
    south: clamp(bounds.south, 90),
    north: clamp(bounds.north, 90),
    west: clamp(bounds.west, 180),
    east: clamp(bounds.east, 180),
  };
}
