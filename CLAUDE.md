# HydroSentinel — Codebase Index

Quick-reference for Claude. Read this before touching any file.

---

## Rules

### Rule 1 — Think Before Coding
State assumptions explicitly. Ask rather than guess.
Push back when a simpler approach exists. Stop when confused.

### Rule 2 — Simplicity First
Minimum code that solves the problem. Nothing speculative.
No abstractions for single-use code.

### Rule 3 — Surgical Changes
Touch only what you must. Don't improve adjacent code.
Match existing style. Don't refactor what isn't broken.

### Rule 4 — Goal-Driven Execution
Define success criteria. Loop until verified.
Strong success criteria let Claude loop independently.

### Rule 5 — Surface conflicts, don't average them
If two patterns contradict, pick one (more recent / more tested).
Explain why. Flag the other for cleanup.
Don't blend conflicting patterns.

### Rule 6 — Read before you write
Before adding code, read exports, immediate callers, shared utilities.
If unsure why existing code is structured a certain way, ask.

### Rule 7 — Tests verify intent, not just behavior
Tests must encode WHY behavior matters, not just WHAT it does.
A test that can't fail when business logic changes is wrong.

---

## What the app does
Monitors South African Water Service Authorities (WSAs). Three user surfaces:
- **Public dashboard** — Leaflet map, WSA cards, AI national digest, per-WSA AI summary
- **Citizen report page** — submit leaks / outages / quality / billing issues with photos
- **Admin page** — manage CAP status, triage citizen reports, view AI recommendations

---

## Stack
| Layer | Tech |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind, shadcn/ui, Leaflet, axios |
| Backend | FastAPI, SQLAlchemy (mapped_column style), PostgreSQL, JWT (jose), bcrypt |
| AI | OpenAI SDK (`gpt-4o`), XGBoost fallback heuristic |
| Infra | Docker Compose — frontend :5173, backend :8000 |

---

## File map

### Backend
```
backend/
  main.py                  # FastAPI app, lifespan (DB init, seed, model load)
  app/
    config.py              # Settings (pydantic-settings, lru_cache) — env vars live here
    database.py            # engine, SessionLocal, Base, get_db()
    models.py              # SQLAlchemy models: WSA, CitizenReport, User, Summary,
                           #   RefreshToken, RiskScoreHistory, AuditLog, Alert
                           # Enums: CAPStatus, RiskLevel, IssueType, UserRole,
                           #   AlertType, ModelSource, AuditAction
    schemas.py             # Pydantic I/O: WSARead/Update, CitizenReportCreate/Read,
                           #   CitizenReportAdminUpdate, LoginRequest, TokenResponse (+ refresh_token),
                           #   RefreshRequest, RiskScore*, RiskScoreHistoryRead, AuditLogRead,
                           #   AlertRead, AITextResponse, AIRecommendationsResponse
    auth.py                # verify_password, get_password_hash, create_access_token,
                           #   get_current_user, get_current_admin_user
    alert_helpers.py       # raise_high_risk_alert, raise_report_volume_spike_alert
    audit_helpers.py       # write_audit(db, user_id, action, table_name, record_id, ...)
    routes/
      auth.py              # POST /auth/login, POST /auth/refresh, POST /auth/logout, GET /auth/me
      wsa.py               # GET /wsa, GET /wsa/{id}, PATCH /wsa/{id} (admin, CAP only)
      reports.py           # POST /reports (multipart+photos), GET /reports (admin),
                           #   PATCH /reports/{id} (admin — case_status + comment)
      risk.py              # POST /risk/score/{wsa_id} (admin), GET /risk/scores,
                           #   GET /risk/history/{wsa_id} (admin)
      alerts.py            # GET /alerts (admin), PATCH /alerts/{id}/acknowledge (admin)
      audit.py             # GET /audit-log (admin)
      ai.py                # GET /ai/wsa/{id}/summary, /recommendations (admin),
                           #   /ai/digest (cached 24h in Summary table),
                           #   /ai/reports/{id}/comment (admin)
  ai/
    predict.py             # predict_wsa_risk(wsa, model) → {risk_level, probability}
    train.py               # offline XGBoost trainer → ai/model.pkl
    features.py            # feature extraction helpers
  etl/
    parse_blue_drop.py     # PDF → Blue Drop scores
    parse_no_drop.py       # PDF → No Drop data
    municipal_money.py     # Municipal Money data fetch
    load.py                # upsert WSA rows
    run_etl.py             # orchestrates all ETL steps
  data/
    raw/                   # place PDFs here before running ETL
    uploads/               # citizen report photos, served as /uploads/{report_id}/{file}
```

### Frontend
```
frontend/src/
  main.tsx                 # React entry, BrowserRouter
  App.tsx                  # AppShell — nav, hero, Routes (/, /reports, /admin, /login)
  api/
    client.ts              # axios instance (VITE_API_URL), authStorage (localStorage),
                           #   REFRESH_TOKEN_KEY, 401 interceptor (refresh + retry),
                           #   authApi.login / .me — TOKEN_KEY / USER_KEY
    wsa.ts                 # fetchWsas, fetchWsa, updateWsaCapStatus, fetchRiskScores,
                           #   fetchRiskHistory
    reports.ts             # createCitizenReport (FormData), fetchCitizenReports,
                           #   updateCitizenReport
    alerts.ts              # fetchAlerts, acknowledgeAlert
    ai.ts                  # fetchAiDigest, fetchWsaSummary, fetchWsaRecommendations,
                           #   generateReportComment
  pages/
    DashboardPage.tsx      # map + WSA list + AI digest + per-WSA summary
    AdminPage.tsx          # reports table + CAP table + AI recommendations
                           #   (large; lots of useMemo/useEffect — read carefully before editing)
    LoginPage.tsx          # simple email/password form → authStorage.setSession
    ReportPage.tsx         # wraps ReportForm; shows AI summary after submit
  components/
    WSAMap.tsx             # Leaflet map, coloured CircleMarkers by risk level
    WSACard.tsx            # selected WSA detail card
    ReportForm.tsx         # controlled form — WSA select, issue type, location, photos
    AITextBlock.tsx        # reusable AI content display (text or items list)
    RiskBadge.tsx          # colour-coded risk label badge
    ProtectedRoute.tsx     # redirects to /login if no token or wrong role
    ui/                    # shadcn primitives (badge, button, card, input, select, …)
  lib/utils.ts             # cn() helper (clsx + tailwind-merge)
```

---

## Key domain concepts
| Term | Meaning |
|---|---|
| WSA | Water Service Authority — one municipal water provider |
| Blue Drop score | DWS quality rating 0–100 (higher = better) |
| NRW % | Non-Revenue Water — water lost before billing (lower = better) |
| maint_pct | Maintenance spending as % (higher = better) |
| CAP | Corrective Action Plan — none / submitted / in_progress / completed |
| Risk level | low / medium / high — set by XGBoost model or heuristic |
| Summary table | Stores AI national digests; reused for 24 h before regenerating |

---

## Auth flow
- Short-lived JWT (`hydrosentinel_token`) + long-lived refresh token (`hydrosentinel_refresh_token`) in `localStorage`
- axios request interceptor auto-attaches `Authorization: Bearer …` to every request
- axios response interceptor: on 401 tries `POST /auth/refresh`, retries original request; on failure clears session and redirects to `/login`
- Refresh tokens stored SHA-256 hashed in `refresh_tokens` table; single-use rotation; 7-day TTL
- `POST /auth/logout` revokes the refresh token server-side
- `get_current_admin_user` FastAPI dependency blocks non-admins (403)
- `ProtectedRoute` on `/admin` redirects to `/login` when no token / not admin role

---

## AI integration (backend/app/routes/ai.py)
- Single `call_openai(system, user, max_tokens)` helper wraps all OpenAI calls
- Model: `gpt-4o`, temperature 0.3
- `OPENAI_API_KEY` must be set in `.env` — returns 503 if missing
- Endpoints: summary (public), recommendations (admin), digest (public, 24 h cache), report comment (admin)

---

## Environment variables (see .env.example)
```
DATABASE_URL
JWT_SECRET_KEY
JWT_EXPIRE_MINUTES
ADMIN_EMAIL
ADMIN_PASSWORD
ADMIN_PASSWORD_HASH   # optional — overrides hashing ADMIN_PASSWORD at startup
MODEL_PATH            # default: ai/model.pkl
OPENAI_API_KEY        # used ONLY for this project — do not reuse
FRONTEND_URL
```

---

## Gotchas
- `AdminPage.tsx` has many interdependent `useEffect` hooks — read all of them before editing any
- `apply_ai_schema_changes()` in `main.py` adds all schema migrations via `ALTER TABLE … IF NOT EXISTS` — safe to run repeatedly; guarded by `TESTING=1` in test suite to prevent deadlocks
- Photos are saved to `data/uploads/{report_id}/` on disk, served via `StaticFiles`; not stored in DB
- There is a stale `AdminPage 2.tsx` in pages/ — it is not imported anywhere, ignore it
- `model.pkl` is not committed; missing model falls back to deterministic heuristic in `predict.py`
- Tests live in `backend/tests/` — run with `cd backend && .venv/bin/pytest tests/ -v`; set `TESTING=1` is handled by conftest.py
- Alert auto-generation: `alert_helpers.py` fires on high risk score (deduped) and on 5+ reports in 24 h per WSA
- Audit log: `audit_helpers.py` `write_audit()` is called from risk.py, reports.py, wsa.py — immutable JSONB rows, never updated
