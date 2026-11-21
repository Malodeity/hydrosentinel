# Database tables (SQLAlchemy). One class = one Postgres table; the enums are the fixed value lists those tables use.
# Read order for a newcomer: WSA (the authorities) -> CitizenReport (what residents send) -> Alert, AuditLog, RiskScoreHistory (what the system records).
# A new column on an existing database must also be added in main.py apply_ai_schema_changes(), because create_all() only creates missing tables.

import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# database tables and the fixed value lists (enums) they use. every table is a class below and sqlalchemy turns it into a postgres table
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
    contractor = "contractor"


class AlertType(str, Enum):
    risk_level_high = "risk_level_high"
    risk_level_increased = "risk_level_increased"
    report_volume_spike = "report_volume_spike"
    cap_overdue = "cap_overdue"
    geo_cluster_incident = "geo_cluster_incident"
    assignment_overdue = "assignment_overdue"


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
    contractor_saved = "contractor_saved"
    report_assigned = "report_assigned"
    assignment_updated = "assignment_updated"
    password_changed = "password_changed"


# an admin or viewer account. the password is stored only as a bcrypt hash (see app/auth.py)
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
    # an admin with wsa_id set only sees and changes that one authority (empty = national admin). a contractor account points at its company
    wsa_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wsa.id", ondelete="SET NULL"), nullable=True)
    contractor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contractors.id", ondelete="SET NULL"), nullable=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


# one long-lived sign-in token per login. only its SHA-256 hash is stored, and it is single-use (revoked when swapped for a new one)
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


# a water service authority: the indicators from the dws reports, its risk level, and its corrective action plan (cap) status
class WSA(Base):
    __tablename__ = "wsa"
    __table_args__ = (
        CheckConstraint("blue_drop_score BETWEEN 0 AND 100", name="wsa_blue_drop_score_check"),
        CheckConstraint("nrw_percent BETWEEN 0 AND 100", name="wsa_nrw_percent_check"),
        CheckConstraint("maint_pct BETWEEN 0 AND 100", name="wsa_maint_pct_check"),
        CheckConstraint("green_drop_score BETWEEN 0 AND 100", name="wsa_green_drop_score_check"),
        CheckConstraint("bdrr_score BETWEEN 0 AND 100", name="wsa_bdrr_score_check"),
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
    # the plan's deadline. only meaningful when a plan exists: the API clears it when cap_status is 'none'
    cap_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # our own risk rating for this authority (low / medium / high), set by POST /risk/score. not the DWS rating (that is bdrr_risk_level)
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
    # DWS-audited Blue Drop Risk Rating — independent ground-truth label for
    # model training, kept separate from risk_level (our own heuristic/XGBoost output)
    bdrr_score: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    bdrr_risk_level: Mapped[RiskLevel | None] = mapped_column(SAEnum(RiskLevel, name="risk_level_enum"), nullable=True)
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


# one report from a resident. case_status moves open -> in_review -> resolved; reviewed_by and resolved_by record which admin did it
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
    reference_code: Mapped[str] = mapped_column(String(12), nullable=False, unique=True, index=True)
    case_status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", server_default=text("'open'"))
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lat: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    lng: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False, default=0.0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # the saved result of an admin asking the AI to look at a photo (see routes/ai.py analyze_report_photo); never shown publicly
    photo_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    wsa: Mapped["WSA"] = relationship("WSA", back_populates="reports")


# every time an authority is scored we add a row, so the history (and the trend forecast built on it) is never overwritten
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


# append-only record of admin changes: rows are only ever added, never edited or deleted
# one row per AI call, so the hourly limit survives a restart and is shared by every server using this database (see app/rate_limit.py).
# key is "user:<id>" for an admin or "ip:<address>" for a public visitor
class AiCall(Base):
    __tablename__ = "ai_calls"
    __table_args__ = (Index("ix_ai_calls_key_created", "key", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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


# automatic warnings (high risk, spike, cluster, overdue cap). acknowledged_at stays empty until an admin marks the alert handled
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


# ---------------------------------------------------------------------------------------------------------------------
# contractors: the companies an authority hires to do repairs. the system records who they are, where they work and which tickets
# they hold. it does not handle contracts, money or procurement.
# ---------------------------------------------------------------------------------------------------------------------
class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    coverage: Mapped[list["ContractorCoverage"]] = relationship("ContractorCoverage", back_populates="contractor", cascade="all, delete-orphan")


# one row = "this contractor works for this authority on these issue types". it decides who may be offered for a report
class ContractorCoverage(Base):
    __tablename__ = "contractor_coverage"
    __table_args__ = (UniqueConstraint("contractor_id", "wsa_id", name="uq_contractor_coverage"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("uuid_generate_v4()")
    )
    contractor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contractors.id", ondelete="CASCADE"), nullable=False, index=True)
    wsa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wsa.id", ondelete="CASCADE"), nullable=False, index=True)
    # comma separated IssueType values, e.g. "leak,outage"
    issue_types: Mapped[str] = mapped_column(String(100), nullable=False)

    contractor: Mapped["Contractor"] = relationship("Contractor", back_populates="coverage")
    wsa: Mapped["WSA"] = relationship("WSA")


# a repair ticket: one citizen report handed to one contractor. a report can have several over time (reassigned or sent back) but only one is active.
# status: assigned, accepted, in_progress, fixed, sent_back (active); rejected, cancelled, closed (finished)
class ReportAssignment(Base):
    __tablename__ = "report_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("uuid_generate_v4()")
    )
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("citizen_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    contractor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contractors.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="assigned", server_default=text("'assigned'"), index=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contractor_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    report: Mapped["CitizenReport"] = relationship("CitizenReport")
    contractor: Mapped["Contractor"] = relationship("Contractor")

    # one open ticket per report, enforced by the database (the same index is created on an existing database in main.apply_ai_schema_changes)
    __table_args__ = (
        Index("uq_report_active_ticket", "report_id", unique=True,
              postgresql_where=text("status IN ('assigned','accepted','in_progress','sent_back','fixed')")),
    )


# a message for one user (shown in the bell). also sent by email when the server has mail settings
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("report_assignments.id", ondelete="CASCADE"), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
