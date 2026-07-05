import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CAPStatus(str, Enum):
    none = "none"
    submitted = "submitted"
    in_progress = "in_progress"
    completed = "completed"


class DWSCAPStatus(str, Enum):
    none = "none"
    submitted = "submitted"
    pending = "pending"
    overdue = "overdue"


class BDCertification(str, Enum):
    certified = "certified"        # score >= 95%
    non_certified = "non_certified"  # score 50–94%
    poor = "poor"                  # score 31–49%
    critical = "critical"          # score < 31%


class NDPerformance(str, Enum):
    excellent = "excellent"  # score >= 90%
    good = "good"            # score 80–89%
    average = "average"      # score 50–79%
    poor = "poor"            # score 31–49%
    critical = "critical"    # score < 31%


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class IssueType(str, Enum):
    leak = "leak"
    outage = "outage"
    quality = "quality"
    billing = "billing"


class UserRole(str, Enum):
    admin = "admin"
    viewer = "viewer"


class AlertType(str, Enum):
    risk_level_high = "risk_level_high"
    risk_level_increased = "risk_level_increased"
    report_volume_spike = "report_volume_spike"
    cap_overdue = "cap_overdue"


class ModelSource(str, Enum):
    xgboost = "xgboost"
    heuristic = "heuristic"


class AuditAction(str, Enum):
    cap_status_updated = "cap_status_updated"
    report_status_updated = "report_status_updated"
    report_comment_updated = "report_comment_updated"
    risk_score_run = "risk_score_run"
    wsa_updated = "wsa_updated"
    user_created = "user_created"
    summary_generated = "summary_generated"


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
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class WSA(Base):
    __tablename__ = "wsa"
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
    lat: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    lng: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    reports: Mapped[list["CitizenReport"]] = relationship("CitizenReport", back_populates="wsa", cascade="all, delete-orphan")
    risk_history: Mapped[list["RiskScoreHistory"]] = relationship("RiskScoreHistory", back_populates="wsa", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="wsa", cascade="all, delete-orphan")


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
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lat: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    lng: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    wsa: Mapped["WSA"] = relationship("WSA", back_populates="reports")


class RiskScoreHistory(Base):
    __tablename__ = "risk_score_history"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    wsa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wsa.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(SAEnum(RiskLevel, name="risk_level_enum"), nullable=False)
    probability: Mapped[float] = mapped_column(Numeric(6, 4, asdecimal=False), nullable=False)
    model_source: Mapped[ModelSource] = mapped_column(SAEnum(ModelSource, name="model_source_enum"), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scored_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    wsa: Mapped["WSA"] = relationship("WSA", back_populates="risk_history")
    scorer: Mapped["User | None"] = relationship("User")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    generator: Mapped["User | None"] = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    action: Mapped[AuditAction] = mapped_column(SAEnum(AuditAction, name="audit_action_enum"), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    actor: Mapped["User"] = relationship("User")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    wsa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wsa.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type: Mapped[AlertType] = mapped_column(SAEnum(AlertType, name="alert_type_enum"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    wsa: Mapped["WSA"] = relationship("WSA", back_populates="alerts")
    acknowledger: Mapped["User | None"] = relationship("User")
