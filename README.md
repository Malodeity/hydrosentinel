# HydroSentinel

Monitors South African Water Service Authorities (WSAs) and closes the loop from a resident's report to a verified repair.
Residents report leaks, outages, quality and billing problems. Admins triage the reports, hand them to contractors as tickets, and verify the work.
An XGBoost model rates each authority's risk and GPT-4o drafts plans and ticket instructions. **A person always decides.**

ISJ107V Integrated Software Project, Assignment 5 (final system). Student: Malibongwe Mthethwa, 213355813.

## What is in the final system

| Surface | Who | Path |
|---|---|---|
| Public dashboard: map, authority cards, AI digest | everyone | `/` |
| Report a problem, track it by code | residents | `/reports` |
| Admin console: reports, contractors, CAP, risk scoring, alerts, AI assistant, users, audit log | admins (national, or limited to one authority) | `/admin` |
| My tickets: accept, reject, start, mark fixed | contractors | `/tickets` |

Stack: React 18 + TypeScript + Vite + Tailwind + Leaflet; FastAPI + SQLAlchemy + PostgreSQL; XGBoost; OpenAI `gpt-4o`.

## Run it (local, no cloud needed)

Requirements: Python 3.12, Node 20, PostgreSQL 15 or 16.

```bash
git clone <repo-url> hydrosentinel && cd hydrosentinel
cp .env.example .env                      # then edit DATABASE_URL / POSTGRES_PORT, JWT_SECRET_KEY, OPENAI_API_KEY (optional)
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8000     # first start creates the tables, the admin and the 169 authorities
```

```bash
cd frontend && npm ci && npm run dev       # http://localhost:5173
```

Or with Docker: `docker compose up --build` (set `POSTGRES_PORT` in `.env` if 5432 is taken on your machine).

### Demo data
`SEED_DEMO_DATA=true` in `.env` creates the demo contractors and logins at start (21 invented companies split by province, plus one authority-limited admin).
It is **off by default**: the demo logins share one password (`DEMO_CONTRACTOR_PASSWORD`). Leave it off outside a demo.
To load the presentation reports (24 realistic reports across several authorities, tickets at different stages):

```bash
cd backend && PYTHONPATH=. .venv/bin/python -m scripts.seed_demo_reports --apply     # replaces existing reports
```

### Logins (from `.env`)
| Role | Email | Password |
|---|---|---|
| National admin | `ADMIN_EMAIL` | `ADMIN_PASSWORD` |
| Authority admin (Ekurhuleni only) | `ekurhuleni.admin@hydrosentinel.co.za` | `DEMO_CONTRACTOR_PASSWORD` |
| Contractor | `<name>@contractors.hydrosentinel.co.za`, listed on the admin Users tab | `DEMO_CONTRACTOR_PASSWORD` |

Everyone can change their own password (key icon in the header). A national admin can reset anyone's on the Users tab.

### What works without an OpenAI key
Everything except the AI text: the dashboard, reports, tickets, XGBoost scoring and alerts all run. AI buttons return a clear error, and the ticket draft falls back to a plain template.
If `ai/model.pkl` is missing the API uses a rule-based fallback; retrain with `cd backend && PYTHONPATH=. .venv/bin/python ai/train_from_bdrr.py --deploy`.
The DWS audit PDFs (`backend/data/raw/`) are not committed (they are public DWS reports; see `.gitignore`). The regulations question box needs them.

## Tests
```bash
cd backend && .venv/bin/pytest tests/ -q          # 279 backend tests (rolled-back transactions on the real database)
cd frontend && npx vitest run && npx tsc --noEmit # 109 frontend tests, type check
cd backend && python scripts/e2e_workflow.py      # end-to-end against the running system, includes the contractor ticket loop
```

## Final submission material
- `docs/a5/slides/` final slides (HTML and PDF)
- `docs/a5/uml/` UML: `.puml` sources, PNG and SVG renders, `gen_class.py` (class diagram generated from `models.py`), `audit_names.py` and `NAME_AUDIT.md` (every name on a diagram checked against the code)
- `docs/a5/requirements.md`, `docs/a5/test_cases.md`, `docs/a5/evidence/` (saved test output and measurements)
- `docs/a5/reset_demo.sh` puts the database back to the presentation state (takes a backup first)
- Earlier assignments: `docs/a3-*`, `docs/a4/`

## Security notes
Passwords are bcrypt hashes. Access tokens are short-lived JWTs; refresh tokens are stored hashed and rotate on use. Admins can be limited to one authority; a contractor sees only its own tickets (another's returns 404) and can never resolve a report. Every admin and ticket action is written to an immutable audit log.
Known limits: report photos are served by URL; the AI rate limit is per process; email has only been tested against a mock.
