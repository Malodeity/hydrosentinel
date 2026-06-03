import { type FormEvent, useEffect, useMemo, useState } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { divIcon, type LatLngLiteral } from "leaflet";

import type { CreateCitizenReportPayload, IssueType } from "@/api/reports";
import type { WSA } from "@/api/wsa";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

interface ReportFormProps {
  wsas: WSA[];
  isSubmitting: boolean;
  onSubmit: (payload: CreateCitizenReportPayload, photos: File[]) => Promise<void>;
}

const defaultLocation: LatLngLiteral = { lat: -26.2041, lng: 28.0473 };
const SOUTH_AFRICA_BOUNDS = {
  viewbox: "16,-35,33,-22",
  bounded: "1",
};

// this draws the custom map pin used for the selected citizen report location
const locationIcon = divIcon({
  className: "",
  html: '<div style="width:20px;height:20px;border-radius:9999px;background:#0f766e;border:4px solid #ccfbf1;box-shadow:0 0 0 3px rgba(15,118,110,0.22)"></div>',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});

function LocationPicker({
  location,
  onPick,
}: {
  location: LatLngLiteral;
  onPick: (nextLocation: LatLngLiteral) => void;
}) {
  // this updates the chosen coordinates every time the user clicks on the map
  useMapEvents({
    click(event) {
      onPick(event.latlng);
    },
  });

  return <Marker position={location} icon={locationIcon} />;
}

function MapViewportSync({ location }: { location: LatLngLiteral }) {
  const map = useMap();

  useEffect(() => {
    map.flyTo(location, Math.max(map.getZoom(), 12), { duration: 0.8 });
  }, [location, map]);

  return null;
}

export function ReportForm({ wsas, isSubmitting, onSubmit }: ReportFormProps) {
  // this stores the current form values until the user submits the report
  const [wsaId, setWsaId] = useState<string>("");
  const [province, setProvince] = useState<string>("");
  const [issueType, setIssueType] = useState<IssueType>("leak");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState<LatLngLiteral>(defaultLocation);
  const [addressQuery, setAddressQuery] = useState("");
  const [searchingAddress, setSearchingAddress] = useState(false);
  const [addressSuggestions, setAddressSuggestions] = useState<Array<{ display_name: string; lat: string; lon: string }>>([]);
  const [locationMessage, setLocationMessage] = useState<string | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);

  // this keeps the dropdown easy to use by sorting the wsas alphabetically
  const sortedWsas = useMemo(() => [...wsas].sort((a, b) => a.name.localeCompare(b.name)), [wsas]);
  const provinces = useMemo(() => [...new Set(sortedWsas.map((wsa) => wsa.province))].sort((a, b) => a.localeCompare(b)), [sortedWsas]);
  const filteredWsas = useMemo(() => {
    if (!province) {
      return [];
    }
    return sortedWsas.filter((wsa) => wsa.province === province);
  }, [province, sortedWsas]);

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationMessage("Location access is not available in this browser.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setLocationMessage("Your current location was loaded as the starting pin.");
      },
      () => {
        setLocationMessage("We could not read your current location, so the map is using the default starting point.");
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }, []);

  useEffect(() => {
    if (!province) {
      setWsaId("");
    } else if (!filteredWsas.some((wsa) => wsa.id === wsaId)) {
      setWsaId("");
    }
  }, [province, filteredWsas, wsaId]);

  useEffect(() => {
    const query = addressQuery.trim();
    if (query.length < 3) {
      setAddressSuggestions([]);
      return;
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await fetch(
          `https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&limit=5&countrycodes=za&viewbox=${encodeURIComponent(SOUTH_AFRICA_BOUNDS.viewbox)}&bounded=${SOUTH_AFRICA_BOUNDS.bounded}&q=${encodeURIComponent(query)}`,
          { signal: controller.signal },
        );
        const results = (await response.json()) as Array<{ display_name: string; lat: string; lon: string }>;
        setAddressSuggestions(results);
      } catch {
        setAddressSuggestions([]);
      }
    }, 300);

    return () => {
      controller.abort();
      window.clearTimeout(timeoutId);
    };
  }, [addressQuery]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    // this stops the browser refresh and sends the finished form data to the parent page
    event.preventDefault();
    if (!wsaId) {
      return;
    }

    await onSubmit({
      wsa_id: wsaId,
      issue_type: issueType,
      description,
      lat: location.lat,
      lng: location.lng,
    }, photos);

    setDescription("");
    setPhotos([]);
  };

  const selectSuggestedAddress = (suggestion: { display_name: string; lat: string; lon: string }) => {
    setLocation({
      lat: Number(suggestion.lat),
      lng: Number(suggestion.lon),
    });
    setAddressQuery(suggestion.display_name);
    setAddressSuggestions([]);
    setLocationMessage(`Showing ${suggestion.display_name}`);
  };

  const searchAddress = async () => {
    if (addressSuggestions[0]) {
      selectSuggestedAddress(addressSuggestions[0]);
      return;
    }

    setSearchingAddress(true);
    setLocationMessage(null);
    try {
      const query = addressQuery.trim();
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&limit=1&countrycodes=za&viewbox=${encodeURIComponent(SOUTH_AFRICA_BOUNDS.viewbox)}&bounded=${SOUTH_AFRICA_BOUNDS.bounded}&q=${encodeURIComponent(query)}`,
      );
      const results = (await response.json()) as Array<{ lat: string; lon: string; display_name: string }>;
      if (!results[0]) {
        setLocationMessage("No address match was found. Try a more specific place name or street.");
        return;
      }
      selectSuggestedAddress(results[0]);
    } catch {
      setLocationMessage("Address search failed. Please try again or place the pin manually.");
    } finally {
      setSearchingAddress(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Submit a citizen report</CardTitle>
        <CardDescription>Choose the WSA, select the issue type, and use your location, an address search, or the map to place the incident pin.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-6" onSubmit={submit}>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Province</label>
              <Select value={province} onValueChange={setProvince}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a province" />
                </SelectTrigger>
                <SelectContent>
                  {provinces.map((provinceName) => (
                    <SelectItem key={provinceName} value={provinceName}>
                      {provinceName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Water Services Authority</label>
              <Select value={wsaId} onValueChange={setWsaId}>
                <SelectTrigger>
                  <SelectValue placeholder={province ? "Select a WSA" : "Select a province first"} />
                </SelectTrigger>
                <SelectContent>
                  {filteredWsas.map((wsa) => (
                    <SelectItem key={wsa.id} value={String(wsa.id)}>
                      {wsa.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Issue type</label>
              <Select value={issueType} onValueChange={(value) => setIssueType(value as IssueType)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select an issue" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="leak">Leak</SelectItem>
                  <SelectItem value="outage">Outage</SelectItem>
                  <SelectItem value="quality">Water quality</SelectItem>
                  <SelectItem value="billing">Billing</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Photos</label>
              <Input
                type="file"
                accept="image/*"
                multiple
                onChange={(event) => setPhotos(Array.from(event.target.files ?? []))}
              />
              {photos.length > 0 ? (
                <p className="text-sm text-muted-foreground">{photos.length} photo{photos.length === 1 ? "" : "s"} ready to upload.</p>
              ) : (
                <p className="text-sm text-muted-foreground">Add photos to help show the issue on site.</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea
              placeholder="Describe the problem, what residents are experiencing, and any context that will help municipal follow-up."
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              minLength={10}
              maxLength={1000}
              required
            />
          </div>

          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium">Location pin</p>
              <p className="text-sm text-muted-foreground">Start from your current location or search for an address before adjusting the pin on the map.</p>
              <p className="text-sm text-muted-foreground">
                Selected coordinates: {location.lat.toFixed(5)}, {location.lng.toFixed(5)}
              </p>
              {locationMessage ? <p className="text-sm text-primary">{locationMessage}</p> : null}
            </div>
            <div className="grid gap-3 md:grid-cols-[1fr_auto]">
              <div className="relative">
                <Input
                  placeholder="Search address or place name"
                  value={addressQuery}
                  onChange={(event) => setAddressQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      void searchAddress();
                    }
                  }}
                />
                {addressSuggestions.length > 0 ? (
                  <div className="absolute z-[1000] mt-2 max-h-64 w-full overflow-y-auto rounded-2xl border border-border bg-white shadow-soft">
                    {addressSuggestions.map((suggestion) => (
                      <button
                        key={`${suggestion.lat}-${suggestion.lon}-${suggestion.display_name}`}
                        type="button"
                        className="block w-full border-b border-border/60 px-4 py-3 text-left text-sm last:border-b-0 hover:bg-secondary/60"
                        onClick={() => selectSuggestedAddress(suggestion)}
                      >
                        {suggestion.display_name}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <Button type="button" variant="secondary" disabled={searchingAddress || !addressQuery.trim()} onClick={searchAddress}>
                {searchingAddress ? "Searching..." : "Find address"}
              </Button>
            </div>
            <MapContainer center={location} zoom={6} scrollWheelZoom className="h-[360px] rounded-[1.5rem]">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapViewportSync location={location} />
              <LocationPicker location={location} onPick={setLocation} />
            </MapContainer>
          </div>

          <div className="flex justify-end">
            <Button disabled={isSubmitting || !province || !wsaId || description.trim().length < 10} type="submit">
              {isSubmitting ? "Submitting..." : "Submit report"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
