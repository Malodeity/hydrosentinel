# Test results for the final system (Assignment 5)

Run on 2026-11-16 on the presenter laptop. Source files are in `docs/a5/evidence/`.

| Level | What | Result |
|---|---|---|
| Unit / functional | `pytest tests/` (backend, transaction rollback on the real database) | **279 passed, 0 failed** (`pytest_full.txt`) |
| Unit | `vitest run` (frontend logic) | **109 passed, 0 failed** (`vitest_full.txt`) |
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

## Unresolved
None failing. Known and stated: real email not tested against a real SMTP server; browser UI is checked by hand and by the UAT, not by automated browser tests; accuracy rests on 29 held-out authorities.

## Quantitative measures (`measurements.txt`, 2026-11-16, one laptop, server and client on the same machine)
- GET /wsa (169 rows): median 7 ms, p95 9 ms (n=50)
- POST /reports (multipart, one photo): median 6 ms, p95 9 ms (n=50)
- GET /reports (admin): median 43 ms, p95 65 ms (n=50)
- GET /assignments (admin): median 14 ms, p95 20 ms (n=50)
- POST /risk/score (XGBoost, one WSA): median 7 ms, p95 9 ms (n=20)
- labelled WSAs in DB: 159
- XGBoost: 89.7% held out (26 of 29), 80.6% five-fold cross-validation, rule baseline 34.5% (A3 evaluation).
- GPT-4o CAP draft: 2.7 s and 4.1 s in the last two end-to-end runs.
