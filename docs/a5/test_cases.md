# Test results for the final system (Assignment 5)

Run on 2026-11-16 on the presenter laptop. Source files are in `docs/a5/evidence/`.

| Level | What | Result |
|---|---|---|
| Unit / functional | `pytest tests/` (backend, transaction rollback on the real database) | **325 passed, 0 failed** (`pytest_full.txt`) |
| Unit | `vitest run` (frontend logic) | **121 passed, 0 failed** (`vitest_full.txt`) |
| Static | `tsc --noEmit` | 0 errors (`tsc.txt`) |
| Integration + system | `scripts/e2e_workflow.py` against the live backend, database and GPT-4o | **27 of 27 checks** (`e2e_output.txt`) |
| User acceptance | 3 testers, 4 tasks each (`uat_form.md`) | see `uat_results.md` (filled in after the sessions) |

## Representative cases (the "recommended evidence format")

| ID | Type | Case | Expected | Actual | Status |
|---|---|---|---|---|---|
| TC-01 | Main workflow | Submit a leak report with a PNG and a text file | 201, one photo kept | 201, one photo | Pass |
| TC-02 | Invalid input | Unknown issue type | 422 | 422 | Pass |
| TC-03 | Data | Unknown authority id | 404 | 404 | Pass |
| TC-04 | Main workflow | Admin sets "in review" with a note | 200, reviewer recorded | as expected | Pass |
| TC-05 | Emerging tech | Score an authority | 200, `xgboost` | xgboost, medium, 0.83 | Pass |
| TC-06 | Emerging tech | GPT-4o CAP draft | 200, 1 to 6 items | 5 items | Pass |
| TC-07 | Privacy | Track by code | status only, no location | as expected | Pass |
| TC-08 | Security | Admin list with no token | 401 | 401 | Pass |
| TC-09 | Security | Wrong password | 401 | 401 | Pass |
| TC-10 | Main workflow | Assign, accept, start, fix, verify | report resolved, audit rows | as expected | Pass |
| TC-11 | Security | Contractor asks for another contractor's ticket | 404 | 404 (pytest) | Pass |
| TC-12 | Security | Contractor calls an admin route | 403 | 403 | Pass |
| TC-13 | Access | Authority admin reads another authority | 403 | 403 (pytest) | Pass |
| TC-14 | Invalid input | Fix without a note | 422 | 422 | Pass |
| TC-15 | Reliability | Assign while the mail server fails | ticket still created | created (pytest) | Pass |
| TC-16 | Business rule | Assign a contractor not set up for that authority or issue | 422 | 422 (pytest) | Pass |
| TC-17 | Integration | Work-order draft with OpenAI unavailable | template text, no error | template (pytest) | Pass |
| TC-18 | Security | Change password: wrong current, short new, success, old refresh token dead | 400, 422, 204, 401 | as expected (pytest) | Pass |
| TC-19 | Reliability | Switched-off contractor finishes an existing ticket, cannot get a new one | 200, then 409 | as expected (pytest) | Pass |
| TC-20 | Data integrity | Database refuses a second open ticket on one report | IntegrityError | as expected (pytest) | Pass |
| TC-21 | Repair photos | Photo after accepting; another contractor; a text file; nine photos | stored and shown to admin; 404; 422; 422 | as expected (pytest) | Pass |
| TC-22 | AI limit | 20 calls recorded in the database, then one more | 429, also after a restart | 429 (pytest) | Pass |
| TC-23 | Re-scoring | Stale score, fresh score, another server holding the lock | stale re-scored, fresh left, nothing scored while locked | as expected (pytest) | Pass |
| TC-24 | Search | Contractors searched by authority, several words, none | matches narrow as words are added | as expected (vitest) | Pass |
| TC-25 | Citizen email | Receipt, looked-at, resolved over real SMTP; no address; bad address; mail server down | one mail each, none without an address, 422, report still saved | as expected (pytest) | Pass |
| TC-26 | Health | Health check with and without the risk model | 200, then 503 | as expected (pytest) | Pass |
| TC-27 | Contractor AI | Invented number, invented claim, OpenAI down, another contractor, hourly limit | rejected or plain fallback; 404; 429 | as expected (pytest) | Pass |
| TC-28 | Contractor dashboard | 7 days, 30 days, 3 months: counts, average time, on time | match the tickets | as expected (vitest) | Pass |

## Unresolved
None failing. Known and stated: browser screens are checked by hand and by the UAT, not by automated browser tests; email is tested through the real SMTP protocol against a mail server inside the test, not against a commercial provider; the risk model accuracy rests on 29 held-out authorities.

## Quantitative measures (`measurements.txt`, 2026-11-21, one laptop, server and client on the same machine)
- GET /wsa (169 rows): median 9 ms, p95 13 ms (n=50)
- POST /reports (multipart, one photo): median 7 ms, p95 11 ms (n=50)
- GET /reports (admin, 60 reports): median 107 ms, p95 169 ms (n=50)
- GET /assignments (admin): median 41 ms, p95 68 ms (n=50)
- POST /risk/score (XGBoost, one WSA): median 8 ms, p95 14 ms (n=20)
- labelled WSAs in DB: 159
- XGBoost: 89.7% held out (26 of 29), 80.6% five-fold cross-validation, rule baseline 34.5% (A3 evaluation).
- GPT-4o CAP draft: 2.7 s and 4.1 s in the last two end-to-end runs.
