"""Response-time measures for the final presentation: median and 95th percentile over repeated calls against a running backend.

Usage: python scripts/measure_performance.py [BASE_URL]      (needs ADMIN_EMAIL / ADMIN_PASSWORD in the environment)
Writes nothing: the output is saved by the caller (docs/a5/evidence/measurements.txt). The test report it creates is labelled and removed from the demo by reset_demo.sh."""
import os
import statistics
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")


def stats(label: str, fn, n: int) -> None:
    times = []
    for _ in range(n):
        start = time.perf_counter()
        r = fn()
        assert r.status_code < 400, (label, r.status_code, r.text[:200])
        times.append((time.perf_counter() - start) * 1000)
    times.sort()
    p95 = times[min(len(times) - 1, int(round(0.95 * len(times))) - 1)]
    print(f"{label}: median {statistics.median(times):.0f} ms, p95 {p95:.0f} ms (n={n})")


with httpx.Client(base_url=BASE, timeout=60) as c:
    wsas = c.get("/wsa").json()
    token = c.post("/auth/login", json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    wsa = next(w for w in wsas if w.get("blue_drop_score") is not None)
    stats(f"GET /wsa ({len(wsas)} rows)", lambda: c.get("/wsa"), 50)
    stats("POST /reports (multipart, one photo)", lambda: c.post("/reports", data={"wsa_id": wsa["id"], "issue_type": "leak", "description": "PERF TEST", "lat": "-26.2", "lng": "28.0"}, files=[("photos", ("t.png", PNG, "image/png"))]), 50)
    stats("GET /reports (admin)", lambda: c.get("/reports", headers=h), 50)
    stats("GET /assignments (admin)", lambda: c.get("/assignments", headers=h), 50)
    stats("POST /risk/score (XGBoost, one WSA)", lambda: c.post(f"/risk/score/{wsa['id']}", headers=h), 20)
    print("labelled WSAs in DB:", sum(1 for w in wsas if w.get("blue_drop_score") is not None))
