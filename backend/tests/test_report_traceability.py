"""Tests for citizen report traceability: reviewed_by, resolved_by, timestamps."""


def _create_report(client, wsa_id: str) -> dict:
    resp = client.post("/reports", data={
        "wsa_id": wsa_id,
        "issue_type": "outage",
        "lat": "-26.2",
        "lng": "28.1",
    })
    assert resp.status_code == 201
    return resp.json()


def test_new_report_has_no_traceability_fields(client, sample_wsa):
    report = _create_report(client, str(sample_wsa.id))
    assert report["reviewed_by"] is None
    assert report["resolved_by"] is None
    assert report["reviewed_at"] is None
    assert report["resolved_at"] is None


def test_moving_to_in_review_sets_reviewed_by(client, auth_headers, admin_user, sample_wsa):
    report = _create_report(client, str(sample_wsa.id))
    resp = client.patch(
        f"/reports/{report['id']}",
        json={"case_status": "in_review", "admin_comment": None},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reviewed_by"] == str(admin_user.id)
    assert data["reviewed_at"] is not None
    assert data["resolved_by"] is None


def test_moving_to_resolved_sets_resolved_by(client, auth_headers, admin_user, sample_wsa):
    report = _create_report(client, str(sample_wsa.id))
    client.patch(
        f"/reports/{report['id']}",
        json={"case_status": "in_review", "admin_comment": None},
        headers=auth_headers,
    )
    resp = client.patch(
        f"/reports/{report['id']}",
        json={"case_status": "resolved", "admin_comment": "Fixed on site."},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["resolved_by"] == str(admin_user.id)
    assert data["resolved_at"] is not None


def test_reviewed_by_not_overwritten_on_subsequent_patch(client, auth_headers, sample_wsa):
    report = _create_report(client, str(sample_wsa.id))
    first = client.patch(
        f"/reports/{report['id']}",
        json={"case_status": "in_review", "admin_comment": None},
        headers=auth_headers,
    ).json()
    original_reviewed_by = first["reviewed_by"]
    original_reviewed_at = first["reviewed_at"]

    # patching again with same status should not reset reviewed_by
    second = client.patch(
        f"/reports/{report['id']}",
        json={"case_status": "in_review", "admin_comment": "Added a note."},
        headers=auth_headers,
    ).json()
    assert second["reviewed_by"] == original_reviewed_by
    assert second["reviewed_at"] == original_reviewed_at


def test_comment_only_change_uses_correct_audit_action(client, auth_headers, sample_wsa, db):
    from app import models

    report = _create_report(client, str(sample_wsa.id))
    client.patch(
        f"/reports/{report['id']}",
        json={"case_status": "open", "admin_comment": "Just a note."},
        headers=auth_headers,
    )
    import uuid
    entry = db.query(models.AuditLog).filter(
        models.AuditLog.record_id == uuid.UUID(report["id"]),
        models.AuditLog.action == models.AuditAction.report_comment_updated,
    ).first()
    assert entry is not None
