# HydroSentinel: code guide and self code-review plan

Purpose: help you understand every part of the system well enough to explain it and defend it. Read it with the code open beside it.

I also added plain-English comments to the code (comments only, no logic changed): backend routes, models, schemas, AI helpers, and the front-end pages and components. Most routes and key functions now have a short comment above them saying what they do and why.

Contents
1. The big picture
2. Repository map
3. Follow one report end to end
4. The main features and where their code is
5. The key pieces, explained
6. The tests
7. A 2-hour self code-review plan
8. Questions to ask yourself
9. Glossary

---

## 1. The big picture

```
 Resident / Admin (browser)
        |   React + TypeScript (frontend/)
        |   axios -> JSON over HTTP (adds the login token)
        v
 FastAPI server (backend/main.py)           <- checks the token, validates input (422), applies rules
   |-- routes/        HTTP endpoints         auth, wsa, reports, risk, ai, alerts, audit, users
   |-- app/           helpers                auth, alert_helpers, audit_helpers, rate_limit, models
   |-- ai/            AI code                predict (XGBoost), features, trajectory, rag, query_agent
   |-- etl/           data pipeline          PDFs + Treasury API -> database (run by hand)
        |                |                  |
        v                v                  v
   PostgreSQL       model.pkl           OpenAI API (GPT-4o)
   (8 tables)       (XGBoost file)      (through one helper: call_openai)
        +  data/uploads/  (report photos, as files)
```

**The three ideas that explain everything:**
1. **Rules live on the server.** The front end is just a nicer way to call the API. Access control, validation, alerts, scoring and audit are all in the back end.
2. **AI proposes, a person decides.** Every AI output is text or a draft. Nothing changes data until an admin clicks Accept or Save.
3. **Everything is recorded.** Every admin change adds a row to the audit log, which is never edited.

---

## 2. Repository map

### Back end (`backend/`)

| Path | What it is |
|---|---|
| `main.py` | Starts the app: creates tables, seeds the admin user and starter authorities, loads the model, registers routers, allows the front end through CORS. |
| `app/config.py` | Reads settings (database URL, secrets, OpenAI key) from `.env`. |
| `app/database.py` | Database connection and the `get_db` session each request uses. |
| `app/models.py` | The 8 database tables and the fixed value lists (enums). |
| `app/schemas.py` | What each endpoint accepts and returns. Wrong input becomes a 422 error here. |
| `app/auth.py` | Password hashing, JWT creation, "who is this user", and the admin-only check. |
| `app/alert_helpers.py` | The rules that raise alerts (high risk, spike, cluster, overdue CAP). |
| `app/audit_helpers.py` | Adds an audit-log row. |
| `app/rate_limit.py` | Limits expensive AI calls to 20 per admin per hour. |
| `app/routes/auth.py` | Login, refresh, logout, who-am-I. |
| `app/routes/wsa.py` | List authorities, update a CAP, CSV export. |
| `app/routes/reports.py` | Submit, track, list, update reports. |
| `app/routes/risk.py` | Run a risk score, history, trend, trending list. |
| `app/routes/ai.py` | Every GPT-4o feature: summaries, CAP draft, case note, map summary, question box. |
| `app/routes/alerts.py`, `audit.py`, `users.py` | Alerts, audit log, user management. |
| `ai/predict.py` | **The risk model:** loads `model.pkl`, predicts, and falls back to the rule. |
| `ai/features.py` | Turns an authority into the six model inputs. |
| `ai/train.py`, `ai/train_from_bdrr.py` | Train and evaluate the model (run by hand). |
| `ai/trajectory.py` | Straight-line trend through score history. |
| `ai/rag.py` | Searches the regulation PDFs (TF-IDF). |
| `ai/query_agent.py` | The question box: GPT-4o plus six safe database tools. |
| `etl/` | Reads the DWS PDFs and the Treasury API into the database. |
| `scripts/e2e_workflow.py` | The 17-check end-to-end test. |
| `scripts/bulk_risk_score.py` | Scores every authority through the API. |
| `tests/` | The 241 automated tests. |
| `data/sample/wsa_sample.sql` | The 169 real authority rows, for anyone who clones the repo. |

### Front end (`frontend/src/`)

| Path | What it is |
|---|---|
| `main.tsx`, `App.tsx` | Starts React, defines the page frame and the routes (`/`, `/reports`, `/login`, `/admin`, `/admin/report`). |
| `api/` | One small file per area. Each function calls one endpoint. `client.ts` adds the login token and renews it. |
| `pages/DashboardPage.tsx` | The public map and AI insight tabs. |
| `pages/ReportPage.tsx` | The resident's report form and tracking. |
| `pages/LoginPage.tsx` | Admin sign-in. |
| `pages/AdminPage.tsx` | **The admin console** (six tabs). The biggest file. |
| `pages/ManagementReportPage.tsx` | The four-page PDF report. |
| `components/WSAMap.tsx` | The map (circles by risk). |
| `components/MapViewSummary.tsx` | The "Summarise this view" panel that follows the map. |
| `components/ReportForm.tsx` | The citizen form with the map pin. |
| `components/AdminTabs.tsx`, `Pager.tsx`, `AgeBadge.tsx` | Tab bar, paging control, and the waiting-time badge. |
| `components/ProtectedRoute.tsx` | Redirects to login when there is no token. |
| `lib/` | **Pure logic with tests**: ageing (`reportAge`), filters (`reportFilters`), paging (`pagination`), report numbers (`managementReport`), alert-map helper (`alertCluster`), formatting. |

---

## 3. Follow one report end to end

This is your demo. Know every step.

1. **Browser, `ReportForm.tsx`:** the Submit button is disabled until province, authority and a 10+ character description exist. The resident can click the map or search an address (OpenStreetMap Nominatim) to place the pin.
2. **Browser, `api/reports.ts` `createCitizenReport`:** packs fields and photos into a form (multipart) and calls `POST /reports`.
3. **Server, `routes/reports.py` `create_report`:** no login needed. Checks the authority exists (404 if not). The enum for `issue_type` is validated by FastAPI (422 if invalid). Saves a row with a random reference code like `HS-1A2B3C4D`. Calls two alert checks in `alert_helpers.py`: `raise_report_volume_spike_alert` and `raise_geo_cluster_alert`. Saves only files ending in jpg, png, webp or gif into `data/uploads/{report id}/`.
4. **Browser, `ReportPage.tsx`:** shows the code, then calls `GET /ai/wsa/{id}/report-context`, which asks GPT-4o for a two-sentence reply. If that fails, the report is still saved.
5. **Anyone, `GET /reports/track/{code}`:** returns only type, status, note and time (not location or description).
6. **Admin, `AdminPage.tsx` Citizen reports tab:** the list comes from `GET /reports` (admin only). Filters run in the browser (`lib/reportFilters.ts`). Age badges come from `lib/reportAge.ts`.
7. **Admin changes status:** `PATCH /reports/{id}` (`update_report`). It records `reviewed_by` and `reviewed_at` the first time the status becomes `in_review`, and the same for `resolved`. It writes an audit row (`write_audit`) with old and new values. Save and audit commit together.
8. **AI note:** the front end sends the status in the dropdown to `GET /ai/reports/{id}/comment?case_status=...`, and the prompt is built to match that status.

---

## 4. The main features and where their code is

| Feature | Back end | Front end |
|---|---|---|
| Risk map and colours | `routes/wsa.py`, `routes/risk.py` (`/scores`) | `components/WSAMap.tsx` |
| AI map summary | `routes/ai.py` `get_map_view_summary` | `components/MapViewSummary.tsx`, `lib/mapBounds.ts` |
| Citizen report | `routes/reports.py` | `components/ReportForm.tsx`, `pages/ReportPage.tsx` |
| Tracking | `routes/reports.py` `track_report` | `pages/ReportPage.tsx` |
| Admin sign-in | `app/auth.py`, `routes/auth.py` | `pages/LoginPage.tsx`, `components/ProtectedRoute.tsx`, `api/client.ts` |
| Triage and AI note | `routes/reports.py` `update_report`, `routes/ai.py` `generate_report_comment` | `pages/AdminPage.tsx` (reports tab) |
| Risk scoring | `routes/risk.py` `score_wsa_risk`, `ai/predict.py` | "Score risk now" button on the admin CAP tab (A5), API and `scripts/` |
| CAP draft and accept | `routes/ai.py` `get_cap_draft`, `routes/wsa.py` `update_wsa_cap_status` | `pages/AdminPage.tsx` (CAP tab) |
| Alerts | `app/alert_helpers.py`, `routes/alerts.py` | `pages/AdminPage.tsx` (overview), `lib/alertCluster.ts` |
| Age flags | none (display logic) | `lib/reportAge.ts`, `components/AgeBadge.tsx` |
| Audit log | `app/audit_helpers.py`, `routes/audit.py` | `pages/AdminPage.tsx` (audit tab), `lib/auditFormat.ts` |
| AI assistant tab (briefing, question box, authority tools, usage meter) | `ai/query_agent.py`, `routes/ai.py` (`post_ai_query`, `get_admin_briefing`, `get_ai_usage`), `app/rate_limit.py` | `components/AiAssistantTab.tsx`, `lib/aiAssistant.ts` |
| Public dashboard numbers and resident-report stats | `routes/reports.py` (`public_report_stats`) | `pages/DashboardPage.tsx`, `components/CitizenActivity.tsx`, `lib/publicStats.ts` |
| Regulation search (index saved to `data/rag_index.pkl`) | `ai/rag.py`, `routes/ai.py` `get_regulatory_context` | `components/AiAssistantTab.tsx` |
| Photo check | `routes/ai.py` `analyze_report_photo`, `call_openai_vision`, `parse_photo_analysis` | `components/PhotoAnalysisPanel.tsx`, `lib/photoAnalysis.ts` |
| Management PDF | none | `pages/ManagementReportPage.tsx`, `lib/managementReport.ts` |
| Rate limit | `app/rate_limit.py` | n/a |

---

## 5. The key pieces, explained

### 5.1 The risk model (`ai/predict.py`)

`predict_wsa_risk(wsa, model)` is the heart of the emerging technology. Read it slowly.

```
if there is no model, or the Blue Drop score is missing:  -> use the rule (heuristic)
else:
    probabilities = model.predict_proba(six inputs)
    top class = the most likely of low / medium / high
    if its probability < 0.5 (the confidence floor):      -> use the rule
    else return that class and its probability, marked "xgboost"
```
- The **six inputs** are in `ai/features.py`: Blue Drop score, NRW %, maintenance %, CAP status (as 0 to 3), latitude, longitude.
- The **rule** is `_heuristic_probability`: 35% how low Blue Drop is, 35% NRW, 20% how low maintenance is, plus CAP points.
- `_probability_to_risk` turns a probability into a level (0.66+ high, 0.33+ medium, else low).
- The result is stored in `risk_score_history` with `model_source` ("xgboost" or "heuristic"), so you can always tell which method scored an authority.
- **Why the fallback exists:** the model must never be trusted when its input is missing or its confidence is low.

Training lives in `ai/train_from_bdrr.py`: 144 labelled authorities, an 80/20 split (fixed seed, stratified), 5-fold cross-validation, and a head-to-head against the rule.

### 5.2 The GPT-4o helper (`routes/ai.py`)

- `get_openai_client()` creates the client, or returns 503 if there is no key. It sets a 30-second timeout and one retry.
- `call_openai(system_prompt, user_prompt, max_tokens)` makes one call. Errors become 502.
- `call_openai_json(...)` is the same but asks for strict JSON (used for the CAP draft).
- Each endpoint builds a prompt from **real database values** (`build_wsa_prompt`) and tells the model to be brief and not invent.
- `parse_cap_draft_json` is the guard for the CAP draft: it accepts only well-formed items and rejects garbage.
- Expensive endpoints use `Depends(enforce_ai_rate_limit)` (20 per hour per admin).

### 5.3 Authentication (`app/auth.py`, `routes/auth.py`)

- Password: stored as a **bcrypt** hash. `verify_password` compares.
- Login returns an **access token** (a JWT, about 60 minutes) and a **refresh token** (random, 7 days).
- Every protected route depends on `get_current_user` (decodes the token, loads the user) and admin routes on `get_current_admin_user` (403 if not admin).
- Refresh tokens are stored only as a SHA-256 **hash** and are **single use**: each refresh revokes the old one.
- Front end: `api/client.ts` attaches the token and, on a 401, tries one refresh, then logs out.

### 5.4 Alerts (`app/alert_helpers.py`)

| Alert | Raised when |
|---|---|
| High risk | An authority is scored high (once per authority until acknowledged). |
| Report spike | 5 or more reports for one authority in 24 hours. |
| Localized incident | 3 or more same-issue reports within 2 km of each other in 6 hours. |
| CAP overdue | A due date has passed and the CAP isn't complete (checked when the alert list is read). |
| Risk increased | An authority moves to a worse tier. |

Each check first looks for an **unacknowledged alert of the same type for the same authority** and skips if one exists. That's the de-duplication. Acknowledging stamps who and when; the front end hides acknowledged alerts by default.

### 5.5 The audit log

`write_audit` adds a row with user, action, table, record id, old value, new value and IP. It only adds to the database session; the route commits, so the change and its audit row are saved together or not at all. There is no update or delete path.

### 5.6 The admin console (`pages/AdminPage.tsx`)

- One component holds all state (about 1,700 lines). A comment block at the top lists the six tabs.
- `loadData` fetches reports, authorities, alerts, audit log and users, and is called again after saves.
- The active tab is in the URL (`?tab=reports`).
- **AI text is only fetched while its tab is open** (the effects check `activeTab`), because each call costs money. Refs remember what was fetched for which authority so switching tabs back and forth makes no extra calls.
- A "stale response" guard: when you select another authority, the old text is cleared and a late reply for the old one is ignored.
- Pure logic is pulled out into `lib/` so it can be unit tested: `reportFilters`, `pagination`, `reportAge`, `auditFormat`.

### 5.7 The map summary (`MapViewSummary.tsx` + `get_map_view_summary`)

- The map passes its bounds. The server counts authorities and open reports inside them from the database, and sends only those facts to GPT-4o.
- Counts always come back even if the AI fails; the sentence is then `null`.
- Cached 10 minutes per set of visible authorities.
- Front end: after the first click, a move that settles for 0.9 seconds triggers a refresh; late replies are ignored.

### 5.8 The management report

`lib/managementReport.ts` (`buildManagementStats`) computes every number: risk by province, report status, age hierarchy, overdue CAPs, high-risk without a plan, alerts. It has 10 tests. `ManagementReportPage.tsx` only draws it, as four A4 sheets that the browser prints to PDF.

---

## 6. The tests

- **Back end:** `backend/tests/` (241 tests, pytest). Each test runs in a database transaction that rolls back, so your real data is never changed. AI calls are replaced with a mock, so tests check the prompt and the failure handling, not GPT's wording.
- **Front end:** `frontend/src/**/*.test.ts` (102 tests, Vitest) for pure logic.
- **End to end:** `backend/scripts/e2e_workflow.py` (17 checks) runs the real workflow against the live system, including a real GPT-4o call.
- **Not covered:** React component rendering, browser flows (checked by hand), load tests, and the quality of AI wording.

Run them:
```bash
cd backend && set -a && . ../.env && set +a
export DATABASE_URL="${DATABASE_URL/:5433\//:5432/}"
~/Library/Caches/hydrosentinel-dev/venv/bin/pytest tests/ -q      # 241 passed
cd ~/Library/Caches/hydrosentinel-dev/fe && npx vitest run        # 102 passed
```

---

## 7. A 2-hour self code-review plan

Do this in order. Tick each box only when you can explain the file to an imaginary examiner.

**Block 1 (20 min): the shape of the system**
- [ ] Read section 1 and 2 of this guide.
- [ ] `backend/main.py`: what happens at start-up (lifespan), which routers, CORS.
- [ ] `frontend/src/App.tsx`: the routes, `ProtectedRoute`.

**Block 2 (25 min): the data and the security**
- [ ] `backend/app/models.py`: the 8 tables. Draw them from memory afterwards.
- [ ] `backend/app/auth.py` and `routes/auth.py`: login, tokens, refresh rotation.
- [ ] `frontend/src/api/client.ts`: how the token is attached and renewed.

**Block 3 (30 min): the main workflow**
- [ ] `backend/app/routes/reports.py`: `create_report`, `track_report`, `update_report`.
- [ ] `backend/app/alert_helpers.py`: the five rules and the de-duplication.
- [ ] `backend/app/audit_helpers.py`: why audit and change commit together.
- [ ] `frontend/src/components/ReportForm.tsx` and `pages/ReportPage.tsx`.

**Block 4 (30 min): the AI (the examiners' favourite)**
- [ ] `backend/ai/predict.py`: say the three fallback cases without looking.
- [ ] `backend/ai/features.py` and `ai/train_from_bdrr.py`: inputs, split, accuracy numbers.
- [ ] `backend/app/routes/ai.py`: `call_openai`, one prompt (`get_cap_draft`), `parse_cap_draft_json`.
- [ ] `backend/ai/query_agent.py`: the six tools and the 5-round limit.
- [ ] `backend/app/rate_limit.py`: how the limit works and its weakness.

**Block 5 (15 min): the admin and the new features**
- [ ] `frontend/src/pages/AdminPage.tsx`: the comment block at the top, `loadData`, one effect, the tabs.
- [ ] `frontend/src/lib/reportAge.ts` and `lib/reportFilters.ts` (short, with tests).
- [ ] `frontend/src/components/MapViewSummary.tsx`.

**Finish (10 min):** run the tests once, then open `QA_PREP.md` and answer five questions out loud without reading the answers.

---

## 8. Questions to ask yourself while reviewing

- What would happen if this input were empty, wrong or very large?
- Who is allowed to call this, and where is that enforced?
- What happens if OpenAI is down here?
- What is recorded in the audit log when this changes?
- Where is the test for this, and what would make it fail?
- If an examiner asked "why did you do it this way?", what is my honest answer and the trade-off?

---

## 9. Glossary

| Term | Meaning |
|---|---|
| WSA | Water Service Authority: the municipal body that runs a town's water supply. |
| CAP | Corrective Action Plan: the fixes an authority must carry out. |
| Blue Drop | DWS score (0 to 100) for drinking-water quality. |
| Green Drop | DWS score for wastewater management. |
| No Drop | DWS report on water losses. |
| NRW | Non-revenue water: water lost before it can be billed. |
| BDRR | Blue Drop Risk Rating: the DWS risk label used to train the model. |
| DWS | Department of Water and Sanitation. |
| XGBoost | A machine-learning method that combines many small decision trees. |
| GPT-4o | OpenAI's language model, used to write text. |
| TF-IDF | A way of scoring how relevant a page is to a question by its words. |
| JWT | JSON Web Token: the signed login token the browser sends. |
| bcrypt | A deliberately slow password-hashing method. |
| ORM (SQLAlchemy) | Lets code use database tables as classes and prevents SQL injection. |
| 422 / 404 / 401 / 403 / 429 / 503 | Invalid input / not found / not signed in / not allowed / rate limit / service unavailable. |
