from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from app.models import BDCertification, CAPStatus, DWSCAPStatus, IssueType, NDPerformance, RiskLevel, UserRole


class WSARead(BaseModel):
    id: UUID
    name: str
    province: str
    blue_drop_score: float | None = None
    nrw_percent: float | None = None
    cap_status: CAPStatus
    maint_pct: float | None = None
    risk_level: RiskLevel
    summary: str | None = None
    # regulatory data fields
    green_drop_score: float | None = None
    dws_cap_status: DWSCAPStatus
    bd_certification: BDCertification
    nd_performance: NDPerformance
    num_water_supply_systems: int | None = None
    maint_expenditure: float | None = None
    asset_value: float | None = None
    lat: float
    lng: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def maint_gap_pct(self) -> float | None:
        # this shows how far the municipality's maintenance spend is from the recommended 8% of asset value
        # positive means spending above 8% (good), negative means shortfall
        if self.maint_pct is None:
            return None
        return round(self.maint_pct - 8.0, 2)


class WSAUpdate(BaseModel):
    cap_status: CAPStatus


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
    case_status: Literal["open", "in_review", "resolved"]
    admin_comment: str | None
    lat: float
    lng: float
    created_at: datetime
    photo_urls: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class CitizenReportAdminUpdate(BaseModel):
    case_status: Literal["open", "in_review", "resolved"]
    admin_comment: str | None = Field(default=None, max_length=2_000)


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class RiskScoreResponse(BaseModel):
    wsa_id: UUID
    name: str
    risk_level: RiskLevel
    probability: float


class RiskScoreListItem(BaseModel):
    wsa_id: UUID
    name: str
    risk_level: RiskLevel


class AITextResponse(BaseModel):
    content: str


class AIRecommendationsResponse(BaseModel):
    content: str
    items: list[str]
