import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, TileLayer } from "react-leaflet";
import { Camera, Search } from "lucide-react";

import { fetchReportsSummary, fetchWsaRecommendations, fetchWsaSummary, generateReportComment } from "@/api/ai";
import { fetchCitizenReports, type CaseStatus, type CitizenReport, type IssueType, updateCitizenReport } from "@/api/reports";
import { fetchWsas, type CapStatus, type RiskLevel, type WSA, updateWsaCapStatus } from "@/api/wsa";
import { AITextBlock } from "@/components/AITextBlock";
import { RiskBadge } from "@/components/RiskBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

const capOptions: CapStatus[] = ["none", "submitted", "in_progress", "completed"];
const issueBadgeClasses: Record<IssueType, string> = {
  leak: "border-sky-200 bg-sky-100 text-sky-800",
  outage: "border-rose-200 bg-rose-100 text-rose-800",
  quality: "border-amber-200 bg-amber-100 text-amber-800",
  billing: "border-indigo-200 bg-indigo-100 text-indigo-800",
};
const apiBaseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const riskOrder: Record<RiskLevel, number> = { high: 0, medium: 1, low: 2 };
const caseStatusOptions: CaseStatus[] = ["open", "in_review", "resolved"];

function formatPercent(value: number | null) {
  return value === null ? "Not available" : `${value}%`;
}

function resolveAssetUrl(url: string) {
  return url.startsWith("http") ? url : `${apiBaseUrl}${url}`;
}

function isReportInsideRange(report: CitizenReport, range: string) {
  if (range === "all") {
    return true;
  }

  const reportDate = new Date(report.created_at);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  if (range === "today") {
    return reportDate >= startOfToday;
  }

  const days = Number(range);
  const cutoff = new Date(now);
  cutoff.setDate(now.getDate() - days);
  return reportDate >= cutoff;
}

export function AdminPage() {
  const [reports, setReports] = useState<CitizenReport[]>([]);
  const [wsas, setWsas] = useState<WSA[]>([]);
  const [pendingCapStatus, setPendingCapStatus] = useState<Record<string, CapStatus>>({});
  const [selectedProvince, setSelectedProvince] = useState("");
  const [capSearch, setCapSearch] = useState("");
  const [selectedWsaId, setSelectedWsaId] = useState<string>("");
  const [selectedWsaSummary, setSelectedWsaSummary] = useState<string | null>(null);
  const [selectedWsaReportsSummary, setSelectedWsaReportsSummary] = useState<string | null>(null);
  const [selectedReportProvince, setSelectedReportProvince] = useState("");
  const [selectedReportWsaId, setSelectedReportWsaId] = useState("all");
  const [reportDateRange, setReportDateRange] = useState("30");
  const [selectedReportId, setSelectedReportId] = useState<string>("");
  const [reportCaseStatus, setReportCaseStatus] = useState<CaseStatus>("open");
  const [reportAdminComment, setReportAdminComment] = useState("");
  const [isGeneratingReportComment, setIsGeneratingReportComment] = useState(false);
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsaById = useMemo(
    () =>
      Object.fromEntries(wsas.map((wsa) => [wsa.id, wsa])) as Record<string, WSA>,
    [wsas],
  );
  const provinces = useMemo(() => [...new Set(wsas.map((item) => item.province))].sort((a, b) => a.localeCompare(b)), [wsas]);
  const reportProvinces = provinces;
  const provinceWsas = useMemo(
    () => (selectedProvince ? wsas.filter((wsa) => wsa.province === selectedProvince) : wsas),
    [selectedProvince, wsas],
  );
  const visibleWsas = useMemo(() => {
    const query = capSearch.trim().toLowerCase();
    const ordered = [...provinceWsas].sort((left, right) => left.name.localeCompare(right.name));
    if (!query) {
      return ordered;
    }
    return ordered.filter((wsa) => wsa.name.toLowerCase().includes(query));
  }, [capSearch, provinceWsas]);
  const selectedWsa = wsas.find((wsa) => wsa.id === selectedWsaId) ?? null;
  const reportWsaOptions = useMemo(() => {
    if (!selectedReportProvince) {
      return [];
    }
    return wsas
      .filter((wsa) => wsa.province === selectedReportProvince)
      .sort((left, right) => left.name.localeCompare(right.name));
  }, [selectedReportProvince, wsas]);
  const filteredReports = useMemo(() => {
    return reports.filter((report) => {
      const wsa = wsaById[report.wsa_id];
      if (!wsa) {
        return false;
      }
      if (selectedReportProvince && wsa.province !== selectedReportProvince) {
        return false;
      }
      if (selectedReportWsaId !== "all" && report.wsa_id !== selectedReportWsaId) {
        return false;
      }
      return isReportInsideRange(report, reportDateRange);
    });
  }, [reportDateRange, reports, selectedReportProvince, selectedReportWsaId, wsaById]);
  const selectedReport = filteredReports.find((report) => report.id === selectedReportId) ?? filteredReports[0] ?? null;
  const capCounts = useMemo(
    () => ({
      none: provinceWsas.filter((wsa) => wsa.cap_status === "none").length,
      submitted: provinceWsas.filter((wsa) => wsa.cap_status === "submitted").length,
      in_progress: provinceWsas.filter((wsa) => wsa.cap_status === "in_progress").length,
      completed: provinceWsas.filter((wsa) => wsa.cap_status === "completed").length,
    }),
    [provinceWsas],
  );
  const recommendationTarget =
    selectedWsa ??
    [...provinceWsas].sort((left, right) => riskOrder[left.risk_level] - riskOrder[right.risk_level] || left.name.localeCompare(right.name))[0] ??
    null;

  const loadData = async () => {
    try {
      const [reportData, wsaData] = await Promise.all([fetchCitizenReports(), fetchWsas()]);
      setReports(reportData);
      setWsas(wsaData);
      setPendingCapStatus(Object.fromEntries(wsaData.map((item) => [item.id, item.cap_status])) as Record<string, CapStatus>);

      const provinceOptions = [...new Set(wsaData.map((item) => item.province))].sort((a, b) => a.localeCompare(b));
      setSelectedProvince((current) => (current && provinceOptions.includes(current) ? current : (provinceOptions[0] ?? "")));
      setSelectedReportProvince((current) => (current && provinceOptions.includes(current) ? current : (provinceOptions[0] ?? "")));
    } catch {
      setError("Unable to load admin data. Make sure you are signed in with an account that has access.");
    }
  };

  useEffect(() => {
    loadData().catch(() => setError("Unable to load admin data."));
  }, []);

  useEffect(() => {
    if (!selectedProvince) {
      setSelectedWsaId("");
      return;
    }

    if (!visibleWsas.some((wsa) => wsa.id === selectedWsaId)) {
      setSelectedWsaId(visibleWsas[0]?.id ?? "");
    }
  }, [selectedProvince, selectedWsaId, visibleWsas]);

  useEffect(() => {
    if (!selectedReportProvince) {
      setSelectedReportWsaId("all");
      return;
    }
    if (selectedReportWsaId !== "all" && !reportWsaOptions.some((wsa) => wsa.id === selectedReportWsaId)) {
      setSelectedReportWsaId("all");
    }
  }, [reportWsaOptions, selectedReportProvince, selectedReportWsaId]);

  useEffect(() => {
    if (!selectedReport) {
      setSelectedReportId("");
      setReportCaseStatus("open");
      setReportAdminComment("");
      return;
    }
    if (!filteredReports.some((report) => report.id === selectedReportId)) {
      setSelectedReportId(selectedReport.id);
    }
  }, [filteredReports, selectedReport, selectedReportId]);

  useEffect(() => {
    if (!selectedReport) {
      return;
    }
    setReportCaseStatus(selectedReport.case_status || "open");
    setReportAdminComment(selectedReport.admin_comment ?? "");
  }, [selectedReport]);

  useEffect(() => {
    if (!recommendationTarget) {
      setRecommendations([]);
      return;
    }

    fetchWsaRecommendations(recommendationTarget.id)
      .then((data) => setRecommendations(data.items))
      .catch(() => setRecommendations([]));
  }, [recommendationTarget]);

  useEffect(() => {
    if (!selectedWsa) {
      setSelectedWsaSummary(null);
      setSelectedWsaReportsSummary(null);
      return;
    }

    fetchWsaSummary(selectedWsa.id)
      .then((data) => setSelectedWsaSummary(data.content))
      .catch(() => setSelectedWsaSummary(selectedWsa.summary ?? null));

    fetchReportsSummary(selectedWsa.id)
      .then((data) => setSelectedWsaReportsSummary(data.content))
      .catch(() => setSelectedWsaReportsSummary(null));
  }, [selectedWsa]);

  return (
    <div className="space-y-6">
      {error ? (
        <div className="rounded-3xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>
      ) : null}
      {successMessage ? (
        <div className="rounded-3xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">{successMessage}</div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>AI recommendations</CardTitle>
          <CardDescription>
            {recommendationTarget
              ? `Focused on ${recommendationTarget.name} in ${recommendationTarget.province}.`
              : "Recommendations will appear after WSA data loads."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AITextBlock items={recommendations} label="AI recommendations" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Citizen reports</CardTitle>
          <CardDescription>Filter reports by province, WSA, and timeframe, then open one report to inspect its location and photos.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Province filter</label>
              <Select value={selectedReportProvince} onValueChange={setSelectedReportProvince}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a province" />
                </SelectTrigger>
                <SelectContent>
                  {reportProvinces.map((province) => (
                    <SelectItem key={province} value={province}>
                      {province}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">WSA filter</label>
              <Select value={selectedReportWsaId} onValueChange={setSelectedReportWsaId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a WSA" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All WSAs</SelectItem>
                  {reportWsaOptions.map((wsa) => (
                    <SelectItem key={wsa.id} value={wsa.id}>
                      {wsa.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Date filter</label>
              <Select value={reportDateRange} onValueChange={setReportDateRange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a date range" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="today">Today</SelectItem>
                  <SelectItem value="7">Last 7 days</SelectItem>
                  <SelectItem value="30">Last 30 days</SelectItem>
                  <SelectItem value="all">All time</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {selectedReport ? (
            <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
              <Card className="border border-border/70 shadow-none">
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-3">
                    <CardTitle className="text-lg">{wsaById[selectedReport.wsa_id]?.name ?? "Report detail"}</CardTitle>
                    <Badge className={issueBadgeClasses[selectedReport.issue_type]} variant="outline">
                      {selectedReport.issue_type}
                    </Badge>
                  </div>
                  <CardDescription>{wsaById[selectedReport.wsa_id]?.province ?? "Unknown province"}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm leading-6 text-foreground">{selectedReport.description ?? "No description provided"}</p>
                  <p className="text-sm text-muted-foreground">{new Date(selectedReport.created_at).toLocaleString()}</p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl bg-secondary/60 p-4">
                      <p className="text-sm text-muted-foreground">Case status</p>
                      <p className="mt-1 font-medium capitalize">{selectedReport.case_status.replace("_", " ")}</p>
                    </div>
                    <div className="rounded-2xl bg-secondary/60 p-4">
                      <p className="text-sm text-muted-foreground">Coordinates</p>
                      <p className="mt-1 font-medium">
                        {selectedReport.lat.toFixed(5)}, {selectedReport.lng.toFixed(5)}
                      </p>
                    </div>
                    <div className="rounded-2xl bg-secondary/60 p-4 sm:col-span-2">
                      <p className="text-sm text-muted-foreground">Photos</p>
                      <p className="mt-1 font-medium">{selectedReport.photo_urls.length}</p>
                    </div>
                  </div>
                  <div className="grid gap-4 xl:grid-cols-[220px_1fr]">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Update case status</label>
                      <Select value={reportCaseStatus} onValueChange={(value) => setReportCaseStatus(value as CaseStatus)}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select case status" />
                        </SelectTrigger>
                        <SelectContent>
                          {caseStatusOptions.map((option) => (
                            <SelectItem key={option} value={option}>
                              {option.replace("_", " ")}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Admin comment</label>
                      <Textarea
                        className="min-h-[128px]"
                        placeholder="Add a saved case note for this report."
                        value={reportAdminComment}
                        onChange={(event) => setReportAdminComment(event.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button
                      variant="secondary"
                      onClick={async () => {
                        try {
                          setError(null);
                          setIsGeneratingReportComment(true);
                          const response = await generateReportComment(selectedReport.id);
                          setReportAdminComment(response.content);
                          setSuccessMessage("AI draft comment generated for the selected report.");
                        } catch {
                          setError("The AI comment could not be generated right now.");
                        } finally {
                          setIsGeneratingReportComment(false);
                        }
                      }}
                    >
                      {isGeneratingReportComment ? "Generating..." : "Generate AI comment"}
                    </Button>
                    <Button
                      onClick={async () => {
                        try {
                          setError(null);
                          const updatedReport = await updateCitizenReport(selectedReport.id, {
                            case_status: reportCaseStatus,
                            admin_comment: reportAdminComment,
                          });
                          setReports((current) => current.map((report) => (report.id === updatedReport.id ? updatedReport : report)));
                          setReportCaseStatus(updatedReport.case_status);
                          setReportAdminComment(updatedReport.admin_comment ?? "");
                          setSuccessMessage("Report case update saved.");
                        } catch {
                          setError("The case update could not be saved. Please check your session and try again.");
                        }
                      }}
                    >
                      Save case update
                    </Button>
                  </div>
                  {selectedReport.photo_urls.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {selectedReport.photo_urls.map((photoUrl) => (
                        <a key={photoUrl} href={resolveAssetUrl(photoUrl)} target="_blank" rel="noreferrer" className="overflow-hidden rounded-2xl border border-border/70">
                          <img alt="Citizen report attachment" className="h-32 w-full object-cover" src={resolveAssetUrl(photoUrl)} />
                        </a>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 rounded-2xl border border-dashed border-border/80 p-4 text-sm text-muted-foreground">
                      <Camera className="h-4 w-4" />
                      No photos were uploaded for this report.
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="border border-border/70 shadow-none">
                <CardHeader>
                  <CardTitle className="text-lg">Report location</CardTitle>
                  <CardDescription>Open the selected report on a mini map to understand where the issue was logged.</CardDescription>
                </CardHeader>
                <CardContent>
                  <MapContainer center={[selectedReport.lat, selectedReport.lng]} zoom={13} scrollWheelZoom className="h-[320px] rounded-[1.5rem]">
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <CircleMarker
                      center={[selectedReport.lat, selectedReport.lng]}
                      radius={9}
                      pathOptions={{ color: "#534AB7", fillColor: "#7F77DD", fillOpacity: 0.85, weight: 2 }}
                    />
                  </MapContainer>
                </CardContent>
              </Card>
            </div>
          ) : null}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>WSA</TableHead>
                <TableHead>Issue</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Photos</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredReports.map((report) => (
                <TableRow
                  key={report.id}
                  className={report.id === selectedReport?.id ? "bg-secondary/50" : "cursor-pointer"}
                  onClick={() => setSelectedReportId(report.id)}
                >
                  <TableCell className="font-medium">{wsaById[report.wsa_id]?.name ?? report.wsa_id}</TableCell>
                  <TableCell>
                    <Badge className={issueBadgeClasses[report.issue_type]} variant="outline">
                      {report.issue_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="capitalize">{report.case_status.replace("_", " ")}</TableCell>
                  <TableCell className="max-w-md">{report.description ?? "No description provided"}</TableCell>
                  <TableCell>{report.photo_urls.length}</TableCell>
                  <TableCell>{new Date(report.created_at).toLocaleString()}</TableCell>
                </TableRow>
              ))}
              {filteredReports.length === 0 ? (
                <TableRow>
                  <TableCell className="text-muted-foreground" colSpan={6}>
                    No reports match the selected filters.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>CAP status updates</CardTitle>
          <CardDescription>Choose a province first, then focus on a smaller WSA list, see province totals, and open one WSA for detail.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-[280px_1fr]">
            <div className="space-y-2">
              <label className="text-sm font-medium">Province filter</label>
              <Select value={selectedProvince} onValueChange={setSelectedProvince}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a province" />
                </SelectTrigger>
                <SelectContent>
                  {provinces.map((province) => (
                    <SelectItem key={province} value={province}>
                      {province}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Search inside province</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input className="pl-10" placeholder="Search WSA name" value={capSearch} onChange={(event) => setCapSearch(event.target.value)} />
              </div>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl bg-secondary/60 p-4">
              <p className="text-sm text-muted-foreground">No CAP</p>
              <p className="mt-1 text-2xl font-semibold">{capCounts.none}</p>
            </div>
            <div className="rounded-2xl bg-secondary/60 p-4">
              <p className="text-sm text-muted-foreground">Submitted</p>
              <p className="mt-1 text-2xl font-semibold">{capCounts.submitted}</p>
            </div>
            <div className="rounded-2xl bg-secondary/60 p-4">
              <p className="text-sm text-muted-foreground">In progress</p>
              <p className="mt-1 text-2xl font-semibold">{capCounts.in_progress}</p>
            </div>
            <div className="rounded-2xl bg-secondary/60 p-4">
              <p className="text-sm text-muted-foreground">Completed</p>
              <p className="mt-1 text-2xl font-semibold">{capCounts.completed}</p>
            </div>
          </div>

          {selectedWsa ? (
            <Card className="border border-border/70 shadow-none">
              <CardHeader>
                <div className="flex flex-wrap items-center gap-3">
                  <CardTitle className="text-lg">{selectedWsa.name}</CardTitle>
                  <RiskBadge riskLevel={selectedWsa.risk_level} />
                </div>
                <CardDescription>{selectedWsa.province}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">Blue Drop</p>
                    <p className="mt-1 text-xl font-semibold">{formatPercent(selectedWsa.blue_drop_score)}</p>
                  </div>
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">NRW</p>
                    <p className="mt-1 text-xl font-semibold">{formatPercent(selectedWsa.nrw_percent)}</p>
                  </div>
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">Maintenance</p>
                    <p className="mt-1 text-xl font-semibold">{formatPercent(selectedWsa.maint_pct)}</p>
                  </div>
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">Current CAP</p>
                    <p className="mt-1 text-xl font-semibold capitalize">{selectedWsa.cap_status.replace("_", " ")}</p>
                  </div>
                </div>
                <AITextBlock content={selectedWsaSummary} label="AI risk summary" />
                <AITextBlock content={selectedWsaReportsSummary} label="AI open reports summary" />
              </CardContent>
            </Card>
          ) : null}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>WSA</TableHead>
                <TableHead>Province</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead>Current CAP</TableHead>
                <TableHead>Update</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleWsas.map((wsa) => (
                <TableRow
                  key={wsa.id}
                  className={wsa.id === selectedWsa?.id ? "bg-secondary/50" : "cursor-pointer"}
                  onClick={() => {
                    setSelectedWsaId(wsa.id);
                    setSuccessMessage(null);
                  }}
                >
                  <TableCell className="font-medium">{wsa.name}</TableCell>
                  <TableCell>{wsa.province}</TableCell>
                  <TableCell>
                    <RiskBadge riskLevel={wsa.risk_level} />
                  </TableCell>
                  <TableCell className="capitalize">{wsa.cap_status.replace("_", " ")}</TableCell>
                  <TableCell className="min-w-[280px]">
                    <div className="flex flex-col gap-3 md:flex-row">
                      <div className="flex-1">
                        <Select
                          value={pendingCapStatus[wsa.id] ?? wsa.cap_status}
                          onValueChange={(value) =>
                            setPendingCapStatus((current) => ({
                              ...current,
                              [wsa.id]: value as CapStatus,
                            }))
                          }
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="CAP status" />
                          </SelectTrigger>
                          <SelectContent>
                            {capOptions.map((option) => (
                              <SelectItem key={option} value={option}>
                                {option.replace("_", " ")}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <Button
                        variant="secondary"
                        onClick={async (event) => {
                          event.stopPropagation();
                          try {
                            const updatedWsa = await updateWsaCapStatus(wsa.id, pendingCapStatus[wsa.id] ?? wsa.cap_status);
                            setSuccessMessage(`Saved CAP status for ${updatedWsa.name}.`);
                            setError(null);
                            await loadData();
                            setSelectedWsaId(updatedWsa.id);
                          } catch {
                            setError("A CAP update failed. Please confirm your login session is still valid.");
                          }
                        }}
                      >
                        Save
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {visibleWsas.length === 0 ? (
                <TableRow>
                  <TableCell className="text-muted-foreground" colSpan={5}>
                    No WSA rows match the selected province and search.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
