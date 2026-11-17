#!/usr/bin/env bash
# Starts everything HydroSentinel needs for the demo on this laptop, then checks it is healthy.
# Safe to run more than once: anything already running is left alone.
#
#   bash docs/a4/start_demo.sh
#
# Why this uses ~/Library/Caches/hydrosentinel-dev and not the repo's own .venv / node_modules:
# the repo lives in the iCloud-synced Documents folder, where those folders are stored in the cloud and
# take an hour to download, so starting from them hangs. The cache folder holds local, ready-to-run copies.

REPO="/Users/malo/Documents/New project/hydrosentinel"
ENV_DIR="$HOME/Library/Caches/hydrosentinel-dev"
PG="/Applications/Postgres.app/Contents/Versions/16/bin"

echo "1/3 PostgreSQL (port 5432)"
if "$PG/pg_isready" -p 5432 >/dev/null 2>&1; then
  echo "    already running"
else
  "$PG/pg_ctl" -D "$HOME/Library/Application Support/Postgres/var-16" -o "-p 5432" -l /tmp/hs_pg.log start >/dev/null 2>&1
  sleep 3
fi

echo "2/3 Backend API (port 8000)"
if curl -s -m2 -o /dev/null http://localhost:8000/wsa; then
  echo "    already running"
else
  if [ ! -x "$ENV_DIR/venv/bin/uvicorn" ]; then
    echo "    MISSING: $ENV_DIR/venv. Rebuild it with:"
    echo "      python3 -m venv $ENV_DIR/venv && $ENV_DIR/venv/bin/pip install -r $REPO/backend/requirements.txt"
    exit 1
  fi
  cd "$REPO/backend" || exit 1
  set -a; . ../.env 2>/dev/null; set +a
  # .env points at port 5433 (another Postgres on this laptop); the HydroSentinel data is on 5432
  export DATABASE_URL="${DATABASE_URL/:5433\//:5432/}" FRONTEND_URL=http://localhost:5173 SEED_DEMO_DATA=true
  nohup "$ENV_DIR/venv/bin/uvicorn" main:app --port 8000 > "$ENV_DIR/backend.log" 2>&1 &
fi

echo "3/3 Front end (port 5173)"
if [ ! -d "$ENV_DIR/fe/node_modules" ]; then
  echo "    MISSING: $ENV_DIR/fe. Rebuild it with:"
  echo "      mkdir -p $ENV_DIR/fe && rsync -a --exclude node_modules $REPO/frontend/ $ENV_DIR/fe/ && cd $ENV_DIR/fe && npm ci"
  exit 1
fi
rsync -a "$REPO/frontend/src/" "$ENV_DIR/fe/src/"   # pick up any code changes
if curl -s -m2 -o /dev/null http://localhost:5173; then
  echo "    already running"
else
  cd "$ENV_DIR/fe" || exit 1
  nohup npx vite --port 5173 --host localhost > "$ENV_DIR/vite.log" 2>&1 &
fi

echo "Waiting for the servers..."
for i in $(seq 1 30); do
  api=$(curl -s -m2 -o /dev/null -w "%{http_code}" http://localhost:8000/wsa)
  web=$(curl -s -m2 -o /dev/null -w "%{http_code}" http://localhost:5173)
  [ "$api" = "200" ] && [ "$web" = "200" ] && break
  sleep 2
done

echo
echo "API  http://localhost:8000  -> $api   (want 200)"
echo "App  http://localhost:5173  -> $web   (want 200)"
if [ "$api" = "200" ] && [ "$web" = "200" ]; then
  count=$(curl -s http://localhost:8000/wsa | python3 -c "import sys,json;print(len(json.load(sys.stdin)))" 2>/dev/null)
  echo "Authorities loaded: $count   (want 169)"
  echo "READY. Admin login: admin@hydrosentinel.co.za / admin123"
else
  echo "NOT READY. Look at: tail $ENV_DIR/backend.log   and   tail $ENV_DIR/vite.log"
  exit 1
fi
