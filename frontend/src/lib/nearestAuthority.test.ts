import { describe, expect, it } from "vitest";

import type { WSA } from "@/api/wsa";
import { distanceKm, nearestAuthority } from "@/lib/nearestAuthority";

const w = (name: string, lat: number, lng: number) => ({ name, lat, lng }) as WSA;

describe("nearestAuthority", () => {
  it("measures real distance: Johannesburg to Pretoria is about 50 km", () => {
    const km = distanceKm(-26.2041, 28.0473, -25.7479, 28.2293);
    expect(km).toBeGreaterThan(45);
    expect(km).toBeLessThan(60);
  });
  it("picks the closest authority and reports how far away it is", () => {
    const result = nearestAuthority([w("Cape Town", -33.92, 18.42), w("Joburg", -26.2, 28.04), w("Durban", -29.86, 31.02)], -26.1, 28.1);
    expect(result?.wsa.name).toBe("Joburg");
    expect(result!.km).toBeLessThan(20);
  });
  it("returns null with no authorities", () => {
    expect(nearestAuthority([], 0, 0)).toBeNull();
  });
});
