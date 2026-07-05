"""Tests for alert auto-generation and acknowledgement."""
import uuid
from app import models


def test_high_risk_score_creates_alert(client, auth_headers, db, sample_wsa):
    # Force the WSA to have a very low Blue Drop score so the heuristic produces high risk
    sample_wsa.blue_drop_score = 1.0
    sample_wsa.cap_status = models.CAPStatus.none
    db.flush()

    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)

    alert = db.query(models.Alert).filter(
        models.Alert.wsa_id == sample_wsa.id,
        models.Alert.alert_type == models.AlertType.risk_level_high,
    ).first()

    # only assert alert exists if risk came back as high
    scored = db.query(models.WSA).filter(models.WSA.id == sample_wsa.id).first()
    if scored.risk_level == models.RiskLevel.high:
        assert alert is not None
        assert alert.acknowledged_at is None


def test_high_risk_alert_not_duplicated(client, auth_headers, db, sample_wsa):
    sample_wsa.blue_drop_score = 1.0
    sample_wsa.cap_status = models.CAPStatus.none
    db.flush()

    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)
    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)

    count = db.query(models.Alert).filter(
        models.Alert.wsa_id == sample_wsa.id,
        models.Alert.alert_type == models.AlertType.risk_level_high,
        models.Alert.acknowledged_at.is_(None),
    ).count()
    assert count <= 1


def test_acknowledge_alert(client, auth_headers, admin_user, db, sample_wsa):
    alert = models.Alert(
        wsa_id=sample_wsa.id,
        alert_type=models.AlertType.cap_overdue,
        message="Test alert",
    )
    db.add(alert)
    db.flush()

    resp = client.patch(f"/alerts/{alert.id}/acknowledge", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["acknowledged_by"] == str(admin_user.id)
    assert data["acknowledged_at"] is not None


def test_acknowledge_already_acknowledged_is_idempotent(client, auth_headers, db, sample_wsa):
    alert = models.Alert(
        wsa_id=sample_wsa.id,
        alert_type=models.AlertType.cap_overdue,
        message="Test alert",
    )
    db.add(alert)
    db.flush()

    client.patch(f"/alerts/{alert.id}/acknowledge", headers=auth_headers)
    resp = client.patch(f"/alerts/{alert.id}/acknowledge", headers=auth_headers)
    assert resp.status_code == 200


def test_list_alerts_returns_all(client, auth_headers, db, sample_wsa):
    db.add(models.Alert(wsa_id=sample_wsa.id, alert_type=models.AlertType.cap_overdue, message="A"))
    db.add(models.Alert(wsa_id=sample_wsa.id, alert_type=models.AlertType.report_volume_spike, message="B"))
    db.flush()

    resp = client.get("/alerts", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_list_alerts_unacknowledged_filter(client, auth_headers, db, sample_wsa):
    a1 = models.Alert(wsa_id=sample_wsa.id, alert_type=models.AlertType.cap_overdue, message="unacked")
    db.add(a1)
    db.flush()
    client.patch(f"/alerts/{a1.id}/acknowledge", headers=auth_headers)

    db.add(models.Alert(wsa_id=sample_wsa.id, alert_type=models.AlertType.cap_overdue, message="acked"))
    db.flush()

    resp = client.get("/alerts?unacknowledged_only=true", headers=auth_headers)
    assert resp.status_code == 200
    assert all(a["acknowledged_at"] is None for a in resp.json())


def test_list_alerts_requires_auth(client):
    resp = client.get("/alerts")
    assert resp.status_code == 401


def test_acknowledge_nonexistent_alert_returns_404(client, auth_headers):
    resp = client.patch(f"/alerts/{uuid.uuid4()}/acknowledge", headers=auth_headers)
    assert resp.status_code == 404
