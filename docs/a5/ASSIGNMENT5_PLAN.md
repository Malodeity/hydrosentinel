# Assignment 5 — Final Presentation and Demonstration: Master Plan

Student: Malibongwe Mthethwa (213355813), ISJ107V. Project: HydroSentinel.
Written: 2026-11-09. Status: **build done 2026-11-16 (see section 10); what is left needs the student: UAT, videos, rehearsals, upload, push.** Come back to this file and tick boxes as work is done.

Read order: sections 1–3 tell you what is being asked and what "finished" means. Section 4 is the work. Section 5 is the schedule. Section 6 is the plan being attacked (challenge log) and section 7 the risks. Section 8 is the cut list if time runs out.

---

## 1. What Assignment 5 actually is

Source: `ISJ107V_Assignment_5 final Presentation (1).pdf` (in Downloads).

| Fact from the brief | Consequence |
|---|---|
| 50 marks, 40% of the module, individual | Highest-stakes assessment. |
| **Presentation only, no written report.** Submit: final slides, **editable UML files**, **accessible final repository** on MyTUTor **before** the presentation | Three things to upload. All marking happens in the room. |
| 12–15 min presentation + about 5 min technical questions | About 14 min of content. Much tighter than A4 (30 min). |
| "Present the completed version and clearly identify any outstanding features or approved changes" | We must name the contractor feature as an approved change, and name what is not done. |
| UML must be "final, readable, consistent with the implemented system, **same names as the application and documentation**" | Names in diagrams = class/table/route names in code. Checkable. |
| "Prepare a tested local or offline fallback for the live demonstration in case internet access or an external service fails" | **Local run is explicitly acceptable. Cloud deployment is not required.** The deployment diagram describes the local/Docker environment honestly. |

### Marks map (where the 50 marks are)

| Q | Marks | What it asks | Evidence we will show |
|---|---|---|---|
| Q1 | 6 | Title, problem, users, aim, value (2); scope, FR/NFR, **approved changes / incomplete items** (2); roadmap + tech stack + emerging tech (2) | Slides 1–3 |
| Q2 | **16** | End-to-end workflow incl. navigation, validation, processing, output, **recovery from invalid input** (6); emerging tech in operation + how output supports a decision (4); persistence/integration (3); security, privacy, reliability, access control, **how credentials and errors are handled** (3) | Live demo |
| Q3 | 10 | Use-case (2); class (2); one sequence **or** activity diagram (2); **component and deployment views** (2); **consistency of requirements, UML and implementation, incl. justified deviations** (2) | Diagram slides |
| Q4 | 8 | Test results: functional, integration, system, **user acceptance**, passed/failed/**unresolved** (3); ≥2 quantitative measures + 1 emerging-tech metric (2); benefit + one ethics/privacy/security/accessibility point (2); principal limitation + one future enhancement (1) | Results slides |
| Q5 | 10 | Narrative and delivery (3); transition between slides and demo, time, fallback (2); technical questions answered with evidence (3); **personal contribution, lessons learned, most important design decision** (2) | Delivery + Q&A |

Rubric top band (e.g. Q2 14–16): "stable and usable final system demonstrates the full workflow, emerging technology, **realistic data** and appropriate controls." Stability and realistic data are explicit marking words.

### Ambiguity to resolve with the lecturer (one email, send today)

1. Q5.1 says delivery "within the allocated **5 minutes**" but the instructions say **12–15 minutes**. Ask: *is the 12–15 min the whole session (slides + demo), and is the 5 minutes just the slides part?* The plan below assumes 12–15 min total, about 14, with the demo inside it.
2. Is a **local** demo acceptable (the brief implies yes)?
3. Date, time slot, venue, and what hardware is provided (HDMI/USB-C, internet, own laptop).
4. How is the repository checked: link only, or a zip? (Plan covers both.)

---

## 2. Definition of done (gates)

The project is "finalised" when every gate below is green. Nothing else counts.

| Gate | Test that proves it |
|---|---|
| G1 Code frozen | Git tag `a5-final` exists; `git status` clean; no work after the tag except documented fixes. |
| G2 Tests green and recorded | `pytest` all pass; `vitest` all pass; `tsc --noEmit` clean; numbers pasted into slides **from the saved output files**, not typed from memory. |
| G3 Fresh-clone works | On a **clean directory** (`git clone` of the pushed repo), following only the README gets the app running with seeded data in under 15 minutes, on this laptop. |
| G4 Diagrams match code | A "name audit" table (section 4.D) shows every class, actor, route and component in the diagrams exists in the code under that exact name. |
| G5 Demo rehearsed 3 times, timed | Three timed runs, each ≤ 7 min for the demo and ≤ 14 min overall, the last with the fallback triggered on purpose. |
| G6 Offline fallback proven | With Wi-Fi off, the app starts and the recorded video of the full loop plays. |
| G7 Submission uploaded | MyTUTor shows slides, UML source files and repo link; each opened from a different device/browser. |
| G8 Q&A readiness | You can answer the 30 questions in section 4.G aloud, without notes, in your own words. |

---

## 3. Scope freeze rule (the main protection against disaster)

- **Last day for new features: 3 days before the presentation** (or today + 2 days if the date is closer than 5 days). After that: **bug fixes only**, each followed by the full test run.
- Every change after the freeze needs: a failing test first (or a reproduced bug), the fix, full tests, and a note in the changelog section at the bottom of this file.
- Reason: a new feature breaking the demo costs more marks than the feature earns. Q2 (16 marks) rewards *stable and usable*.

---

## 4. Workstreams

Effort estimates are working time for Claude + you together. "You" = tasks only the student can do (talking, testers, uploading, deciding).

### A. Product hardening (code) — owner: Claude, you review

Goal: remove anything that can embarrass the live demo. Ordered by risk.

**A1. Faults found in the contractor feature (must fix) — ~3 h**

| # | Fault | Fix | Acceptance test |
|---|---|---|---|
| A1.1 | Switching a contractor off blocks it from tickets it already holds (server returns 403 on `/my/tickets`), but the screen says "tickets stay with it". | Switch-off stops **new** assignments only. Contractor can still see and finish open tickets. When an admin switches off a contractor that has open tickets, the screen offers "Reassign N open tickets". | Backend test: inactive contractor can still PATCH its existing ticket but cannot be assigned a new one. UI check. |
| A1.2 | Two admins can assign the same report at once → two active tickets. | Partial unique index on `report_assignments(report_id)` where status in active set; migration in `apply_ai_schema_changes()`; assign code catches the conflict and returns 409. | Test that inserting a second active ticket for a report fails at the database level. |
| A1.3 | Demo seeder runs on every real start; all 21 logins share one password. | New env flag `SEED_DEMO_DATA` (default **true in `.env.example`** for the demo, false in any other config); README states to turn it off in production. | Test: with flag off, no contractors are seeded. |
| A1.4 | No way to change or reset a password. | `POST /auth/change-password` (current + new, min 8, revokes other refresh tokens); admin `PATCH /users/{id}/password` (national admin only, audited). Small UI: "Change password" in the header menu; "Reset password" on the Users tab. | Tests: wrong current password → 400; success revokes refresh tokens; scoped admin cannot reset others (403). |

**A2. Usability gaps on the Contractors tab (should fix) — ~4 h**

| # | Item | Acceptance |
|---|---|---|
| A2.1 | Edit contractor details (name, contact, phone, email) in the card. | Edit saves, audit row written, unique-name clash shows a clear message. |
| A2.2 | "Add all authorities in <province>" and "Remove all in <province>" buttons on coverage. | One click adds the province; removal still refuses when open tickets exist there. |
| A2.3 | Bulk assign: filter waiting reports by province/authority, "select all shown", only offer contractors that can serve **every** ticked report, allow instructions + due date. | Choosing a mixed set disables unsuitable contractors; no all-or-nothing surprise. |
| A2.4 | Show the contractor's logins on its card with activate/deactivate. | Matches the Users tab. |
| A2.5 | Notifications link to the report/ticket they are about. | Click opens the right report (admin) or ticket (contractor). |

**A3. Optional polish (only if time remains before the freeze)**
Photo on "Fixed"; reminders when a ticket is near its due time; adjustable standard due hours; ticket history in the audit tab with report codes and contractor names. Each is independent. **Default: do not build.**

**A4. Requirements audit — ~1 h** — The A4 report lists FR-01…FR-11 with statuses written weeks ago (e.g. FR-08 "no button"). Re-verify **every** row against the current code and update the status in one place (`docs/a5/requirements.md`). Add new rows:

| New ID | Requirement | Status to confirm |
|---|---|---|
| FR-12 | Admin assigns a citizen report to a contractor as a ticket; contractor accepts/rejects, works, marks fixed; admin verifies and the report resolves | Implemented |
| FR-13 | A contractor sees only its own tickets and can never resolve a report | Implemented |
| FR-14 | Admin accounts can be limited to one authority | Implemented |
| FR-15 | In-app notifications, optional email | Implemented (email tested with a mock only) |
| FR-16 | Overdue tickets raise an alert | Implemented |
| FR-17 | AI drafts the ticket instructions and suggests a contractor (human confirms) | Implemented |
| NRW estimate | Province average shown as a labelled estimate, never used in scoring | Implemented |

Every "Partially/Deferred" row stays on the slide as an honest **incomplete item** (Q1.2 explicitly rewards this).

### B. Test evidence (Q4: 8 marks) — owner: Claude runs, you run UAT

**B1. Final test run — 30 min.** Run and save, with timestamps, into `docs/a5/evidence/`:
`pytest -q` (expect ≥ 274 + new tests), `vitest run`, `tsc --noEmit`, `backend/scripts/e2e_workflow.py` (extended to cover assign → accept → fix → verify), a timing/measure file. Slides quote these files verbatim.

**B2. Extend test cases (traceability, the "recommended evidence format" in the brief).** Keep TC-01…TC-09. Add:

| TC | Type | Case | Expected |
|---|---|---|---|
| TC-10 | Main workflow | Admin assigns a report; contractor accepts, starts, fixes; admin verifies | Report resolved, audit rows for each step |
| TC-11 | Security | Contractor requests another contractor's ticket | 404 |
| TC-12 | Security | Contractor calls an admin route | 403 |
| TC-13 | Access | Authority admin reads another authority's report | 403 / not listed |
| TC-14 | Invalid input | Reject without a reason; fix without a note | 422 |
| TC-15 | Reliability | Assign with the mail server down | Ticket still created |
| TC-16 | Business rule | Assign a contractor not set up for that authority/issue | 422 |
| TC-17 | Integration | AI work-order draft with OpenAI unavailable | Plain template returned, no error |

**B3. User acceptance testing (UAT) — you must do this; it is the biggest hole in Q4.**
- 3 testers minimum (classmates, family, a municipal-minded friend). Not the author.
- Each performs 4 tasks cold, with no help: (1) report a leak, (2) track it with the code, (3) as admin assign it, (4) as contractor accept and fix it.
- Record: task done yes/no, time, errors, one comment. Plus 5 rating questions (1–5): easy to understand, easy to find things, confident the right information was entered, would use it, anything confusing.
- Use a one-page form (Claude drafts it in `docs/a5/uat_form.md`). Report **real** results including failures; "unresolved" is a legitimate column.
- No personal data: testers use made-up descriptions.

**B4. The evaluation measures for Q4.2 (need ≥ 2 quantitative + 1 emerging-tech metric):**
1. Test suite: N passed / 0 failed, backend and front end.
2. Response time: p50/p95 of `GET /wsa`, `POST /reports`, `GET /reports` measured over 50 calls (script exists in `docs/a4/evidence/measurements.txt` — rerun it, the data changed).
3. Emerging-tech metric: XGBoost 89.7% held-out accuracy (26/29), 80.6% five-fold cross-validation, vs 34.5% for the rule-of-thumb baseline. Say the sample caveat: one wrong answer moves 3.4 points.
4. Optional: UAT task success rate and average rating.

**B5. Ethics/privacy/security point (4.3) — choose one and prepare it well:** residents' reports contain locations and photos; the tracker hides them; contractors see location/photos only for tickets assigned to them; AI sends the description (and photo on request) to OpenAI so is on demand and rate-limited; a person always decides. Pick this one: it is true, demonstrable and connects to Q2.4.

### C. Documentation and data consistency — owner: Claude

- C1. Update `CLAUDE.md` file map (it lists contractor files but not all) and the README (run instructions, see section 4.H).
- C2. Replace stale numbers everywhere: grep the repo and decks for `184`, `13 front`, `203`, `63`, "six tools" (QA_PREP) and fix. Single source: `docs/a5/evidence/`.
- C3. Create a **names glossary** (`docs/a5/names.md`): the exact names used in code and shown on diagrams — `Contractor`, `ContractorCoverage`, `ReportAssignment`, `Notification`, `CitizenReport`, `WSA`, `User`, `UserRole`, `AuditLog`, `Alert`, `RiskScoreHistory`, `Summary`, `RefreshToken`; routes `/reports/{id}/assign`, `/my/tickets`, `/assignments/{id}/review`, etc. Diagrams are drawn from this file.

### D. UML (Q3: 10 marks) — owner: Claude draws and audits, you learn to explain

Required set (the brief: use case, class, one sequence **or** activity, **component and deployment**). Plan: **use case, class, sequence, component, deployment** (5). Keep the A4 activity diagram only as backup.

| Diagram | Must show | Source of truth for names |
|---|---|---|
| D1 Use case | Actors: Citizen, Admin (national), Authority admin, Contractor, AI services (GPT-4o), ML model. Use cases incl. Submit report, Track, Triage, Assign to contractor, Work ticket (accept/reject/start/fix), Verify repair, Manage contractors, Manage CAP, Score risk, Notifications, Audit log, User management. Includes/extends only where the code does it. | routes + `UserRole` |
| D2 Class | All models above with their real attributes and multiplicities from the foreign keys (`ReportAssignment`→`CitizenReport` many-to-one, `Contractor`→`ContractorCoverage` one-to-many, `User`→`Contractor`/`WSA` optional). Include enums `UserRole` (adds `contractor`), `AlertType` (adds `assignment_overdue`). | `backend/app/models.py` |
| D3 Sequence | The demonstrated workflow end to end including the emerging-tech interaction: Citizen → Report API → DB; Admin → AI work-order draft (GPT-4o) → Assign; Contractor → accept → fix; Admin → verify → report resolved; alert/notification. Keep to ~12 messages so it is readable. | `routes/assignments.py`, `routes/ai.py` |
| D4 Component | Frontend modules (Dashboard, Report, Admin, Contractor tickets, Notification bell), API client, FastAPI routers (auth, wsa, reports, risk, ai, alerts, audit, users, assignments), services (auth, alert/assignment helpers, mailer, rate limiter), AI (XGBoost predictor, RAG, query agent), data (PostgreSQL, uploads folder, model.pkl, regulatory PDFs), external (OpenAI). | `backend/app/*`, `frontend/src/*` |
| D5 Deployment | **The real environment**: presenter laptop (browser :5173 Vite, FastAPI/uvicorn :8000, PostgreSQL :5432, file system for uploads/model/PDFs) + Docker Compose variant (db, backend, frontend containers) + external HTTPS to OpenAI. State plainly: local / Docker, no cloud hosting. | `docker-compose.yml`, `start_demo.sh` |

**The "100%" audit (mandatory, repeat until zero mismatches).** For each diagram produce a table row per element: `diagram element → file:line in code → match yes/no`. Methods: class attributes diffed against `models.py` via a script; routes diffed against `app.routes` listing (`app.openapi()`); component boxes against folders. Any mismatch is fixed in the diagram **or** is listed as a justified deviation (3.5).

**Deliverables:** PNG (≥ 2400 px wide) for slides, **editable source for each** (`.puml` or the Python generators + `.svg`) in `docs/a5/uml/`, and a README there explaining how to re-render. Name files `ISJ107V_A5_Q3.x_<Name>.{png,puml|svg}` exactly like A4.

**Q3.5 consistency slide (2 marks):** one table: requirement → diagram element → implemented code → status, plus **justified deviations**, e.g.:
- Contractor tickets are a separate table, not a new `case_status`, so the citizen tracker and CSV keep working.
- Photo on "fixed" and email to citizens were deferred.
- NRW shown as province average, display only; the model is not retrained.
- Risk scoring runs on request, not scheduled.

### E. Slides (Q1, Q3, Q4, Q5) — owner: Claude builds, you tailor

Format: one HTML presenter deck (reuse the look of `intro_visual.html`) **and** a PDF export for MyTUTor. Only readable slides: ≥ 24 px text, one idea each, diagrams full width.

Time plan (target **14:00**, hard cap 15:00). The demo is Q2 = 16 marks, so it gets the most time.

| Time | Slide(s) | Content | Marks |
|---|---|---|---|
| 0:00–1:30 | 1 Title + problem + users + aim + value; 2 Scope: what is **done**, **approved change** (contractor assignment), **not done** (FR list incomplete items); 3 Roadmap + stack + emerging tech (XGBoost, GPT-4o) | Q1 | 6 |
| 1:30–4:00 | 4 Use case; 5 Class; 6 Sequence; 7 Component + Deployment (side by side); 8 Consistency/deviations | Q3. Spend 20 s on 4, 5, 7; 40 s on the sequence; 30 s on 8 | 10 |
| 4:00–10:30 | **Live demo** (section 4.F) | Q2 | 16 |
| 10:30–12:30 | 9 Test results table (passed/failed/unresolved incl. UAT); 10 Measures (2 + model metric); 11 Benefit + ethics point; 12 Limitation + future enhancement | Q4 | 8 |
| 12:30–14:00 | 13 Contribution, lesson, most important decision; thank-you + questions | Q5.4 | 2 |

Rules: slide numbers on every slide; each slide has speaker notes (what to say, what to click); backup slides after "Questions" (data pipeline, how XGBoost predicts, security table, NRW estimate, traceability table) — not shown unless asked.

### F. Live demo (Q2: 16 marks) — owner: you perform, Claude scripts and rehearses

**F1. Clean demo state.** The dev database now contains test data (e.g. HS-63E6C7F3, 32 reports). Create `docs/a5/demo_baseline.sql` (a `pg_dump` of the database in the exact state we want to present: realistic reports across several authorities, a few unassigned, one with a rejected ticket history, no stray test reports), and a one-command restore `bash docs/a5/reset_demo.sh`. Run it before **every** rehearsal and on the day.

**F2. Script (6:30), every step named after the rubric word it earns:**

| Min | Step | Shows | Rubric |
|---|---|---|---|
| 0:00 | Dashboard: map, authority card with risk and the NRW estimate label | realistic data | 2.1, 2.3 |
| 0:40 | Report form: press Submit with a missing description/pin → blocked; upload a .txt as photo → rejected; fix and submit → reference code | **validation + recovery from invalid input** | 2.1 |
| 1:30 | Track by code (shows status only, no location) | privacy | 2.4 |
| 2:00 | Admin sign-in (and a wrong password once → clear error, nothing leaked) | access control, error handling | 2.4 |
| 2:30 | Open the report → **Draft with AI** → GPT-4o text + suggested contractor, edit, Assign | **emerging tech decision support** (human confirms) | 2.2 |
| 3:30 | Switch to contractor login: sees only its ticket; opens `/admin` → bounced back | role isolation | 2.4 |
| 4:00 | Accept → Start → Mark fixed (try without a note → blocked) | validation | 2.1 |
| 4:45 | Back to admin: bell notification, Verify → report resolved; tracker now "resolved" | **end-to-end output + persistence** | 2.1, 2.3 |
| 5:30 | Risk scoring of one authority: model source `xgboost`, level, probability; alert appears | **emerging tech in operation** | 2.2 |
| 6:00 | Audit log (national admin) shows who did what; authority-only admin sees a reduced menu | security/audit | 2.4 |

**F3. Fallbacks (required by the brief and by 5.2) — pre-recorded and rehearsed.**

| Failure | Detect | Response (≤ 15 s) |
|---|---|---|
| OpenAI/Internet down | AI button errors/slow | Say "external service unavailable"; the template draft still appears (A1 behaviour); then play `fallback_ai.mp4` (recorded earlier with the real model output) |
| Backend crashes | blank dashboard | `bash docs/a4/start_demo.sh` (restart, 10 s); if it fails, play `fallback_full_loop.mp4` |
| Database empty/corrupt | no data | `bash docs/a5/reset_demo.sh` |
| Projector/laptop problem | — | second device with the PDF slides + the video + screenshots in `docs/a5/screens/` |
| Browser trouble | — | pre-opened second profile with logins already done |

Record **two videos** (full loop ≈ 4 min with narration off; AI clip ≈ 40 s) on the actual laptop at the actual resolution. Test playback with Wi-Fi off.

**F4. Demo environment settings:** close other apps; notifications off (Do Not Disturb); browser zoom 110–125%; light theme; second user profiles pre-logged-in for admin/contractor/authority admin; laptop on power, sleep disabled; run **production-style** processes (`vite build` + `vite preview`, uvicorn without `--reload`) if the dev server proves flaky in rehearsals.

### G. Question preparation (Q5.3: 3 marks; Q5.4: 2 marks) — owner: Claude drafts, you practise aloud

30 questions, grouped. Answers go in `docs/a5/QA.md` (update `QA_PREP.md`: stale numbers) in 2–3 sentences each **with the file/test that proves it**.

- **Design (8):** why a separate `ReportAssignment` table instead of a new `case_status`? why can't a contractor resolve a report? why `ContractorCoverage` per authority + issue type? why one active ticket per report? why 404 not 403 for another contractor's ticket? why FastAPI/PostgreSQL? why rate limit AI?
- **AI/ML (7):** how XGBoost predicts; why 50% confidence gate; why NRW has no weight (data empty) and what the province estimate is; 89.7% vs 80.6% vs 34.5%; train/test split of 115/29; what can the AI change without a human (nothing); what leaves the system to OpenAI.
- **Security/privacy (6):** JWT + refresh rotation; password hashing; scoped admin; audit log immutability; public repo and secrets handling; photos publicly served by URL (known limitation).
- **Testing (5):** what pytest covers (transaction rollback); what vitest covers; what is *not* tested (real email, real browser UI end-to-end); UAT results; how you know tests would fail if logic broke (mutation checks done on contractor rules).
- **Process/ownership (4):** what you wrote vs AI assistance (the declaration), a bug you found and fixed (e.g. contractor switch-off lockout), what you would do differently, where the code for X is.

**5.4 (prepare all three, 3 sentences each, out loud):**
- *Personal contribution:* defined the problem and requirements, chose the architecture, designed the ticket workflow and its rules, directed and reviewed AI-assisted implementation, ran and recorded the tests and UAT.
- *Lesson learned:* examples — "validate against the real data first (NRW was empty for all 169 authorities)"; "a rule that matters (contractor cannot resolve) must be enforced on the server and tested, not just hidden in the UI".
- *Most important decision:* **a person always decides** — AI drafts and suggests, a human accepts; the contractor can mark fixed but only the authority can verify. Back it with the test names.

**Code-fluency drill (you):** be able to open and explain, without help: `models.py` (the 4 new classes), `routes/assignments.py` (assign and review), `assignment_helpers.py` (status steps), `predict.py` (confidence gate), `auth.py` (roles). `docs/a4/CODE_GUIDE.md` is the starting point; extend it.

### H. Repository and submission (G3, G7) — highest "silent failure" risk

Current facts found while planning: the GitHub repo `Malodeity/hydrosentinel` is **public**; its last push was **2026-09-24**; there are **156 uncommitted changes** locally; `model.pkl` and the regulatory PDFs are **not tracked**, so a fresh clone has no trained model and no PDFs (the app falls back to the heuristic and the regulations feature has nothing to read); `.env` is ignored (good). There are stray folders (`forge-workspace`, `.freebuff`, `graphify-out`, `skills-lock.json`).

Tasks:
1. **Secret scan** of tracked files **and history** for API keys/passwords (`git log -S` for `sk-`; check `.env.example` has only placeholders). If anything real was ever committed, rotate the key. *First pass done 2026-11-09: no OpenAI-style key (`sk-` + 20 characters) in tracked files, no `sk-proj` in any commit, and `.env` was never committed. Not yet checked: other key formats, and passwords in old commits. Re-run once more right before the final push, because new files are about to be added.*
2. **Decide what is in the repo** (write the decision in the README):
   - Commit source, tests, docs, diagrams, evidence, demo baseline SQL.
   - Decide on `model.pkl` (small? then commit, so the marker sees XGBoost) — otherwise provide `python -m ai.train` instructions and the saved metrics. Same for PDFs: commit if licence allows (public DWS reports) else document where to download.
   - Add stray folders to `.gitignore`.
3. **README rewrite**: what it is, how to run in two ways (Docker Compose; or local using `start_demo.sh`), seeded logins table (admin, authority admin, a contractor; password = `DEMO_CONTRACTOR_PASSWORD`/`ADMIN_PASSWORD` from `.env.example`), how to run tests, how the AI key is optional (what degrades without it), links to the UML and evidence folders.
4. **Commit in logical commits** (not one 156-file blob), push to `main`, tag `a5-final`. Do not commit PDFs of the A4 report bloat unless needed.
5. **Fresh-clone test (gate G3)**: `git clone` into an empty folder (outside iCloud-synced Documents, e.g. `~/Desktop/a5-clone-test`), follow only the README, run tests, open the app. Fix every gap found. Repeat until a clean pass. (Known trap: this repo lives in iCloud Documents where `.venv` and `node_modules` are cloud-only; the helper cache `~/Library/Caches/hydrosentinel-dev` is what works today — the README must not depend on it.)
6. **Docker Compose path check:** `docker compose up --build` works from the clone (compose currently reads `.env`; port 5432 conflicts with Postgres.app on this laptop — document the `POSTGRES_PORT` override).
7. **MyTUTor package** (G7): `ISJ107V_A5_213355813_Slides.pdf` (+ the HTML deck), `ISJ107V_A5_213355813_UML.zip` (PNG + editable sources), repo URL file/text. Upload early (day before), then re-download each file to check it opens. Keep a copy on a USB and on the second device.
8. **Repo visibility:** a public repo is accessible to the marker without permission problems. Keep it public until marking is done, or add the marker as collaborator if told to make it private.

### I. Rehearsal and day-of (G5, G6) — you

- Three timed runs with a phone stopwatch, standing, aloud: run 1 with notes (find the weak spots), run 2 without notes, run 3 with a planted failure (kill the backend at the AI step) and recover.
- One run in front of a person who asks 3 hard questions from section 4.G.
- **T-24h checklist:** reset demo data; fresh `git pull` of nothing — we present from the tagged state; full test run; both videos playing; charger; adapters (HDMI/USB-C); phone hotspot works; slides PDF on USB + cloud + phone; logins noted on paper; browser profiles logged in; clear browser notifications; sleep off.
- **T-1h:** `reset_demo.sh`, `start_demo.sh`, open the three browser profiles, open slides in presenter mode, play 3 seconds of each video, mute system sounds.
- **During:** if anything fails, say one sentence, switch to the fallback, keep talking. A recovered failure scores better (5.2) than a frozen one.

---

## 5. Schedule

The presentation date is **unknown** — fill it in: **Date: ______ Time: ______ Venue: ______**

Two versions; pick by days remaining (D = days until the presentation).

### If D ≥ 7 (comfortable)

| Day | Work |
|---|---|
| D-7 | Send the lecturer email. Section 4.A1 faults fixed + tests. Requirements audit (A4). Start names glossary. |
| D-6 | A2 usability items. Re-run all tests. Diagram D1, D2 drawn. |
| D-5 | **Freeze new features at end of day.** Diagrams D3, D4, D5 drawn. Name audit started. |
| D-4 | Name audit to zero mismatches. Test evidence run (B1, B2). Slide deck built (section E). |
| D-3 | UAT sessions (B3) with 3 testers. Q&A document. Demo baseline + reset script + demo script. |
| D-2 | Record both fallback videos. README rewrite, secret scan, commits, push, tag. Fresh-clone test (G3). |
| D-1 | Rehearsals 1–3. Upload to MyTUTor and verify downloads. T-24h checklist. |
| D | T-1h checklist. Present. |

### If D is 3–6 days (tight) — drop A2.3–A2.5 and A3 entirely; do A1.1, A1.2, A1.4 only; UAT with 2 testers on D-3; diagrams reuse existing D1/D2 generators.

### If D ≤ 2 days (emergency) — **no code changes at all.** Do, in this order: (1) update diagrams to include contractors (D1, D2, D3, D5 minimal), (2) slides with refreshed numbers, (3) the 2 videos + reset script, (4) push + tag + upload, (5) rehearse twice. Declare the A1 faults as "known limitations" on the limitation slide.

---

## 6. Challenge log — the plan attacked, and what it became

Each challenge was raised against an earlier draft of this plan. The right-hand column is what changed in the plan.

| # | Challenge | Resolution built into the plan |
|---|---|---|
| 1 | "The brief says present within the allocated **5 minutes** and also **12–15 minutes**. You could prepare the wrong length." | Ambiguity listed in section 1 with a lecturer email. Plan is built so the **slides part ≈ 5–6 min** and the demo is the remainder; either reading survives (talk sections are modular). |
| 2 | "Do we need to deploy to a server?" | No: the brief asks for a **local or offline fallback** and a **deployment diagram**, not hosting. D5 shows the real local/Docker environment. Lecturer email confirms. |
| 3 | "More features before the presentation could break the demo." | Scope freeze (section 3) with a date rule; A3 defaults to *do not build*. |
| 4 | "Diagrams might look right but not match code." | The audit table with file:line evidence, a script to diff class attributes with `models.py` and routes with the OpenAPI list, and zero tolerance or a listed deviation. |
| 5 | "UAT is required in Q4.1 but nobody has done it." | B3: concrete protocol, 3 testers, results reported honestly including failures; "unresolved" allowed. |
| 6 | "The database now has test data and stray records; the demo might show junk." | F1: dump a curated baseline and restore it before every run. |
| 7 | "OpenAI or Wi-Fi may fail in the room." | F3 table; template fallback in the AI draft; videos recorded with real output; offline test (G6). |
| 8 | "A marker clones the repo and it doesn't run (no model, no PDFs, venv in iCloud)." | Section 4.H items 2, 3, 5, 6, gate G3 done from a clean directory. |
| 9 | "The repo is public and a key or the shared demo password could leak." | History secret scan; placeholders only in `.env.example`; A1.3 seeding flag; A1.4 password change. Rotate keys if anything real was ever committed. |
| 10 | "14 minutes for five diagrams, a demo and results is too much." | Fixed time budget with per-slide seconds; sequence diagram gets the most time, others 20 s; backup slides for depth; cut list (section 8). |
| 11 | "Numbers on slides could differ from reality." | Numbers are pasted from saved output files with timestamps; grep for stale values (C2); one source folder. |
| 12 | "You might be asked about code you did not write." | Section 4.G code-fluency drill, `CODE_GUIDE.md` extended, 'what you wrote vs AI-assisted' answer prepared and consistent with the declaration. |
| 13 | "The requirements table is weeks old; a marker may notice a feature listed as missing that exists (or the reverse)." | A4 requirements audit; every row verified; incomplete items kept visible on slide 2. |
| 14 | "Fixes themselves (A1) could introduce bugs or break the migrations on the existing database." | Each fix has a failing-test-first acceptance test; new enum/index changes tested against the existing dev database (`ALTER … IF NOT EXISTS`, partial index created idempotently); full suite after each; freeze after D-5. |
| 15 | "Dev server (`vite`, `--reload`) is flaky under load." | F4: production-style processes if rehearsals show instability; run3 includes a deliberate restart. |
| 16 | "What if the presentation laptop is not this laptop?" | Fresh-clone test proves it runs elsewhere; slides PDF + videos on USB/cloud/phone; README documents setup; ask lecturer about hardware. |
| 17 | "UAT testers may break the data you then present." | UAT runs on a **copy** (a separate database or restore afterwards); `reset_demo.sh` is run after UAT. |
| 18 | "The contractor feature is new: is it an 'approved change'?" | The slide says "approved change **requested after Assignment 4**" — if there is any doubt about approval, state it as an extension and confirm with the lecturer in the same email. |
| 19 | "The emerging-tech slide may overclaim." | Keep claims tied to evidence: 26/29 held-out; 80.6% cross-validated; AI never applies changes by itself; NRW estimate is display-only. |
| 20 | "Q3.5 (consistency) is easy to forget." | It has its own slide (8) and its own table, with justified deviations written out in section 4.D. |

Residual honest limits (stated on the limitation slide, not hidden): AI limit is per process; photos are served by URL; real email never tested against a real server; accuracy rests on 29 test cases; scoring is manual; the NRW figure is a province estimate.

---

## 7. Risk register (top risks, ranked)

| Rank | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| 1 | Demo fails live (backend, DB, AI, network) | Medium | Very high (Q2 16 marks) | Baseline restore, fallbacks F3, rehearsals, offline videos | You + Claude |
| 2 | Diagrams do not match the system | High today | High (10 marks) | Name audit; redraw all | Claude |
| 3 | Repo not runnable by marker | Medium | High | Fresh-clone test, README, model/PDF decision | Claude |
| 4 | No UAT evidence | High today | Medium (3 of 8) | B3 within D-3 | You |
| 5 | Running over time | Medium | Medium | Timed plan, cut list, 3 timed runs | You |
| 6 | New code breaks something late | Medium | High | Freeze, tests, no changes in emergency mode | Claude |
| 7 | Questions on code you cannot explain | Medium | High (Q5.3 3 marks + individual mastery) | Drill, code guide, honest AI-use answer | You |
| 8 | Secrets/demo password exposed in a public repo | Low–medium | Medium | Scan, rotate, flag, change-password | Claude |
| 9 | Hardware/projector issue | Low | Medium | Adapters, second device, PDF on USB | You |
| 10 | Illness/emergency | Low | Very high | Tell the lecturer early; everything stays in the repo and the cloud | You |

---

## 8. Cut list (if time runs short, cut from the bottom)

P0 (never cut): Q3 diagrams reflecting contractors; refreshed test numbers; UAT with at least 2 testers; demo baseline + reset; two fallback videos; README + push + tag + fresh-clone test; rehearsals; MyTUTor upload.
P1 (cut only in emergency): A1.1, A1.2 fixes; names audit table (do a lighter manual check); component diagram detail.
P2 (cut first): A1.3, A1.4 (state as limitations), all of A2, all of A3, extra Q&A depth, the Docker Compose path check (keep local path only).

---

## 9. Open questions to answer (fill in)

- [ ] Presentation date / time / venue: __________
- [ ] Lecturer reply on "5 minutes vs 12–15", local demo, hardware, repo access: __________
- [ ] Do we keep the repo public until marking ends? __________
- [ ] Commit `model.pkl` and the DWS PDFs, or document how to regenerate? __________
- [ ] UAT testers (3 names): __________
- [ ] AI-use declaration wording for A5 (what AI did vs what you did): __________

---

## 10. Progress tracker (updated 2026-11-16)

Done by Claude: A1.1 to A1.4 fixed with tests (279 backend tests) · A2.1, A2.2, A2.3, A2.5 built (A2.4 skipped: logins are on the Users tab) · FR-08 "Score risk now" button · requirements re-audited (`requirements.md`) · TC-10 to TC-20 (`test_cases.md`) · e2e extended to 27 checks · measurements re-run · five UML diagrams redrawn with sources, class diagram generated from code, name audit 60/60 · demo baseline (`reset_demo.sh`, `seed_demo_reports.py`) · screens (`shot.mjs`) · final deck (HTML + PDF) · README, CLAUDE.md, script and Q&A (`PRESENTATION_SCRIPT.md`) · UAT form.

Still open (needs the student): [ ] UAT with 3 testers, then fill slide 11 and `uat_results.md` · [ ] lecturer answers (5 vs 12 to 15 min, date, hardware) · [ ] record 2 fallback videos and test offline (G6) · [ ] 3 timed rehearsals (G5) · [ ] decide commit of `model.pkl` and PDFs, commit, push, tag `a5-final`, fresh-clone test (G3), re-run secret scan · [ ] upload slides, UML sources, repo link to MyTUTor (G7) · [ ] AI-use declaration wording · [ ] frontend component tests for the new Contractors tab pieces (none written)

Gates: G2 green (279 / 109 / tsc 0 / e2e 27 of 27) · G4 green (name audit) · others open.

### Changelog after freeze
(add one line per post-freeze change: date, what, test that proves it)
