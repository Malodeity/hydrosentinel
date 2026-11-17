#!/usr/bin/env bash
# Puts the demo database back to the presentation state. Takes a backup first. Run before every rehearsal and on the day.
#   bash docs/a5/reset_demo.sh
REPO="/Users/malo/Documents/New project/hydrosentinel"
ENV_DIR="$HOME/Library/Caches/hydrosentinel-dev"
PG="/Applications/Postgres.app/Contents/Versions/16/bin"
set -a; . "$REPO/.env" 2>/dev/null; set +a
export DATABASE_URL="${DATABASE_URL/:5433\//:5432/}"
mkdir -p "$ENV_DIR/backups"
BACKUP="$ENV_DIR/backups/hydrosentinel_$(date +%Y%m%d_%H%M%S).sql"
"$PG/pg_dump" "$DATABASE_URL" > "$BACKUP" && echo "backup: $BACKUP" || { echo "backup failed, stopping"; exit 1; }
cd "$REPO/backend" && PYTHONPATH=. SEED_DEMO_DATA=true "$ENV_DIR/venv/bin/python" -m scripts.seed_demo_reports --apply
