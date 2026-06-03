import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CAPStatus(str, Enum):
    # this enum stores the corrective action plan stage exactly like the postgres type
    none = "none"
    submitted = "submitted"
    in_progress = "in_progress"
    completed = "completed"


class DWSCAPStatus(str, Enum):
    # this enum stores the dws-reported cap status from the green drop regulatory programme
    none = "none"
    submitted = "submitted"
    pending = "pending"
    overdue = "overdue"


class BDCertification(str, Enum):
    # this enum stores the blue drop certification tier derived from the 2023 audit score
    certified = "certified"        # score >= 95%
    non_certified = "non_certified"  # score 50–94%
    poor = "poor"                  # score 31–49%
    critical = "critical"          # score < 31%


class NDPerformance(str, Enum):
    # this enum stores the no drop performance category from the 2023 nrw audit
    excellent = "excellent"  # score >= 90%
    good = "good"            # score 80–89%
    average = "average"      # score 50–79%
    poor = "poor"            # score 31–49%
    critical = "critical"    # score < 31%


class RiskLevel(str, Enum):
    # this enum stores the final risk label that the dashboard uses for colours and filtering
    low = "low"
    medium = "medium"
    high = "high"


class IssueType(str, Enum):
    # this enum stores the issue options that citizens can choose in the report form
    leak = "leak"
    outage = "outage"
    quality = "quality"
    billing = "billing"


class UserRole(str, Enum):
    # this enum controls which users can open admin-only pages and routes
    admin = "admin"
    viewer = "viewer"


class WSA(Base):
    __tablename__ = "wsa"
    # this keeps the database values inside the 0 to 100 range used by the real schema
    __table_args__ = (
        CheckConstraint("blue_drop_score BETWEEN 0 AND 100", name="wsa_blue_drop_score_check"),
        CheckConstraint("nrw_percent BETWEEN 0 AND 100", name="wsa_nrw_percent_check"),
        CheckConstraint("maint_pct BETWEEN 0 AND 100", name="wsa_maint_pct_check"),
        CheckConstraint("green_drop_score BETWEEN 0 AND 100", name="wsa_green_drop_score_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    blue_drop_score: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    nrw_percent: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    cap_status: Mapped[CAPStatus] = mapped_column(
        SAEnum(CAPStatus, name="cap_status_enum"),
        default=CAPStatus.none,
        server_default=text("'none'::cap_status_enum"),
        nullable=False,
    )
    maint_pct: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, name="risk_level_enum"),
        default=RiskLevel.low,
        server_default=text("'low'::risk_level_enum"),
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # --- new regulatory data fields ---
    green_drop_score: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    dws_cap_status: Mapped[DWSCAPStatus] = mapped_column(
        SAEnum(DWSCAPStatus, name="dws_cap_status_enum"),
        default=DWSCAPStatus.none,
        server_default=text("'none'::dws_cap_status_enum"),
        nullable=False,
    )
    bd_certification: Mapped[BDCertification] = mapped_column(
        SAEnum(BDCertification, name="bd_certification_enum"),
        default=BDCertification.non_certified,
        server_default=text("'non_certified'::bd_certification_enum"),
        nullable=False,
    )
    nd_performance: Mapped[NDPerformance] = mapped_column(
        SAEnum(NDPerformance, name="nd_performance_enum"),
        default=NDPerformance.average,
        server_default=text("'average'::nd_performance_enum"),
        nullable=False,
    )
    num_water_supply_systems: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maint_expenditure: Mapped[float | None] = mapped_column(Numeric(15, 2, asdecimal=False), nullable=True)
    asset_value: Mapped[float | None] = mapped_column(Numeric(18, 2, asdecimal=False), nullable=True)
    # ---
    lat: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    lng: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # this connects one wsa to all citizen reports so sqlalchemy can load them together when needed
    reports: Mapped[list["CitizenReport"]] = relationship("CitizenReport", back_populates="wsa", cascade="all, delete-orphan")


class CitizenReport(Base):
    __tablename__ = "citizen_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    wsa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wsa.id", ondelete="CASCADE"), nullable=False, index=True)
    issue_type: Mapped[IssueType] = mapped_column(SAEnum(IssueType, name="issue_type_enum"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    case_status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", server_default=text("'open'"))
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    lng: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # this connects each report back to the wsa that owns it
    wsa: Mapped["WSA"] = relationship("WSA", back_populates="reports")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role_enum"),
        default=UserRole.viewer,
        server_default=text("'viewer'::user_role_enum"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
