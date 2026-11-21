# HydroSentinel: questions and answers

Rehearse these out loud. The brief (Q5.4) marks you on "answering technical questions accurately and explaining individual design, implementation and testing decisions", so answer in **your own words**.

**Answer shape that works:** the direct answer (one sentence), then why, then the trade-off or limit. Stop there.

**Rule for anything you are unsure of:** say "I'm not sure of the exact detail, but here's what I know..." Never invent a number.

Each answer ends with **Show:** the place in the code to open if they ask to see it. Details of those files are in `CODE_GUIDE.md`.

Contents
1. The project and requirements
2. Architecture and design
3. The AI: machine learning (XGBoost)
4. The AI: language model (GPT-4o), the question agent and regulation search
5. Data
6. Security and privacy
7. Reliability and performance
8. Testing
9. UML and the report
10. Limitations, ethics and next steps
11. Process, integrity and "your own work"
12. Walk-through questions ("what happens when...")

---

## 1. The project and requirements

**Q1. In one sentence, what is HydroSentinel and who is it for?**
A web app where residents report water problems and officials see which municipalities are at risk, with AI rating risk and drafting action plans. The users are residents (no account), municipal and oversight admins, and regulators who read the public dashboard.

**Q2. Which requirements did you implement, which partly, which not?**
Ten implemented: the risk map and digest, reporting with photos, public tracking, admin sign-in, triage, alerts, CAP updates, XGBoost scoring, the AI CAP draft and regulatory questions. Two partial: there's no scoring button in the admin page (only the API and a script), and the AI rate limit isn't shared across servers. Two deferred: scheduled re-scoring and notifying residents by email or SMS. That's Table 1 in my report.

**Q3. What is the "emerging technology" and why does it belong in this system?**
Artificial intelligence and machine learning. XGBoost rates each authority's risk from audited data, and GPT-4o writes the resident reply, drafts action plans and answers officials' questions. They matter because the data is too large and scattered for an official to read by hand: the model turns it into a ranked view, and the language model turns it into a draft a person can approve.

**Q4. Why did you choose a corrective action plan (CAP) as the AI output?**
Because it's the real next step after a risk finding. An authority with a high rating has to do something about it, and drafting a plan with evidence is time-consuming. The AI proposes three to five items, each citing a number from the data, and an admin accepts one to apply it.

**Q5. What is the central value of the prototype?**
It closes the loop between what residents experience and what regulators see: a report goes in, is triaged, linked to the authority's risk, turned into an action, and every step is recorded.

---

## 2. Architecture and design

**Q6. Describe the architecture.**
A React and TypeScript front end talks to a FastAPI back end over JSON. The back end owns the rules, authentication and the audit log, stores data in PostgreSQL, loads the XGBoost model at start-up, and calls the OpenAI API through one helper. Report photos are files on disk. **Show:** `backend/main.py` (the routers), `frontend/src/App.tsx` (the routes).

**Q7. Why FastAPI and React?**
FastAPI validates input automatically from type definitions, which is where my 422 errors come from, and it's quick to build and test. React gives a component-based interface that handles the many filters and tabs in the admin console. Both were familiar choices rather than the only options.

**Q8. Why PostgreSQL, and what are the tables?**
It's relational data with clear links (authorities, reports, scores, alerts), so a relational database fits, and it supports enums, constraints and JSON for the audit log. Eight tables: authorities, citizen reports, users, refresh tokens, risk score history, summaries, alerts and the audit log. **Show:** `backend/app/models.py`.

**Q9. Why is the audit log append-only?**
So it can't be quietly changed. Each admin action adds a row with the user, action, old value, new value and IP. There is no code path that edits or deletes a row. **Show:** `backend/app/audit_helpers.py`.

**Q10. How do the front end and back end share data shapes?**
The back end defines them as Pydantic schemas (`backend/app/schemas.py`) and the front end mirrors them as TypeScript interfaces in `frontend/src/api/`. They are kept in step by hand, which is a weakness: generating one from the other would be safer.

**Q11. Where does the business logic live: front end or back end?**
The rules that matter (access control, validation, alerts, scoring, audit) are on the back end, so they can't be bypassed. The front end handles presentation and convenience such as filters, paging and age badges. The age thresholds live in one front-end file for the display and the PDF. **Show:** `frontend/src/lib/reportAge.ts`.

**Q12. How do you keep the code organised?**
Back end: routes for HTTP, helpers for logic (`alert_helpers.py`, `audit_helpers.py`), `ai/` for model and retrieval code, `etl/` for the data pipeline. Front end: `pages/` for screens, `components/` for reusable pieces, `lib/` for pure, tested logic, `api/` for server calls.

---

## 3. The AI: machine learning (XGBoost)

**Q13. What does the model predict, from what?**
It predicts low, medium or high risk for an authority from six inputs: Blue Drop score, non-revenue water percentage, maintenance spending percentage, CAP status, latitude and longitude. **Show:** `backend/ai/features.py`.

**Q14. Where did the training labels come from?**
From the Department of Water and Sanitation's own Blue Drop Risk Rating for 144 authorities. So the model learns to reproduce an audited rating, not my opinion. **Show:** `backend/ai/train_from_bdrr.py`.

**Q15. How accurate is it, and how do you know?**
On 29 authorities held out of training it got 26 right, which is 89.7%. A simple rule of thumb scored 34.5% on the same 29. Because 29 is small, I also ran 5-fold cross-validation, which gives 80.6% with a spread of 8 points. I trust the cross-validated figure more, and I say so in the report.

**Q16. Isn't 89.7% too good? Could the model be cheating?**
It's a fair concern. The labels come from a DWS rating that is itself related to Blue Drop scores, which is one of my inputs, so some of the accuracy is the model recovering an existing relationship. The held-out split was stratified and fixed, so there's no leakage between train and test, but the honest reading is "it reproduces the DWS rating well from related indicators". Its real value is covering authorities between audit cycles.

**Q17. Why XGBoost and not another model?**
It suits small tabular data like 144 rows and six columns: it handles non-linear relationships and needs no feature scaling, and it's fast. I compared it to my fallback rule but didn't benchmark other model families, such as logistic regression or a random forest. That's a limit I'd address next.

**Q18. Why are latitude and longitude features? Isn't that a proxy?**
Risk clusters regionally, so location carries signal, for example the Northern Cape has many high-risk authorities. But with only 144 rows, the model may lean on geography rather than causes. That's a limitation, and I would test the model without the coordinates.

**Q19. What do you do when the model can't be trusted?**
`predict_wsa_risk` falls back to a rule-based heuristic in three cases: no model is loaded, the Blue Drop score is missing (a made-up zero must never drive a prediction), or the model's top class has under 50% confidence. The history table records which source scored each run. **Show:** `backend/ai/predict.py`.

**Q20. What is the fallback rule?**
A weighted score: 35% from how low the Blue Drop score is, 35% from the NRW percentage, 20% from how low the maintenance spend is, plus a few points by CAP status. It's transparent but crude: 34.5% accurate on the held-out set.

**Q21. The classes are imbalanced. How did you handle that?**
Of the 144 labels, 95 are low, 32 medium and 17 high. I used a stratified split so each class appears in train and test, and I report per-class results. The medium class is the weakest, with recall 0.71 on 7 examples, and I list that as a limitation.

**Q22. Was the deployed model trained on all the data?**
Yes. For deployment it's retrained on all 144 labelled rows. The 89.7% comes from the earlier experiment with a held-out split. So there is no leftover test set for the deployed model, which is why I quote the experiment and the cross-validation.

**Q23. What is the risk trend forecast?**
It fits a straight line through an authority's score history and projects the next score. It is simple statistics, not machine learning. I don't count it as AI. **Show:** `backend/ai/trajectory.py`.

**Q24. The model once switched itself off. What happened?**
My local `.env` held a Docker-only path to the model file. Outside Docker the file wasn't found, the model never loaded, and every authority was scored by the weak fallback rule, with nothing in the interface to show it. I fixed the loader to fall back to the bundled file and log a warning, wrote a test, and recorded it as a limitation, with a fix for the final system (show the scoring source in the admin page).

---

## 4. The AI: language model, question agent and regulation search

**Q25. How do you use GPT-4o, and where?**
Through one helper, `call_openai`, with a 30-second timeout and one retry. It writes the resident's reply, summaries and the national digest, admin case notes, the CAP draft, and the map-view summary. It's also behind the question box. **Show:** `backend/app/routes/ai.py`.

**Q26. How do you stop the AI making things up?**
Four ways. Prompts contain only real data from the database and say not to invent anything. Prompts limit length, so there's less room to wander. The CAP draft must be structured JSON with a number cited in each justification, and a reply that can't be parsed is rejected with a 502. And most importantly, nothing the AI writes changes data until a person clicks Accept or Save.

**Q27. What happens if OpenAI is down or there's no key?**
The AI features return a clear error (503 with no key, 502 on failure) and the rest of the system keeps working. The map summary even returns its live counts with the sentence marked unavailable. I tested these cases.

**Q28. How does the question agent work, and why is it safe?**
The model can call ten fixed, read-only tools, for example authorities, trending authorities, report counts, alerts, audit summary and province comparison. It can't run arbitrary SQL. The loop is bounded to five rounds, and the answer must cite numbers the tools returned. **Show:** `backend/ai/query_agent.py`.

**Q29. How does the regulation question work?**
I split the DWS report PDFs into page-sized chunks and index them with TF-IDF. A question retrieves the five most relevant pages, and GPT-4o answers only from those, citing file and page. If the pages don't answer it, the model says so. **Show:** `backend/ai/rag.py`.

**Q30. Why TF-IDF and not embeddings?**
It's simple, free, explainable and works well on keyword-heavy regulatory text, and it needs no extra service. The cost is that it misses paraphrases. Embeddings would improve recall and are a sensible upgrade.

**Q31. How do you control the cost of the AI?**
Three ways. Expensive endpoints (CAP draft, question box, regulation search) are limited to 20 per admin per hour and return 429 beyond that. Text is cached (the national digest for 24 hours, the map summary for 10 minutes per view). And on the admin page, AI text is only fetched when its tab is opened.

**Q32. Why are the AI answers so short now?**
I tightened every prompt after noticing the model over-explained. Each one asks for at most two sentences and a word limit, with no introduction. Users want a status, not an essay.

**Q33. Is the "Summarise this view" endpoint safe to leave public?**
It has no login, so someone could call it repeatedly and cost money. The cache limits that for repeated views, but a per-IP rate limit is the right fix, and I'd add it before wider use.

---

## 5. Data

**Q34. Where does the data come from?**
Five DWS PDF reports (Blue Drop, No Drop, the Blue Drop Risk Rating, and Green Drop for the nation and Gauteng) and the National Treasury Municipal Money API for maintenance spending. A pipeline parses the PDFs, merges the sources and loads the authorities. **Show:** `backend/etl/run_etl.py`.

**Q35. How did you handle the same authority spelled differently in different reports?**
I match on a key made from province plus a cleaned name (`authority_key`), and a separate clean-up merged duplicates that were already in the database. That removed 115 duplicate rows and left 169 authorities. **Show:** `backend/etl/load.py`, `backend/etl/dedupe_wsa.py`.

**Q36. What does "maintenance %" actually measure?**
Repairs and maintenance as a share of total operating spending. Treasury's usual 8% benchmark is measured against asset value, which my data doesn't have, so I label it honestly and don't compare it to that benchmark.

**Q37. Is the data real or simulated?**
The 169 authorities and their indicators are real, from the DWS and Treasury sources. The citizen reports are created during the demo or tests. The source PDFs are not in the repository, so the repo ships the extracted authority rows as `backend/data/sample/wsa_sample.sql` for anyone who clones it.

**Q38. How fresh is the data?**
As fresh as the last ETL run, because the DWS publishes annually. Risk scores are only recomputed when someone runs scoring, and that's one of my deferred items.

---

## 6. Security and privacy

**Q39. How does authentication work?**
Login checks the email and a bcrypt-hashed password and returns two tokens: a short-lived access token (a JWT, about an hour) and a refresh token (7 days). The front end sends the access token on every request; the server decodes it and loads the user. **Show:** `backend/app/auth.py`, `backend/app/routes/auth.py`.

**Q40. How do refresh tokens work, and why are they safer?**
They're random, stored only as a SHA-256 hash, and single-use: each refresh revokes the old one and issues a new pair. So a stolen copy stops working as soon as the real user refreshes, and a database leak doesn't give anyone a usable token.

**Q41. How do you stop a normal user using admin endpoints?**
Every admin route depends on `get_current_admin_user`, which returns 401 with no token and 403 for a non-admin. It's enforced on the server, not just hidden in the interface. I tested the no-token cases.

**Q42. What other security controls do you have?**
Passwords hashed with bcrypt. Secrets and the OpenAI key in a `.env` that git ignores. Database access through an ORM, so queries are parameterised, which prevents SQL injection. CORS limited to the front-end address. Upload extensions restricted to images. An append-only audit log. And an admin can't deactivate their own account.

**Q43. What are the security weaknesses?**
I'd name four. Tokens live in the browser's localStorage, so a script-injection bug could steal them; an httpOnly cookie is stronger. There's no limit on sign-in attempts. Uploads are checked by file extension, not content or size. And the default JWT secret in the code is `change-me-in-production`, so a real deployment must set its own, and the app should refuse to start with the default.

**Q44. What about personal data? Do you comply with POPIA?**
I collect little: no names or phone numbers, but residents type free text and a location, which can identify someone. The public tracking page deliberately shows only the status. I haven't built a consent notice or a retention policy, so I wouldn't claim full POPIA compliance: those are required before real use. One more point: the admin AI photo check sends a photo to OpenAI. It only runs when an official clicks the button, the model is told not to identify or describe people, and the result is never shown on the public page. A real deployment still needs a consent notice that says photos may be processed by a third party.

**Q44b. How does the photo check work, and can you trust it?**
An official clicks Analyse photo. The back end checks the file, sends it to GPT-4o with a prompt that does not tell it what the resident reported, and asks for a strict JSON answer: what it shows, severity, confidence. The server, not the model, compares that with the reported issue and sets the verdict: matches, mismatch, or inconclusive (billing problems and unclear photos can't be judged). I don't fully trust it, so it never changes a case on its own. It only flags for a human. Limits: it can be wrong, a photo can't prove a report false, and each check uses one of 20 AI calls per hour.

---

## 7. Reliability and performance

**Q45. How fast is it?**
Listing all 169 authorities takes a median of 5 ms and scoring one takes about 5 ms. The AI calls take 2 to 6 seconds, so they're always shown with a loading state. These are local measurements, not a deployed system.

**Q46. Would it scale?**
The database and API would handle much more. The weak points I know are the in-memory rate limiter (it resets on restart and isn't shared across servers), the front end downloading all reports and paging in the browser, and manual scoring. The fixes are Redis, server-side paging and a scheduled job.

**Q47. What happens if two admins edit the same report?**
The last save wins, and both saves are in the audit log. There's no edit-conflict check, which I'd add for a real team.

**Q48. How do you handle errors?**
Validation errors return 422 with the field that failed, missing records return 404, auth problems return 401 or 403, rate limits 429, and AI problems 503 or 502. The interface shows plain messages (and a pop-up that doesn't vanish off-screen). **Show:** the error-feedback paragraph in section 2.1 of the report.

---

## 8. Testing

**Q49. How did you test it?**
Four layers. 292 automated back-end tests (pytest, in database transactions that roll back so real data is never changed). 113 front-end tests (Vitest) for the pure logic. An end-to-end script that runs the whole workflow, including the contractor ticket loop, against the live system: 27 checks. And I checked the interface in a real browser. **Show:** `backend/tests/`, `backend/scripts/e2e_workflow.py`.

**Q50. What did the tests actually catch?**
Real bugs. The model silently not loading. A fresh database crashing on start-up because migrations ran before the tables existed. A map that showed nothing for old alerts because the time window was measured from now, not from when the alert was raised. And an admin being able to deactivate their own account. While preparing this presentation I also found that the "risk increased" alert was in the report and the interface labels but nothing actually raised it, so I implemented it and wrote tests that force each outcome.

**Q51. What do your tests *not* cover?**
React components and full browser flows (I verified those by hand but have no Playwright tests), load testing, and AI output quality, which can't be tested deterministically. Two older alert tests also only assert when the score happens to come back high, so they can't fail; my newer tests force the exact before and after instead. The AI endpoints are tested with the OpenAI call mocked, to prove the right prompt and the right failure handling.

**Q52. Give me an example of a test that proves something meaningful.**
`test_comment_follows_the_status_the_admin_selected`: the admin picks "in review" in the dropdown before saving, and the test checks the AI prompt describes moving to review, not the saved "open" status. It would fail if someone changed the endpoint to ignore the dropdown.

**Q53. How do you know the AI did not break when you changed a prompt?**
The tests check what's sent (the prompt contents, word limits, and failure behaviour), and I read real outputs after each change. I can't test the wording itself automatically.

---

## 9. UML and the report

**Q54. Where does your design differ from the prototype?**
Scoring: the design assumed it refreshes when new data arrives; it now also scores on a schedule (every 24 hours). The rate limiter: designed as shared, first built in memory, now counted in the database. And deployment: designed around Docker Compose, demonstrated by running the services directly. They're in section 3.5 of my report.

**Q55. Explain your use-case diagram.**
Two human actors and one system actor: a resident reports and tracks, an admin signs in then triages, scores, drafts and accepts a CAP, and OpenAI is an external actor for the four functions that call GPT-4o. Sign-in is included by every admin function, and accepting a CAP item extends drafting.

**Q56. Walk me through the sequence diagram.**
The admin interface calls the API with a token. The API checks it, reads the authority, asks the XGBoost model for a score (or falls back to the rule), saves the result and an audit row, and returns it. Then for the CAP draft it checks the rate limit, gathers data, calls GPT-4o with a timeout, and returns items. The alternative frames show the failure paths: a bad token, a model fallback, a limit and an OpenAI failure.

---

## 10. Limitations, ethics and next steps

**Q57. What are the main limitations?**
The limits, each with a fix. The model can fail silently (now it warns and falls back; next, show the scoring source in the interface). The AI limit and manual scoring were two limits in Assignment 4, and both are now fixed (database-backed limit, scheduled re-scoring). What is left: citizens get no email on a status change, email was never tested on a real mail server, and Docker Compose was not run.

**Q58. What are the ethical risks?**
A wrong "high risk" rating can wrongly label a municipality, and an AI summary can be wrong. My mitigations are human approval before any change, showing which method scored an authority, and citing numbers from the data. I'd also want an appeal or review route for rated authorities before real use.

**Q59. What would you build next?**
Notifications to residents when their report changes status, scheduled scoring, a per-IP limit on the public AI endpoint, rotating the leaked database password out of the repository history, and assigning reports to a named person with editable age thresholds.

**Q60. If you started again, what would you change?**
I'd set up automated tests and a start-up check from day one, because several of my bugs (the model path, the blank-database crash) were configuration problems that a basic check would have caught early.

---

## 11. Process, integrity and "your own work"

**Q61. Did you write this yourself?**
Be direct and consistent with your declaration. Say what it says: "I used an AI assistant for code, design and diagrams, integrations, tests and documentation. I reviewed and ran everything, I can explain it, and I take responsibility for it." Then show you can: answer the question they ask about it. Do **not** claim sole authorship, and do not minimise.

**Q62. Which parts did *you* do?**
Answer with what is true for you: the decisions (the project, the technology, what to build and what to leave out), the review and testing, and the understanding you can show now. Name specific choices you made and why. Do not name parts you cannot explain.

**Q63. Why is the AI-use declaration worded the way it is?**
Because it must be accurate. The brief asks for "permitted AI-tool use". I listed the areas where I used the assistant and confirmed I reviewed and can explain the result.

**Q64. Explain this function to me.** *(they point at code)*
Read it, say what goes in and what comes out in one sentence, then the key line. Use the comments I added to the code: each route and key function has a plain-English comment above it.

---

## 12. Walk-through questions ("what happens when...")

**Q65. What happens, step by step, when a resident submits a report?**
1. The form disables Submit until the province, authority and description (10+ characters) are valid. 2. The browser sends a multipart request to `POST /reports` (no login). 3. The server checks the authority exists (404 if not), validates the issue type (422 if not), saves the report with a random reference code, then runs the volume-spike and geographic-cluster alert checks. 4. It stores only image files. 5. The browser then asks the AI for a short reply (if that fails, the report is still saved). 6. The resident sees the code. **Show:** `backend/app/routes/reports.py` (`create_report`).

**Q66. What happens when an admin changes a report's status?**
`PATCH /reports/{id}` requires an admin token. The server updates the status and note, records who reviewed it and when (first move to "in review") or who resolved it (first move to "resolved"), writes an audit row with the old and new values, and commits. **Show:** `update_report` in the same file.

**Q67. What happens when you click "Draft CAP"?**
The browser calls `GET /ai/wsa/{id}/cap-draft`. The server checks the admin token and the 20-per-hour limit, loads the authority and its open reports, builds a prompt of real values, calls GPT-4o asking for JSON, parses and validates it (3 to 5 items), and returns it. Nothing is saved until an admin clicks Accept, which calls `PATCH /wsa/{id}` and writes an audit row.

**Q68. What happens when an alert is raised, and when does it go away?**
Alerts are created inside the actions that cause them (a report, a score, or a read of the alert list for overdue CAPs). Only one unacknowledged alert per type per authority can exist. An admin acknowledges it, which records who and when, and it then leaves the active list (it stays in history).

**Q69. How does "Summarise this view" follow the map?**
The map reports its bounds. The server finds the authorities inside, counts them, and sends only those facts to GPT-4o. After the first click, every time the map stops moving for about a second, the front end asks again; if an older answer arrives late it's ignored. **Show:** `frontend/src/components/MapViewSummary.tsx`.

**Q70. How does the age flag work?**
Whole days since the report was created, and only for unresolved reports. The level is the highest threshold reached: 3 days attention, 7 overdue, 14 critical, 30 escalate. It's in one file used by the list, the filters and the PDF. **Show:** `frontend/src/lib/reportAge.ts`.

**Q71. How is the management PDF made?**
It's a normal page styled for A4 that the browser prints to PDF. The numbers come from a tested function (`buildManagementStats`), so every figure is checked. The trade-off is that it uses the browser's print dialog rather than a server-generated file, which avoids adding a dependency.
