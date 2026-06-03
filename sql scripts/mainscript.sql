-- =============================================================================
-- HydroSentinel — full schema script
-- Run this on a fresh database. Safe to re-run: all CREATE statements use
-- IF NOT EXISTS; enum types use the duplicate-safe DO $$ pattern.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- Enum types
-- ---------------------------------------------------------------------------

DO $$ BEGIN
    CREATE TYPE cap_status_enum AS ENUM ('none', 'submitted', 'in_progress', 'completed');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE dws_cap_status_enum AS ENUM ('none', 'submitted', 'pending', 'overdue');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE bd_certification_enum AS ENUM ('certified', 'non_certified', 'poor', 'critical');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE nd_performance_enum AS ENUM ('excellent', 'good', 'average', 'poor', 'critical');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE risk_level_enum AS ENUM ('low', 'medium', 'high');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE issue_type_enum AS ENUM ('leak', 'outage', 'quality', 'billing');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('admin', 'viewer');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id              UUID           PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255)   NOT NULL UNIQUE,
    hashed_password VARCHAR(255)   NOT NULL,
    role            user_role_enum NOT NULL DEFAULT 'viewer',
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- wsa
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS wsa (
    id              UUID                  PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255)          NOT NULL UNIQUE,
    province        VARCHAR(100)          NOT NULL,

    -- scores from DWS regulatory audits
    blue_drop_score NUMERIC(5,2)          CHECK (blue_drop_score  BETWEEN 0 AND 100),
    nrw_percent     NUMERIC(5,2)          CHECK (nrw_percent      BETWEEN 0 AND 100),
    green_drop_score NUMERIC(5,2)         CHECK (green_drop_score BETWEEN 0 AND 100),

    -- certification and performance tiers derived from audit scores
    bd_certification  bd_certification_enum NOT NULL DEFAULT 'non_certified',
    nd_performance    nd_performance_enum   NOT NULL DEFAULT 'average',

    -- corrective action plan tracking
    cap_status      cap_status_enum       NOT NULL DEFAULT 'none',   -- admin-managed internal status
    dws_cap_status  dws_cap_status_enum   NOT NULL DEFAULT 'none',   -- dws-reported regulatory status

    -- infrastructure
    num_water_supply_systems INTEGER,

    -- maintenance financials (from municipal money)
    maint_pct       NUMERIC(5,2)          CHECK (maint_pct        BETWEEN 0 AND 100),
    maint_expenditure NUMERIC(15,2),      -- actual maintenance spend in ZAR
    asset_value       NUMERIC(18,2),      -- total infrastructure asset value in ZAR
    -- note: maint_gap_pct (maint_pct - 8%) is computed at the API layer, not stored

    -- model output
    risk_level      risk_level_enum       NOT NULL DEFAULT 'low',

    -- ai-generated summary (cached)
    summary         TEXT,

    -- location
    lat             NUMERIC(9,6)          NOT NULL DEFAULT 0,
    lng             NUMERIC(9,6)          NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ           NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ           NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wsa_province ON wsa (province);
CREATE INDEX IF NOT EXISTS idx_wsa_name     ON wsa (name);

-- ---------------------------------------------------------------------------
-- citizen_reports
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS citizen_reports (
    id           UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    wsa_id       UUID            NOT NULL REFERENCES wsa(id) ON DELETE CASCADE,
    issue_type   issue_type_enum NOT NULL,
    description  TEXT,
    case_status  VARCHAR(50)     NOT NULL DEFAULT 'open',
    admin_comment TEXT,
    lat          NUMERIC(9,6)    NOT NULL DEFAULT 0,
    lng          NUMERIC(9,6)    NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_wsa_id ON citizen_reports (wsa_id);

-- ---------------------------------------------------------------------------
-- summaries  (AI national digest cache)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS summaries (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    content      TEXT        NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- updated_at trigger  (keeps wsa.updated_at current on every row change)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_wsa_updated_at ON wsa;
CREATE TRIGGER trg_wsa_updated_at
    BEFORE UPDATE ON wsa
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Default admin user
-- Password hash below is for the seed account created by the FastAPI lifespan.
-- Replace with your own bcrypt hash if you change ADMIN_PASSWORD in .env.
-- ---------------------------------------------------------------------------

INSERT INTO users (email, hashed_password, role)
VALUES ('admin@hydrosentinel.co.za', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iG8i', 'admin')
ON CONFLICT (email) DO NOTHING;
