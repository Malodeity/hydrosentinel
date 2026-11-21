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
- **Admin page** — manage CAP status, triage citizen reports, assign reports to contractors, view AI recommendations
- **Contractor page** (`/tickets`) — a contractor sees only its own repair tickets: accept/reject, start, mark fixed. The authority verifies, which resolves the report

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
                           #   RefreshToken, RiskScoreHistory, AuditLog, Alert,
                           #   Contractor, ContractorCoverage, ReportAssignment, Notification
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
    assignment_helpers.py  # ticket rules: can_serve, status steps, default due hours, notify(), overdue, public_repair_status
    mailer.py              # optional SMTP email (no-op unless SMTP_HOST set; never raises)
    routes/
      auth.py              # POST /auth/login, /auth/refresh, /auth/logout, /auth/change-password, GET /auth/me
      wsa.py               # GET /wsa, GET /wsa/{id}, PATCH /wsa/{id} (admin, CAP only)
      reports.py           # POST /reports (multipart+photos), GET /reports (admin),
                           #   PATCH /reports/{id} (admin — case_status + comment)
      risk.py              # POST /risk/score/{wsa_id} (admin), GET /risk/scores,
                           #   GET /risk/history/{wsa_id} (admin)
      alerts.py            # GET /alerts (admin), PATCH /alerts/{id}/acknowledge (admin)
      audit.py             # GET /audit-log (admin)
      assignments.py       # /contractors (+coverage, performance), POST /reports/{id}/assign, /reports/assign-bulk,
                           #   PATCH /assignments/{id}/review (verify|send_back|cancel), /my/tickets (contractor), /notifications
      ai.py                # GET /ai/reports/{id}/work-order (draft ticket), GET /ai/wsa/{id}/summary, /recommendations (admin),
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
    ContractorsTab.tsx / ReportTicketPanel.tsx / NotificationBell.tsx / TicketStatus.tsx  # contractor + ticket UI
  pages/ContractorTicketsPage.tsx  # contractor's own tickets (/tickets)
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
| maint_pct | Repairs and maintenance as a share of total operating expenditure (Treasury's Municipal Money API has no usable asset value, so it is not a share of asset value). Empty when there is no maintenance figure |
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
SMTP_HOST             # optional — empty means no email, notifications stay in the app bell
SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM
SEED_DEMO_DATA        # true = seed demo contractors + logins at start (default false)
DEMO_CONTRACTOR_PASSWORD  # password of the seeded demo contractor/authority-admin logins
```

---

## Gotchas
- `AdminPage.tsx` has many interdependent `useEffect` hooks — read all of them before editing any
- `apply_ai_schema_changes()` in `main.py` adds all schema migrations via `ALTER TABLE … IF NOT EXISTS` — safe to run repeatedly; guarded by `TESTING=1` in test suite to prevent deadlocks
- Photos are saved to `data/uploads/{report_id}/` on disk, served via `StaticFiles`; not stored in DB
- There is a stale `AdminPage 2.tsx` in pages/ — it is not imported anywhere, ignore it
- `model.pkl` is not committed; missing model falls back to deterministic heuristic in `predict.py`
- Tests live in `backend/tests/` — run with `cd backend && .venv/bin/pytest tests/ -v`; set `TESTING=1` is handled by conftest.py
- Authorities are matched across sources and in the DB by `etl.load.authority_key` (province + suffix-stripped name + metro aliases), not by exact name; after loading older data run `python -m etl.dedupe_wsa` (dry run) and add `--apply` to merge duplicate spellings. Take a `pg_dump` backup first
- AI rate limit is stored in the `ai_calls` table (`rate_limit.py`, advisory lock per key), not in memory. Scheduled re-scoring (`app/scheduler.py`, started in the lifespan unless `TESTING`; `RESCORE_INTERVAL_HOURS`, 0 = off) scores authorities whose latest score is stale via `routes/risk.py record_score`; `scored_by` empty = automatic. Contractor "after" photos: `POST /my/tickets/{id}/photos`, saved under `data/uploads/{report_id}/repair/{ticket_id}/`, returned as `repair_photo_urls`
- FR-11: a citizen can give an optional email on the report form (`citizen_reports.contact_email`, never returned or exported); `notify_citizen` in `mailer.py` sends a notice when the report is received, goes to in_review and is resolved (BackgroundTasks, so a slow mail server never delays a request). `GET /health` returns 503 if the risk model is not loaded or the database is down. `docs/a5/run_tests_demo.sh` runs the live testing segment of the presentation
- Contractor AI helpers (`routes/contractor_ai.py`, `/ai/my/...`): job brief, fix-note writer, 7/30/90 day summary. Draft-only. Model answers are checked before use (no number or claim the contractor/ticket did not supply, no links), any failure falls back to plain text with `ai: false`, contractors reach only their own tickets (404), phone numbers are stripped from what is sent, and each call counts in the same `ai_calls` limit
- Alert auto-generation: `alert_helpers.py` fires on high risk score (deduped) and on 5+ reports in 24 h per WSA
- Audit log: `audit_helpers.py` `write_audit()` is called from risk.py, reports.py, wsa.py, assignments.py — immutable JSONB rows, never updated
- One open ticket per report is a partial unique index (`uq_report_active_ticket`). A switched-off contractor keeps and can finish tickets it holds; it just gets no new ones. Passwords: `POST /auth/change-password` (self), `PATCH /users/{id}/password` (national admin, audited).
- Final-presentation tooling lives in `docs/a5/` (`reset_demo.sh` + `backend/scripts/seed_demo_reports.py` restore the demo state; `uml/` has the diagrams, generator and name audit; `shot.mjs` takes screenshots).
- Contractor tickets: a contractor can never resolve a report; `fixed` waits for an admin `verify`, which resolves it. `case_status` stays open/in_review/resolved (the ticket is its own table). A contractor only gets reports for an authority + issue type it is set up for (`ContractorCoverage`). Another contractor's ticket returns 404, not 403
- Authority-scoped admin: `users.wsa_id` set = admin limited to that authority (reports, alerts, CAP, risk, tickets). Users, audit log, AI question box and briefing are national-admin only (`get_current_national_admin`). `contractor` is a `UserRole`; new enum values are added with `ALTER TYPE ... ADD VALUE` in `apply_ai_schema_changes()`
- Demo contractors, their logins and one Ekurhuleni-only admin are seeded at start only when `SEED_DEMO_DATA=true` (`seed_demo_contractors`, never under TESTING). Companies are invented, 2 per province + 3 metro (`PROVINCE_CONTRACTORS` / `METRO_CONTRACTORS` in main.py); logins are `<name>@contractors.hydrosentinel.co.za`; password is `DEMO_CONTRACTOR_PASSWORD`
