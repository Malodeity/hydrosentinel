# Audit plan: is everything linked, and does the data make sense?

Rule for this pass: no redesigns. Fix only what is broken, confusing, or not connected. Each item below gets a status.

## A. Numbers must agree everywhere
- [x] A1. Overview tiles vs the lists they open (unresolved, 2+ weeks, overdue plans, high risk without a plan, alerts)
- [x] A2. Tab badges vs the numbers inside the tabs (what does each badge count, and is it said?)
- [x] A3. CAP tab: status chips, charts, table rows and pager all describe the same set
- [x] A4. Citizen reports tab: charts vs chips vs table
- [x] A5. Public dashboard tiles vs admin numbers (same definitions: high risk, critical drinking water)
- [x] A6. Public report stats (counts, median) vs the admin list

## B. Every click goes somewhere sensible (nothing gets stuck)
- [x] B1. Overview: each tile, each "Do these first" item, "Why?" on trending, alert acknowledge
- [x] B2. CAP tab: filters can always be cleared; an empty result explains itself and offers a way out
- [x] B3. Reports tab: same, plus opening a report from Overview shows it in the list
- [x] B4. Saving a CAP / report status refreshes the numbers everywhere
- [x] B5. Photo check: errors, no photo, re-run
- [x] B6. Management report page: opens, links back
- [x] B7. Public dashboard: find my area, search, authority card buttons, report link, tabs
- [x] B8. Report form pre-selection when arriving from the dashboard

## C. Data logic and edge cases (back end)
- [x] C1. Alerts: auto-close rules, no duplicates, nothing closes that should stay open
- [x] C2. CAP save: status and deadline combinations that make no sense (completed with no date, none with a date)
- [x] C3. Public endpoints leak nothing admin-only
- [x] C4. AI endpoints: auth, rate limit, failure paths

## D. Wording and readability
- [x] D1. Labels that a new admin would not understand
- [x] D2. Docs and test counts match reality

Status is recorded at the bottom as each item is closed.

## Findings and fixes

Numbers were checked against the API directly (a script recomputing unresolved reports, 14+ day reports, overdue plans, high risk without a plan, active alerts, public report stats). Every tile, chip and public number matched.

| # | Gap found | Fix |
|---|---|---|
| 1 | Three places defined "CAP overdue" differently (tab badge, management PDF, alerts counted authorities with no plan; Overview and CAP table did not). Same authority could be overdue in one screen and not in another | One rule everywhere: no plan means no deadline, so never overdue. Tab badge, PDF and the back-end alert scan now use it. Tests added |
| 2 | Saving "No CAP" with a deadline kept the deadline, which then raised "CAP overdue" alerts for a plan that did not exist | Server clears the deadline when status is none; the deadline box is disabled for "none" |
| 3 | Moving a deadline left no audit trace (only the status was recorded) | Audit entries now include the deadline, old and new |
| 4 | Narrow filters (arriving from an Overview tile) could not be cleared except one by one; an empty list gave no way out | "Clear filters" on the Reports and CAP tabs, and the empty message points to it |
| 5 | Tab badges were bare numbers | Hover text says what each counts |
| 6 | Overview showed zeros and "Nothing is urgent" while still loading | Tiles show an ellipsis and the list says Loading until data arrives |
| 7 | Audit log tab stayed stale after saving a report status | Background refresh now includes the audit log, and runs right after a report save |
| 8 | "Active alerts" tile did not scroll to the alert list in some browsers (smooth scroll) | Plain scroll |
| 9 | Six public AI endpoints (new "Explain this rating", digests, map summary) had no limit, so anyone could run up the OpenAI bill | Per-visitor-address limit (40 per hour, shared across endpoints; the cached national digest is exempt). Tests added |
| 10 | Dashboard search results hid behind the "Summarise this view" button | Raised the dropdown above the map controls |

Checked and fine: Overview tiles open the right filtered lists and counts match; "Do these first" items open the right report or authority; trending "Why?" works; photo check; report form pre-selection; public tiles equal admin numbers; public report stats match the admin list; no admin-only data on public endpoints.

Not changed on purpose: the scoring history mixes XGBoost and heuristic scores in one forecast (explained to the AI, not yet fixed); one legacy authority still has a deadline with no plan (harmless now, cleared the next time it is saved); the report and slides still quote older test counts.
