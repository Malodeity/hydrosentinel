from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from ai.predict import load_serialized_model
from app.auth import get_password_hash
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import CAPStatus, RiskLevel, User, UserRole, WSA
from app.routes import ai, alerts, audit, auth, reports, risk, wsa


def seed_default_admin() -> None:
    # this adds the starter admin user only when that email is not already in the database
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.email == settings.admin_email).first()
        if existing_admin:
            return

        admin_user = User(
            email=settings.admin_email,
            hashed_password=settings.admin_password_hash or get_password_hash(settings.admin_password),
            role=UserRole.admin,
        )
        db.add(admin_user)
        db.commit()
    finally:
        db.close()


def seed_wsas() -> None:
    # this fills the empty database with starter wsa rows so the map works before the real etl runs
    db = SessionLocal()
    try:
        if db.query(WSA).count() > 0:
            return

        provinces = [
            ("Eastern Cape", -32.0, 26.5),
            ("Free State", -28.6, 27.3),
            ("Gauteng", -26.2, 28.1),
            ("KwaZulu-Natal", -29.7, 30.7),
            ("Limpopo", -23.9, 29.5),
            ("Mpumalanga", -25.5, 30.9),
            ("Northern Cape", -29.0, 22.8),
            ("North West", -26.5, 25.6),
            ("Western Cape", -33.8, 19.9),
        ]
        cap_cycle = [CAPStatus.none, CAPStatus.submitted, CAPStatus.in_progress, CAPStatus.completed]
        risk_cycle = [RiskLevel.low, RiskLevel.medium, RiskLevel.high]

        wsas: list[WSA] = []
        for province_index, (province, base_lat, base_lng) in enumerate(provinces):
            for item_index in range(16):
                blue_drop_score = round(max(45.0, 92.0 - (item_index * 1.5) - province_index), 1)
                nrw_percent = round(min(55.0, 18.0 + (item_index * 1.8) + province_index), 1)
                maint_pct = round(max(20.0, 9.0 + (item_index * 1.7)), 1)
                wsas.append(
                    WSA(
                        name=f"{province} WSA {item_index + 1:02d}",
                        province=province,
                        blue_drop_score=blue_drop_score,
                        nrw_percent=nrw_percent,
                        cap_status=cap_cycle[item_index % len(cap_cycle)],
                        maint_pct=maint_pct,
                        risk_level=risk_cycle[(item_index + province_index) % len(risk_cycle)],
                        lat=base_lat + (item_index % 4) * 0.32,
                        lng=base_lng + (item_index // 4) * 0.4,
                    )
                )

        db.add_all(wsas)
        db.commit()
    finally:
        db.close()


def create_database_extensions() -> None:
    # this enables the postgres uuid function used by the real schema defaults
    with engine.begin() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))


def apply_ai_schema_changes() -> None:
    # this brings existing databases up to the current schema without touching fresh installs
    with engine.begin() as connection:
        # create new enum types — safe to run repeatedly, the exception block swallows duplicates
        connection.execute(text("""
            DO $$ BEGIN
                CREATE TYPE dws_cap_status_enum AS ENUM ('none', 'submitted', 'pending', 'overdue');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        connection.execute(text("""
            DO $$ BEGIN
                CREATE TYPE bd_certification_enum AS ENUM ('certified', 'non_certified', 'poor', 'critical');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        connection.execute(text("""
            DO $$ BEGIN
                CREATE TYPE nd_performance_enum AS ENUM ('excellent', 'good', 'average', 'poor', 'critical');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        # wsa columns added in earlier releases
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS summary TEXT;"))
        # wsa regulatory data columns
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS green_drop_score NUMERIC(5,2);"))
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS dws_cap_status dws_cap_status_enum NOT NULL DEFAULT 'none';"))
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS bd_certification bd_certification_enum NOT NULL DEFAULT 'non_certified';"))
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS nd_performance nd_performance_enum NOT NULL DEFAULT 'average';"))
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS num_water_supply_systems INTEGER;"))
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS maint_expenditure NUMERIC(15,2);"))
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS asset_value NUMERIC(18,2);"))
        # citizen_reports columns added in earlier releases
        connection.execute(text("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS case_status VARCHAR(50) NOT NULL DEFAULT 'open';"))
        connection.execute(text("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS admin_comment TEXT;"))
        # alerts table
        connection.execute(text("""
            DO $$ BEGIN
                CREATE TYPE alert_type_enum AS ENUM (
                    'risk_level_high', 'risk_level_increased', 'report_volume_spike', 'cap_overdue'
                );
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS alerts (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                wsa_id UUID NOT NULL REFERENCES wsa(id) ON DELETE CASCADE,
                alert_type alert_type_enum NOT NULL,
                message TEXT NOT NULL,
                acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
                acknowledged_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_alerts_wsa_id ON alerts(wsa_id);"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_alerts_acknowledged_at ON alerts(acknowledged_at);"))
        # users — new columns
        connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;"))
        connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;"))
        # refresh_tokens table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash VARCHAR(255) NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens(user_id);"))
        # citizen_reports — traceability columns
        connection.execute(text("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL;"))
        connection.execute(text("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS resolved_by UUID REFERENCES users(id) ON DELETE SET NULL;"))
        connection.execute(text("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;"))
        connection.execute(text("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;"))
        # risk_score_history table
        connection.execute(text("""
            DO $$ BEGIN
                CREATE TYPE model_source_enum AS ENUM ('xgboost', 'heuristic');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_score_history (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                wsa_id UUID NOT NULL REFERENCES wsa(id) ON DELETE CASCADE,
                risk_level risk_level_enum NOT NULL,
                probability NUMERIC(6,4) NOT NULL,
                model_source model_source_enum NOT NULL,
                model_version VARCHAR(50),
                scored_by UUID REFERENCES users(id) ON DELETE SET NULL,
                scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_risk_score_history_wsa_id ON risk_score_history(wsa_id);"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_risk_score_history_scored_at ON risk_score_history(scored_at);"))
        # summaries — generated_by column
        connection.execute(text("ALTER TABLE summaries ADD COLUMN IF NOT EXISTS generated_by UUID REFERENCES users(id) ON DELETE SET NULL;"))
        # audit_log table
        connection.execute(text("""
            DO $$ BEGIN
                CREATE TYPE audit_action_enum AS ENUM (
                    'cap_status_updated', 'report_status_updated', 'report_comment_updated',
                    'risk_score_run', 'wsa_updated', 'user_created', 'summary_generated'
                );
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                action audit_action_enum NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                record_id UUID NOT NULL,
                old_value JSONB,
                new_value JSONB,
                ip_address VARCHAR(45),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_user_id ON audit_log(user_id);"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_record_id ON audit_log(record_id);"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log(created_at);"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # this runs startup setup once so tables, seed data, and the risk model are ready before requests start
    # schema migrations are skipped in the test suite (TESTING=1) because they run once in conftest.ensure_schema
    import os as _os
    if not _os.getenv("TESTING"):
        create_database_extensions()
        apply_ai_schema_changes()
    Base.metadata.create_all(bind=engine)
    seed_default_admin()
    seed_wsas()
    app.state.risk_model = load_serialized_model(settings.model_path)
    yield


app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.add_middleware(
    # this lets the frontend running on localhost call the backend during development
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(wsa.router)
app.include_router(reports.router)
app.include_router(risk.router)
app.include_router(ai.router)
app.include_router(alerts.router)
app.include_router(audit.router)
app.mount("/uploads", StaticFiles(directory=str(Path(__file__).resolve().parent / "data" / "uploads")), name="uploads")


@app.get("/")
def read_root() -> dict[str, str]:
    # this gives a quick health check response when you open the api root
    return {"message": "HydroSentinel API is running"}
