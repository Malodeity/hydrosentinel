# API shapes (Pydantic). Each class describes the JSON one endpoint accepts or returns, and is the contract with the frontend (frontend/src/api/*.ts
# mirrors these by hand). *Read classes are responses, *Create / *Update classes are request bodies. Validation (lengths, allowed values) lives here.

from datetime import date, datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, model_validator

from app.nrw_benchmark import NRW_ESTIMATE_NOTE, PROVINCE_NRW_PERCENT
from app.models import AlertType, AuditAction, BDCertification, CAPStatus, DWSCAPStatus, IssueType, ModelSource, NDPerformance, RiskLevel, UserRole


# pydantic models: they define what each endpoint accepts and returns. fastapi rejects anything that does not match,
# which is where the 422 validation errors come from
class WSARead(BaseModel):
    id: UUID
    name: str
    province: str
    blue_drop_score: float | None = None
    nrw_percent: float | None = None
    cap_status: CAPStatus
    cap_due_date: date | None = None
    maint_pct: float | None = None
    risk_level: RiskLevel
    summary: str | None = None
    green_drop_score: float | None = None
    dws_cap_status: DWSCAPStatus
    bd_certification: BDCertification
    nd_performance: NDPerformance
    num_water_supply_systems: int | None = None
    maint_expenditure: float | None = None
    asset_value: float | None = None
    bdrr_score: float | None = None
    bdrr_risk_level: RiskLevel | None = None
    lat: float
    lng: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def nrw_estimate_percent(self) -> float | None:
        # only when the authority has no NRW of its own: its province's average, shown as an estimate (display only, never stored or scored)
        if self.nrw_percent is not None:
            return None
        return PROVINCE_NRW_PERCENT.get(self.province)

    @computed_field
    @property
    def nrw_estimate_note(self) -> str | None:
        return NRW_ESTIMATE_NOTE if self.nrw_estimate_percent is not None else None

    @computed_field
    @property
    def maint_gap_pct(self) -> float | None:
        if self.maint_pct is None:
            return None
        return round(self.maint_pct - 8.0, 2)


class WSAUpdate(BaseModel):
    cap_status: CAPStatus
    cap_due_date: date | None = None


class CitizenReportCreate(BaseModel):
    wsa_id: UUID
    issue_type: IssueType
    description: str | None = Field(default=None, max_length=1_000)
    lat: float
    lng: float


class PhotoAnalysis(BaseModel):
    issue_type: Literal["leak", "quality", "outage", "not_water_related", "unclear"]
    severity: Literal["low", "medium", "high"]
    confidence: Literal["low", "medium", "high"]
    summary: str
    verdict: Literal["matches", "mismatch", "inconclusive"]  # decided by the server, not the model
    photo: str
    analysed_at: datetime


class CitizenReportRead(BaseModel):
    id: UUID
    wsa_id: UUID
    issue_type: IssueType
    description: str | None
    reference_code: str
    case_status: Literal["open", "in_review", "resolved"]
    admin_comment: str | None
    reviewed_by: UUID | None = None
    resolved_by: UUID | None = None
    reviewed_at: datetime | None = None
    resolved_at: datetime | None = None
    lat: float
    lng: float
    created_at: datetime
    photo_urls: list[str] = []
    photo_analysis: PhotoAnalysis | None = None
    assignment: "AssignmentSummary | None" = None

    model_config = ConfigDict(from_attributes=True)


class CitizenReportTrackRead(BaseModel):
    reference_code: str
    issue_type: IssueType
    case_status: Literal["open", "in_review", "resolved"]
    admin_comment: str | None
    created_at: datetime
    # public repair progress, with no company name or contact details: assigned, in_progress or awaiting_check
    repair_status: str | None = None
    repair_due_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WsaReportCounts(BaseModel):
    open: int
    resolved: int


# public, aggregate only: counts and a median, never a description, location, photo or reference code
class PublicReportStats(BaseModel):
    received_7d: int
    total: int
    open: int
    resolved: int
    median_days_to_resolve: float | None  # None until at least one resolved report has a recorded resolution time
    resolved_sample: int  # how many reports the median is based on
    by_wsa: dict[str, WsaReportCounts]


class CitizenReportAdminUpdate(BaseModel):
    case_status: Literal["open", "in_review", "resolved"]
    admin_comment: str | None = Field(default=None, max_length=2_000)


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    wsa_id: UUID | None = None
    contractor_id: UUID | None = None
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.viewer
    # admin tied to one authority (empty = national admin)
    wsa_id: UUID | None = None
    # required for a contractor account: the company it belongs to
    contractor_id: UUID | None = None

    @model_validator(mode="after")
    def _check_scope(self):
        if self.role == UserRole.contractor and self.contractor_id is None:
            raise ValueError("A contractor account needs a contractor_id")
        if self.role != UserRole.contractor and self.contractor_id is not None:
            raise ValueError("Only contractor accounts have a contractor_id")
        if self.role != UserRole.admin and self.wsa_id is not None:
            raise ValueError("Only admin accounts can be tied to one authority")
        return self


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=8)


class UserStatusUpdate(BaseModel):
    is_active: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str


class RiskScoreResponse(BaseModel):
    wsa_id: UUID
    name: str
    risk_level: RiskLevel
    probability: float
    model_source: ModelSource


class RiskScoreListItem(BaseModel):
    wsa_id: UUID
    name: str
    risk_level: RiskLevel


class RiskTrajectoryResponse(BaseModel):
    wsa_id: UUID
    name: str
    trend: Literal["insufficient_data", "improving", "stable", "worsening"]
    current_probability: float | None
    current_risk_level: RiskLevel | None
    projected_probability: float | None
    projected_risk_level: RiskLevel | None
    crosses_tier: bool
    sample_size: int


class RiskScoreHistoryRead(BaseModel):
    id: UUID
    wsa_id: UUID
    risk_level: RiskLevel
    probability: float
    model_source: ModelSource
    model_version: str | None
    scored_by: UUID | None
    scored_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogRead(BaseModel):
    id: UUID
    user_id: UUID
    action: AuditAction
    table_name: str
    record_id: UUID
    old_value: dict | None
    new_value: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertRead(BaseModel):
    id: UUID
    wsa_id: UUID
    wsa_name: str
    alert_type: AlertType
    message: str
    acknowledged_by: UUID | None
    acknowledged_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIUsage(BaseModel):
    used: int
    limit: int
    resets_in_minutes: int


# the briefing keeps the plain numbers next to the AI wording, so the facts can be checked without trusting the text
class AdminBriefing(BaseModel):
    content: str
    facts: dict[str, int]


class AITextResponse(BaseModel):
    content: str


class MapViewStats(BaseModel):
    total: int
    high: int
    medium: int
    low: int
    open_reports: int


class MapViewSummaryResponse(BaseModel):
    stats: MapViewStats
    content: str | None = None  # None when OpenAI is unavailable; the counts still hold


class AIRecommendationsResponse(BaseModel):
    content: str
    items: list[str]


class CapDraftItem(BaseModel):
    action: str
    priority: Literal["high", "medium", "low"]
    suggested_due_in_days: int | None
    justification: str


class CapDraftResponse(BaseModel):
    items: list[CapDraftItem]


class RegulatorySource(BaseModel):
    source: str
    page: int
    score: float


class RegulatoryContextResponse(BaseModel):
    answer: str
    sources: list[RegulatorySource]


class AIQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AIQueryToolCall(BaseModel):
    tool: str
    arguments: dict
    result: str


class AIQueryResponse(BaseModel):
    answer: str
    tool_calls: list[AIQueryToolCall]


# ---------------------------------------------------------------------------------------------------------------------
# contractors and repair tickets
# ---------------------------------------------------------------------------------------------------------------------
AssignmentStatus = Literal["assigned", "accepted", "in_progress", "fixed", "sent_back", "rejected", "cancelled", "closed"]
_ISSUES = {"leak", "outage", "quality", "billing"}


class CoverageWrite(BaseModel):
    wsa_id: UUID
    issue_types: list[IssueType] = Field(min_length=1)


class CoverageRead(BaseModel):
    wsa_id: UUID
    wsa_name: str
    issue_types: list[str]


class ContractorWrite(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    is_active: bool = True


class ContractorRead(BaseModel):
    id: UUID
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool
    coverage: list[CoverageRead] = []
    open_tickets: int = 0


class AssignRequest(BaseModel):
    contractor_id: UUID
    instructions: str | None = Field(default=None, max_length=2_000)
    due_at: datetime | None = None


class BulkAssignRequest(AssignRequest):
    report_ids: list[UUID] = Field(min_length=1, max_length=50)


class AssignmentSummary(BaseModel):
    id: UUID
    status: AssignmentStatus
    contractor_id: UUID
    contractor_name: str
    due_at: datetime | None = None
    overdue: bool = False
    contractor_note: str | None = None
    rejected_reason: str | None = None


class AssignmentRead(AssignmentSummary):
    report_id: UUID
    wsa_id: UUID
    wsa_name: str
    reference_code: str
    issue_type: IssueType
    description: str | None = None
    lat: float
    lng: float
    photo_urls: list[str] = []
    repair_photo_urls: list[str] = []  # the contractor's "after" photos for this ticket
    instructions: str | None = None
    admin_note: str | None = None
    created_at: datetime
    accepted_at: datetime | None = None
    started_at: datetime | None = None
    fixed_at: datetime | None = None
    closed_at: datetime | None = None


class TicketAction(BaseModel):
    action: Literal["accept", "reject", "start", "fix"]
    note: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def _need_reason(self):
        if self.action == "reject" and not (self.note and self.note.strip()):
            raise ValueError("Say why you are rejecting the ticket")
        if self.action == "fix" and not (self.note and self.note.strip()):
            raise ValueError("Say what was done")
        return self


class TicketReview(BaseModel):
    action: Literal["verify", "send_back", "cancel"]
    note: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def _need_note(self):
        if self.action == "send_back" and not (self.note and self.note.strip()):
            raise ValueError("Tell the contractor what is still wrong")
        return self


class NotificationRead(BaseModel):
    id: UUID
    title: str
    body: str | None = None
    assignment_id: UUID | None = None
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContractorPerformance(BaseModel):
    contractor_id: UUID
    name: str
    total: int
    open: int
    overdue: int
    fixed: int
    rejected: int
    fixed_on_time_pct: float | None = None
    avg_hours_to_fix: float | None = None


class WorkOrderDraft(BaseModel):
    instructions: str
    suggested_contractor_id: UUID | None = None
    suggested_contractor_name: str | None = None
    reason: str
    due_at: datetime

CitizenReportRead.model_rebuild()


# GET /risk/schedule: whether automatic re-scoring is on (interval_hours > 0) and when it last ran
class RiskSchedule(BaseModel):
    interval_hours: float
    last_automatic_run: datetime | None = None


# the contractor's own AI helpers (routes/contractor_ai.py). ai is False when the text is the plain fallback because OpenAI was unavailable or its answer failed a check
class JobBrief(BaseModel):
    summary: str
    steps: list[str]
    safety: list[str]
    ai: bool


class FixNoteRequest(BaseModel):
    rough: str = Field(min_length=3, max_length=500)


class FixNoteDraft(BaseModel):
    note: str
    ai: bool


class ContractorSummary(BaseModel):
    text: str
    days: int
    ai: bool
