# Requirements status at final submission (Assignment 5)

Re-checked against the code on 2026-11-16. Evidence column points at a saved test output or a screen.

| ID | Requirement | Status | Prototype feature | Test case | Evidence |
|---|---|---|---|---|---|
| FR-01 | Public dashboard with risk map, authority details and AI national digest | Completed | `DashboardPage`, `GET /wsa`, `GET /ai/digest` | TC-01 area | screen 01 |
| FR-02 | Citizen submits a report with type, description, map pin and photos | Completed | `ReportPage`, `POST /reports` | TC-01, TC-02, TC-03 | e2e_output.txt |
| FR-03 | Citizen tracks a report by reference code (no location or description shown) | Completed | `GET /reports/track/{reference_code}` | TC-07 | e2e_output.txt |
| FR-04 | Admin sign-in with access control on every admin function | Completed | JWT + rotating refresh token, `UserRole` | TC-08, TC-09 | e2e_output.txt |
| FR-05 | Admin triages reports (open, in review, resolved) with a note | Completed | `PATCH /reports/{report_id}` | TC-04 | e2e_output.txt |
| FR-06 | Automatic alerts: high risk, increase, volume spike, cluster, overdue CAP, **overdue ticket** | Completed | `alert_helpers.py` | pytest `test_alerts.py`, `test_assignments.py` | pytest_full.txt |
| FR-07 | Admin updates CAP status and due date, audited | Completed | `PATCH /wsa/{wsa_id}` | pytest `test_audit_log.py` | pytest_full.txt |
| FR-08 | Risk scoring from the admin page | **Completed (was Partial in A4)** | "Score risk now" button, `POST /risk/score/{wsa_id}` | TC-05 | e2e_output.txt |
| FR-09 | AI rate limit shared across servers | Partial | 20 per hour per user, held in one process (`rate_limit.py`) | pytest | limitation slide |
| FR-10 | Scheduled automatic re-scoring | Deferred | Scoring runs on request | none | limitation slide |
| FR-11 | Email/SMS to **citizens** on status change | Deferred | Citizens use the tracker. Staff get bell notices and optional email | none | limitation slide |
| FR-12 *(approved change)* | Admin assigns a report to a contractor as a ticket. Contractor accepts or rejects, works it, marks fixed. Admin verifies, which resolves the report | Completed | `ReportAssignment`, `POST /reports/{report_id}/assign`, `PATCH /my/tickets/{assignment_id}`, `PATCH /assignments/{assignment_id}/review` | TC-10 | e2e_output.txt |
| FR-13 | A contractor sees only its own tickets and can never resolve a report | Completed | `get_current_contractor`, 404 for another's ticket | TC-11, TC-12 | pytest `test_assignments.py` |
| FR-14 | Admin accounts can be limited to one authority | Completed | `users.wsa_id`, `require_wsa_access` | TC-13 | pytest |
| FR-15 | In-app notifications, optional email | Completed (email tested with a mock only) | `Notification`, `mailer.py` | TC-15 | pytest |
| FR-16 | Overdue tickets raise an alert | Completed | `assignment_overdue` | pytest | pytest_full.txt |
| FR-17 | AI drafts ticket instructions and suggests a contractor; a person confirms | Completed | `GET /ai/reports/{report_id}/work-order` | TC-17 | pytest |
| FR-18 | Users can change their password; a national admin can reset one | Completed | `POST /auth/change-password`, `PATCH /users/{user_id}/password` | TC-18 | pytest |
| ETR-01 | XGBoost risk scoring with rule-based fallback | Completed | `ai/predict.py` | TC-05 | e2e_output.txt, 89.7% held out |
| ETR-02 | GPT-4o drafts CAP items; admin accepts | Completed | `GET /ai/wsa/{wsa_id}/cap-draft` | TC-06 | e2e_output.txt |
| ETR-03 | Regulatory questions answered from the DWS PDFs | Completed | `ai/rag.py`, `POST /ai/query` | pytest `test_rag.py` | pytest_full.txt |

## Approved change since Assignment 4
FR-12 to FR-18: contractor tickets, authority-scoped admins, notifications, AI work-order draft, bulk assign, province-wide coverage, password change and reset, "Score risk now" button, single-open-ticket database rule.

## Incomplete items (kept on the scope slide)
FR-09 (limit per process), FR-10 (no scheduler), FR-11 (no citizen email). Also: photo on "Fixed" not built; email never sent to a real SMTP server; NRW is a province estimate, display only.

## Justified deviations from the design
1. Contractor tickets are a separate table (`ReportAssignment`), not a new `case_status`, so the citizen tracker, CSV and old reports keep working.
2. Switching a contractor off stops new tickets only. It can still finish tickets it holds (found in review: the first version locked it out and stranded repairs).
3. One open ticket per report is enforced by a partial unique index in PostgreSQL, not only in code.
4. Risk scoring is manual, not scheduled (FR-10).
