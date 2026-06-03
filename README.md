# HydroSentinel

HydroSentinel is a solo student project for monitoring South African water service performance, surfacing citizen issue reports, and scoring municipal risk using a lightweight XGBoost model.

## Stack

- Frontend: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Leaflet, axios
- Backend: FastAPI, SQLAlchemy, PostgreSQL, JWT auth, passlib
- Data and AI: pandas, pdfplumber, scikit-learn, XGBoost, joblib
- Local infrastructure: Docker Compose

## Repository Layout

```text
hydrosentinel/
├── backend/
├── frontend/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Clone And Configure

```bash
git clone <your-repo-url> hydrosentinel
cd hydrosentinel
cp .env.example .env
```

Update `.env` if you want different database credentials, a different JWT secret, or a custom seeded admin account.

## Start The App

```bash
docker compose up --build
```

This starts:

- Frontend on [http://localhost:5173](http://localhost:5173)
- Backend on [http://localhost:8000](http://localhost:8000)
- Swagger docs on [http://localhost:8000/docs](http://localhost:8000/docs)

On first backend startup, the app creates the tables, seeds a default admin account, and inserts 144 starter WSA rows if the database is empty.

## Default Login

If you created the database with the SQL script you shared, use that existing admin record:

```text
Email: admin@hydrosentinel.co.za
Password: the password that matches your inserted bcrypt hash
```

If you let the FastAPI app seed a fresh admin user instead, it uses `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env`.

## Run The ETL

Place Blue Drop and No Drop PDFs inside `backend/data/raw/`, then run:

```bash
docker compose exec backend python etl/run_etl.py
```

The ETL parses available source files, merges the extracted data, and upserts WSA records into PostgreSQL.

## Train The Risk Model Offline

The risk route expects a serialized model at `backend/ai/model.pkl`. Train and save one manually when you have labelled data:

```bash
docker compose exec backend python ai/train.py data/training/wsa_training.csv
```

If `model.pkl` is missing, the API falls back to a deterministic starter heuristic so the demo still works.

## Useful Commands

```bash
docker compose exec backend python -m pip list
docker compose exec backend python etl/run_etl.py
docker compose exec backend python ai/train.py data/training/wsa_training.csv
docker compose down
```

## API Summary

- `GET /wsa` returns all WSAs
- `GET /wsa/{id}` returns one WSA
- `PATCH /wsa/{id}` updates CAP status for admins
- `POST /reports` creates a citizen report
- `GET /reports` lists reports for admins
- `POST /risk/score/{wsa_id}` scores a WSA and writes the risk level back
- `GET /risk/scores` lists current risk scores
- `POST /auth/login` returns a JWT
- `GET /auth/me` returns the current user
