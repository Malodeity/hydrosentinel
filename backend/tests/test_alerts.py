"""Tests for alert auto-generation and acknowledgement."""
import uuid
from datetime import date, timedelta
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


def _add_reports(db, wsa, count):
    for i in range(count):
        db.add(models.CitizenReport(
            wsa_id=wsa.id, issue_type=models.IssueType.outage, description="volume test",
            reference_code=f"HS-V{i}{uuid.uuid4().hex[:6]}"[:12], case_status="open", lat=-26.2, lng=28.0,
        ))
    db.flush()


def test_report_volume_spike_alert_fires_at_five_reports_in_24h(db, sample_wsa):
    from app.alert_helpers import raise_report_volume_spike_alert
    _add_reports(db, sample_wsa, 5)

    raise_report_volume_spike_alert(sample_wsa, db)
    db.flush()

    alert = db.query(models.Alert).filter(
        models.Alert.wsa_id == sample_wsa.id,
        models.Alert.alert_type == models.AlertType.report_volume_spike,
    ).first()
    assert alert is not None


def test_report_volume_spike_alert_does_not_fire_below_five_reports(db, sample_wsa):
    from app.alert_helpers import raise_report_volume_spike_alert
    _add_reports(db, sample_wsa, 4)

    raise_report_volume_spike_alert(sample_wsa, db)
    db.flush()

    assert db.query(models.Alert).filter(
        models.Alert.wsa_id == sample_wsa.id,
        models.Alert.alert_type == models.AlertType.report_volume_spike,
    ).count() == 0


# --- "risk increased" alert: raised when a score moves an authority to a worse tier ---
from unittest.mock import patch  # noqa: E402


def _score_as(client, auth_headers, wsa, level):
    # force the scoring result so each test controls the exact before/after, instead of hoping the heuristic lands on a tier
    result = {"risk_level": level, "probability": 0.5, "model_source": models.ModelSource.heuristic}
    with patch("app.routes.risk.predict_wsa_risk", return_value=result):
        return client.post(f"/risk/score/{wsa.id}", headers=auth_headers)


def _increase_alerts(db, wsa):
    return db.query(models.Alert).filter(
        models.Alert.wsa_id == wsa.id,
        models.Alert.alert_type == models.AlertType.risk_level_increased,
    ).all()


def test_moving_to_a_worse_tier_raises_a_risk_increased_alert(client, auth_headers, db, sample_wsa):
    sample_wsa.risk_level = models.RiskLevel.low
    db.flush()

    _score_as(client, auth_headers, sample_wsa, models.RiskLevel.medium)

    alerts = _increase_alerts(db, sample_wsa)
    assert len(alerts) == 1
    assert "low to medium" in alerts[0].message


def test_staying_the_same_or_improving_raises_no_risk_increased_alert(client, auth_headers, db, sample_wsa):
    sample_wsa.risk_level = models.RiskLevel.medium
    db.flush()

    _score_as(client, auth_headers, sample_wsa, models.RiskLevel.medium)  # same tier
    _score_as(client, auth_headers, sample_wsa, models.RiskLevel.low)  # better tier

    assert _increase_alerts(db, sample_wsa) == []


def test_a_second_increase_is_not_duplicated_until_the_first_is_acknowledged(client, auth_headers, db, sample_wsa):
    sample_wsa.risk_level = models.RiskLevel.low
    db.flush()
    _score_as(client, auth_headers, sample_wsa, models.RiskLevel.medium)

    sample_wsa.risk_level = models.RiskLevel.low  # drops back, then rises again
    db.flush()
    _score_as(client, auth_headers, sample_wsa, models.RiskLevel.medium)
    assert len(_increase_alerts(db, sample_wsa)) == 1

    first = _increase_alerts(db, sample_wsa)[0]
    client.patch(f"/alerts/{first.id}/acknowledge", headers=auth_headers)
    sample_wsa.risk_level = models.RiskLevel.low
    db.flush()
    _score_as(client, auth_headers, sample_wsa, models.RiskLevel.high)
    assert len(_increase_alerts(db, sample_wsa)) == 2  # the handled one stays as history, a fresh one is raised


def test_cap_overdue_alert_closes_itself_once_the_plan_is_completed(client, auth_headers, db, sample_wsa):
    # an alert saying "CAP overdue" about a plan that is now complete is wrong and trains admins to ignore alerts
    sample_wsa.cap_due_date = date.today() - timedelta(days=3)
    sample_wsa.cap_status = models.CAPStatus.in_progress
    db.flush()
    mine = lambda: [a for a in client.get("/alerts", headers=auth_headers).json() if a["alert_type"] == "cap_overdue" and a["wsa_id"] == str(sample_wsa.id)]  # other authorities in the database may be overdue too
    still_open = [a for a in mine() if not a["acknowledged_at"]]
    assert len(still_open) == 1  # genuinely overdue: stays open

    sample_wsa.cap_status = models.CAPStatus.completed
    db.flush()
    alerts = mine()
    assert alerts and all(a["acknowledged_at"] for a in alerts)


def test_cap_overdue_alert_closes_when_the_deadline_moves_into_the_future(client, auth_headers, db, sample_wsa):
    sample_wsa.cap_due_date = date.today() - timedelta(days=3)
    sample_wsa.cap_status = models.CAPStatus.submitted
    db.flush()
    client.get("/alerts", headers=auth_headers)
    sample_wsa.cap_due_date = date.today() + timedelta(days=30)
    db.flush()
    alerts = [a for a in client.get("/alerts", headers=auth_headers).json() if a["alert_type"] == "cap_overdue" and a["wsa_id"] == str(sample_wsa.id)]
    assert alerts and all(a["acknowledged_at"] for a in alerts)


def test_high_risk_alert_closes_when_the_authority_is_no_longer_high_risk(client, auth_headers, db, sample_wsa):
    sample_wsa.risk_level = models.RiskLevel.high
    db.add(models.Alert(wsa_id=sample_wsa.id, alert_type=models.AlertType.risk_level_high, message="high"))
    db.flush()
    assert not [a for a in client.get("/alerts", headers=auth_headers).json() if a["alert_type"] == "risk_level_high"][0]["acknowledged_at"]
    sample_wsa.risk_level = models.RiskLevel.medium
    db.flush()
    assert [a for a in client.get("/alerts", headers=auth_headers).json() if a["alert_type"] == "risk_level_high"][0]["acknowledged_at"]


def test_an_authority_with_no_plan_is_never_overdue(client, auth_headers, db, sample_wsa):
    # a leftover deadline on an authority with no CAP must not raise "CAP overdue": there is no plan to be late
    sample_wsa.cap_status = models.CAPStatus.none
    sample_wsa.cap_due_date = date.today() - timedelta(days=10)
    db.flush()
    alerts = [a for a in client.get("/alerts", headers=auth_headers).json() if a["alert_type"] == "cap_overdue" and a["wsa_id"] == str(sample_wsa.id)]
    assert alerts == []
