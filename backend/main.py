# The FastAPI application. Start here: it wires the routers (one file per area in app/routes/), runs start-up setup in lifespan(),
# and applies column additions to an existing database in apply_ai_schema_changes(). Run with: uvicorn main:app --port 8000

import asyncio
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
from app.models import CAPStatus, Contractor, ContractorCoverage, RiskLevel, User, UserRole, WSA
from app.routes import ai, alerts, assignments, audit, auth, reports, risk, users, wsa


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


# starter contractors so the assign / accept / fix flow and the per-authority view work out of the box. the companies are invented (they only
# look like the local firms an authority hires). an admin adds, edits or switches off real ones on the Contractors tab.
# each entry: (company, contact person, login name, phone, earlier name, earlier login, areas). the earlier name and login let an existing record be renamed in place.
LOGIN_DOMAIN = "contractors.hydrosentinel.co.za"
METRO_CONTRACTORS = [
    ("Radebe Plumbing Services (Pty) Ltd", "Sipho Radebe", "radebe-plumbing", "011 555 0114",
     "Demo Plumbing Services (sample data)", "contractor1", [("City of Ekurhuleni", "leak,outage"), ("City of Johannesburg", "leak")]),
    ("Molapo Rapid Response Repairs (Pty) Ltd", "Lerato Molapo", "molapo-repairs", "012 555 0127",
     "Demo Rapid Response Repairs (sample data)", "contractor2", [("City of Ekurhuleni", "leak,outage,quality"), ("City of Tshwane", "leak,outage")]),
    ("Tshabalala Water Quality Services (Pty) Ltd", "Nomsa Tshabalala", "tshabalala-water", "011 555 0138",
     "Demo Water Quality Services (sample data)", "contractor3", [("City of Johannesburg", "quality"), ("City of Tshwane", "quality")]),
]
# two per province, each covering every authority there: repairs (leaks, outages) and water quality
PROVINCE_CONTRACTORS = {
    "Eastern Cape": [("Mkhonto Civils & Plumbing (Pty) Ltd", "Thandeka Mkhonto", "mkhonto-civils", "041 555 0142"),
                     ("Nqabeni Water Testing Services (Pty) Ltd", "Andile Nqabeni", "nqabeni-testing", "041 555 0156")],
    "Free State": [("Mokoena Pipe & Drain Contractors (Pty) Ltd", "Tumelo Mokoena", "mokoena-pipe", "051 555 0163"),
                   ("Lekhanya Environmental Laboratories (Pty) Ltd", "Palesa Lekhanya", "lekhanya-labs", "051 555 0177")],
    "Gauteng": [("Sibanyoni Civils Holdings (Pty) Ltd", "Bheki Sibanyoni", "sibanyoni-civils", "011 555 0181"),
                ("Dlamini-Pretorius Analytical Services (Pty) Ltd", "Zanele Dlamini", "dlamini-pretorius", "012 555 0195")],
    "KwaZulu-Natal": [("Zondi & Sons Plumbing Contractors (Pty) Ltd", "Sbusiso Zondi", "zondi-plumbing", "031 555 0108"),
                      ("Ngcobo Water Quality Solutions (Pty) Ltd", "Nokuthula Ngcobo", "ngcobo-water", "031 555 0119")],
    "Limpopo": [("Maluleke Engineering & Construction (Pty) Ltd", "Tsakani Maluleke", "maluleke-engineering", "015 555 0121"),
                ("Mashaba Environmental Testing (Pty) Ltd", "Kgomotso Mashaba", "mashaba-testing", "015 555 0133")],
    "Mpumalanga": [("Mahlangu Pipelines (Pty) Ltd", "Sifiso Mahlangu", "mahlangu-pipelines", "013 555 0146"),
                   ("Nkosi Water Analytics (Pty) Ltd", "Thulisile Nkosi", "nkosi-analytics", "013 555 0158")],
    "North West": [("Tlhapi Civil Works (Pty) Ltd", "Kabelo Tlhapi", "tlhapi-civils", "018 555 0164"),
                   ("Molefe Aqua Laboratories (Pty) Ltd", "Boitumelo Molefe", "molefe-aqua", "018 555 0172")],
    "Northern Cape": [("Van Wyk Pipe & Plumbing (Pty) Ltd", "Johan van Wyk", "vanwyk-plumbing", "053 555 0185"),
                      ("Cloete Environmental Laboratories (Pty) Ltd", "Elmarie Cloete", "cloete-labs", "053 555 0191")],
    "Western Cape": [("Jacobs & Abrahams Plumbing (Pty) Ltd", "Riaan Jacobs", "jacobs-abrahams", "021 555 0103"),
                     ("Adams Water Quality Laboratory (Pty) Ltd", "Fatima Adams", "adams-laboratory", "021 555 0116")],
}
AUTHORITY_ADMIN = ("ekurhuleni.admin@hydrosentinel.co.za", "ekurhuleni.admin@demo.hydrosentinel.co.za", "City of Ekurhuleni")


def seed_demo_contractors() -> None:
    # safe to run on every start: it adds only what is missing, and renames records that still carry an earlier version's names or logins
    db = SessionLocal()
    try:
        password_hash = get_password_hash(settings.demo_contractor_password)

        def ensure(name: str, contact: str, login_name: str, phone: str, was: str | None, old_login: str | None,
                   areas: list[tuple[WSA, str]]) -> None:
            login = f"{login_name}@{LOGIN_DOMAIN}"
            contractor = db.query(Contractor).filter(Contractor.name == name).first()
            if contractor is None and was:
                contractor = db.query(Contractor).filter(Contractor.name == was).first()
            if contractor is None:
                contractor = Contractor(name=name, contact_name=contact, phone=phone, email=login, is_active=True)
                db.add(contractor)
                db.flush()
            elif contractor.name == was:
                contractor.name, contractor.contact_name, contractor.phone, contractor.email = name, contact, phone, login
            have = {row.wsa_id for row in db.query(ContractorCoverage).filter(ContractorCoverage.contractor_id == contractor.id)}
            for wsa, issues in areas:
                if wsa.id not in have:
                    db.add(ContractorCoverage(contractor_id=contractor.id, wsa_id=wsa.id, issue_types=issues))
            user = db.query(User).filter(User.email.in_([login, old_login or login])).first()
            if user is None:
                db.add(User(email=login, hashed_password=password_hash, role=UserRole.contractor, contractor_id=contractor.id))
            elif user.email != login:
                user.email = login

        for name, contact, login_name, phone, was, was_login, areas in METRO_CONTRACTORS:
            found = [(w, issues) for wsa_name, issues in areas if (w := db.query(WSA).filter(WSA.name == wsa_name).first())]
            ensure(name, contact, login_name, phone, was, f"{was_login}@demo.hydrosentinel.co.za", found)

        by_province: dict[str, list[WSA]] = {}
        for wsa in db.query(WSA).order_by(WSA.name).all():
            by_province.setdefault(wsa.province, []).append(wsa)
        for province, members in sorted(by_province.items()):
            if province not in PROVINCE_CONTRACTORS:
                continue
            slug = province.lower().replace(" ", "-")
            (r_name, r_contact, r_login, r_phone), (q_name, q_contact, q_login, q_phone) = PROVINCE_CONTRACTORS[province]
            ensure(r_name, r_contact, r_login, r_phone, f"Demo {province} Water Repairs (sample data)",
                   f"repairs.{slug}@demo.hydrosentinel.co.za", [(w, "leak,outage") for w in members])
            ensure(q_name, q_contact, q_login, q_phone, f"Demo {province} Water Quality Lab (sample data)",
                   f"quality.{slug}@demo.hydrosentinel.co.za", [(w, "quality") for w in members])

        admin_email, old_admin_email, admin_wsa_name = AUTHORITY_ADMIN
        admin_wsa = db.query(WSA).filter(WSA.name == admin_wsa_name).first()
        existing_admin = db.query(User).filter(User.email.in_([admin_email, old_admin_email])).first()
        if existing_admin is not None:
            existing_admin.email = admin_email
        elif admin_wsa:
            db.add(User(email=admin_email, hashed_password=password_hash, role=UserRole.admin, wsa_id=admin_wsa.id))
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
        connection.execute(text("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS photo_analysis JSONB;"))
        # alerts table
        connection.execute(text("""
            DO $$ BEGIN
                CREATE TYPE alert_type_enum AS ENUM (
                    'risk_level_high', 'risk_level_increased', 'report_volume_spike', 'cap_overdue'
                );
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        connection.execute(text("ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'geo_cluster_incident';"))
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
        # citizen_reports — public tracking reference code
        connection.execute(text("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS reference_code VARCHAR(12);"))
        connection.execute(text("""
            UPDATE citizen_reports
            SET reference_code = 'HS-' || upper(substr(md5(id::text), 1, 8))
            WHERE reference_code IS NULL;
        """))
        connection.execute(text("ALTER TABLE citizen_reports ALTER COLUMN reference_code SET NOT NULL;"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_citizen_reports_reference_code ON citizen_reports(reference_code);"))
        # wsa — CAP due date, used to raise cap_overdue alerts
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS cap_due_date DATE;"))
        # wsa — Blue Drop Risk Rating, DWS-audited ground-truth label for model training
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS bdrr_score NUMERIC(5,2);"))
        connection.execute(text("ALTER TABLE wsa ADD COLUMN IF NOT EXISTS bdrr_risk_level risk_level_enum;"))
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
        # contractor tickets: new enum values (a new value cannot be used in the transaction that adds it, and nothing here does)
        connection.execute(text("ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'contractor';"))
        connection.execute(text("ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'assignment_overdue';"))
        for value in ("contractor_saved", "report_assigned", "assignment_updated", "password_changed"):
            connection.execute(text(f"ALTER TYPE audit_action_enum ADD VALUE IF NOT EXISTS '{value}';"))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_report_active_ticket ON report_assignments(report_id) "
            "WHERE status IN ('assigned','accepted','in_progress','sent_back','fixed');"))
        connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS wsa_id UUID REFERENCES wsa(id) ON DELETE SET NULL;"))
        connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS contractor_id UUID REFERENCES contractors(id) ON DELETE SET NULL;"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # this runs startup setup once so tables, seed data, and the risk model are ready before requests start
    # schema migrations are skipped in the test suite (TESTING=1) because they run once in conftest.ensure_schema
    import os as _os
    if not _os.getenv("TESTING"):
        create_database_extensions()
        # tables must exist before the ALTER TABLE migrations run, or a blank database fails to start
        Base.metadata.create_all(bind=engine)
        apply_ai_schema_changes()
    Base.metadata.create_all(bind=engine)
    seed_default_admin()
    seed_wsas()
    app.state.risk_model = load_serialized_model(settings.model_path)
    rescore_task = None
    if not _os.getenv("TESTING"):
        if settings.seed_demo_data:
            seed_demo_contractors()
        # read the regulatory PDFs in the background so the first "Ask the regulations" question is not the one that waits for them
        import threading

        from ai.rag import get_index

        threading.Thread(target=get_index, daemon=True, name="rag-warmup").start()
        if settings.rescore_interval_hours > 0:
            from app.scheduler import run_forever

            rescore_task = asyncio.create_task(run_forever(app, settings.rescore_interval_hours))
    yield
    if rescore_task:
        rescore_task.cancel()


app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.add_middleware(
    # this lets the frontend running on localhost call the backend during development
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# each router groups related endpoints: auth, wsa, reports, risk, ai, alerts, audit, users, assignments (contractors and repair tickets)
app.include_router(auth.router)
app.include_router(wsa.router)
app.include_router(reports.router)
app.include_router(risk.router)
app.include_router(ai.router)
app.include_router(alerts.router)
app.include_router(audit.router)
app.include_router(users.router)
app.include_router(assignments.router)
app.mount("/uploads", StaticFiles(directory=str(Path(__file__).resolve().parent / "data" / "uploads")), name="uploads")


@app.get("/")
def read_root() -> dict[str, str]:
    # this gives a quick health check response when you open the api root
    return {"message": "HydroSentinel API is running"}
