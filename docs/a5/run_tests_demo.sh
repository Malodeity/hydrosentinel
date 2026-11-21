#!/usr/bin/env bash
# Shows the testing live in about a minute, for the presentation (Q4.1). Run after start_demo.sh:   bash docs/a5/run_tests_demo.sh
#   1. the end-to-end check: the whole workflow on the running system (27 checks, real database, real GPT-4o when a key is set)
#   2. a fast slice of the automated suite that covers the fixes to the Assignment 4 limitations (AI limit, scheduler, email over SMTP, health, contractor AI)
#   3. the totals of the full suite, from the saved run (the full suite takes about two minutes, so it is not run on stage)
REPO="/Users/malo/Documents/New project/hydrosentinel"
ENV_DIR="$HOME/Library/Caches/hydrosentinel-dev"
PY="$ENV_DIR/venv/bin/python"
cd "$REPO/backend" || exit 1
set -a; . ../.env 2>/dev/null; set +a
export DATABASE_URL="${DATABASE_URL/:5433\//:5432/}"

echo; echo "=== 1. End-to-end on the running system ==="
"$PY" scripts/e2e_workflow.py | sed -e 's/^PASS/  pass/' -e 's/^FAIL/  FAIL/' -e 's/^SKIP/  skip/'
echo; echo "=== 2. Automated tests for the Assignment 4 limitations ==="
"$PY" -m pytest tests/test_ai_rate_limit.py tests/test_scheduler.py tests/test_citizen_email.py tests/test_contractor_ai.py -q -p no:cacheprovider -p no:warnings 2>&1 | tail -3
echo; echo "=== 3. Full suite (saved run, $(date -r "$REPO/docs/a5/evidence/pytest_full.txt" '+%d %b %Y')) ==="
tail -1 "$REPO/docs/a5/evidence/pytest_full.txt" | sed 's/=//g'
grep -E "Tests |Test Files" "$REPO/docs/a5/evidence/vitest_full.txt" | sed 's/^ *//'
echo "TypeScript type check: $(tail -1 "$REPO/docs/a5/evidence/tsc.txt")"
echo
