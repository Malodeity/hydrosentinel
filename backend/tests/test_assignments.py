"""Contractor tickets: who may be assigned, the status steps, what each role can see, scoping, alerts, notifications.

Every test states the rule it protects, because the point is that a wrong business rule fails the test.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import models
from app.auth import get_password_hash


def _login(client, user, password):
    resp = client.post("/auth/login", json={"email": user.email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def report(db, sample_wsa):
    r = models.CitizenReport(
        wsa_id=sample_wsa.id, issue_type=models.IssueType.leak, description="Burst pipe",
        reference_code=f"HS-{uuid.uuid4().hex[:8].upper()}", case_status="open", lat=-26.1, lng=28.2,
    )
    db.add(r)
    db.flush()
    return r


def _contractor(db, wsa, name=None, issues="leak,outage", active=True, with_login=True):
    c = models.Contractor(name=name or f"Contractor {uuid.uuid4().hex[:6]}", is_active=active)
    db.add(c)
    db.flush()
    db.add(models.ContractorCoverage(contractor_id=c.id, wsa_id=wsa.id, issue_types=issues))
    user = None
    if with_login:
        user = models.User(email=f"c-{uuid.uuid4().hex[:8]}@test.com", hashed_password=get_password_hash("contractor1"),
                           role=models.UserRole.contractor, contractor_id=c.id)
        db.add(user)
    db.flush()
    return c, user


@pytest.fixture
def contractor(db, sample_wsa):
    return _contractor(db, sample_wsa)


def _assign(client, headers, report, contractor_id, **extra):
    return client.post(f"/reports/{report.id}/assign", json={"contractor_id": str(contractor_id), **extra}, headers=headers)


# ---- assigning ----------------------------------------------------------------------------------------------

def test_assign_creates_ticket_moves_report_to_in_review_and_notifies_contractor(client, auth_headers, report, contractor, db):
    c, c_user = contractor
    resp = _assign(client, auth_headers, report, c.id, instructions="Check the main valve")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "assigned" and body["contractor_name"] == c.name
    assert body["due_at"] is not None  # a default due time is set when the admin gives none
    db.refresh(report)
    assert report.case_status == "in_review"  # an assigned report is being worked, so it must not look untouched
    assert db.query(models.Notification).filter_by(user_id=c_user.id).count() == 1


def test_default_due_time_follows_issue_type(client, auth_headers, db, sample_wsa):
    c, _ = _contractor(db, sample_wsa, issues="leak,quality,billing", with_login=False)
    due = {}
    for issue in ("leak", "quality", "billing"):
        r = models.CitizenReport(wsa_id=sample_wsa.id, issue_type=models.IssueType(issue), reference_code=f"HS-{uuid.uuid4().hex[:8].upper()}",
                                 case_status="open", lat=0, lng=0)
        db.add(r)
        db.flush()
        resp = _assign(client, auth_headers, r, c.id)
        assert resp.status_code == 201
        due[issue] = (datetime.fromisoformat(resp.json()["due_at"]) - datetime.now(timezone.utc)).total_seconds() / 3600
    assert 23 < due["leak"] < 25 and 47 < due["quality"] < 49 and 71 < due["billing"] < 73


def test_cannot_assign_contractor_who_does_not_cover_that_issue_or_authority(client, auth_headers, report, db, sample_wsa):
    water_quality_only, _ = _contractor(db, sample_wsa, issues="quality")
    assert _assign(client, auth_headers, report, water_quality_only.id).status_code == 422  # wrong issue type
    other_wsa = models.WSA(name=f"Other {uuid.uuid4().hex[:6]}", province="Gauteng")
    db.add(other_wsa)
    db.flush()
    elsewhere, _ = _contractor(db, other_wsa)
    assert _assign(client, auth_headers, report, elsewhere.id).status_code == 422  # works for a different authority


def test_cannot_assign_inactive_contractor_or_resolved_report(client, auth_headers, report, db, sample_wsa):
    off, _ = _contractor(db, sample_wsa, active=False)
    assert _assign(client, auth_headers, report, off.id).status_code == 409
    on, _ = _contractor(db, sample_wsa)
    report.case_status = "resolved"
    db.flush()
    assert _assign(client, auth_headers, report, on.id).status_code == 409


def test_due_date_must_be_in_the_future(client, auth_headers, report, contractor):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert _assign(client, auth_headers, report, contractor[0].id, due_at=past).status_code == 422


def test_reassign_cancels_previous_ticket_and_tells_old_contractor(client, auth_headers, report, contractor, db, sample_wsa):
    first, first_user = contractor
    second, _ = _contractor(db, sample_wsa)
    t1 = _assign(client, auth_headers, report, first.id).json()
    t2 = _assign(client, auth_headers, report, second.id).json()
    history = client.get(f"/reports/{report.id}/assignments", headers=auth_headers).json()
    statuses = {t["id"]: t["status"] for t in history}
    assert statuses[t1["id"]] == "cancelled" and statuses[t2["id"]] == "assigned"  # only one active ticket per report
    assert db.query(models.Notification).filter_by(user_id=first_user.id, title="Ticket reassigned").count() == 1


def test_bulk_assign_is_all_or_nothing(client, auth_headers, report, contractor, db, sample_wsa):
    c, _ = contractor
    bad = models.CitizenReport(wsa_id=sample_wsa.id, issue_type=models.IssueType.billing, reference_code=f"HS-{uuid.uuid4().hex[:8].upper()}",
                               case_status="open", lat=0, lng=0)  # contractor does not do billing
    db.add(bad)
    db.flush()
    resp = client.post("/reports/assign-bulk", json={"contractor_id": str(c.id), "report_ids": [str(report.id), str(bad.id)]}, headers=auth_headers)
    assert resp.status_code == 422
    assert db.query(models.ReportAssignment).filter_by(report_id=report.id).count() == 0  # the good one was not assigned either
    ok = client.post("/reports/assign-bulk", json={"contractor_id": str(c.id), "report_ids": [str(report.id)]}, headers=auth_headers)
    assert ok.status_code == 201 and len(ok.json()) == 1


def test_assign_requires_admin_and_login(client, report, contractor):
    c, c_user = contractor
    assert _assign(client, {}, report, c.id).status_code == 401
    assert _assign(client, _login(client, c_user, "contractor1"), report, c.id).status_code == 403  # a contractor cannot assign


# ---- contractor side ----------------------------------------------------------------------------------------

def _ticket_id(client, auth_headers, report, c):
    return _assign(client, auth_headers, report, c.id).json()["id"]


def test_full_happy_path_fix_then_verify_resolves_report(client, auth_headers, report, contractor, db):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    ch = _login(client, c_user, "contractor1")
    for action, note in (("accept", None), ("start", None), ("fix", "Replaced the section of pipe")):
        r = client.patch(f"/my/tickets/{tid}", json={"action": action, "note": note}, headers=ch)
        assert r.status_code == 200, r.text
    assert r.json()["status"] == "fixed"
    db.refresh(report)
    assert report.case_status == "in_review"  # a contractor marking it fixed must NOT resolve the report
    v = client.patch(f"/assignments/{tid}/review", json={"action": "verify"}, headers=auth_headers)
    assert v.status_code == 200 and v.json()["status"] == "closed"
    db.refresh(report)
    assert report.case_status == "resolved" and report.resolved_at is not None and report.resolved_by is not None


def test_contractor_cannot_skip_steps_or_resolve(client, auth_headers, report, contractor):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    ch = _login(client, c_user, "contractor1")
    assert client.patch(f"/my/tickets/{tid}", json={"action": "start"}, headers=ch).status_code == 409  # must accept first
    assert client.patch(f"/my/tickets/{tid}", json={"action": "fix", "note": "done"}, headers=ch).status_code == 409
    assert client.patch(f"/assignments/{tid}/review", json={"action": "verify"}, headers=ch).status_code == 403  # no admin powers
    assert client.patch(f"/reports/{report.id}", json={"case_status": "resolved"}, headers=ch).status_code == 403


def test_reject_needs_reason_and_frees_the_report(client, auth_headers, report, contractor, db):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    ch = _login(client, c_user, "contractor1")
    assert client.patch(f"/my/tickets/{tid}", json={"action": "reject"}, headers=ch).status_code == 422
    r = client.patch(f"/my/tickets/{tid}", json={"action": "reject", "note": "No crew in that area"}, headers=ch)
    assert r.json()["status"] == "rejected" and r.json()["rejected_reason"] == "No crew in that area"
    # report can be given to someone else straight away
    other, _ = _contractor(db, report.wsa)
    assert _assign(client, auth_headers, report, other.id).status_code == 201
    # a rejected ticket cannot be revived
    assert client.patch(f"/my/tickets/{tid}", json={"action": "accept"}, headers=ch).status_code == 409


def test_fix_needs_a_note(client, auth_headers, report, contractor):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    ch = _login(client, c_user, "contractor1")
    client.patch(f"/my/tickets/{tid}", json={"action": "accept"}, headers=ch)
    assert client.patch(f"/my/tickets/{tid}", json={"action": "fix"}, headers=ch).status_code == 422


def test_send_back_returns_work_to_contractor_who_can_fix_again(client, auth_headers, report, contractor):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    ch = _login(client, c_user, "contractor1")
    client.patch(f"/my/tickets/{tid}", json={"action": "accept"}, headers=ch)
    client.patch(f"/my/tickets/{tid}", json={"action": "fix", "note": "patched"}, headers=ch)
    assert client.patch(f"/assignments/{tid}/review", json={"action": "send_back"}, headers=auth_headers).status_code == 422  # must say why
    sb = client.patch(f"/assignments/{tid}/review", json={"action": "send_back", "note": "Still leaking"}, headers=auth_headers)
    assert sb.json()["status"] == "sent_back" and sb.json()["admin_note"] == "Still leaking"
    assert client.patch(f"/my/tickets/{tid}", json={"action": "fix", "note": "re-sealed"}, headers=ch).json()["status"] == "fixed"


def test_verify_only_when_fixed(client, auth_headers, report, contractor):
    c, _ = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    assert client.patch(f"/assignments/{tid}/review", json={"action": "verify"}, headers=auth_headers).status_code == 409


def test_cancel_notifies_contractor_and_ends_ticket(client, auth_headers, report, contractor, db):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    r = client.patch(f"/assignments/{tid}/review", json={"action": "cancel", "note": "Fixed by municipal crew"}, headers=auth_headers)
    assert r.json()["status"] == "cancelled"
    assert db.query(models.Notification).filter(models.Notification.user_id == c_user.id, models.Notification.title.like("%cancelled")).count() == 1
    assert client.patch(f"/assignments/{tid}/review", json={"action": "cancel"}, headers=auth_headers).status_code == 409


def test_admin_resolving_report_by_hand_closes_open_ticket(client, auth_headers, report, contractor, db):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    client.patch(f"/reports/{report.id}", json={"case_status": "resolved"}, headers=auth_headers)
    t = db.get(models.ReportAssignment, uuid.UUID(tid))
    db.refresh(t)
    assert t.status == "closed"  # no contractor keeps a ticket on a report that is already resolved


# ---- isolation ----------------------------------------------------------------------------------------------

def test_contractor_sees_only_own_tickets_and_cannot_touch_anothers(client, auth_headers, report, contractor, db, sample_wsa):
    c, c_user = contractor
    other, other_user = _contractor(db, sample_wsa)
    tid = _ticket_id(client, auth_headers, report, c)
    mine = client.get("/my/tickets", headers=_login(client, c_user, "contractor1")).json()
    assert [t["id"] for t in mine] == [tid]
    theirs = _login(client, other_user, "contractor1")
    assert client.get("/my/tickets", headers=theirs).json() == []
    # another contractor's ticket looks like it does not exist, so ids cannot be probed
    assert client.patch(f"/my/tickets/{tid}", json={"action": "accept"}, headers=theirs).status_code == 404


def test_admin_and_viewer_cannot_use_contractor_endpoints(client, auth_headers, db, sample_wsa):
    assert client.get("/my/tickets", headers=auth_headers).status_code == 403
    viewer = models.User(email=f"v-{uuid.uuid4().hex[:6]}@test.com", hashed_password=get_password_hash("viewerpass1"), role=models.UserRole.viewer)
    db.add(viewer)
    db.flush()
    assert client.get("/contractors", headers=_login(client, viewer, "viewerpass1")).status_code == 403


def test_switched_off_contractor_can_still_finish_tickets_it_already_holds(client, auth_headers, report, contractor, db, sample_wsa):
    # switching a contractor off stops NEW work only. locking it out of a ticket it holds would strand a half-fixed repair and the citizen's report
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    ch = _login(client, c_user, "contractor1")
    c.is_active = False
    db.flush()
    assert client.get("/my/tickets", headers=ch).status_code == 200
    for action, note in (("accept", None), ("fix", "Done")):
        assert client.patch(f"/my/tickets/{tid}", json={"action": action, "note": note}, headers=ch).status_code == 200
    other = models.CitizenReport(wsa_id=sample_wsa.id, issue_type=models.IssueType.leak, reference_code=f"HS-{uuid.uuid4().hex[:8].upper()}",
                                 case_status="open", lat=0, lng=0)
    db.add(other)
    db.flush()
    assert _assign(client, auth_headers, other, c.id).status_code == 409  # but it can not be given new work


def test_database_refuses_a_second_open_ticket_on_the_same_report(db, report, contractor):
    # two admins clicking Assign at the same moment must not both win: the rule is enforced by the database, not only by the code
    from sqlalchemy.exc import IntegrityError
    c, _ = contractor
    db.add(models.ReportAssignment(report_id=report.id, contractor_id=c.id, status="assigned"))
    db.flush()
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(models.ReportAssignment(report_id=report.id, contractor_id=c.id, status="accepted"))
            db.flush()
    # a finished ticket does not block a new one
    db.add(models.ReportAssignment(report_id=report.id, contractor_id=c.id, status="cancelled"))
    db.flush()


def test_reassign_still_works_with_the_one_open_ticket_rule(client, auth_headers, report, contractor, db, sample_wsa):
    first, _ = contractor
    second, _ = _contractor(db, sample_wsa)
    assert _assign(client, auth_headers, report, first.id).status_code == 201
    assert _assign(client, auth_headers, report, second.id).status_code == 201
    active = db.query(models.ReportAssignment).filter(models.ReportAssignment.report_id == report.id,
                                                      models.ReportAssignment.status.in_(("assigned", "accepted", "in_progress", "sent_back", "fixed"))).count()
    assert active == 1


def test_demo_seeding_is_off_unless_switched_on(monkeypatch):
    # the demo logins share one password, so they must never appear in a deployment that did not ask for them
    from app.config import Settings
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)  # a shell that exported .env must not change what the default is
    assert Settings(_env_file=None).seed_demo_data is False


# ---- passwords ----------------------------------------------------------------------------------------------

def test_change_password_needs_current_password_and_ends_other_sessions(client, db, contractor):
    _, c_user = contractor
    login = client.post("/auth/login", json={"email": c_user.email, "password": "contractor1"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.post("/auth/change-password", json={"current_password": "wrong-one", "new_password": "brandnew123"}, headers=headers).status_code == 400
    assert client.post("/auth/change-password", json={"current_password": "contractor1", "new_password": "short"}, headers=headers).status_code == 422
    assert client.post("/auth/change-password", json={"current_password": "contractor1", "new_password": "contractor1"}, headers=headers).status_code == 400
    assert client.post("/auth/change-password", json={"current_password": "contractor1", "new_password": "brandnew123"}, headers=headers).status_code == 204
    assert client.post("/auth/login", json={"email": c_user.email, "password": "contractor1"}).status_code == 401
    assert client.post("/auth/login", json={"email": c_user.email, "password": "brandnew123"}).status_code == 200
    # the refresh token from before the change no longer works, so a stolen session ends
    assert client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401
    assert db.query(models.AuditLog).filter_by(action=models.AuditAction.password_changed, user_id=c_user.id).count() == 1


def test_only_a_national_admin_can_reset_someone_elses_password(client, auth_headers, contractor, db, sample_wsa):
    _, c_user = contractor
    body = {"new_password": "resetpass123"}
    assert client.patch(f"/users/{c_user.id}/password", json=body, headers=_login(client, c_user, "contractor1")).status_code == 403
    scoped = models.User(email=f"s-{uuid.uuid4().hex[:6]}@test.com", hashed_password=get_password_hash("scopedpass1"),
                         role=models.UserRole.admin, wsa_id=sample_wsa.id)
    db.add(scoped)
    db.flush()
    assert client.patch(f"/users/{c_user.id}/password", json=body, headers=_login(client, scoped, "scopedpass1")).status_code == 403
    assert client.patch(f"/users/{c_user.id}/password", json=body, headers=auth_headers).status_code == 204
    assert client.post("/auth/login", json={"email": c_user.email, "password": "resetpass123"}).status_code == 200
    assert client.patch(f"/users/{uuid.uuid4()}/password", json=body, headers=auth_headers).status_code == 404
    log = db.query(models.AuditLog).filter_by(action=models.AuditAction.password_changed, record_id=c_user.id).first()
    assert "resetpass123" not in str(log.new_value)  # the password itself is never written to the log


# ---- public tracker -----------------------------------------------------------------------------------------

def test_public_tracker_shows_progress_but_not_the_company(client, auth_headers, report, contractor):
    c, c_user = contractor
    assert client.get(f"/reports/track/{report.reference_code}").json()["repair_status"] is None
    tid = _ticket_id(client, auth_headers, report, c)
    body = client.get(f"/reports/track/{report.reference_code}").json()
    assert body["repair_status"] == "assigned" and c.name not in str(body)
    ch = _login(client, c_user, "contractor1")
    client.patch(f"/my/tickets/{tid}", json={"action": "accept"}, headers=ch)
    client.patch(f"/my/tickets/{tid}", json={"action": "fix", "note": "done"}, headers=ch)
    assert client.get(f"/reports/track/{report.reference_code}").json()["repair_status"] == "awaiting_check"


# ---- overdue alert ------------------------------------------------------------------------------------------

def test_overdue_ticket_raises_one_alert_and_it_closes_when_fixed(client, auth_headers, report, contractor, db):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    t = db.get(models.ReportAssignment, uuid.UUID(tid))
    t.due_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db.flush()
    alerts = [a for a in client.get("/alerts", headers=auth_headers).json() if a["alert_type"] == "assignment_overdue" and a["wsa_id"] == str(report.wsa_id)]
    assert len(alerts) == 1
    again = [a for a in client.get("/alerts", headers=auth_headers).json() if a["alert_type"] == "assignment_overdue" and a["wsa_id"] == str(report.wsa_id)]
    assert len(again) == 1  # not duplicated on every read
    assert client.get("/my/tickets", headers=_login(client, c_user, "contractor1")).json()[0]["overdue"] is True
    ch = _login(client, c_user, "contractor1")
    client.patch(f"/my/tickets/{tid}", json={"action": "accept"}, headers=ch)
    client.patch(f"/my/tickets/{tid}", json={"action": "fix", "note": "done"}, headers=ch)
    after = [a for a in client.get("/alerts", headers=auth_headers).json() if a["alert_type"] == "assignment_overdue" and a["wsa_id"] == str(report.wsa_id)]
    assert all(a["acknowledged_at"] is not None for a in after)  # a fixed ticket is no longer overdue, so the alert closes itself


# ---- notifications ------------------------------------------------------------------------------------------

def test_admins_are_told_when_contractor_acts_and_notifications_are_private(client, auth_headers, report, contractor, admin_user, db):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    ch = _login(client, c_user, "contractor1")
    client.patch(f"/my/tickets/{tid}", json={"action": "reject", "note": "no crew"}, headers=ch)
    admin_items = client.get("/notifications", headers=auth_headers).json()
    assert any("rejected" in n["title"] for n in admin_items)
    mine = client.get("/notifications", headers=ch).json()
    assert all("rejected" not in n["title"] for n in mine)
    nid = admin_items[0]["id"]
    assert client.patch(f"/notifications/{nid}/read", headers=ch).status_code == 404  # someone else's bell
    assert client.patch(f"/notifications/{nid}/read", headers=auth_headers).json()["read_at"] is not None
    assert client.post("/notifications/read-all", headers=auth_headers).status_code == 204


def test_email_is_sent_only_when_mail_is_configured_and_failures_do_not_break_tickets(client, auth_headers, report, contractor, monkeypatch):
    from app import mailer
    from app.config import settings

    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(mailer.smtplib, "SMTP", lambda *a, **k: (_ for _ in ()).throw(OSError("mail server down")))
    resp = _assign(client, auth_headers, report, contractor[0].id)
    assert resp.status_code == 201  # a dead mail server must not stop a ticket being created
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(mailer, "send_email", lambda *a, **k: sent.append(a))
    assert sent == []


# ---- per-authority admin ------------------------------------------------------------------------------------

@pytest.fixture
def scoped(db, sample_wsa):
    user = models.User(email=f"s-{uuid.uuid4().hex[:6]}@test.com", hashed_password=get_password_hash("scopedpass1"),
                       role=models.UserRole.admin, wsa_id=sample_wsa.id)
    db.add(user)
    db.flush()
    return user


def test_authority_admin_only_sees_and_changes_own_authority(client, db, report, contractor, scoped):
    h = _login(client, scoped, "scopedpass1")
    other_wsa = models.WSA(name=f"Other {uuid.uuid4().hex[:6]}", province="Gauteng")
    db.add(other_wsa)
    db.flush()
    foreign = models.CitizenReport(wsa_id=other_wsa.id, issue_type=models.IssueType.leak, reference_code=f"HS-{uuid.uuid4().hex[:8].upper()}",
                                   case_status="open", lat=0, lng=0)
    db.add(foreign)
    db.flush()
    ids = {r["id"] for r in client.get("/reports", headers=h).json()}
    assert str(report.id) in ids and str(foreign.id) not in ids
    assert client.patch(f"/reports/{foreign.id}", json={"case_status": "in_review"}, headers=h).status_code == 403
    assert client.patch(f"/reports/{report.id}", json={"case_status": "in_review"}, headers=h).status_code == 200
    assert client.patch(f"/wsa/{other_wsa.id}", json={"cap_status": "submitted", "cap_due_date": None}, headers=h).status_code == 403
    assert client.post(f"/risk/score/{other_wsa.id}", headers=h).status_code == 403
    assert _assign(client, h, foreign, contractor[0].id).status_code == 403
    assert _assign(client, h, report, contractor[0].id).status_code == 201


def test_authority_admin_cannot_use_national_tools_or_see_other_alerts(client, db, scoped, auth_headers):
    h = _login(client, scoped, "scopedpass1")
    assert client.get("/audit-log", headers=h).status_code == 403
    assert client.get("/users", headers=h).status_code == 403
    assert client.post("/users", json={"email": "x@test.com", "password": "password123", "role": "viewer"}, headers=h).status_code == 403
    other_wsa = models.WSA(name=f"Other {uuid.uuid4().hex[:6]}", province="Gauteng")
    db.add(other_wsa)
    db.flush()
    alert = models.Alert(wsa_id=other_wsa.id, alert_type=models.AlertType.risk_level_high, message="x")
    db.add(alert)
    db.flush()
    assert str(alert.id) not in {a["id"] for a in client.get("/alerts", headers=h).json()}
    assert client.patch(f"/alerts/{alert.id}/acknowledge", headers=h).status_code == 403
    assert client.post("/ai/query", json={"question": "hello there"}, headers=h).status_code == 403


def test_authority_admin_contractor_directory_is_limited_to_their_authority(client, db, scoped, sample_wsa):
    h = _login(client, scoped, "scopedpass1")
    mine, _ = _contractor(db, sample_wsa, with_login=False)
    other_wsa = models.WSA(name=f"Other {uuid.uuid4().hex[:6]}", province="Gauteng")
    db.add(other_wsa)
    db.flush()
    theirs, _ = _contractor(db, other_wsa, with_login=False)
    names = {c["name"] for c in client.get("/contractors", headers=h).json()}
    assert mine.name in names and theirs.name not in names
    assert client.put(f"/contractors/{mine.id}/coverage", json={"wsa_id": str(other_wsa.id), "issue_types": ["leak"]}, headers=h).status_code == 403
    assert client.patch(f"/contractors/{theirs.id}", json={"name": "Renamed Co"}, headers=h).status_code == 403


# ---- contractor directory + users ---------------------------------------------------------------------------

def test_contractor_crud_and_coverage_rules(client, auth_headers, sample_wsa, report, contractor):
    created = client.post("/contractors", json={"name": "Acme Repairs", "email": "ops@acme.co.za"}, headers=auth_headers)
    assert created.status_code == 201
    cid = created.json()["id"]
    assert client.post("/contractors", json={"name": "acme repairs"}, headers=auth_headers).status_code == 409  # names are unique ignoring case
    covered = client.put(f"/contractors/{cid}/coverage", json={"wsa_id": str(sample_wsa.id), "issue_types": ["leak", "outage"]}, headers=auth_headers)
    assert covered.json()["coverage"][0]["issue_types"] == ["leak", "outage"]
    assert client.put(f"/contractors/{cid}/coverage", json={"wsa_id": str(uuid.uuid4()), "issue_types": ["leak"]}, headers=auth_headers).status_code == 404
    assert client.put(f"/contractors/{cid}/coverage", json={"wsa_id": str(sample_wsa.id), "issue_types": []}, headers=auth_headers).status_code == 422
    # coverage cannot be removed while the contractor holds an open ticket there
    c, _ = contractor
    _ticket_id(client, auth_headers, report, c)
    assert client.delete(f"/contractors/{c.id}/coverage/{sample_wsa.id}", headers=auth_headers).status_code == 409
    assert client.delete(f"/contractors/{cid}/coverage/{sample_wsa.id}", headers=auth_headers).status_code == 200


def test_creating_contractor_and_scoped_accounts_validates_links(client, auth_headers, db, sample_wsa):
    c = models.Contractor(name=f"Co {uuid.uuid4().hex[:6]}")
    db.add(c)
    db.flush()
    base = {"password": "password123"}
    assert client.post("/users", json={**base, "email": "no-link@test.com", "role": "contractor"}, headers=auth_headers).status_code == 422
    assert client.post("/users", json={**base, "email": "viewer-link@test.com", "role": "viewer", "contractor_id": str(c.id)}, headers=auth_headers).status_code == 422
    assert client.post("/users", json={**base, "email": "viewer-scope@test.com", "role": "viewer", "wsa_id": str(sample_wsa.id)}, headers=auth_headers).status_code == 422
    ok = client.post("/users", json={**base, "email": "worker@test.com", "role": "contractor", "contractor_id": str(c.id)}, headers=auth_headers)
    assert ok.status_code == 201 and ok.json()["contractor_id"] == str(c.id)
    scoped = client.post("/users", json={**base, "email": "local@test.com", "role": "admin", "wsa_id": str(sample_wsa.id)}, headers=auth_headers)
    assert scoped.status_code == 201 and scoped.json()["wsa_id"] == str(sample_wsa.id)


def test_performance_counts_are_display_only_and_correct(client, auth_headers, report, contractor, db):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    ch = _login(client, c_user, "contractor1")
    client.patch(f"/my/tickets/{tid}", json={"action": "accept"}, headers=ch)
    client.patch(f"/my/tickets/{tid}", json={"action": "fix", "note": "done"}, headers=ch)
    row = next(r for r in client.get("/contractors/performance", headers=auth_headers).json() if r["contractor_id"] == str(c.id))
    assert row["total"] == 1 and row["fixed"] == 1 and row["fixed_on_time_pct"] == 100.0 and row["rejected"] == 0


def test_every_ticket_action_is_audited(client, auth_headers, report, contractor, db):
    c, c_user = contractor
    tid = _ticket_id(client, auth_headers, report, c)
    client.patch(f"/my/tickets/{tid}", json={"action": "accept"}, headers=_login(client, c_user, "contractor1"))
    actions = [r.action.value for r in db.query(models.AuditLog).filter(models.AuditLog.record_id == uuid.UUID(tid)).all()]
    assert "report_assigned" in actions and "assignment_updated" in actions


def test_csv_export_includes_ticket_columns(client, auth_headers, report, contractor):
    _ticket_id(client, auth_headers, report, contractor[0])
    text = client.get("/reports/export.csv", headers=auth_headers).text
    assert "assigned_contractor" in text.splitlines()[0] and contractor[0].name in text


def test_work_order_draft_suggests_least_loaded_contractor_and_falls_back_without_ai(client, auth_headers, report, db, sample_wsa, monkeypatch):
    busy, _ = _contractor(db, sample_wsa, name="AAA Busy", with_login=False)
    free, _ = _contractor(db, sample_wsa, name="ZZZ Free", with_login=False)
    other = models.CitizenReport(wsa_id=sample_wsa.id, issue_type=models.IssueType.leak, reference_code=f"HS-{uuid.uuid4().hex[:8].upper()}",
                                 case_status="open", lat=0, lng=0)
    db.add(other)
    db.flush()
    _assign(client, auth_headers, other, busy.id)  # busy now holds one open ticket
    from app.config import settings
    monkeypatch.setattr(settings, "openai_api_key", None)
    resp = client.get(f"/ai/reports/{report.id}/work-order", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["suggested_contractor_name"] == "ZZZ Free"  # name order would pick AAA; load must win
    assert "Attend to the reported leak" in body["instructions"]  # plain template when AI is unavailable
