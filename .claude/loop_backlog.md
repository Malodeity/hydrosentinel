# Loop backlog — HydroSentinel feature build

Status tracked here so each 20-min cron cycle knows what's next.
Update the row when a feature starts/finishes. One feature per cycle.

| # | Feature | Test-first | Status |
|---|---|---|---|
| 1 | WSA province centroid coords (ETL fallback when lat/lng=0.0) | yes | done |
| 2 | Report photo viewer in admin triage | no | done (already built — thumbnail grid at AdminPage.tsx:499-506) |
| 3 | Citizen report reference code + public tracking endpoint | yes | done |
| 4 | CAP due date + overdue alert | yes | done |
| 5 | Risk trend sparkline (frontend, uses existing history data) | no | done |
| 6 | Green Drop score display on WSA card | no | done |
| 7 | Data completeness badge (frontend, null-check existing fields) | no | done |
| 8 | Multi-admin management (create/deactivate users) | yes | pending |
| 9 | CSV export (WSA + reports) | yes | pending |

Statuses: pending / in_progress / done / blocked (note reason)
