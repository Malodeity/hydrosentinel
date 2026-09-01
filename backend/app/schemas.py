from datetime import date, datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from app.models import AlertType, AuditAction, BDCertification, CAPStatus, DWSCAPStatus, IssueType, ModelSource, NDPerformance, RiskLevel, UserRole


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

    model_config = ConfigDict(from_attributes=True)


class CitizenReportTrackRead(BaseModel):
    reference_code: str
    issue_type: IssueType
    case_status: Literal["open", "in_review", "resolved"]
    admin_comment: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CitizenReportAdminUpdate(BaseModel):
    case_status: Literal["open", "in_review", "resolved"]
    admin_comment: str | None = Field(default=None, max_length=2_000)


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.viewer


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


class AITextResponse(BaseModel):
    content: str


class AIRecommendationsResponse(BaseModel):
    content: str
    items: list[str]
