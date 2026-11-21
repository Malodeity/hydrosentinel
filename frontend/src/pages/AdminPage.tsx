// The admin console: one big component with six tabs. All state lives in AdminPage() so a tab can open another tab with filters already set.
//
// HOW TO FIND THINGS (search for these in this file):
//   state            "const [" blocks at the top of AdminPage(): data (reports, wsas, alerts...), then each tab's filters (report*, cap*, audit*)
//   loading data     loadData (everything, after a save) and refreshLive (every minute, in the background)
//   derived lists    scopedReports / filteredReports (Citizen reports tab), capScopeWsas / visibleWsas (CAP tab), agedReports (backlog)
//   jumping tabs     openAgedReports, openCapView, handleOverviewNavigate (used by the Overview tiles and 'Do these first')
//   tab bar          the `tabs` array (names, badge counts and what each badge means)
//   tab panels       {activeTab === "overview"} ... "ai" | "reports" | "cap" | "users" | "audit"   (each one renders only while its tab is open)
//   messages         the toast at the bottom (successMessage / error)
// The AI assistant tab is its own component (components/AiAssistantTab.tsx); the Overview top section is components/OverviewSummary.tsx.
// Numbers are computed in src/lib/* (small pure functions with tests), so the same rule is used on every screen.

import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CircleMarker, MapContainer, TileLayer } from "react-leaflet";
import { AlertTriangle, Bell, Camera, FileText, Loader2, Search, X } from "lucide-react";

import {
  fetchCapDraft,
  fetchReportsSummary,
  fetchTrendingWsas,
  fetchWsaSummary,
  generateReportComment,
  type CapDraftItem,
  type RiskTrajectory,
} from "@/api/ai";
import { acknowledgeAlert, fetchAlerts, type Alert } from "@/api/alerts";
import { authStorage } from "@/api/client";
import { fetchAuditLog, type AuditLogEntry } from "@/api/audit";
import { createUser, fetchUsers, resetUserPassword, setUserActive, type AdminUser, type UserRole as AdminUserRole } from "@/api/users";
import { downloadReportsCsv, fetchCitizenReports, type CaseStatus, type CitizenReport, type IssueType, updateCitizenReport } from "@/api/reports";
import { downloadWsaCsv, fetchWsas, type CapStatus, type RiskLevel, type WSA, updateWsaCapStatus, fetchRiskHistory, fetchRiskSchedule, scoreWsaRisk, type RiskSchedule, type RiskScoreHistoryEntry } from "@/api/wsa";
import { AITextBlock } from "@/components/AITextBlock";
import { AiAssistantTab } from "@/components/AiAssistantTab";
import { RiskBadge } from "@/components/RiskBadge";
import { dataCompleteness } from "@/components/WSACard";
import { AdminTabs, type AdminTab } from "@/components/AdminTabs";
import { ContractorsTab } from "@/components/ContractorsTab";
import { ReportTicketPanel } from "@/components/ReportTicketPanel";
import { TabSkeleton } from "@/components/TabSkeleton";
import { TicketStatus } from "@/components/TicketStatus";
import { OverviewSummary, type OverviewTarget } from "@/components/OverviewSummary";
import { ReportCharts } from "@/components/ReportCharts";
import { CapCharts } from "@/components/CapCharts";
import { AgeBadge } from "@/components/AgeBadge";
import { IssueLabel } from "@/components/IssueLabel";
import { StatusLabel } from "@/components/StatusLabel";
import { PhotoAnalysisPanel } from "@/components/PhotoAnalysisPanel";
import { Pager } from "@/components/Pager";
import { clusterReportsForAlert, reportBounds } from "@/lib/alertCluster";
import { formatAuditAction, formatAuditValue } from "@/lib/auditFormat";
import { describeDeadline } from "@/lib/capDeadline";
import { riskTrend } from "@/lib/riskTrend";
import { paginate } from "@/lib/pagination";
import { isReportInsideRange } from "@/lib/reportDateRange";
import { AGE_LEVELS, ageInDays, formatAge, isUnresolved, reportAgeLevel } from "@/lib/reportAge";
import { countByStatus, matchesReportFilters, sortOldestFirst, type IssueFilter, type StatusFilter } from "@/lib/reportFilters";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

const capOptions: CapStatus[] = ["none", "submitted", "in_progress", "completed"];
const alertBadgeClasses: Record<string, string> = {
  risk_level_high: "border-rose-200 bg-rose-100 text-rose-800",
  risk_level_increased: "border-orange-200 bg-orange-100 text-orange-800",
  report_volume_spike: "border-amber-200 bg-amber-100 text-amber-800",
  cap_overdue: "border-purple-200 bg-purple-100 text-purple-800",
  geo_cluster_incident: "border-red-300 bg-red-100 text-red-900",
  assignment_overdue: "border-fuchsia-200 bg-fuchsia-100 text-fuchsia-900",
};
const alertTypeLabel: Record<string, string> = {
  risk_level_high: "High risk",
  risk_level_increased: "Risk increased",
  report_volume_spike: "Report spike",
  cap_overdue: "CAP overdue",
  geo_cluster_incident: "Localized incident",
  assignment_overdue: "Repair overdue",
};
const issueBadgeClasses: Record<IssueType, string> = {
  leak: "border-sky-200 bg-sky-100 text-sky-800",
  outage: "border-rose-200 bg-rose-100 text-rose-800",
  quality: "border-amber-200 bg-amber-100 text-amber-800",
  billing: "border-indigo-200 bg-indigo-100 text-indigo-800",
};
const apiBaseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const caseStatusOptions: CaseStatus[] = ["open", "in_review", "resolved"];

type AdminTabId = "overview" | "reports" | "contractors" | "cap" | "ai" | "users" | "audit";
const ADMIN_TAB_IDS: AdminTabId[] = ["overview", "reports", "contractors", "cap", "ai", "users", "audit"];
const REPORTS_PAGE_SIZE = 8;
const ALL_PROVINCES = "*"; // province select value meaning every province
const CAP_PAGE_SIZE = 8;
const AUDIT_PAGE_SIZE = 15;

function formatPercent(value: number | null) {
  return value === null ? "Not available" : `${value}%`;
}

function resolveAssetUrl(url: string) {
  return url.startsWith("http") ? url : `${apiBaseUrl}${url}`;
}


// Risk history as a small step line (low / medium / high) with a plain-words label. Red = got worse, green = improved, grey = unchanged.
function RiskTrendSparkline({ entries }: { entries: RiskScoreHistoryEntry[] }) {
  const trend = riskTrend(entries);
  if (!trend) return null;
  const width = 120;
  const height = 28;
  const step = width / (trend.levels.length - 1);
  const levelIndex = { low: 0, medium: 1, high: 2 };
  const points = trend.levels.map((level, index) => `${index * step},${height - 3 - (levelIndex[level] / 2) * (height - 6)}`).join(" ");
  const tone = trend.direction === "worse" ? "text-rose-600" : trend.direction === "better" ? "text-emerald-600" : "text-slate-500";
  const label = trend.direction === "worse" ? "Getting worse" : trend.direction === "better" ? "Improving" : "No change";

  return (
    <div className="flex items-center gap-3" title="Each point is one risk scoring, oldest to newest. Higher on the line means a higher risk level.">
      <div className="text-right text-xs">
        <p className={cn("font-semibold", tone)}>{label}</p>
        <p className="text-muted-foreground">
          {trend.from} to {trend.to} over {trend.count} scorings
        </p>
      </div>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className={tone} aria-hidden="true">
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

const CAP_DOT: Record<CapStatus, string> = { none: "#94a3b8", submitted: "#0ea5e9", in_progress: "#f59e0b", completed: "#16a34a" };
const DEADLINE_TEXT: Record<string, string> = { overdue: "font-semibold text-rose-700", soon: "text-amber-700", ok: "text-muted-foreground", none: "text-muted-foreground" };

// CAP status (dot + words) with its deadline underneath in plain language: "12 Dec 2026 · in 36 days" or "... · 5 days overdue"
function CapProgress({ status, dueDate }: { status: CapStatus; dueDate: string | null }) {
  const deadline = describeDeadline(status, dueDate);
  return (
    <div>
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-sm font-medium capitalize">
        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: CAP_DOT[status] }} aria-hidden="true" />
        {status === "none" ? "No CAP" : status.replace("_", " ")}
      </span>
      <p className={cn("mt-0.5 text-xs", DEADLINE_TEXT[deadline.tone])}>{deadline.text}</p>
    </div>
  );
}

// the admin console. all state lives in this one component; each tab only decides what to show:
//   overview - system alerts, reports waiting longest, authorities trending toward higher risk
//   reports  - citizen reports: filters, paged list, detail, AI note, status change
//   cap      - corrective action plans: status chips, table, AI risk summary, draft and accept a CAP
//   ai       - ask the data, ask the regulations, AI recommendations
//   users    - create and deactivate users
//   audit    - append-only history of admin changes
// the active tab is kept in the url (?tab=reports). AI text is only fetched while its tab is open, because every AI call costs money
export function AdminPage() {
  const [reports, setReports] = useState<CitizenReport[]>([]);
  const [wsas, setWsas] = useState<WSA[]>([]);
  const [pendingCapStatus, setPendingCapStatus] = useState<Record<string, CapStatus>>({});
  const [pendingCapDueDate, setPendingCapDueDate] = useState<Record<string, string>>({});
  const [selectedProvince, setSelectedProvince] = useState("");
  const [capSearch, setCapSearch] = useState("");
  const [capRiskFilter, setCapRiskFilter] = useState<RiskLevel | "all">("all");
  const [capOverdueOnly, setCapOverdueOnly] = useState(false);
  const [selectedWsaId, setSelectedWsaId] = useState<string>("");
  const [selectedWsaSummary, setSelectedWsaSummary] = useState<string | null>(null);
  const [selectedWsaReportsSummary, setSelectedWsaReportsSummary] = useState<string | null>(null);
  const [selectedReportProvince, setSelectedReportProvince] = useState("");
  const [selectedReportWsaId, setSelectedReportWsaId] = useState("all");
  const [reportDateRange, setReportDateRange] = useState("all");
  const [selectedReportId, setSelectedReportId] = useState<string>("");
  const [reportCaseStatus, setReportCaseStatus] = useState<CaseStatus>("open");
  const [reportAdminComment, setReportAdminComment] = useState("");
  const [isGeneratingReportComment, setIsGeneratingReportComment] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [riskHistory, setRiskHistory] = useState<RiskScoreHistoryEntry[]>([]);
  const [isScoring, setIsScoring] = useState(false);
  const [scoreMessage, setScoreMessage] = useState<string | null>(null);
  const [riskSchedule, setRiskSchedule] = useState<RiskSchedule | null>(null);
  useEffect(() => {
    fetchRiskSchedule().then(setRiskSchedule).catch(() => setRiskSchedule(null)); // a missing schedule only hides the note below
  }, []);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserRole, setNewUserRole] = useState<AdminUserRole>("viewer");
  const [newUserWsaId, setNewUserWsaId] = useState("all"); // "all" = a national admin; an authority id = an admin who only manages that authority
  const [userManagementError, setUserManagementError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [trendingWsas, setTrendingWsas] = useState<RiskTrajectory[]>([]);

  const [capDraftItems, setCapDraftItems] = useState<CapDraftItem[] | null>(null);
  const [isDraftingCap, setIsDraftingCap] = useState(false);
  const [acceptedCapDraftIndex, setAcceptedCapDraftIndex] = useState<number | null>(null);
  const [isAcceptingCapDraft, setIsAcceptingCapDraft] = useState(false);
  const [expandedClusterAlertId, setExpandedClusterAlertId] = useState<string | null>(null);
  const [showAcknowledgedAlerts, setShowAcknowledgedAlerts] = useState(false);

  // the active tab lives in the URL (?tab=reports) so a refresh or the back button keeps the admin where they were
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab") as AdminTabId | null;
  // tabs that read across every authority are not offered to an admin tied to one authority (the server refuses them too)
  const tabAllowed = (tab: AdminTabId) => !authStorage.getUser()?.wsa_id || !["ai", "users", "audit"].includes(tab);
  const activeTab: AdminTabId = requestedTab && ADMIN_TAB_IDS.includes(requestedTab) && tabAllowed(requestedTab) ? requestedTab : "overview";
  const setActiveTab = (tab: AdminTabId) => setSearchParams({ tab }, { replace: true });

  const [reportStatusFilter, setReportStatusFilter] = useState<StatusFilter>("all");
  const [reportIssueFilter, setReportIssueFilter] = useState<IssueFilter>("all");
  const [reportQuery, setReportQuery] = useState("");
  const [reportAgeFilter, setReportAgeFilter] = useState("0"); // minimum days waiting; "0" means any age
  const [reportOldestFirst, setReportOldestFirst] = useState(false);
  const [reportPage, setReportPage] = useState(1);
  const [capStatusFilter, setCapStatusFilter] = useState<CapStatus | "all">("all");
  const [capPage, setCapPage] = useState(1);
  const [auditActionFilter, setAuditActionFilter] = useState("all");
  const [auditPage, setAuditPage] = useState(1);
  // remembers which authority state the AI text was fetched for, so switching tabs back and forth costs no extra AI calls
  const summaryLoadedFor = useRef<string | null>(null);
  const riskHistoryLoadedFor = useRef<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingSummaries, setIsLoadingSummaries] = useState(false);
  const currentUserId = authStorage.getUser()?.id ?? null;
  // an admin tied to one authority (wsa_id set) sees only that authority and has no Users, Audit log or AI assistant tabs
  const isNationalAdmin = !authStorage.getUser()?.wsa_id;

  const wsaById = useMemo(
    () =>
      Object.fromEntries(wsas.map((wsa) => [wsa.id, wsa])) as Record<string, WSA>,
    [wsas],
  );
  const provinces = useMemo(() => [...new Set(wsas.map((item) => item.province))].sort((a, b) => a.localeCompare(b)), [wsas]);
  const reportProvinces = provinces;
  const provinceWsas = useMemo(
    () => (selectedProvince && selectedProvince !== ALL_PROVINCES ? wsas.filter((wsa) => wsa.province === selectedProvince) : wsas),
    [selectedProvince, wsas],
  );
  // province + risk + overdue narrow the set; the status chips then count inside it, so every chip number matches the rows it would show
  const capScopeWsas = useMemo(
    () =>
      provinceWsas
        .filter((wsa) => capRiskFilter === "all" || wsa.risk_level === capRiskFilter)
        .filter((wsa) => !capOverdueOnly || describeDeadline(wsa.cap_status, wsa.cap_due_date).tone === "overdue"),
    [capOverdueOnly, capRiskFilter, provinceWsas],
  );
  const visibleWsas = useMemo(() => {
    const query = capSearch.trim().toLowerCase();
    const ordered = [...capScopeWsas]
      .filter((wsa) => capStatusFilter === "all" || wsa.cap_status === capStatusFilter)
      .sort((left, right) => left.name.localeCompare(right.name));
    if (!query) {
      return ordered;
    }
    return ordered.filter((wsa) => wsa.name.toLowerCase().includes(query));
  }, [capScopeWsas, capSearch, capStatusFilter]);
  const capPageData = paginate(visibleWsas, capPage, CAP_PAGE_SIZE);
  const selectedWsa = wsas.find((wsa) => wsa.id === selectedWsaId) ?? null;
  const reportWsaOptions = useMemo(() => {
    if (!selectedReportProvince) {
      return [];
    }
    return wsas
      .filter((wsa) => wsa.province === selectedReportProvince)
      .sort((left, right) => left.name.localeCompare(right.name));
  }, [selectedReportProvince, wsas]);
  // province, authority and date narrow the scope; status, issue type and search then filter inside it
  const scopedReports = useMemo(() => {
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
  const reportStatusCounts = useMemo(
    () =>
      countByStatus(
        scopedReports.filter((report) =>
          matchesReportFilters(
            report,
            { status: "all", issue: reportIssueFilter, query: reportQuery, minAgeDays: Number(reportAgeFilter) },
            wsaById[report.wsa_id]?.name ?? "",
          ),
        ),
      ),
    [reportAgeFilter, reportIssueFilter, reportQuery, scopedReports, wsaById],
  );
  const filteredReports = useMemo(() => {
    const matching = scopedReports.filter((report) =>
      matchesReportFilters(
        report,
        { status: reportStatusFilter, issue: reportIssueFilter, query: reportQuery, minAgeDays: Number(reportAgeFilter) },
        wsaById[report.wsa_id]?.name ?? "",
      ),
    );
    return reportOldestFirst ? sortOldestFirst(matching) : matching;
  }, [reportAgeFilter, reportIssueFilter, reportOldestFirst, reportQuery, reportStatusFilter, scopedReports, wsaById]);
  // unresolved reports that have waited 3+ days, longest first: the backlog that needs someone's attention
  const agedReports = useMemo(
    () => sortOldestFirst(reports.filter((report) => isUnresolved(report) && ageInDays(report.created_at) >= AGE_LEVELS[1].minDays)),
    [reports],
  );
  const reportsPage = paginate(filteredReports, reportPage, REPORTS_PAGE_SIZE);
  const selectedReport = filteredReports.find((report) => report.id === selectedReportId) ?? filteredReports[0] ?? null;
  const capCounts = useMemo(
    () => ({
      none: capScopeWsas.filter((wsa) => wsa.cap_status === "none").length,
      submitted: capScopeWsas.filter((wsa) => wsa.cap_status === "submitted").length,
      in_progress: capScopeWsas.filter((wsa) => wsa.cap_status === "in_progress").length,
      completed: capScopeWsas.filter((wsa) => wsa.cap_status === "completed").length,
    }),
    [capScopeWsas],
  );
  const auditActions = useMemo(() => [...new Set(auditLog.map((entry) => entry.action))].sort(), [auditLog]);
  const auditPageData = paginate(
    auditLog.filter((entry) => auditActionFilter === "all" || entry.action === auditActionFilter),
    auditPage,
    AUDIT_PAGE_SIZE,
  );

  // loads everything the console needs in one go (reports, authorities, alerts, audit log, users). called again after a save so the screen matches the database
  const loadData = async () => {
    try {
      // the audit log and accounts are for national admins; an admin tied to one authority gets empty lists instead of an error
      const [reportData, wsaData, alertData, auditData, userData] = await Promise.all([
        fetchCitizenReports(),
        fetchWsas(),
        fetchAlerts(),
        isNationalAdmin ? fetchAuditLog() : Promise.resolve([] as AuditLogEntry[]),
        isNationalAdmin ? fetchUsers() : Promise.resolve([] as AdminUser[]),
      ]);
      setReports(reportData);
      setWsas(wsaData);
      setAlerts(alertData);
      setAuditLog(auditData);
      setAdminUsers(userData);
      setPendingCapStatus(Object.fromEntries(wsaData.map((item) => [item.id, item.cap_status])) as Record<string, CapStatus>);

      const provinceOptions = [...new Set(wsaData.map((item) => item.province))].sort((a, b) => a.localeCompare(b));
      setSelectedProvince((current) => (current === ALL_PROVINCES || (current && provinceOptions.includes(current)) ? current : (provinceOptions[0] ?? "")));
      setSelectedReportProvince((current) => (current && provinceOptions.includes(current) ? current : ""));
    } catch {
      setError("Unable to load admin data. Make sure you are signed in with an account that has access.");
    }
  };

  useEffect(() => {
    loadData()
      .catch(() => setError("Unable to load admin data."))
      .finally(() => setIsLoading(false));
    fetchTrendingWsas().then(setTrendingWsas).catch(() => setTrendingWsas([]));
  }, []);

  // keeps the numbers live: every minute, while this browser tab is visible, re-read reports, authorities and alerts.
  // it deliberately does not touch the CAP edit boxes, so nothing an admin is typing is ever overwritten
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const refreshLive = async () => {
    try {
      const [reportData, wsaData, alertData, auditData] = await Promise.all([
        fetchCitizenReports(),
        fetchWsas(),
        fetchAlerts(),
        isNationalAdmin ? fetchAuditLog() : Promise.resolve([] as AuditLogEntry[]),
      ]);
      setReports(reportData);
      setWsas(wsaData);
      setAlerts(alertData);
      setAuditLog(auditData); // so the Audit log tab shows the change that was just saved
      setLastRefreshed(new Date());
    } catch {
      // a failed background refresh stays silent: the numbers on screen are still the last good ones
    }
  };
  useEffect(() => {
    const timer = setInterval(() => {
      if (!document.hidden) void refreshLive();
    }, 60_000);
    return () => clearInterval(timer);
  }, []);

  // success messages clear themselves; errors stay until dismissed so they are not missed
  useEffect(() => {
    if (!successMessage) {
      return;
    }
    const timer = setTimeout(() => setSuccessMessage(null), 6000);
    return () => clearTimeout(timer);
  }, [successMessage]);

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
    // keyed on the saved values, not the object: the background refresh creates new objects every minute and must not wipe a note being typed
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedReport?.id, selectedReport?.case_status, selectedReport?.admin_comment]);

  // page changes reset to the first page so a narrower filter never leaves the admin on an empty page
  useEffect(() => {
    setReportPage(1);
  }, [selectedReportProvince, selectedReportWsaId, reportDateRange, reportStatusFilter, reportIssueFilter, reportQuery, reportAgeFilter, reportOldestFirst]);
  useEffect(() => {
    setCapPage(1);
  }, [selectedProvince, capSearch, capStatusFilter, capRiskFilter, capOverdueOnly]);
  useEffect(() => {
    setAuditPage(1);
  }, [auditActionFilter]);


  useEffect(() => {
    setCapDraftItems(null);
    setAcceptedCapDraftIndex(null);

    if (!selectedWsa) {
      setSelectedWsaSummary(null);
      setSelectedWsaReportsSummary(null);
      setRiskHistory([]);
      summaryLoadedFor.current = null;
      riskHistoryLoadedFor.current = null;
      return;
    }

    const key = selectedWsa.id;
    riskHistoryLoadedFor.current = key;
    fetchRiskHistory(key)
      .then((data) => riskHistoryLoadedFor.current === key && setRiskHistory(data))
      .catch(() => riskHistoryLoadedFor.current === key && setRiskHistory([]));
  }, [selectedWsa]);

  useEffect(() => {
    if (activeTab !== "cap" || !selectedWsa) {
      return;
    }
    const key = `${selectedWsa.id}:${selectedWsa.updated_at}`;
    if (summaryLoadedFor.current === key) {
      return;
    }
    summaryLoadedFor.current = key;
    // clear the previous authority's text straight away so it is never shown under the wrong name
    setSelectedWsaSummary(null);
    setSelectedWsaReportsSummary(null);
    setIsLoadingSummaries(true);

    const isCurrent = () => summaryLoadedFor.current === key;
    const summaryRequest = fetchWsaSummary(selectedWsa.id)
      .then((data) => isCurrent() && setSelectedWsaSummary(data.content))
      .catch(() => isCurrent() && setSelectedWsaSummary(selectedWsa.summary ?? null));
    const reportsRequest = fetchReportsSummary(selectedWsa.id)
      .then((data) => isCurrent() && setSelectedWsaReportsSummary(data.content))
      .catch(() => isCurrent() && setSelectedWsaReportsSummary(null));
    Promise.all([summaryRequest, reportsRequest]).finally(() => isCurrent() && setIsLoadingSummaries(false));
  }, [selectedWsa, activeTab]);

  const unacknowledgedAlerts = alerts.filter((a) => !a.acknowledged_at);
  // handled alerts leave the list; "Show acknowledged" brings the history back
  const visibleAlerts = showAcknowledgedAlerts ? alerts : unacknowledgedAlerts;
  const acknowledgedCount = alerts.length - unacknowledgedAlerts.length;
  // opens the reports tab showing the backlog (unresolved 3+ days, oldest first) unless told which filters to apply, optionally with one report selected
  const openAgedReports = (options: { reportId?: string; status?: StatusFilter; age?: string } = {}) => {
    setSelectedReportProvince("");
    setSelectedReportWsaId("all");
    setReportDateRange("all");
    setReportStatusFilter(options.status ?? "all");
    setReportIssueFilter("all");
    setReportQuery("");
    setReportAgeFilter(options.age ?? "3");
    setReportOldestFirst(true);
    if (options.reportId) setSelectedReportId(options.reportId);
    setActiveTab("reports");
  };
  // back to "everything": what the tab shows when nobody has narrowed it
  const reportFiltersActive =
    reportStatusFilter !== "all" || reportIssueFilter !== "all" || reportQuery !== "" || reportAgeFilter !== "0" || selectedReportProvince !== "" || selectedReportWsaId !== "all" || reportDateRange !== "all";
  const clearReportFilters = () => {
    setReportStatusFilter("all");
    setReportIssueFilter("all");
    setReportQuery("");
    setReportAgeFilter("0");
    setSelectedReportProvince("");
    setSelectedReportWsaId("all");
    setReportDateRange("all");
  };
  const capFiltersActive = selectedProvince !== ALL_PROVINCES || capStatusFilter !== "all" || capRiskFilter !== "all" || capOverdueOnly || capSearch !== "";
  const clearCapFilters = () => {
    setSelectedProvince(ALL_PROVINCES);
    setCapStatusFilter("all");
    setCapRiskFilter("all");
    setCapOverdueOnly(false);
    setCapSearch("");
  };
  // opens the CAP tab across all provinces with the given filters, so a tile's number matches the rows shown
  const openCapView = (options: { status?: CapStatus | "all"; risk?: RiskLevel | "all"; overdue?: boolean; query?: string }) => {
    setSelectedProvince(ALL_PROVINCES);
    setCapStatusFilter(options.status ?? "all");
    setCapRiskFilter(options.risk ?? "all");
    setCapOverdueOnly(options.overdue ?? false);
    setCapSearch(options.query ?? "");
    setActiveTab("cap");
  };
  const handleOverviewNavigate = (target: OverviewTarget) =>
    target.tab === "reports" ? openAgedReports({ reportId: target.reportId, status: target.status, age: target.age }) : openCapView(target);
  // same rule as the Overview tile and the CAP table (a plan with no status never counts), so the badge cannot disagree with them
  const capOverdueCount = wsas.filter((wsa) => describeDeadline(wsa.cap_status, wsa.cap_due_date).tone === "overdue").length;
  const overdueTicketCount = reports.filter((report) => report.assignment?.overdue).length;
  const tabs: AdminTab<AdminTabId>[] = [
    { id: "overview", label: "Overview", count: unacknowledgedAlerts.length, countLabel: "Alerts not yet acknowledged" },
    { id: "reports", label: "Citizen reports", count: agedReports.length, countLabel: "Unresolved reports that have waited 3 days or more" },
    { id: "contractors", label: "Contractors", count: overdueTicketCount, countLabel: "Repair tickets past their due time" },
    { id: "cap", label: "CAP management", count: capOverdueCount, countLabel: "Corrective action plans past their deadline" },
    ...(isNationalAdmin
      ? ([{ id: "ai", label: "AI assistant" }, { id: "users", label: "Users" }, { id: "audit", label: "Audit log" }] as AdminTab<AdminTabId>[])
      : []),
  ];

  return (
    <div className="space-y-6">
      <AdminTabs
        tabs={tabs}
        active={activeTab}
        onChange={setActiveTab}
        trailing={
          <Button asChild size="sm" variant="outline">
            <Link to="/admin/report">
              <FileText className="h-4 w-4" />
              Management report
            </Link>
          </Button>
        }
      />

      <p className="-mt-3 text-right text-xs text-muted-foreground">
        {lastRefreshed ? `Updated ${lastRefreshed.toLocaleTimeString("en-ZA", { hour: "2-digit", minute: "2-digit" })}` : "Live"} · refreshes every minute ·{" "}
        <button type="button" className="underline underline-offset-2 hover:text-foreground" onClick={() => void refreshLive()}>
          Refresh now
        </button>
      </p>

      {/* while the first load is still running every tab shows its own placeholder shapes instead of a blank page */}
      {isLoading ? <TabSkeleton tab={activeTab} /> : null}

      {/* ============ TAB: Overview. summary tiles, alerts, longest-waiting reports (the trending list is inside OverviewSummary) ============ */}
      {!isLoading && activeTab === "overview" ? (
        <div role="tabpanel" id="admin-panel-overview" aria-labelledby="admin-tab-overview" className="space-y-6">
      <OverviewSummary wsas={wsas} reports={reports} alerts={alerts} trending={trendingWsas} loading={isLoading} onNavigate={handleOverviewNavigate} />

      {/* System alerts */}
      <Card id="system-alerts" className="scroll-mt-24">
        <CardHeader className="border-b border-border/60 pb-4">
          <div className="flex items-center gap-3">
            <Bell className="h-5 w-5 text-primary" />
            <CardTitle>System alerts</CardTitle>
            {unacknowledgedAlerts.length > 0 && (
              <span className="inline-flex items-center justify-center rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-800">
                {unacknowledgedAlerts.length} new
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardDescription>Raised automatically. Acknowledge an alert once it has been handled and it leaves this list.</CardDescription>
            {acknowledgedCount > 0 ? (
              <Button size="sm" variant="ghost" onClick={() => setShowAcknowledgedAlerts((current) => !current)}>
                {showAcknowledgedAlerts ? "Hide" : "Show"} acknowledged ({acknowledgedCount})
              </Button>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading alerts...</p>
          ) : alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No alerts have been generated yet.</p>
          ) : visibleAlerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">Every alert has been acknowledged. Nothing needs attention.</p>
          ) : (
            <ScrollArea className="max-h-[28rem]">
              <div className="space-y-2 pr-4">
                {visibleAlerts.map((alert) => {
                  const isCluster = alert.alert_type === "geo_cluster_incident";
                  const isExpanded = expandedClusterAlertId === alert.id;
                  // the window is measured from when the alert was raised, so the map still works days later
                  const clusterReports = isCluster ? clusterReportsForAlert(alert, reports) : [];

                  return (
                    <div
                      key={alert.id}
                      id={`alert-${alert.id}`}
                      className={`rounded-2xl border p-4 ${alert.acknowledged_at ? "bg-secondary/30 opacity-70" : "border-border"}`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
                            <Badge className={alertBadgeClasses[alert.alert_type]} variant="outline">
                              {alertTypeLabel[alert.alert_type]}
                            </Badge>
                            <span className="text-sm font-medium">{alert.wsa_name}</span>
                          </div>
                          <p className="pl-6 text-sm text-muted-foreground">{alert.message}</p>
                          <p className="pl-6 text-xs text-muted-foreground">
                            {new Date(alert.created_at).toLocaleString()}
                            {alert.acknowledged_at ? ` · Acknowledged ${new Date(alert.acknowledged_at).toLocaleString()}` : ""}
                          </p>
                        </div>
                        <div className="flex shrink-0 gap-2">
                          {isCluster && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setExpandedClusterAlertId(isExpanded ? null : alert.id);
                                // the list scrolls inside a fixed-height box, so bring the opened map into view (plain scroll: smooth is unreliable)
                                if (!isExpanded) setTimeout(() => document.getElementById(`alert-${alert.id}`)?.scrollIntoView({ block: "nearest" }), 50);
                              }}
                            >
                              {isExpanded ? "Hide map" : "View on map"}
                            </Button>
                          )}
                          {!alert.acknowledged_at && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={async () => {
                                try {
                                  const updated = await acknowledgeAlert(alert.id);
                                  setAlerts((current) => current.map((a) => (a.id === updated.id ? updated : a)));
                                } catch {
                                  setError("Could not acknowledge alert.");
                                }
                              }}
                            >
                              Acknowledge
                            </Button>
                          )}
                        </div>
                      </div>
                      {isCluster && isExpanded && (
                        <div className="mt-3 pl-6">
                          {clusterReports.length === 0 ? (
                            <p className="text-sm text-muted-foreground">The reports behind this alert are no longer available.</p>
                          ) : (
                            <MapContainer
                              bounds={reportBounds(clusterReports)}
                              boundsOptions={{ padding: [40, 40], maxZoom: 16 }}
                              scrollWheelZoom={false}
                              className="h-[220px] w-full rounded-2xl"
                            >
                              <TileLayer
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                              />
                              {clusterReports.map((r) => (
                                <CircleMarker
                                  key={r.id}
                                  center={[r.lat, r.lng]}
                                  radius={8}
                                  pathOptions={{ color: "#dc2626", fillColor: "#dc2626", fillOpacity: 0.8, weight: 2 }}
                                />
                              ))}
                            </MapContainer>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Reports that have waited longest */}
      {agedReports.length > 0 ? (
        <Card>
          <CardHeader className="border-b border-border/60 pb-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle>Reports waiting longest</CardTitle>
              <Button size="sm" variant="outline" onClick={() => openAgedReports()}>
                See all {agedReports.length}
              </Button>
            </div>
            <CardDescription>Unresolved for 3 days or more, oldest first</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 pt-4">
            {agedReports.slice(0, 5).map((report) => (
              <button
                key={report.id}
                type="button"
                onClick={() => openAgedReports({ reportId: report.id })}
                className="flex w-full flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/70 p-4 text-left transition-colors hover:bg-secondary/50"
              >
                <div className="min-w-0">
                  <p className="font-medium">{wsaById[report.wsa_id]?.name ?? "Unknown authority"}</p>
                  <p className="line-clamp-1 text-sm text-muted-foreground">{report.description ?? "No description provided"}</p>
                  <p className="mt-0.5 text-xs"><IssueLabel type={report.issue_type} /></p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusLabel status={report.case_status} />
                  <AgeBadge report={report} />
                </div>
              </button>
            ))}
          </CardContent>
        </Card>
      ) : null}

        </div>
      ) : null}

      {/* ============ TAB: AI assistant (components/AiAssistantTab.tsx) ============ */}
      {!isLoading && activeTab === "ai" ? (
        <div role="tabpanel" id="admin-panel-ai" aria-labelledby="admin-tab-ai" className="space-y-6">
          <AiAssistantTab wsas={wsas} />
        </div>
      ) : null}

      {/* ============ TAB: Citizen reports. filters + charts, the list on the left, the selected report on the right ============ */}
      {!isLoading && activeTab === "reports" ? (
        <div role="tabpanel" id="admin-panel-reports" aria-labelledby="admin-tab-reports" className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>Citizen reports</CardTitle>
            <Button variant="outline" size="sm" onClick={() => downloadReportsCsv()}>
              Export CSV
            </Button>
          </div>
          <CardDescription>Narrow by place and date, then filter by status, issue or text</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Province filter</label>
              <Select value={selectedReportProvince || "all"} onValueChange={(value) => setSelectedReportProvince(value === "all" ? "" : value)}>
                <SelectTrigger>
                  <SelectValue placeholder="All provinces" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All provinces</SelectItem>
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
              <Select value={selectedReportWsaId} onValueChange={setSelectedReportWsaId} disabled={!selectedReportProvince}>
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

          <div className="grid gap-4 md:grid-cols-[1fr_200px_200px]">
            <div className="space-y-2">
              <label className="text-sm font-medium">Search reports</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="pl-10"
                  placeholder="Description, reference code, authority or note"
                  value={reportQuery}
                  onChange={(event) => setReportQuery(event.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Issue type</label>
              <Select value={reportIssueFilter} onValueChange={(value) => setReportIssueFilter(value as IssueFilter)}>
                <SelectTrigger>
                  <SelectValue placeholder="Issue type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All issues</SelectItem>
                  <SelectItem value="leak">Leak</SelectItem>
                  <SelectItem value="outage">Outage</SelectItem>
                  <SelectItem value="quality">Water quality</SelectItem>
                  <SelectItem value="billing">Billing</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Waiting time</label>
              <Select value={reportAgeFilter} onValueChange={setReportAgeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Any age" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">Any age</SelectItem>
                  {AGE_LEVELS.slice(1).map((level) => (
                    <SelectItem key={level.id} value={String(level.minDays)}>
                      {level.minDays}+ days ({level.label})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by case status">
            {(
              [
                ["all", "All"],
                ["unresolved", "Unresolved"],
                ["open", "Open"],
                ["in_review", "In review"],
                ["resolved", "Resolved"],
              ] as [StatusFilter, string][]
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={reportStatusFilter === value}
                onClick={() => setReportStatusFilter(value)}
                className={cn(
                  "rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                  reportStatusFilter === value ? "border-primary bg-primary text-primary-foreground" : "border-border bg-background hover:bg-secondary",
                )}
              >
                {label} <span className="opacity-70">{reportStatusCounts[value]}</span>
              </button>
            ))}
            {reportFiltersActive ? (
              <button type="button" onClick={clearReportFilters} className="rounded-full px-3 py-1.5 text-sm font-medium text-primary underline-offset-2 hover:underline">
                Clear filters
              </button>
            ) : null}
            <button
              type="button"
              aria-pressed={reportOldestFirst}
              onClick={() => setReportOldestFirst((current) => !current)}
              className={cn(
                "ml-auto rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                reportOldestFirst ? "border-primary bg-primary text-primary-foreground" : "border-border bg-background hover:bg-secondary",
              )}
            >
              Oldest first
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground" aria-label="Waiting time flags">
            <span className="font-medium">Flags by days waiting:</span>
            {AGE_LEVELS.map((level) => (
              <span key={level.id} className="inline-flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: level.color }} />
                {level.label}
                {level.minDays > 0 ? ` ${level.minDays}d+` : ""}
              </span>
            ))}
          </div>

          {/* charts follow province / authority / date only (not status or search), so clicking a status chip never empties them */}
          <ReportCharts reports={scopedReports} authorityName={(wsaId) => wsaById[wsaId]?.name ?? "Unknown authority"} />

          <div className="grid gap-6 xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
            <div className="space-y-2">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Report</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reportsPage.items.map((report) => (
                    <TableRow
                      key={report.id}
                      className={report.id === selectedReport?.id ? "bg-secondary/60" : "cursor-pointer hover:bg-secondary/30"}
                      onClick={() => setSelectedReportId(report.id)}
                    >
                      <TableCell>
                        <span className="font-medium">{wsaById[report.wsa_id]?.name ?? report.wsa_id}</span>
                        <p className="mt-0.5 line-clamp-1 text-sm text-muted-foreground">{report.description ?? "No description provided"}</p>
                        <p className="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
                          <IssueLabel type={report.issue_type} /> · {new Date(report.created_at).toLocaleString()} · {report.photo_urls.length} photo{report.photo_urls.length === 1 ? "" : "s"}
                        </p>
                      </TableCell>
                      <TableCell className="align-top">
                        <div className="flex flex-col items-start gap-1">
                          <StatusLabel status={report.case_status} />
                          {report.assignment ? (
                            <span className="text-xs text-muted-foreground" title="Repair ticket">
                              <TicketStatus status={report.assignment.status} overdue={report.assignment.overdue} />
                              <span className="block">{report.assignment.contractor_name}</span>
                            </span>
                          ) : null}
                          <AgeBadge report={report} />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {filteredReports.length === 0 ? (
                    <TableRow>
                      <TableCell className="text-muted-foreground" colSpan={2}>
                        {isLoading ? "Loading reports..." : "No reports match these filters. Use \"Clear filters\" above."}
                      </TableCell>
                    </TableRow>
                  ) : null}
                </TableBody>
              </Table>
              <Pager page={reportsPage} noun="reports" onPageChange={setReportPage} />
            </div>

            <div className="space-y-4">
              {/* the selected report: facts, photos + AI photo check, then the status / comment form. Save refreshes the Overview numbers and audit log */}
              {selectedReport ? (
                <>
              <Card className="border border-border/70 shadow-none">
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-3">
                    <CardTitle className="text-lg">{wsaById[selectedReport.wsa_id]?.name ?? "Report detail"}</CardTitle>
                    <Badge className={issueBadgeClasses[selectedReport.issue_type]} variant="outline">
                      {selectedReport.issue_type}
                    </Badge>
                  </div>
                  <CardDescription>
                    {wsaById[selectedReport.wsa_id]?.province ?? "Unknown province"} · <span className="font-mono">{selectedReport.reference_code}</span>
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {(() => {
                    const level = reportAgeLevel(selectedReport);
                    if (!level || level.minDays === 0) return null;
                    return (
                      <div className="rounded-2xl border-l-4 bg-secondary/50 p-4 text-sm" style={{ borderLeftColor: level.color }}>
                        <p className="font-semibold">
                          {level.label}: waiting {formatAge(ageInDays(selectedReport.created_at))}
                        </p>
                        <p className="mt-0.5 text-muted-foreground">
                          {level.description}. Flags rise at {AGE_LEVELS.slice(1).map((item) => `${item.minDays} days`).join(", ")}.
                        </p>
                      </div>
                    );
                  })()}
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
                    {selectedReport.reviewed_at && (
                      <div className="rounded-2xl bg-secondary/60 p-4">
                        <p className="text-sm text-muted-foreground">Reviewed at</p>
                        <p className="mt-1 font-medium">{new Date(selectedReport.reviewed_at).toLocaleString()}</p>
                      </div>
                    )}
                    {selectedReport.resolved_at && (
                      <div className="rounded-2xl bg-secondary/60 p-4">
                        <p className="text-sm text-muted-foreground">Resolved at</p>
                        <p className="mt-1 font-medium">{new Date(selectedReport.resolved_at).toLocaleString()}</p>
                      </div>
                    )}
                  </div>
                  <div className="space-y-3">
                    <p className="text-sm font-medium">Photos ({selectedReport.photo_urls.length})</p>
                  {selectedReport.photo_urls.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {selectedReport.photo_urls.map((photoUrl) => (
                        <a key={photoUrl} href={resolveAssetUrl(photoUrl)} target="_blank" rel="noreferrer" className="overflow-hidden rounded-2xl border border-border/70">
                          <img alt="Citizen report attachment" className="h-44 w-full object-cover" src={resolveAssetUrl(photoUrl)} />
                        </a>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 rounded-2xl border border-dashed border-border/80 p-4 text-sm text-muted-foreground">
                      <Camera className="h-4 w-4" />
                      No photos were uploaded for this report.
                    </div>
                  )}
                  {selectedReport.photo_urls.length > 0 ? (
                    <PhotoAnalysisPanel
                      report={selectedReport}
                      onAnalysed={(analysis) => {
                        // keep the result on the report in memory so it shows again without another AI call
                        setReports((current) => current.map((item) => (item.id === selectedReport.id ? { ...item, photo_analysis: analysis } : item)));
                        setError(null);
                      }}
                      onError={setError}
                    />
                  ) : null}
                  </div>

                  <ReportTicketPanel report={selectedReport} onChanged={loadData} onSuccess={setSuccessMessage} />

                  <div className="border-t border-border/60 pt-4 text-sm font-medium">Update this case</div>
                  <div className="grid gap-4 xl:grid-cols-[220px_1fr]">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Status</label>
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
                  <div className="flex flex-wrap items-center justify-end gap-3">
                    <Button
                      variant="secondary"
                      onClick={async () => {
                        try {
                          setError(null);
                          setIsGeneratingReportComment(true);
                          const response = await generateReportComment(selectedReport.id, reportCaseStatus);
                          setReportAdminComment(response.content);
                          setSuccessMessage(`AI note drafted for "${reportCaseStatus.replace("_", " ")}". Review it, then save.`);
                        } catch {
                          setError("The AI comment could not be generated right now.");
                        } finally {
                          setIsGeneratingReportComment(false);
                        }
                      }}
                    >
                      {isGeneratingReportComment ? "Generating..." : "AI comment"}
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
                          void refreshLive(); // the audit log and the Overview numbers move when a report's status changes
                        } catch {
                          setError("The case update could not be saved. Please check your session and try again.");
                        }
                      }}
                    >
                      Save
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card className="border border-border/70 shadow-none">
                <CardHeader>
                  <CardTitle className="text-lg">Report location</CardTitle>
                  <CardDescription>Reported location</CardDescription>
                </CardHeader>
                <CardContent>
                  <MapContainer key={selectedReport.id} center={[selectedReport.lat, selectedReport.lng]} zoom={13} scrollWheelZoom className="h-[320px] rounded-[1.5rem]">
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
                </>
              ) : (
                <p className="rounded-2xl border border-dashed border-border/80 p-6 text-sm text-muted-foreground">Select a report to see its detail.</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
        </div>
      ) : null}

      {/* ============ TAB: CAP management. filters, charts, the selected authority's card, then the table where plans are edited ============ */}
      {/* ============ TAB: Contractors. the companies that do repairs, where they work, their tickets and how they are doing ============ */}
      {!isLoading && activeTab === "contractors" ? (
        <div role="tabpanel" id="admin-panel-contractors" aria-labelledby="admin-tab-contractors" className="space-y-6">
          <ContractorsTab wsas={wsas} reports={reports} isNational={isNationalAdmin} onChanged={loadData} />
        </div>
      ) : null}

      {!isLoading && activeTab === "cap" ? (
        <div role="tabpanel" id="admin-panel-cap" aria-labelledby="admin-tab-cap" className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>CAP status updates</CardTitle>
            <Button variant="outline" size="sm" onClick={() => downloadWsaCsv()}>
              Export CSV
            </Button>
          </div>
          <CardDescription>A CAP (Corrective Action Plan) is the plan an authority commits to in order to fix the failures found in its audits. Track its status and due date here.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-[240px_200px_1fr]">
            <div className="space-y-2">
              <label className="text-sm font-medium">Province filter</label>
              <Select value={selectedProvince} onValueChange={setSelectedProvince}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a province" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_PROVINCES}>All provinces</SelectItem>
                  {provinces.map((province) => (
                    <SelectItem key={province} value={province}>
                      {province}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Risk level</label>
              <Select value={capRiskFilter} onValueChange={(value) => setCapRiskFilter(value as RiskLevel | "all")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All risk levels</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Search authorities</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input className="pl-10" placeholder="Search WSA name" value={capSearch} onChange={(event) => setCapSearch(event.target.value)} />
              </div>
            </div>
          </div>

          <div>
            <button
              type="button"
              aria-pressed={capOverdueOnly}
              onClick={() => setCapOverdueOnly((value) => !value)}
              className={cn(
                "rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                capOverdueOnly ? "border-primary bg-primary text-primary-foreground" : "border-border bg-background hover:bg-secondary",
              )}
            >
              Overdue plans only
            </button>
            {capFiltersActive ? (
              <button type="button" onClick={clearCapFilters} className="ml-2 rounded-full px-3 py-1.5 text-sm font-medium text-primary underline-offset-2 hover:underline">
                Clear filters
              </button>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5" role="group" aria-label="Filter by CAP status">
            {(
              [
                ["all", "All", capScopeWsas.length],
                ["none", "No CAP", capCounts.none],
                ["submitted", "Submitted", capCounts.submitted],
                ["in_progress", "In progress", capCounts.in_progress],
                ["completed", "Completed", capCounts.completed],
              ] as [CapStatus | "all", string, number][]
            ).map(([value, label, count]) => (
              <button
                key={value}
                type="button"
                aria-pressed={capStatusFilter === value}
                onClick={() => setCapStatusFilter(value)}
                className={cn(
                  "rounded-2xl p-3 text-left transition-colors sm:p-4",
                  capStatusFilter === value ? "bg-primary text-primary-foreground" : "bg-secondary/60 hover:bg-secondary",
                )}
              >
                <p className={cn("text-sm", capStatusFilter === value ? "text-primary-foreground/80" : "text-muted-foreground")}>{label}</p>
                <p className="mt-1 text-2xl font-semibold">{count}</p>
              </button>
            ))}
          </div>

          {/* charts follow the province only, so they keep showing the whole picture while the table below is filtered */}
          <CapCharts wsas={provinceWsas} />

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
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">Blue Drop</p>
                    <p className="mt-1 text-xl font-semibold">{formatPercent(selectedWsa.blue_drop_score)}</p>
                  </div>
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">Green Drop</p>
                    <p className="mt-1 text-xl font-semibold">{formatPercent(selectedWsa.green_drop_score)}</p>
                  </div>
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">NRW</p>
                    <p className="mt-1 text-xl font-semibold" title={selectedWsa.nrw_estimate_note ?? undefined}>
                      {selectedWsa.nrw_percent === null && selectedWsa.nrw_estimate_percent != null ? `~${selectedWsa.nrw_estimate_percent}% (province avg)` : formatPercent(selectedWsa.nrw_percent)}
                    </p>
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
                <AITextBlock content={selectedWsaSummary} label="AI risk summary" loading={isLoadingSummaries} />
                <AITextBlock content={selectedWsaReportsSummary} label="AI open reports summary" loading={isLoadingSummaries} />
                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    size="sm"
                    disabled={isScoring}
                    onClick={async () => {
                      setIsScoring(true);
                      setScoreMessage(null);
                      try {
                        const result = await scoreWsaRisk(selectedWsa.id);
                        setScoreMessage(`Scored ${result.risk_level} (${(result.probability * 100).toFixed(1)}%) by ${result.model_source}.`);
                        setRiskHistory(await fetchRiskHistory(selectedWsa.id));
                        await loadData();
                      } catch {
                        setScoreMessage("Could not score this authority.");
                      } finally {
                        setIsScoring(false);
                      }
                    }}
                  >
                    {isScoring ? "Scoring…" : "Score risk now"}
                  </Button>
                  {scoreMessage ? <p role="status" className="text-sm text-muted-foreground">{scoreMessage}</p> : null}
                  {riskSchedule ? (
                    <p className="text-xs text-muted-foreground">
                      {riskSchedule.interval_hours > 0
                        ? `Scores also refresh by themselves every ${riskSchedule.interval_hours} h${riskSchedule.last_automatic_run ? ` (last automatic run ${new Date(riskSchedule.last_automatic_run).toLocaleString()})` : ""}.`
                        : "Automatic re-scoring is off. Scores change only when you press the button."}
                    </p>
                  ) : null}
                </div>
                {riskHistory.length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center justify-between">
                      <div><p className="text-sm font-medium">Risk score history</p><p className="text-xs text-muted-foreground">Every time this authority is scored, the result is recorded. The line shows where it is heading.</p></div>
                      <RiskTrendSparkline entries={riskHistory} />
                    </div>
                    <ScrollArea className="max-h-56">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Risk</TableHead>
                            <TableHead>Probability</TableHead>
                            <TableHead>Source</TableHead>
                            <TableHead>Scored at</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {riskHistory.map((entry) => (
                            <TableRow key={entry.id}>
                              <TableCell><RiskBadge riskLevel={entry.risk_level} compact /></TableCell>
                              <TableCell>{(entry.probability * 100).toFixed(1)}%</TableCell>
                              <TableCell className="capitalize">{entry.model_source}</TableCell>
                              <TableCell className="text-muted-foreground">{new Date(entry.scored_at).toLocaleString()}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </ScrollArea>
                  </div>
                )}

                <div className="space-y-2 pt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={isDraftingCap}
                    onClick={async () => {
                      setIsDraftingCap(true);
                      setCapDraftItems(null);
                      setAcceptedCapDraftIndex(null);
                      try {
                        const draft = await fetchCapDraft(selectedWsa.id);
                        setCapDraftItems(draft.items);
                      } catch {
                        setError("Could not generate a CAP draft for this WSA.");
                      } finally {
                        setIsDraftingCap(false);
                      }
                    }}
                  >
                    {isDraftingCap ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Drafting...
                      </>
                    ) : (
                      "Draft CAP"
                    )}
                  </Button>
                  {capDraftItems ? (
                    <div className="space-y-2">
                      {capDraftItems.map((item, index) => (
                        <div key={index} className="rounded-2xl border border-border/70 p-4 text-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="font-medium">{item.action}</p>
                            <Badge
                              variant="outline"
                              className={
                                item.priority === "high"
                                  ? "border-rose-200 bg-rose-100 text-rose-800"
                                  : item.priority === "medium"
                                    ? "border-amber-200 bg-amber-100 text-amber-800"
                                    : "border-emerald-200 bg-emerald-100 text-emerald-800"
                              }
                            >
                              {item.priority}
                              {item.suggested_due_in_days ? ` · ${item.suggested_due_in_days}d` : ""}
                            </Badge>
                          </div>
                          <p className="mt-1 text-muted-foreground">{item.justification}</p>
                          <div className="mt-3">
                            <Button
                              size="sm"
                              variant={acceptedCapDraftIndex === index ? "secondary" : "outline"}
                              disabled={isAcceptingCapDraft || acceptedCapDraftIndex === index}
                              onClick={async () => {
                                setIsAcceptingCapDraft(true);
                                try {
                                  const dueDate = item.suggested_due_in_days
                                    ? new Date(Date.now() + item.suggested_due_in_days * 86400000).toISOString().slice(0, 10)
                                    : null;
                                  const updated = await updateWsaCapStatus(selectedWsa.id, "submitted", dueDate);
                                  setAcceptedCapDraftIndex(index);
                                  setSuccessMessage(`CAP updated for ${updated.name}.`);
                                  setError(null);
                                  await loadData();
                                  setSelectedWsaId(updated.id);
                                } catch {
                                  setError("Could not apply this CAP item.");
                                } finally {
                                  setIsAcceptingCapDraft(false);
                                }
                              }}
                            >
                              {acceptedCapDraftIndex === index ? "Applied to CAP" : "Accept"}
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ) : null}

          {/* the plan table: current status + deadline on the left, "Set status" / "Set deadline" / Save on the right. Saving re-reads all data (loadData) */}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>WSA</TableHead>
                <TableHead>Province</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead title="Progress of the corrective action plan, and when it must be finished">Corrective action plan</TableHead>
                <TableHead>Set status</TableHead>
                <TableHead>Set deadline</TableHead>
                <TableHead className="w-20"><span className="sr-only">Save</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {capPageData.items.map((wsa) => (
                <TableRow
                  key={wsa.id}
                  className={wsa.id === selectedWsa?.id ? "bg-secondary/50" : "cursor-pointer"}
                  onClick={() => {
                    setSelectedWsaId(wsa.id);
                    setSuccessMessage(null);
                  }}
                >
                  <TableCell className="font-medium">
                    {wsa.name}
                    {dataCompleteness(wsa).filled < dataCompleteness(wsa).total ? (
                      <Badge variant="outline" className="ml-2 text-xs font-normal text-muted-foreground" title="Some source data (Blue Drop, Green Drop, NRW, etc.) is missing for this authority, so its risk score is less reliable">
                        {dataCompleteness(wsa).filled}/{dataCompleteness(wsa).total} data
                      </Badge>
                    ) : null}
                  </TableCell>
                  <TableCell>{wsa.province}</TableCell>
                  <TableCell>
                    <RiskBadge riskLevel={wsa.risk_level} compact />
                  </TableCell>
                  <TableCell>
                    <CapProgress status={wsa.cap_status} dueDate={wsa.cap_due_date} />
                  </TableCell>
                  <TableCell>
                      <Select
                        value={pendingCapStatus[wsa.id] ?? wsa.cap_status}
                        onValueChange={(value) =>
                          setPendingCapStatus((current) => ({
                            ...current,
                            [wsa.id]: value as CapStatus,
                          }))
                        }
                      >
                        <SelectTrigger className="min-w-36">
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
                  </TableCell>
                  <TableCell>
                      <Input
                        type="date"
                        aria-label="CAP deadline"
                        disabled={(pendingCapStatus[wsa.id] ?? wsa.cap_status) === "none"}
                        title={(pendingCapStatus[wsa.id] ?? wsa.cap_status) === "none" ? "No plan means no deadline" : undefined} className="min-w-40"
                        value={pendingCapDueDate[wsa.id] ?? wsa.cap_due_date ?? ""}
                        onChange={(event) =>
                          setPendingCapDueDate((current) => ({
                            ...current,
                            [wsa.id]: event.target.value,
                          }))
                        }
                        onClick={(event) => event.stopPropagation()}
                      />
                  </TableCell>
                  <TableCell>
                      <Button
                        variant="secondary"
                        onClick={async (event) => {
                          event.stopPropagation();
                          try {
                            const dueDate = pendingCapDueDate[wsa.id] ?? wsa.cap_due_date ?? null;
                            const updatedWsa = await updateWsaCapStatus(wsa.id, pendingCapStatus[wsa.id] ?? wsa.cap_status, dueDate || null);
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
                  </TableCell>
                </TableRow>
              ))}
              {visibleWsas.length === 0 ? (
                <TableRow>
                  <TableCell className="text-muted-foreground" colSpan={8}>
                    {isLoading ? "Loading authorities..." : "No authorities match these filters. Use \"Clear filters\" above."}
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
          <Pager page={capPageData} noun="authorities" onPageChange={setCapPage} />
        </CardContent>
      </Card>
        </div>
      ) : null}

      {/* ============ TAB: Users. create accounts, activate / deactivate ============ */}
      {!isLoading && activeTab === "users" ? (
        <div role="tabpanel" id="admin-panel-users" aria-labelledby="admin-tab-users" className="space-y-6">
      {/* User management */}
      <Card>
        <CardHeader className="border-b border-border/60 pb-4">
          <CardTitle>Admin users</CardTitle>
          <CardDescription>Create, deactivate, and manage access</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          {userManagementError ? <p className="text-sm text-destructive">{userManagementError}</p> : null}
          <div className="grid gap-3 sm:grid-cols-[1fr_1fr_140px_auto]" aria-label="Add a user">
            <Input placeholder="email@example.com" value={newUserEmail} onChange={(event) => setNewUserEmail(event.target.value)} />
            <Input
              type="password"
              placeholder="Password (min 8 chars)"
              value={newUserPassword}
              onChange={(event) => setNewUserPassword(event.target.value)}
            />
            <Select value={newUserRole} onValueChange={(value) => setNewUserRole(value as AdminUserRole)}>
              <SelectTrigger>
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="viewer">Viewer</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
            {newUserRole === "admin" ? (
              <div className="sm:col-span-4">
                <label className="text-sm font-medium">Which authorities can this admin manage?</label>
                <Select value={newUserWsaId} onValueChange={setNewUserWsaId}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All authorities (national admin)</SelectItem>
                    {[...wsas].sort((a, b) => a.name.localeCompare(b.name)).map((wsa) => (
                      <SelectItem key={wsa.id} value={wsa.id}>
                        Only {wsa.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : null}
            <Button
              onClick={async () => {
                setUserManagementError(null);
                try {
                  await createUser({
                    email: newUserEmail,
                    password: newUserPassword,
                    role: newUserRole,
                    wsa_id: newUserRole === "admin" && newUserWsaId !== "all" ? newUserWsaId : null,
                  });
                  setNewUserEmail("");
                  setNewUserPassword("");
                  setNewUserRole("viewer");
                  setNewUserWsaId("all");
                  await loadData();
                } catch {
                  setUserManagementError("Could not create user. Check the email is unique and the password is at least 8 characters.");
                }
              }}
              disabled={!newUserEmail.trim() || newUserPassword.length < 8}
            >
              Add user
            </Button>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last login</TableHead>
                <TableHead>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {adminUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.email}</TableCell>
                  <TableCell className="capitalize">
                    {user.role}
                    {user.wsa_id ? <span className="block text-xs normal-case text-muted-foreground">Only {wsaById[user.wsa_id]?.name ?? "one authority"}</span> : null}
                    {user.contractor_id ? <span className="block text-xs normal-case text-muted-foreground">Contractor login</span> : null}
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.is_active ? "outline" : "secondary"} className={user.is_active ? "" : "text-muted-foreground"}>
                      {user.is_active ? "active" : "deactivated"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={user.id === currentUserId}
                      title={user.id === currentUserId ? "You cannot deactivate your own account" : undefined}
                      onClick={async () => {
                        if (user.is_active && !window.confirm(`Deactivate ${user.email}? They will no longer be able to sign in.`)) {
                          return;
                        }
                        try {
                          const updated = await setUserActive(user.id, !user.is_active);
                          setAdminUsers((current) => current.map((u) => (u.id === updated.id ? updated : u)));
                        } catch {
                          setUserManagementError("Could not update that user.");
                        }
                      }}
                    >
                      {user.is_active ? "Deactivate" : "Reactivate"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="ml-2"
                      onClick={async () => {
                        const password = window.prompt(`New password for ${user.email} (8+ characters). Tell them in person; they should change it after signing in.`);
                        if (!password) return;
                        if (password.length < 8) {
                          setUserManagementError("A password needs at least 8 characters.");
                          return;
                        }
                        try {
                          await resetUserPassword(user.id, password);
                          setUserManagementError(null);
                        } catch {
                          setUserManagementError("Could not reset that password.");
                        }
                      }}
                    >
                      Reset password
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

        </div>
      ) : null}

      {/* ============ TAB: Audit log. read-only history of admin changes ============ */}
      {!isLoading && activeTab === "audit" ? (
        <div role="tabpanel" id="admin-panel-audit" aria-labelledby="admin-tab-audit" className="space-y-6">
      {/* Audit log */}
      <Card>
        <CardHeader className="border-b border-border/60 pb-4">
          <CardTitle>Audit log</CardTitle>
          <CardDescription>Every CAP, report, and risk change</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          {auditLog.length === 0 ? (
            <p className="text-sm text-muted-foreground">{isLoading ? "Loading audit log..." : "No audit entries yet."}</p>
          ) : (
            <>
              <div className="max-w-xs space-y-2">
                <label className="text-sm font-medium">Action</label>
                <Select value={auditActionFilter} onValueChange={setAuditActionFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="All actions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All actions</SelectItem>
                    {auditActions.map((action) => (
                      <SelectItem key={action} value={action}>
                        {formatAuditAction(action)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Action</TableHead>
                    <TableHead>Table</TableHead>
                    <TableHead>Before</TableHead>
                    <TableHead>After</TableHead>
                    <TableHead>When</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditPageData.items.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>{formatAuditAction(entry.action)}</TableCell>
                      <TableCell className="text-muted-foreground">{entry.table_name}</TableCell>
                      <TableCell className="max-w-[280px] whitespace-normal break-words text-xs text-muted-foreground" title={formatAuditValue(entry.old_value, Infinity)}>
                        {formatAuditValue(entry.old_value)}
                      </TableCell>
                      <TableCell className="max-w-[280px] whitespace-normal break-words text-xs" title={formatAuditValue(entry.new_value, Infinity)}>
                        {formatAuditValue(entry.new_value)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{new Date(entry.created_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Pager page={auditPageData} noun="entries" onPageChange={setAuditPage} />
            </>
          )}
        </CardContent>
      </Card>
        </div>
      ) : null}

      {/* messages float at the bottom right so they are seen wherever the admin has scrolled to */}
      <div className="pointer-events-none fixed bottom-6 right-6 z-[1300] flex w-[calc(100%-3rem)] max-w-sm flex-col gap-2">
        {error ? (
          <div role="alert" className="pointer-events-auto flex items-start justify-between gap-3 rounded-2xl border border-destructive/30 bg-white p-4 text-sm text-destructive shadow-soft">
            <span>{error}</span>
            <button type="button" aria-label="Dismiss message" onClick={() => setError(null)} className="shrink-0 opacity-70 hover:opacity-100">
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : null}
        {successMessage ? (
          <div role="status" className="pointer-events-auto flex items-start justify-between gap-3 rounded-2xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800 shadow-soft">
            <span>{successMessage}</span>
            <button type="button" aria-label="Dismiss message" onClick={() => setSuccessMessage(null)} className="shrink-0 opacity-70 hover:opacity-100">
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
