"""
Run POST /risk/score/{wsa_id} for every WSA to populate risk_score_history
and update risk_level on all WSA rows.

Usage:
    cd backend
    PYTHONPATH=. .venv/bin/python scripts/bulk_risk_score.py

Requires a running backend server (http://localhost:8000) with valid ADMIN_EMAIL/ADMIN_PASSWORD.
"""
import os
import sys

import requests

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
EMAIL = os.getenv("ADMIN_EMAIL", "admin@hydrosentinel.local")
PASSWORD = os.getenv("ADMIN_PASSWORD", "")


def main() -> None:
    # log in
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=10)
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # fetch all WSAs
    wsas = requests.get(f"{BASE_URL}/wsa", timeout=10).json()
    print(f"Scoring {len(wsas)} WSAs…")

    ok = failed = 0
    for wsa in wsas:
        r = requests.post(f"{BASE_URL}/risk/score/{wsa['id']}", headers=headers, timeout=10)
        if r.status_code == 200:
            result = r.json()
            print(f"  {wsa['name']}: {result['risk_level']} ({result['probability']:.1%}) [{result.get('model_source', '?')}]")
            ok += 1
        else:
            print(f"  {wsa['name']}: FAILED {r.status_code}", file=sys.stderr)
            failed += 1

    print(f"\nDone — {ok} scored, {failed} failed")


if __name__ == "__main__":
    main()
