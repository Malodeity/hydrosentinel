"""
Admins set a CAP due date when they assign a corrective action plan. If that
date passes and the CAP still isn't completed, an alert should surface it —
otherwise a stale CAP just sits invisible until someone happens to check.
"""
from datetime import date, timedelta

from app import models
from app.alert_helpers import raise_cap_overdue_alerts


def test_admin_can_set_cap_due_date(client, sample_wsa, auth_headers):
    due = (date.today() + timedelta(days=30)).isoformat()
    resp = client.patch(f"/wsa/{sample_wsa.id}", json={"cap_status": "submitted", "cap_due_date": due}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["cap_due_date"] == due


def test_overdue_cap_raises_alert(db, sample_wsa):
    sample_wsa.cap_status = models.CAPStatus.submitted
    sample_wsa.cap_due_date = date.today() - timedelta(days=5)
    db.add(sample_wsa)
    db.flush()

    raise_cap_overdue_alerts(db)
    db.flush()

    alert = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.cap_overdue)
        .first()
    )
    assert alert is not None
    assert sample_wsa.name in alert.message


def test_completed_cap_past_due_date_does_not_alert(db, sample_wsa):
    sample_wsa.cap_status = models.CAPStatus.completed
    sample_wsa.cap_due_date = date.today() - timedelta(days=5)
    db.add(sample_wsa)
    db.flush()

    raise_cap_overdue_alerts(db)
    db.flush()

    alert = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.cap_overdue)
        .first()
    )
    assert alert is None


def test_future_due_date_does_not_alert(db, sample_wsa):
    sample_wsa.cap_status = models.CAPStatus.submitted
    sample_wsa.cap_due_date = date.today() + timedelta(days=5)
    db.add(sample_wsa)
    db.flush()

    raise_cap_overdue_alerts(db)
    db.flush()

    alert = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.cap_overdue)
        .first()
    )
    assert alert is None


def test_overdue_alert_not_duplicated(db, sample_wsa):
    sample_wsa.cap_status = models.CAPStatus.submitted
    sample_wsa.cap_due_date = date.today() - timedelta(days=5)
    db.add(sample_wsa)
    db.flush()

    raise_cap_overdue_alerts(db)
    raise_cap_overdue_alerts(db)
    db.flush()

    count = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.cap_overdue)
        .count()
    )
    assert count == 1


def test_get_alerts_triggers_overdue_check(client, db, sample_wsa, auth_headers):
    sample_wsa.cap_status = models.CAPStatus.submitted
    sample_wsa.cap_due_date = date.today() - timedelta(days=1)
    db.add(sample_wsa)
    db.commit()

    resp = client.get("/alerts", headers=auth_headers)
    assert resp.status_code == 200
    types = [a["alert_type"] for a in resp.json()]
    assert "cap_overdue" in types
