"""Tests for audit log entries: CAP change, report status change, risk score run."""
from app import models


def test_cap_status_change_writes_audit_entry(client, auth_headers, sample_wsa, db):
    resp = client.patch(
        f"/wsa/{sample_wsa.id}",
        json={"cap_status": "submitted"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    entry = db.query(models.AuditLog).filter(
        models.AuditLog.record_id == sample_wsa.id
    ).first()
    assert entry is not None
    assert entry.action == models.AuditAction.cap_status_updated
    assert entry.table_name == "wsa"
    assert entry.old_value == {"cap_status": "none"}
    assert entry.new_value == {"cap_status": "submitted"}


def test_audit_entry_contains_actor(client, auth_headers, admin_user, sample_wsa, db):
    client.patch(f"/wsa/{sample_wsa.id}", json={"cap_status": "in_progress"}, headers=auth_headers)
    entry = db.query(models.AuditLog).filter(models.AuditLog.record_id == sample_wsa.id).first()
    assert entry.user_id == admin_user.id


def test_report_status_update_writes_audit_entry(client, auth_headers, sample_wsa, db):
    # create a report first
    create_resp = client.post("/reports", data={
        "wsa_id": str(sample_wsa.id),
        "issue_type": "leak",
        "lat": "-26.2",
        "lng": "28.1",
    })
    assert create_resp.status_code == 201
    report_id = create_resp.json()["id"]

    client.patch(
        f"/reports/{report_id}",
        json={"case_status": "in_review", "admin_comment": None},
        headers=auth_headers,
    )

    entry = db.query(models.AuditLog).filter(
        models.AuditLog.record_id == report_id
    ).first()
    assert entry is not None
    assert entry.action == models.AuditAction.report_status_updated
    assert entry.old_value["case_status"] == "open"
    assert entry.new_value["case_status"] == "in_review"


def test_risk_score_run_writes_audit_entry(client, auth_headers, sample_wsa, db):
    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)

    entry = db.query(models.AuditLog).filter(
        models.AuditLog.record_id == sample_wsa.id,
        models.AuditLog.action == models.AuditAction.risk_score_run,
    ).first()
    assert entry is not None
    assert "risk_level" in entry.old_value
    assert "probability" in entry.new_value


def test_get_audit_log_endpoint(client, auth_headers, sample_wsa):
    client.patch(f"/wsa/{sample_wsa.id}", json={"cap_status": "completed"}, headers=auth_headers)
    resp = client.get("/audit-log", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_audit_log_filter_by_record(client, auth_headers, sample_wsa):
    client.patch(f"/wsa/{sample_wsa.id}", json={"cap_status": "submitted"}, headers=auth_headers)
    resp = client.get(f"/audit-log?record_id={sample_wsa.id}", headers=auth_headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert all(e["record_id"] == str(sample_wsa.id) for e in entries)


def test_audit_log_requires_admin(client, sample_wsa):
    resp = client.get("/audit-log")
    assert resp.status_code == 401
