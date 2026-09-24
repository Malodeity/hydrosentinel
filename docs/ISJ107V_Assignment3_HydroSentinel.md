# ISJ107V Assignment 3: Project Documentation and UML Design

**Project:** HydroSentinel (prototype build)
**Module:** ISJ107V (Integrated Software Project)

---

## Question 1: Project Baseline

### 1.1 Title, purpose, users, technology and executive summary

**Title:** HydroSentinel, an AI-assisted water service risk monitoring platform for South African Water Service Authorities (WSAs).

**Purpose.** One live view of which WSAs are at risk, what corrective action is under way and what residents report. It replaces reading annual Department of Water and Sanitation (DWS) PDF reports by hand.

**Users.**
- Citizens: use the public dashboard and the report page, with no account.
- Municipal and oversight admins: triage reports, set corrective action plan (CAP) status, run risk scoring and use the AI tools.
- Regulators: read the public dashboard.

**Emerging technology.** AI and machine learning. An XGBoost classifier predicts risk level. OpenAI GPT-4o drafts CAPs, writes summaries, answers data questions through fixed database tools, and answers regulatory questions through a TF-IDF search of the DWS PDFs.

**Executive summary.** The prototype is a three-tier web app: a React 18 and TypeScript frontend (four pages), a FastAPI server with 36 endpoints, and eight PostgreSQL tables holding 169 WSAs. An ETL pipeline loads them from five DWS PDF reports and the National Treasury Municipal Money API. XGBoost scores risk, with a rule-based heuristic as the fallback. GPT-4o drafts structured CAPs that an admin accepts in one click, and answers data questions in 2 to 3 seconds. The three costliest AI functions (CAP draft, data question, regulatory question) are limited to 20 requests per admin per hour, and every admin change is written to an audit log. 183 backend tests and 13 frontend tests pass.

### 1.2 Final aim, objectives, scope and approved changes

**Aim.** Give municipal water oversight staff a continuously updated, AI-assisted view of WSA risk that shortens the time between a service problem and a corrective action.

**Measurable objectives and status.**
1. A risk level for every WSA, refreshed when new data or citizen reports arrive. Partly met. All 169 WSAs have a level, and 159 (94%) are scored by the model. The other 10 use the fallback because they have no Blue Drop score. Scoring is manual (`backend/scripts/bulk_risk_score.py` or the scoring endpoint). Nothing re-scores automatically, and the admin page has no scoring button.
2. An AI CAP draft an admin can accept in under two minutes. Met on system time: a draft takes 2.5 to 3.3 seconds and accepting is one click. Real-user review time is not measured.
3. At least three early-warning signals raised without a manual query. Met: five alert types (high risk, risk increase, report volume spike, overdue CAP, geographic cluster).

**Scope.** In scope: risk scoring, citizen reporting and tracking, CAP tracking, AI digests, recommendations and CAP drafts, search of regulatory PDFs, a natural-language query agent, alerts and an audit log. Out of scope: payment processing, carrying out a CAP (the system tracks and drafts only), and SMS or USSD channels.

**Approved changes.** The project and the emerging technology are unchanged. The author approved three edits, recorded here.
- Requirement wording corrected to match the code, with no target lowered: FR-01 (photos are optional, with no limit of five), FR-10 (3 or more reports within 2 km inside 6 hours), AI-NFR-01 (the script prints a report and enforces no threshold) and NFR-02 (503 for a missing key, 502 for a failed call).
- Additions inside the same aim: risk trend forecast, CSV export, admin user management, public report tracking, overdue-CAP alerts, the AI rate limiter, and a 30 second OpenAI timeout (the library default is 600 seconds).
- Data clean-up while gathering evidence: 284 rows were duplicate spellings of 169 authorities, maintenance was mislabelled as a share of asset value and stored as 0.00% when missing, and the AI digest turned missing NRW into "0.0, indicating efficient water usage". All were fixed with tests (section 5.1).

### 1.3 Document control

**Title:** ISJ107V Assignment 3, HydroSentinel project documentation and UML design.
**Version:** 1.0 (prototype baseline).
**Date:** 20 September 2026.
**Author:** Malo.

**Revision history.**
- 0.1, 16 September 2026: first draft of requirements and four UML diagrams.
- 0.2, 19 September 2026: diagrams redrawn in strict UML 2 notation, requirement wording corrected (section 1.2).
- 1.0, 20 September 2026: this document, after the full test run, measurements, data clean-up and model evaluation in Question 5.

**Glossary.**
- WSA: Water Service Authority, a municipality or water board that supplies water.
- DWS: Department of Water and Sanitation, which audits WSAs.
- Blue Drop, Green Drop, No Drop: DWS programmes scoring drinking water quality, wastewater and water losses.
- NRW: non-revenue water, water lost before it is billed.
- BDRR: Blue Drop Risk Rating, a risk percentage DWS auditors calculate from five indicators. It is the label the model is trained on.
- CAP: corrective action plan.
- Risk level: low, medium or high, set by the XGBoost model or the fallback heuristic.
- RAG: retrieval-augmented generation, an answer built from retrieved document passages.
- TF-IDF: a text-weighting method that ranks which PDF passages match a question.
- ETL: the batch scripts that load source data into the database.
- JWT: JSON Web Token, the signed token that proves an admin is signed in.

**Referenced artefacts.**
- Repository: github.com/Malodeity/hydrosentinel, main branch.
- Code: `backend/` (`app/`, `ai/`, `etl/`, `tests/`) and `frontend/src/`.
- Deployment: `docker-compose.yml` and `.env.example`.
- Diagrams and screenshots: `docs/diagrams/`, `docs/a3-diagrams/`, `docs/a3-screens/`.
- Evidence: `docs/a3-evidence/` (test output, measurement scripts and results, model evaluation before and after the clean-up).
- Data: `backend/data/raw/` (six PDF files, five distinct DWS reports).

---

## Question 2: Requirements and Traceability

### 2.1 Final prioritised requirements

Each requirement has a unique ID, a priority and a measurable acceptance criterion. Wording corrections are listed in section 1.2.

#### Functional requirements

ID: FR-01  
Priority: Must  
Requirement: The system shall allow a citizen to submit a report against a WSA, selecting an issue type (leak, outage, quality, billing), a description, a map location and optional photos.  
Acceptance criterion: Given a citizen on the report form, when they select a WSA, issue type and location and submit, then a `CitizenReport` row is created with `case_status = open` and is visible in the admin reports table within one refresh.

ID: FR-02  
Priority: Must  
Requirement: The system shall allow an admin to update a citizen report's case status (open/in review/resolved) and attach an admin comment.  
Acceptance criterion: Given an admin viewing an open report, when they change status and save, then the report's `case_status`, `admin_comment`, `reviewed_by`/`reviewed_at` fields update and an audit log entry is written.

ID: FR-03  
Priority: Must  
Requirement: The system shall allow an admin to update a WSA's CAP status (none/submitted/in_progress/completed) and due date.  
Acceptance criterion: Given an admin on a WSA's CAP card, when they change CAP status, then `WSA.cap_status` updates, an `AuditLog` row with action `cap_status_updated` is written, and the CAP dashboard totals update.

ID: FR-04  
Priority: Must  
Requirement: The system shall compute and store a risk level (low/medium/high) and probability for each WSA using the trained XGBoost model, or a deterministic heuristic if no model is loaded.  
Acceptance criterion: Given an admin triggers risk scoring for a WSA, when scoring completes, then a `RiskScoreHistory` row is created and `WSA.risk_level` reflects the new score within the same request.

ID: FR-05  
Priority: Must  
Requirement: The system shall generate an AI-written natural-language risk summary for a selected WSA on request.  
Acceptance criterion: Given a WSA with at least Blue Drop or Green Drop data present, when a user requests the summary, then a non-empty text response referencing that WSA's actual scores is returned within 8 seconds.

ID: FR-06  
Priority: Should  
Requirement: The system shall generate an AI-drafted, prioritised CAP (list of structured action items with a suggested due-in-days) for a WSA on admin request.  
Acceptance criterion: Given an admin clicks "Draft CAP" for a WSA, when generation completes, then at least one CAP draft item with a title, priority and suggested due-in-days is displayed.

ID: FR-07  
Priority: Should  
Requirement: The system shall let an admin accept a single CAP draft item, which applies it to the WSA's live CAP status (status = submitted, due date computed from the suggested days).  
Acceptance criterion: Given a rendered CAP draft, when the admin clicks "Accept" on an item, then `updateWsaCapStatus` is called, the WSA's CAP status becomes `submitted`, and the button changes to "Applied to CAP".

ID: FR-08  
Priority: Should  
Requirement: The system shall let an admin ask a free-text question about live WSA/report/alert/audit data and receive an answer computed from real backend data via tool calls, not from the LLM's own knowledge.  
Acceptance criterion: Given an admin submits a question such as "which Eastern Cape WSAs have no CAP and are high risk", when the query agent resolves it, then the response text only contains values traceable to a tool-function result for that query.

ID: FR-09  
Priority: Should  
Requirement: The system shall let an admin ask a free-text question against the indexed regulatory PDF corpus and receive an answer with the source document referenced.  
Acceptance criterion: Given regulatory PDFs are indexed, when the admin submits a regulations question, then the response cites at least one source PDF filename.

ID: FR-10  
Priority: Could  
Requirement: The system shall automatically raise an alert when a WSA's risk score crosses into "high", when a WSA receives 5+ citizen reports in 24 hours, or when 3+ reports fall within 2 km of each other inside 6 hours.  
Acceptance criterion: Given the qualifying condition occurs, when the triggering event is processed, then an `Alert` row is created with the correct `alert_type` and is visible, unacknowledged, in the admin alerts panel without further action.

#### Non-functional requirements (FURPS+)

ID: NFR-01  
Category: Performance  
Priority: Must  
Requirement: The system shall return the WSA list and risk map data within 3 seconds under normal load (≤50 concurrent admin users).  
Acceptance criterion: Measured server response time for `GET /wsa` is ≤3 seconds at the 95th percentile.

ID: NFR-02  
Category: Reliability  
Priority: Must  
Requirement: The system shall remain available for AI-independent core functions (report submission, CAP tracking, dashboard) when the OpenAI API is unreachable.  
Acceptance criterion: Given `OPENAI_API_KEY` is unset or the OpenAI call fails, when a user submits a citizen report or updates CAP status, then the action still completes successfully (AI-only endpoints return 503 when the key is missing and 502 when the OpenAI call fails, instead of crashing the app).

ID: NFR-03  
Category: Usability  
Priority: Should  
Requirement: The system shall let a first-time citizen submit a report in 5 fields or fewer without requiring an account.  
Acceptance criterion: A usability walkthrough confirms report submission requires no login and completes in ≤5 form interactions before photo upload.

ID: NFR-04  
Category: Security / Constraint  
Priority: Must  
Requirement: The system shall restrict all CAP-modification, risk-scoring, alert-acknowledgement and audit-log endpoints to authenticated users with the `admin` role.  
Acceptance criterion: Given a request without a valid admin JWT, when it hits a protected endpoint, then the API returns `401`/`403` and no data is modified.

#### AI and machine learning requirements

ID: AI-NFR-01  
Priority: Must  
Requirement: The XGBoost risk model shall achieve at least 80% classification accuracy on a held-out validation split of labelled WSA risk data.  
Acceptance criterion: The classification report that `ai/train_from_bdrr.py` prints for the held-out split shows accuracy ≥0.80 before the model is deployed.

ID: AI-NFR-02  
Priority: Should  
Requirement: The AI query agent shall resolve a natural-language data question in at most 5 OpenAI round-trips and return a result within 15 seconds under normal load.  
Acceptance criterion: Given a representative query set, when run through `run_query_agent`, then the tool-call loop terminates within 5 iterations and total wall-clock time is ≤15 seconds.

ID: AI-NFR-03  
Priority: Must  
Requirement: The AI layer shall enforce a per-admin rate limit of 20 AI requests per rolling hour across the query agent, CAP draft and regulatory-context endpoints, to bound OpenAI API cost and prevent abuse.  
Acceptance criterion: Given an admin has made 20 AI requests within the last 60 minutes, when a 21st request is made, then the API returns `429 Too Many Requests` and no OpenAI call is made.

### 2.2 Requirements traceability matrix

Each requirement maps to its UML element, module, test case and status. Test case IDs are defined in section 5.1. "Live" means run by hand against the running system on 19 September 2026.

Requirement: FR-01  
UML reference: use case Submit Citizen Report, class CitizenReport, activity diagram (section 3.5)  
Module: `backend/app/routes/reports.py`, `frontend/src/components/ReportForm.tsx`  
Test case: TC-I1 (6 tests)  
Status: Pass

Requirement: FR-02  
UML reference: use case Triage Citizen Report, class CitizenReport  
Module: `backend/app/routes/reports.py`, `backend/app/audit_helpers.py`  
Test case: TC-I2  
Status: Pass

Requirement: FR-03  
UML reference: use case Update CAP Status, class WSA  
Module: `backend/app/routes/wsa.py`, `frontend/src/pages/AdminPage.tsx`  
Test case: TC-I3  
Status: Pass

Requirement: FR-04  
UML reference: use case Run Risk Scoring, classes WSA and RiskScoreHistory  
Module: `backend/app/routes/risk.py`, `backend/ai/predict.py`  
Test case: TC-U1, TC-I4 (13 tests)  
Status: Pass. Scoring runs through the API or `scripts/bulk_risk_score.py`. The admin page has no scoring button and nothing re-scores automatically.

Requirement: FR-05  
UML reference: use case View AI Recommendations, AI Engine actor  
Module: `backend/app/routes/ai.py` (summary endpoint)  
Test case: ST-04 (live)  
Status: Pass. Three WSAs answered in 1.6 to 2.1 seconds, each quoting the real Blue Drop score. Checked live only.

Requirement: FR-06  
UML reference: use case Generate AI CAP Draft, sequence diagram (section 3.4)  
Module: `backend/app/routes/ai.py` (`get_cap_draft`, `parse_cap_draft_json`)  
Test case: TC-U2, TC-I5 (11 tests), ST-05 (live)  
Status: Pass

Requirement: FR-07  
UML reference: use case Accept CAP Draft Item, sequence diagram (section 3.4)  
Module: `frontend/src/pages/AdminPage.tsx` (Accept button), `backend/app/routes/wsa.py`  
Test case: UAT-02 (live)  
Status: Pass. Checked live only.

Requirement: FR-08  
UML reference: use case Ask NL Data Query, AI Engine actor  
Module: `backend/ai/query_agent.py`, `backend/app/routes/ai.py`  
Test case: TC-I6 (14 tests), ST-06 (live)  
Status: Pass

Requirement: FR-09  
UML reference: use case Ask Regulatory Question (RAG), AI Engine actor  
Module: `backend/ai/rag.py`, `backend/app/routes/ai.py`  
Test case: TC-I7 (14 tests)  
Status: Pass

Requirement: FR-10  
UML reference: use case Raise Alert, class Alert  
Module: `backend/app/alert_helpers.py`  
Test case: TC-I8 (24 tests)  
Status: Pass

Requirement: NFR-01  
UML reference: deployment and architecture diagrams (API layer)  
Module: `backend/app/routes/wsa.py`  
Test case: ST-01 (live)  
Status: Pass. 95th percentile 10 ms for one user and 317 ms for 50 concurrent users, against a 3 second target.

Requirement: NFR-02  
UML reference: component diagram (AI isolated behind one helper), activity diagram exceptions  
Module: `backend/app/routes/ai.py` (`get_openai_client`, `call_openai`)  
Test case: ST-02, ST-07 (live)  
Status: Pass. AI endpoints return 503 (no key) or 502 (failed call) and every core endpoint still returns 200.

Requirement: NFR-03  
UML reference: use case Submit Citizen Report  
Module: `frontend/src/components/ReportForm.tsx`  
Test case: IN-01 (inspection)  
Status: Pass. Only province, WSA and a description of 10 or more characters are required, with no account. Not tested with real citizens.

Requirement: NFR-04  
UML reference: use case Log In, sequence diagram (JWT check)  
Module: `backend/app/auth.py` (`get_current_admin_user`)  
Test case: TC-I9, ST-03 (live)  
Status: Pass. Six protected endpoints returned 401 without a token.

Requirement: AI-NFR-01  
UML reference: AI component in the architecture and component diagrams  
Module: `backend/ai/train_from_bdrr.py`  
Test case: ST-08 (live evaluation)  
Status: Pass, with little margin. 89.7% on the held-out split and 80.6% (standard deviation 8.0%) under cross-validation.

Requirement: AI-NFR-02  
UML reference: use case Ask NL Data Query, sequence diagram of the tool loop  
Module: `backend/ai/query_agent.py` (`run_query_agent`)  
Test case: ST-06 (live), TC-I6  
Status: Pass. 1.8 to 3.4 seconds with one tool call each.

Requirement: AI-NFR-03  
UML reference: component diagram (Rate Limiter), activity diagram (429 path)  
Module: `backend/app/rate_limit.py`  
Test case: TC-I10 (6 tests)  
Status: Pass. The count lives in one process's memory (section 5.4).

Summary: 17 of 17 requirements Pass. Caveats: FR-04 (scoring is manual), FR-05 and FR-07 (checked live only) and AI-NFR-01 (narrow margin).

### 2.3 How the system meets the three AI requirements

**AI-NFR-01, at least 80% accuracy.** `backend/ai/train_from_bdrr.py` trains XGBoost (three classes) on the 144 WSAs that carry a DWS BDRR label. On a single 80/20 split (29 test rows) accuracy is 89.7%, against 34.5% for the rule-based heuristic. Five-fold cross-validation gives 80.6% with a standard deviation of 8.0% (folds 79.3, 75.9, 69.0, 89.7 and 89.3). The target is met on both measures, but the cross-validated mean clears it by 0.6 points, so the margin is small. Medium risk is the weak class, with recall 0.71 (5 of 7 found). Before the duplicate records were merged the same script gave 77.8% and 0.57. The deployed `model.pkl` is dated 1 September 2026 and was not retrained on the cleaned data. Retraining with `--deploy` is the next step.

**AI-NFR-02, at most five round-trips and 15 seconds.** The query agent lets GPT-4o call one of five whitelisted database tools, capped at five rounds in code and in a test. Three live questions returned in 3.43, 1.77 and 2.25 seconds, each with one tool call.

**AI-NFR-03, at most 20 AI requests per admin per hour.** A dependency on the query, CAP-draft and regulatory endpoints counts each admin's calls in a sliding one-hour window and returns 429 from the 21st. Six tests cover it, plus the 30 second timeout.

---

## Question 3: Final Design as Implemented

Actor, class and use case names are the same in every diagram and in the text. The diagrams are PlantUML, or SVG in UML 2 notation where automatic layout crossed lines. Sources are in `docs/diagrams/` and `docs/a3-diagrams/`.

### 3.1 High-level system architecture

![Figure 1: High-level system architecture](a3-diagrams/A3-3.1-architecture.png)

Figure 1. Citizens and Admins use four React pages (dashboard, report, login, admin). The pages call a FastAPI server over REST and JSON. Admin calls carry a JWT, and the citizen endpoints need none. The AI component has four parts: the risk predictor (XGBoost with a heuristic fallback), the retrieval index over the DWS PDFs, the query agent, and the CAP drafter and summary writer. The query agent and drafter reach the OpenAI API, the only external AI service, through one helper. Data stores are PostgreSQL, the photo folder, the PDFs and `model.pkl`. An offline ETL step loads the DWS reports and the Municipal Money API into PostgreSQL.

### 3.2 Use-case diagram and detailed use-case description

![Figure 2: Use-case diagram](diagrams/4.1-use-case.png)

Figure 2. Every use case exists in the running system, and each carries the requirement it realises. `Accept CAP Draft Item` includes `Update CAP Status`. `Generate AI CAP Draft` includes `Run Risk Scoring` (it reads a stored score, and scoring runs through the API or bulk script, not a button). `Raise Alert` extends `Submit Citizen Report` and `Run Risk Scoring`. The two AI question use cases specialise `Ask AI Question`.

**Use case: Generate and Accept an AI CAP Draft** (FR-06, FR-07)

Primary actor: Admin. Supporting actor: AI Engine.  
Goal: turn a WSA's data into a reviewed CAP item recorded against the WSA.  
Preconditions: the Admin is signed in with the admin role, the WSA exists and an OpenAI key is configured.  
Trigger: the Admin selects a WSA and clicks Draft CAP.

Normal flow:
1. The system checks the Admin's token and role.
2. The system checks the Admin has made fewer than 20 AI requests in the last hour.
3. The system loads the WSA's indicators, latest risk score and open report counts by issue type.
4. The system asks GPT-4o for three to five CAP items as JSON: action, priority, suggested days, and a justification quoting a number from the data.
5. The system validates the reply, sets any invalid priority to medium, drops items without an action and keeps at most six.
6. The system shows the items, each with an Accept button.
7. The Admin clicks Accept on an item.
8. The system sets the CAP status to submitted, the due date to today plus the suggested days, and writes an audit entry.
9. The page shows "Applied to CAP" and refreshes the CAP totals.

Alternative flows:
- A1, step 1: missing, expired or non-admin token. The system returns 401 or 403.
- A2, step 2: hourly limit reached. The system returns 429 and makes no OpenAI call.
- A3, step 3: WSA not found. The system returns 404.
- A4, step 4: no OpenAI key. The system returns 503. Everything that does not use AI keeps working.
- A5, steps 4 and 5: the OpenAI call fails or times out (30 seconds), or the reply has no valid item. The system returns 502 and the Admin can retry.
- A6, step 7: the Admin accepts nothing. The CAP is unchanged.
- A7, step 8: the save fails. The page shows "Could not apply this CAP item" and the item can be accepted again.

Postconditions: on success the WSA has CAP status submitted, a due date and an audit entry. On any alternative flow the WSA is unchanged.  
Business rules: only an Admin's Accept changes a CAP. The model may only cite numbers in the prompt. The score used is the last stored one.

### 3.3 Class diagram

![Figure 3: Class diagram](diagrams/4.3-class.png)

Figure 3 shows the eight domain classes, with attribute names and types taken from `backend/app/models.py`. `WSA` composes `CitizenReport`, `RiskScoreHistory` and `Alert`, and `User` composes `RefreshToken`, because deletes cascade to these children. `User` links to `AuditLog` and, through `reviewed_by` and `resolved_by`, to `CitizenReport`. Multiplicities are on every association and the enumerations are listed below the diagram. The operations are implemented as functions and route handlers, not model methods: `verifyPassword` is `verify_password` in `auth.py`, `updateCapStatus` is the `PATCH /wsa/{id}` handler, and `acknowledge` is the `PATCH /alerts/{id}/acknowledge` handler.

### 3.4 Sequence diagram

![Figure 4: Sequence diagram, Admin accepts an AI-drafted CAP item](diagrams/4.4-sequence.png)

Figure 4 follows the core transaction. The Admin clicks Draft CAP in the React page (interface). The FastAPI route (control) runs the rate limiter, reads the WSA and latest score from PostgreSQL (data) and calls GPT-4o (emerging technology). On Accept, the page sends a PATCH. The route checks the admin token, updates the WSA and inserts the audit entry in one commit. The two `alt` boxes show 429 for the rate limit and 401 or 403 for a bad token.

### 3.5 Activity diagram

![Figure 5: Activity diagram, draft and accept a Corrective Action Plan](a3-diagrams/A3-3.5-activity.png)

Figure 5 shows the same workflow in three swimlanes (Admin, System, AI Engine). It has one start node and seven decisions: valid token, under the limit, WSA exists, key configured, OpenAI call succeeded, at least one valid item, and whether the Admin accepts. Each exception (401 or 403, 429, 404, 503, 502) ends in a final node after the Admin sees a message. "Applied to CAP" is the only success ending, and declining ends with no change.

### 3.6 Component and deployment diagrams

![Figure 6: Component diagram](a3-diagrams/A3-3.6a-component.png)

Figure 6. The React pages call one API client, which calls the REST routers or the AI router. The REST routers use the alert and audit helpers, the risk predictor, PostgreSQL and the photo folder. The AI router uses the rate limiter, query agent, retrieval index and the OpenAI helper, the only component that reaches OpenAI. The ETL pipeline writes to PostgreSQL and reads the Municipal Money API and the DWS reports.

![Figure 7: Deployment diagram, Docker Compose topology](a3-diagrams/A3-3.6b-deployment.png)

Figure 7. `docker-compose.yml` defines three containers on one Docker host: a `node:20-alpine` container running Vite on port 5173, a Python container running FastAPI under Uvicorn on port 8000, and a `postgres:15` container with a named volume. The backend container holds `model.pkl`, the uploads folder and the PDFs. The backend calls OpenAI outbound over HTTPS. The prototype was tested as local processes (PostgreSQL 16 on 5433, Uvicorn on 8010, Vite on 5182), because Docker was not running, so the Compose start-up has not been exercised. A production release needs a built frontend behind HTTPS.

### 3.7 Design decisions

1. The AI never changes a record on its own. An Admin must click Accept, and every change is audited.
2. The risk model has a fallback. If no model is loaded, the WSA has no Blue Drop score or the top probability is under 0.5, the heuristic scores it and the result is labelled with its source. Scoring never fails. Today the fallback scores only the 10 WSAs with no Blue Drop score.
3. All OpenAI traffic goes through one helper, so the key check, 30 second timeout and error translation (503, 502) live in one place.
4. The query agent can only call whitelisted database tools, so every figure in an answer comes from a query, and the answer shows which tool was used (Figure 11).
5. Deleting a WSA cascades to its reports, history and alerts. Deleting a user cascades only to that user's refresh tokens, other references to users use ON DELETE SET NULL, and the audit log uses RESTRICT, so history is never lost.
6. The audit log is append-only: rows are written by one helper and never updated.

---

## Question 4: Implementation Documentation

### 4.1 Technology stack, structure, modules and interface

**Stack.**
- Frontend: React 18.3, TypeScript 5.8, Vite 5, Tailwind CSS 3, shadcn/ui, Leaflet 1.9 with react-leaflet 4, axios, React Router 6, Vitest 2.
- Backend: Python, FastAPI 0.115 on Uvicorn 0.34, SQLAlchemy 2.0, Pydantic 2, python-jose (JWT), bcrypt. The Docker image uses Python 3.11 and development used 3.13.
- Database: PostgreSQL (15 in Compose, 16 in development).
- AI: XGBoost 2.1, scikit-learn 1.6 (TF-IDF index), pdfplumber, OpenAI SDK 2.40 (GPT-4o).
- Tooling: pytest 8, Docker Compose, Git.

**Structure.**
- `backend/main.py`: creates the app, registers eight routers, sets CORS, loads the model, seeds the admin account.
- `backend/app/`: config, database, models, schemas, auth, alert and audit helpers, rate limiter, and `routes/` (one file per router).
- `backend/ai/`: predictor, features, training scripts, trend forecast, query agent, retrieval index.
- `backend/etl/`: one parser per source, name matching, loader, `run_etl.py`, `dedupe_wsa.py`.
- `backend/data/`: `raw/` (source PDFs) and `uploads/` (photos). `backend/tests/`: 25 test files.
- `frontend/src/`: `pages/` (four), `components/`, `api/`, `lib/` (tested helpers).

**Modules and responsibilities.**
- Authentication (`auth.py`, `routes/auth.py`): sign-in, access and rotating refresh tokens, the admin-only guard.
- WSA and risk (`routes/wsa.py`, `routes/risk.py`, `ai/predict.py`): list WSAs, update CAP, score risk, store history, forecast trend.
- Reports (`routes/reports.py`): intake with photos, tracking by reference code, admin case status and comment.
- Alerts and audit (`alert_helpers.py`, `audit_helpers.py`): five alert types with deduplication, and the append-only audit log.
- AI service (`routes/ai.py`, `ai/query_agent.py`, `ai/rag.py`, `rate_limit.py`): summaries, digests, CAP drafts, data and regulatory questions, all through one OpenAI helper.
- ETL (`backend/etl/`): PDFs and the Municipal Money API into WSA rows.

**Interface screenshots.**

![Figure 8: Public dashboard](a3-screens/s1-dashboard.png)

Figure 8: public dashboard with the cached AI national digest, the risk map and the selected WSA's card.

![Figure 9: Citizen report form](a3-screens/s2-report-form.png)

Figure 9: citizen report page. Province, WSA, issue type, optional photos, description and a map pin.

![Figure 10: Admin sign-in page](a3-screens/s3-login.png)

Figure 10: admin sign-in. Only admin accounts reach the admin page.

![Figure 11: Admin page with alerts, trending WSAs and the AI assistant](a3-screens/s6-ai-query.png)

Figure 11: admin page. The trend panel comes from `ai/trajectory.py`, and the AI assistant shows the tool it used ("Checked: compare_provinces").

![Figure 12: CAP status table](a3-screens/s7-reports-cap.png)

Figure 12: CAP table, where an admin sets a WSA's CAP status and due date and saves.

![Figure 13: AI CAP draft with Accept buttons](a3-screens/s5-cap-draft.png)

Figure 13: an AI-drafted CAP. Each item shows a priority, suggested days and a justification quoting the WSA's data.

### 4.2 Database and dataset

![Figure 14: Entity-relationship diagram](a3-diagrams/A3-4.2-erd.png)

Figure 14 shows the eight tables, keys and delete rules. The five nullable references to `users` are marked on the columns.

**Data dictionary.**
- `wsa` (169 rows): `id` (uuid, primary key), `name` (unique), `province`, `blue_drop_score`, `green_drop_score`, `nrw_percent`, `maint_pct` (nullable numbers), `cap_status` (none, submitted, in_progress, completed), `cap_due_date`, `risk_level` (low, medium, high), `bdrr_risk_level` (the DWS label, nullable), `lat`, `lng`, and other ETL fields. `asset_value` is empty for every row.
- `citizen_reports`: `wsa_id` (foreign key), `issue_type` (leak, outage, quality, billing), `reference_code` (unique, 12 characters), `case_status` (open, in_review, resolved), `description`, `admin_comment`, `reviewed_by`, `resolved_by`, `reviewed_at`, `resolved_at`, `lat`, `lng`, `created_at`.
- `risk_score_history` (338 rows): `wsa_id`, `risk_level`, `probability`, `model_source` (xgboost, heuristic), `model_version`, `scored_by`, `scored_at`.
- `alerts`: `wsa_id`, `alert_type` (risk_level_high, risk_level_increased, report_volume_spike, cap_overdue, geo_cluster_incident), `message`, `acknowledged_by`, `acknowledged_at`, `created_at`.
- `users` (3 rows): `email` (unique), `hashed_password`, `role` (admin, viewer), `is_active`, `last_login_at`, `created_at`.
- `refresh_tokens`: `user_id`, `token_hash` (unique), `expires_at`, `revoked_at`.
- `audit_log`: `user_id`, `action`, `table_name`, `record_id`, `old_value` and `new_value` (JSON), `ip_address`, `created_at`.
- `summaries`: the cached AI digest (`content`, `generated_by`, `generated_at`), reused for 24 hours.

**Data sources and training labels.** All data is public, and no personal data is used.
- WSA names and Blue Drop scores: DWS 2023 Blue Drop report (`etl/parse_blue_drop.py`). These audits define the 169 authorities.
- Training labels: the BDRR tables in the same report (`etl/parse_bdrr.py`). DWS auditors calculate BDRR independently from five indicators, so it is an audited outcome and not a value the system made up. Bands map to three levels: 70% and above (including "critical") is high, 50% to 69% medium, below 50% low. 144 WSAs carry a label: 95 low, 32 medium, 17 high.
- No Drop performance: 2023 No Drop report. Green Drop scores: 2023 national and 2025 Gauteng Green Drop reports.
- Maintenance spending: National Treasury Municipal Money API, audited actuals. `maint_pct` is repairs and maintenance as a share of total operating expenditure. The API has no usable asset value, so the Treasury's 8% norm (defined against asset value) is not quoted. A missing figure stays empty and is never stored as 0.00%.
- Coordinates: OpenStreetMap Nominatim lookups of each authority name (`etl/fix_wsa_data.py`). They are place-name points, not surveyed sites. 16 authorities use a province centroid because the lookup found nothing.
- The same PDFs plus `benchmarking_2022.pdf` feed regulatory question answering only.

**Duplicate records.** The DWS reports spell the same authority differently ("Alfred Nzo DM", "Alfred Nzo District Municipality"), and the ETL joined on the exact name, so one authority became two rows: 284 rows for 169 authorities. `merge_sources` and the loader now match on an authority key (province, suffix-stripped name, metro aliases), and `etl/dedupe_wsa.py` merged the existing rows after a `pg_dump` backup. All 144 labels and 6 citizen reports survived, and 7 tests cover it. The matching is a rule of thumb, so an unusual new spelling could slip through. Check the script's dry run after each data load. Before and after figures are in `docs/a3-evidence/duplicate_cleanup_report.txt`.

**What the model learns from.** Six inputs: Blue Drop score, NRW percent, maintenance percent, CAP status code, latitude, longitude.
- `nrw_percent` is empty for all 169 WSAs (the No Drop parser reads a score, not NRW). Missing values become zero, so this input is constant.
- 10 WSAs have no Blue Drop score and use the fallback. Maintenance percent is missing for 49.
- Coordinates are approximate place points.
- The BDRR label and the Blue Drop score come from the same DWS audit and are correlated.

The deployed `backend/ai/model.pkl` (1 September 2026) was trained before the clean-up and not retrained since.

**Validation rules.**
- Report intake: the WSA must exist (404), `issue_type` must be one of four values (422), and coordinates must be numbers. Only image files (.jpg, .jpeg, .png, .webp, .gif) are stored. The form also requires a province, a WSA and a description of 10 or more characters.
- Case status must be open, in_review or resolved, and an admin comment is at most 2,000 characters. Passwords need 8 or more characters, emails must be valid, and a duplicate email returns 409. AI questions are 3 to 500 characters.
- CAP drafts: invalid JSON gives an empty result, a bad priority becomes medium, an item without an action is dropped, and at most six items are kept.
- Not enforced on the server: description length, coordinate ranges, photo count and size. Only the form limits these.

**Privacy controls.**
- No account for citizens. A report holds only what they type and a map pin, and public tracking returns status only.
- Passwords are bcrypt hashes. Refresh tokens are SHA-256 hashes, single use, revoked at logout. Access tokens last 60 minutes, refresh tokens 7 days.
- Admin endpoints reject calls without a valid admin token. Photos sit under a random report id folder. The audit log records the actor and old and new values. CORS allows only the configured frontend address and local port 5173.

**Backup.** The database is the only store that cannot be rebuilt by script: it holds reports, admin decisions, alerts and the audit trail. The plan is a nightly `pg_dump` kept 30 days on a separate host, plus a copy of `data/uploads/`. WSA data, the model and the search index rebuild from the PDFs and scripts. No backup job exists yet.

### 4.3 API and integration interface

REST with JSON. Interactive docs are at `/docs` on the running server. Errors return `{"detail": "..."}` with these codes: 401 missing or invalid token, 403 non-admin or inactive account, 404 unknown record, 409 duplicate, 422 invalid body, 429 AI rate limit, 502 AI call failed or unusable, 503 no OpenAI key.

**Authentication.**
- `POST /auth/login`: email and password in; access token, refresh token and user out. No token needed. Errors: 401, 403.
- `POST /auth/refresh`: refresh token in; new tokens out. The old token cannot be reused. Error: 401.
- `POST /auth/logout`: revokes the refresh token. `GET /auth/me`: the signed-in user.

**Public (no token).**
- `GET /wsa`, `GET /risk/scores`: WSAs with indicators, risk level and CAP status.
- `POST /reports`: multipart form (`wsa_id`, `issue_type`, `description`, `lat`, `lng`, optional `photos`); returns 201 with the report and reference code. Errors: 404, 422.
- `GET /reports/track/{reference_code}`: status and timestamps only. Error: 404.

**Admin (admin token).**
- `PATCH /wsa/{id}`: CAP status and due date in; updated WSA out; writes an audit entry. Error: 404.
- `PATCH /reports/{id}`: `case_status` and comment in; sets `reviewed_by` or `resolved_by` and writes an audit entry. Errors: 404, 422.
- `POST /risk/score/{wsa_id}`: risk level, probability and source out; updates the WSA, stores history, writes an audit entry, may raise a high-risk alert. Error: 404.
- `GET /alerts`, `PATCH /alerts/{id}/acknowledge` (safe to repeat), `GET /audit-log`, `GET /reports`, the two CSV exports, `GET /risk/history/{wsa_id}`, `GET /risk/trajectory/{wsa_id}`, `GET /risk/trending`, `POST /users`, `GET /users` and `PATCH /users/{id}`.

**AI.**
- `GET /ai/wsa/{id}/cap-draft`, `POST /ai/query` (`{"question": "..."}`, 3 to 500 characters, returns the answer and tools used), `GET /ai/regulatory-context?query=`: admin token, rate limited. Errors: 404, 422, 429, 502, 503.
- Recommendations, report summary and report comment: admin token, not rate limited.
- Six endpoints are public with no rate limit: WSA summary, risk explanation, comparison, report context, province digest and national digest. The national digest is cached 24 hours, and the other five call OpenAI on every request. This is an open cost risk (section 5.4).

**External integrations.** OpenAI Chat Completions (outbound HTTPS, key from the environment, 30 second timeout, one retry). The National Treasury Municipal Money API (ETL only).

### 4.4 Installation, configuration and deployment

**Minimum requirements.**
- Server: 2 cores at 2.0 GHz, 4 GB memory, 20 GB SSD, stable outbound internet for OpenAI. Recommended: 4 cores, 8 GB, 50 GB SSD.
- Software: Docker with Compose, or Python 3.11+, Node.js 20+ and PostgreSQL 15+ for a local run.
- Client: current Chrome, Safari, Firefox or Edge, at least 1280 by 720 for the admin page.

**Configure.**
1. Clone the repository and copy `.env.example` to `.env`.
2. Set `POSTGRES_PASSWORD` and the matching `DATABASE_URL`, a long random `JWT_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` and `OPENAI_API_KEY` (leave the key blank to run without AI). Set `FRONTEND_URL` to the exact address the browser uses, because the API only accepts that origin.
3. Put the source PDFs in `backend/data/raw/`.

**Run with Docker.** Run `docker compose up --build`, then open `http://localhost:5173`. The backend creates the tables and the admin account on start-up.

**Run without Docker.** Create the database to match `DATABASE_URL`. In `backend/`, create a virtual environment, install `requirements.txt` and run `uvicorn main:app --port 8000`. In `frontend/`, run `npm install` and `npm run dev` with `VITE_API_URL` set to the backend.

**Load the data.** In `backend/` run `python -m etl.run_etl` with `PYTHONPATH` set to the backend folder. On an older database run `python -m etl.dedupe_wsa` (dry run) and add `--apply` to merge duplicates, after a `pg_dump`. Then run `scripts/bulk_risk_score.py` (needs `API_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`) with the backend running, and repeat it after each data load. `ai/train_from_bdrr.py` evaluates the model, and `--deploy` retrains on all labelled rows and overwrites `ai/model.pkl`.

**Run the tests.** `pytest tests/` in `backend/` and `npm test` in `frontend/`. Backend tests run inside a transaction that rolls back.

**Before real deployment.** Replace every example secret, serve over HTTPS behind a reverse proxy, build the frontend as static files, restrict the database port to the backend host, and add the backup job.

---

## Question 5: Evaluation and Responsible Use

### 5.1 Test summary

**Environment.** Results are from 19 September 2026 on the development machine: PostgreSQL 16 holding the real data (169 WSAs), Uvicorn on port 8010, Vite on port 5182, Python 3.13, Node 20, Chrome and the project's live OpenAI key. Backend tests run in a transaction that rolls back.

**Overall.** 183 backend tests pass (pytest, about 33 seconds, 25 files). 13 frontend tests pass (Vitest, 3 files) and `tsc --noEmit` reports no errors.
- Unit tests check single functions: predictor choice, CAP JSON parsing, distance, PDF parsers and name matching, trend forecast, frontend helpers.
- Integration tests call real endpoints through FastAPI's test client on the real schema: sign-in, reports, CAP updates and audit, scoring, alerts, users, CSV export, AI endpoints with OpenAI replaced by a stand-in, rate limiter.
- System tests (ST) ran by hand against the running servers with the live key.
- Acceptance tests (UAT) are scripted browser walkthroughs by the developer. No real citizens or administrators have tested it yet.

**Test case register.**
- TC-U1: `tests/test_predict.py`, model or fallback choice.
- TC-U2: `tests/test_cap_draft.py`, parsing the AI's CAP JSON.
- TC-U3: `tests/test_geo_cluster_alert.py`, cluster distance calculation.
- TC-U4: frontend `wsaSelection`, `reportDateRange` and `WSACard` tests.
- TC-U5: `tests/test_data_labels.py`, honest labels and missing data.
- TC-I1: `tests/test_report_tracking.py`, intake, reference codes, public tracking.
- TC-I2: `tests/test_report_traceability.py` and the report-status audit test, who reviewed or resolved a report.
- TC-I3: `tests/test_audit_log.py` and `tests/test_cap_overdue.py`, CAP status and due date.
- TC-I4: `tests/test_risk_history.py`, scoring history with source and scorer.
- TC-I5: endpoint tests in `tests/test_cap_draft.py`, admin only, 404, items, 502.
- TC-I6: `tests/test_query_agent.py`, tools, five-round limit, endpoint.
- TC-I7: `tests/test_rag.py`, retrieval, index refresh, cited answer.
- TC-I8: `tests/test_alerts.py`, `tests/test_geo_cluster_alert.py`, `tests/test_cap_overdue.py`, all alert types.
- TC-I9: `tests/test_auth.py` and the admin-only tests, sign-in, token rotation, access control.
- TC-I10: `tests/test_ai_rate_limit.py`, hourly limit and OpenAI timeout.
- TC-I11: `tests/test_wsa_dedupe.py`, merging duplicate spellings.
- IN-01: inspection of the report form and its submit rule.
- ST-01 to ST-08 and UAT-01 to UAT-03: defined below.

**Representative tests.** Evidence for TC tests is `docs/a3-evidence/pytest_output.txt`. Evidence for ST tests is `docs/a3-evidence/measurements_output.txt` unless stated.

Test case: TC-U1, predictor falls back on low confidence  
Expected result: a top probability under 0.5 returns the heuristic result, labelled "heuristic".  
Actual result: as expected.  
Status: Pass

Test case: TC-U2, malformed CAP draft  
Expected result: invalid JSON gives an empty list, a bad priority becomes medium, at most six items are returned.  
Actual result: as expected.  
Status: Pass

Test case: TC-I1, public tracking hides personal data  
Expected result: the tracking response holds status and no personal fields.  
Actual result: no personal fields.  
Status: Pass

Test case: TC-I3, CAP change is audited  
Expected result: a CAP status change writes an audit entry naming the actor.  
Actual result: as expected.  
Status: Pass

Test case: TC-I8, alerts  
Expected result: 3 same-type reports within 2 km and 6 hours raise a cluster alert and 2 do not. 5 reports in 24 hours raise a volume alert and 4 do not.  
Actual result: as expected in all four cases (the volume tests were added during this evaluation).  
Status: Pass

Test case: TC-I9, refresh token is single use  
Expected result: a second use is rejected.  
Actual result: 401.  
Status: Pass

Test case: TC-I10, rate limit and timeout  
Expected result: the 21st request in an hour returns 429, other users are unaffected, and the OpenAI client has a 30 second timeout and one retry.  
Actual result: as expected. The timeout test failed first because the client used the 600 second default, and passed after the fix.  
Status: Pass

Test case: TC-I11, duplicate spellings merge  
Expected result: differently spelled sources join into one row, same names in different provinces stay apart, metro aliases join, the merge keeps the scored row and moves reports and CAP status, a dry run changes nothing, and a new spelling updates the existing row.  
Actual result: all 7 tests pass. On the real data the merge removed 115 rows (284 to 169) and lost no label or report.  
Status: Pass  
Evidence: pytest output and `duplicate_cleanup_report.txt`.

Test case: TC-U5, honest data labels  
Expected result: prompts call maintenance a share of operating expenditure and quote no asset value or 8% benchmark, an average over no data reads "not available", and a municipality with no maintenance figure is skipped, not stored as 0.00%.  
Actual result: failed before the fix, all 3 pass after.  
Status: Pass

Test case: ST-01, list response time (NFR-01)  
Expected result: `GET /wsa` under 3 seconds at the 95th percentile.  
Actual result: 100 sequential requests: median 6 ms, 95th percentile 10 ms. 50 concurrent users, 200 requests: median 261 ms, 95th percentile 317 ms, slowest 409 ms. The response is 169 WSAs and about 105 KB. Before the clean-up it was 474 ms with 284 records and 175 KB.  
Status: Pass

Test case: ST-02, core functions without AI (NFR-02)  
Expected result: with no OpenAI key, AI endpoints fail cleanly and the core keeps working.  
Actual result: a server with a blank key returned 503 "OPENAI_API_KEY is not configured" in 2 to 3 ms, and `/wsa`, `/alerts` and `/risk/scores` returned 200. The national digest returned 200 from its cache.  
Status: Pass

Test case: ST-03, anonymous access (NFR-04)  
Expected result: admin endpoints return 401 without a token.  
Actual result: `GET /audit-log`, `GET /alerts`, `POST /risk/score/{id}`, `GET /reports`, `GET /users` and `PATCH /wsa/{id}` all returned 401.  
Status: Pass

Test case: ST-04, AI summary (FR-05)  
Expected result: a summary in under 8 seconds using the WSA's real scores.  
Actual result: 2.13, 1.55 and 1.80 seconds, each quoting the real Blue Drop score.  
Status: Pass

Test case: ST-05, CAP draft (FR-06)  
Expected result: at least one structured item per WSA.  
Actual result: 5, 4 and 5 items in 2.79, 2.53 and 3.25 seconds, each with a priority and due days.  
Status: Pass  
Evidence: measurements output and Figure 13.

Test case: ST-06, data question (FR-08, AI-NFR-02)  
Expected result: a correct answer from the database within 15 seconds and five round-trips.  
Actual result: 3.43, 1.77 and 2.25 seconds, one tool call each. The comparison (Gauteng 87.42, Western Cape 70.97) matched the database.  
Status: Pass  
Evidence: measurements output and Figure 11.

Test case: ST-07, AI failure cases (NFR-02, AI-NFR-03)  
Expected result: a missing key gives 503, an invalid key gives 502 without breaking other endpoints, and the 21st request in an hour gives 429.  
Actual result: a blank key gave 503 in about 2 ms. An invalid key gave 502 "OpenAI request failed" in 0.64 to 1.02 seconds and `/wsa` still returned 200. Twenty-two rapid CAP-draft calls on a nonexistent WSA (no OpenAI cost) returned 404 until the counter hit 20, then 429 from the 21st call overall. The counter includes calls that end in 404.  
Status: Pass

Test case: ST-08, model accuracy (AI-NFR-01)  
Expected result: at least 80% on held-out data, and better than the fallback.  
Actual result: 89.7% on the held-out split (29 WSAs) against 34.5% for the fallback, and 80.6% (standard deviation 8.0%) under five-fold cross-validation. It was 77.8% before the merge.  
Status: Pass, with little margin  
Evidence: `model_evaluation_after_cleanup.txt` and `model_evaluation_before_cleanup.txt`.

Test case: UAT-01, report page (NFR-03)  
Expected result: a citizen reaches the form without an account and few fields are required.  
Actual result: no sign-in needed, and submit needs only province, WSA and a description of 10 or more characters.  
Status: Pass  
Evidence: Figure 9.

Test case: UAT-02, draft and accept a CAP item (FR-06, FR-07)  
Expected result: after sign-in the Admin drafts a CAP, accepts an item and the CAP status updates.  
Actual result: on 16 September 2026 Accept showed "CAP updated for Alfred Nzo District Municipality" with no console errors. On 19 September Draft CAP showed four items with Accept buttons.  
Status: Pass  
Evidence: Figure 13.

Test case: UAT-03, public dashboard  
Expected result: digest, map and a default WSA card.  
Actual result: all three loaded.  
Status: Pass  
Evidence: Figure 8.

**Defects found and fixed during testing.**
- The OpenAI client had no timeout (default 600 seconds). It now uses 30 seconds and one retry, with a test.
- The volume alert had no test. Two tests now pin the threshold at five reports.
- One test assumed an empty audit table. It now compares against a baseline.
- `.env.example` named `ANTHROPIC_API_KEY`, but the code reads `OPENAI_API_KEY`. Fixed.
- Four requirement statements did not match the code (section 1.2).
- Duplicate authority rows (284 for 169), which overstated totals and made the fallback score about 70% of stored results. The ETL now matches on an authority key and the rows are merged.
- Maintenance was labelled a share of asset value and missing values were stored as 0.00%. Corrected.
- The AI digest turned missing NRW into "0.0, indicating efficient water usage". Averages over no data now read "not available".

### 5.2 Quantitative evaluation

**NFR-01, performance.** Target: 95th percentile of 3 seconds or less for the WSA list with up to 50 concurrent users. Measured: 10 ms for one user and 317 ms for 50 users, about ten times faster than the target. Server and client shared one laptop and one Uvicorn process, so this shows headroom, not capacity.

**NFR-02, reliability without AI.** Target: reporting, CAP tracking and the dashboard keep working without OpenAI. Measured: with a blank key AI endpoints answered 503 in 2 to 3 ms, and with an invalid key 502 in about a second. Core endpoints returned 200 in both cases.

**NFR-04, security.** Six admin endpoints returned 401 without a token, and 11 automated tests check that admin-only endpoints refuse non-admins.

**AI-NFR-01, model accuracy.** Measured with `ai/train_from_bdrr.py` on the 144 BDRR labels, after the merge. Held-out accuracy 89.7% against 34.5% for the fallback. Cross-validation 80.6% with a standard deviation of 8.0% (folds 69.0% to 89.7%). Per class on the held-out split: high precision 1.00 and recall 1.00 (3 WSAs), low 0.90 and 0.95 (19), medium 0.83 and 0.71 (7). Before the merge cross-validation was 77.8% and medium recall 0.57. The target is met on both measures, narrowly on the cross-validated one, and medium risk is the weakest class.

**AI-NFR-02, query latency.** Three live questions took 1.77 to 3.43 seconds against a 15 second target.

### 5.3 User guide for the main workflow

From a resident's report to an accepted CAP item.

1. **Report a problem (citizen).** Open the report page (Figure 9). Choose province and WSA and issue type, add photos, describe the problem in 10 or more characters, move the map pin and submit. Keep the reference code: it shows the report's status without personal details.
2. **Sign in (admin).** Open the sign-in page (Figure 10) and enter the admin email and password. The admin page opens (Figure 11).
3. **Review alerts.** "System alerts" lists high risk scores, volume spikes and clusters. "Trending toward higher risk" lists WSAs heading into a worse tier. Acknowledge an alert once handled.
4. **Triage reports.** In "Citizen reports", filter by province, WSA and date. Set the case status (open, in review, resolved), write a comment ("Generate AI comment" drafts one) and save.
5. **Keep scores current.** Scores are the last stored ones and nothing re-scores automatically. After loading data, run `scripts/bulk_risk_score.py`, or call `POST /risk/score/{wsa_id}` for one WSA.
6. **Ask the AI assistant.** Type a data question in "Ask the data", such as "Compare the average Blue Drop score of Gauteng and Western Cape", and press Ask. The answer shows the tool used (Figure 11). "Ask the regulations" answers from the DWS reports. Limit: 20 AI requests per admin per hour.
7. **Draft and accept a CAP.** Choose a WSA and click Draft CAP. Read each item and its justification (Figure 13), then click Accept to set the CAP to submitted with the suggested due date. You can also set status and due date in the CAP table (Figure 12) and click Save.

**Troubleshooting** (the 503, 502 and 429 cases were reproduced live, test ST-07).
- "Unable to load admin data" or "Unable to load WSA data": the page cannot reach the API. Check the backend is running, `VITE_API_URL` points to it, and `FRONTEND_URL` matches the browser address exactly (`localhost` differs from `127.0.0.1`).
- Sign-in returns 401: wrong email or password. 403: the account is deactivated.
- AI returns 503: no OpenAI key. Set `OPENAI_API_KEY` in `.env` and restart. Everything else works without it.
- AI returns 429: the admin has used 20 requests this hour. Every call counts, including ones that end in 404. Wait for old calls to drop out.
- AI or CAP draft returns 502: OpenAI failed, rejected the key or returned nothing usable. Retry, then check the key and that the machine can reach api.openai.com.
- No digest on the dashboard: it needs the OpenAI key and is generated once every 24 hours.
- No WSAs on the map: run the ETL step, then the bulk scoring script.
- Risk levels look stale: run the bulk scoring script.
- Backend tests hang: the database is not running or `DATABASE_URL` is wrong.

### 5.4 Limitations, risks, ethics, maintenance and future work

**Limitations.**
- Only 144 labelled WSAs (17 high, 32 medium). Cross-validated accuracy is 80.6%, 0.6 points above target, with folds from 69% to 90%. Medium recall is 0.71.
- The deployed `model.pkl` (1 September 2026) predates the data clean-up and should be retrained.
- Weak inputs: `nrw_percent` is empty for every WSA, `maint_pct` is a share of operating expenditure and missing for 49 of 169, and coordinates are place-name points. The 10 WSAs with no Blue Drop score use the fallback, which reached 34.5% accuracy on the test rows.
- Scoring is manual with no button, so the "continuously updated" aim is only partly met.
- Name matching is a rule of thumb. An unusual new spelling could create a duplicate, so check the dedupe dry run after each load.
- No real-user testing, Docker start-up not run, no automated test for the Accept button or the summary endpoint. The Docker image uses Python 3.11 against 3.13 in development, and the frontend container runs the Vite development server.

**Unresolved risks.**
- Six public AI endpoints have no sign-in and no rate limit, and five call OpenAI on every request, so anyone could run up the bill. They need sign-in, caching or a per-IP limit before release.
- The rate limiter counts in one process's memory. A restart clears it and two processes would each allow 20.
- Server-side input limits are thin: a direct API call can send a long description, bad coordinates or many large photos.
- The example configuration and test setup contain a database password and the default admin password `admin123` in a public repository. Treat them as exposed and replace them. The OpenAI key lives only in the git-ignored `.env`, and a scan found no key in any tracked file or in the git history.
- No backup job exists.

**Ethical and security concerns.**
- The AI can be wrong and can repeat a data mistake it is given. Two were found and fixed here (the asset-value label and "0.0 NRW means efficient"). Every accepted CAP change is audited and the evidence is shown beside each item, but a busy admin could still accept a poor one. The final product should record which items were AI-drafted.
- A risk label on a named municipality has consequences. It should be shown as an estimate with its source (model or fallback) and its data completeness, not as an audit finding.
- Data is public and citizens type only what they choose, so privacy exposure is low. Three helpers (report comment, reports summary, report context) send citizens' free text to OpenAI, and the report context endpoint is public, so this needs a data-protection review before release.
- The dependency audit reports a critical issue in Vitest 2, reachable only through its optional `--ui` server, which the project never starts. It is a development dependency and does not ship.

**Maintenance.** After each DWS report cycle: re-run the ETL, check the dedupe dry run, run bulk scoring, and retrain with `ai/train_from_bdrr.py --deploy` once new labelled data exists. Keep the PDFs in `data/raw/` current (the index rebuilds itself). Update dependencies and re-run both test suites, watch OpenAI model and pricing changes, rotate secrets, and track the share of scores from the fallback.

**Two future improvements.**
1. Improve the model and data after the prototype presentation: retrain and deploy on the cleaned data, fix NRW extraction, obtain an asset value to measure maintenance against the Treasury's 8% norm, add earlier DWS years and other public data where the licence allows, and re-evaluate with cross-validation. Aim for cross-validated accuracy well above 80% and medium recall above 0.75, and show data completeness beside each score.
2. Prepare for public release: automate scoring when data or reports arrive, add rate limiting and caching to the public AI endpoints, move the limiter to a shared store, serve a built frontend over HTTPS, add a nightly backup, and run acceptance testing with real citizens and administrators.
