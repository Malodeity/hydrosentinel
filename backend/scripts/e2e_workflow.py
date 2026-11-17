"""End-to-end check of the main workflow against a running backend.

Usage: python scripts/e2e_workflow.py [BASE_URL]
Needs ADMIN_EMAIL and ADMIN_PASSWORD in the environment (see .env.example).
Creates one clearly labelled test report. Skips the CAP draft step if OpenAI is not configured.
"""
import os
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")
results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def timed(fn):
    start = time.perf_counter()
    r = fn()
    return r, round((time.perf_counter() - start) * 1000)


with httpx.Client(base_url=BASE, timeout=60) as c:
    wsas = c.get("/wsa").json()
    wsa = next(w for w in wsas if w.get("lat") is not None) if wsas else None
    check("WSAs are seeded", bool(wsas), f"{len(wsas)} rows")

    r, ms = timed(lambda: c.post(
        "/reports",
        data={"wsa_id": wsa["id"], "issue_type": "leak", "description": "E2E TEST report", "lat": "-26.2", "lng": "28.0"},
        files=[("photos", ("t.png", PNG, "image/png")), ("photos", ("t.txt", b"x", "text/plain"))],
    ))
    check("TC-01 submit report with photo", r.status_code == 201, f"{r.status_code} {ms} ms")
    report = r.json()
    check("non-image upload is ignored", len(report.get("photo_urls", [])) == 1, f"{len(report.get('photo_urls', []))} stored")

    r = c.post("/reports", data={"wsa_id": wsa["id"], "issue_type": "bogus", "lat": "0", "lng": "0"})
    check("TC-02 invalid issue_type rejected", r.status_code == 422, str(r.status_code))
    r = c.post("/reports", data={"wsa_id": "00000000-0000-0000-0000-000000000000", "issue_type": "leak", "lat": "0", "lng": "0"})
    check("TC-03 unknown WSA rejected", r.status_code == 404, str(r.status_code))

    r = c.get(f"/reports/track/{report['reference_code']}")
    check("public tracking by reference code", r.status_code == 200 and r.json()["case_status"] == "open")
    check("tracking hides location and description", "lat" not in r.json() and "description" not in r.json())

    check("admin list needs a token", c.get("/reports").status_code == 401)
    r = c.post("/auth/login", json={"email": os.environ["ADMIN_EMAIL"], "password": "wrong-password"})
    check("wrong password rejected", r.status_code == 401, str(r.status_code))
    r = c.post("/auth/login", json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]})
    check("admin login", r.status_code == 200)
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = c.patch(f"/reports/{report['id']}", headers=h, json={"case_status": "in_review", "admin_comment": "E2E triage"})
    check("TC-04 admin triage", r.status_code == 200 and r.json()["reviewed_by"] is not None, str(r.status_code))
    r = c.patch(f"/reports/{report['id']}", headers=h, json={"case_status": "bogus"})
    check("invalid case status rejected", r.status_code == 422, str(r.status_code))

    # the model defers to the heuristic when its confidence is low, so try a few audited WSAs
    scored = [w for w in wsas if w.get("blue_drop_score") is not None][:5]
    for w in scored:
        r, ms = timed(lambda: c.post(f"/risk/score/{w['id']}", headers=h))
        body = r.json()
        if r.status_code == 200 and body["model_source"] == "xgboost":
            break
    check("TC-05 XGBoost risk score", r.status_code == 200 and body["model_source"] == "xgboost",
          f"{w['name']} {body.get('risk_level')} p={body.get('probability')} {ms} ms")

    r, ms = timed(lambda: c.get(f"/ai/wsa/{wsa['id']}/cap-draft", headers=h))
    if r.status_code == 503:
        print("SKIP  CAP draft (no OpenAI key)")
    else:
        items = r.json().get("items", []) if r.status_code == 200 else []
        check("TC-06 GPT-4o CAP draft", r.status_code == 200 and 1 <= len(items) <= 6, f"{r.status_code} {len(items)} items {ms} ms")

    r = c.patch(f"/reports/{report['id']}", headers=h, json={"case_status": "resolved", "admin_comment": "E2E done"})
    check("resolve report", r.status_code == 200 and r.json()["resolved_at"] is not None)
    check("tracking shows resolved", c.get(f"/reports/track/{report['reference_code']}").json()["case_status"] == "resolved")
    r = c.get("/audit-log", headers=h)
    check("audit log records the actions", r.status_code == 200 and len(r.json()) >= 3, f"{len(r.json())} rows")

    # ---- contractor ticket loop: assign -> accept -> start -> fix -> verify (needs the demo contractors, i.e. SEED_DEMO_DATA=true) ----
    password = os.environ.get("DEMO_CONTRACTOR_PASSWORD", "contractor123")
    users = c.get("/users", headers=h).json()
    candidate = None
    for w in wsas:
        if w.get("province") != "Gauteng":
            continue
        for ct in c.get("/contractors", headers=h).json():
            if ct["is_active"] and any(row["wsa_id"] == w["id"] and "leak" in row["issue_types"] for row in ct["coverage"]):
                login = next((u for u in users if u.get("contractor_id") == ct["id"]), None)
                if login:
                    candidate = (w, ct, login)
                    break
        if candidate:
            break
    if not candidate or not password:
        print("SKIP  contractor ticket loop (no demo contractors or DEMO_CONTRACTOR_PASSWORD)")
    else:
        w2, contractor, login = candidate
        r = c.post("/reports", data={"wsa_id": w2["id"], "issue_type": "leak", "description": "E2E TEST ticket", "lat": "-26.2", "lng": "28.0"})
        rep2 = r.json()
        r = c.post(f"/reports/{rep2['id']}/assign", headers=h, json={"contractor_id": contractor["id"], "instructions": "E2E"})
        check("TC-10 admin assigns report to contractor", r.status_code == 201 and r.json()["status"] == "assigned", str(r.status_code))
        ticket = r.json()["id"]
        check("tracker shows repair progress, not the company", "repair_status" in c.get(f"/reports/track/{rep2['reference_code']}").json())
        ch = {"Authorization": "Bearer " + c.post("/auth/login", json={"email": login["email"], "password": password}).json().get("access_token", "")}
        check("contractor sees its ticket", any(t["id"] == ticket for t in c.get("/my/tickets", headers=ch).json()))
        check("TC-12 contractor cannot use admin routes", c.get("/users", headers=ch).status_code == 403)
        r = c.patch(f"/my/tickets/{ticket}", headers=ch, json={"action": "fix", "note": "too early"})
        check("cannot fix before accepting", r.status_code == 409, str(r.status_code))
        for action in ("accept", "start"):
            r = c.patch(f"/my/tickets/{ticket}", headers=ch, json={"action": action})
        r = c.patch(f"/my/tickets/{ticket}", headers=ch, json={"action": "fix"})
        check("TC-14 fix without a note rejected", r.status_code == 422, str(r.status_code))
        r = c.patch(f"/my/tickets/{ticket}", headers=ch, json={"action": "fix", "note": "Replaced the section"})
        check("contractor marks fixed", r.status_code == 200 and r.json()["status"] == "fixed")
        check("fixed does not resolve the report", c.get(f"/reports/track/{rep2['reference_code']}").json()["case_status"] != "resolved")
        r = c.patch(f"/assignments/{ticket}/review", headers=h, json={"action": "verify"})
        check("admin verifies, ticket closes", r.status_code == 200 and r.json()["status"] == "closed")
        check("report is now resolved", c.get(f"/reports/track/{rep2['reference_code']}").json()["case_status"] == "resolved")

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
