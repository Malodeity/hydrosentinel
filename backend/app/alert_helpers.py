from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models


def raise_high_risk_alert(wsa: models.WSA, db: Session) -> None:
    # fire once per WSA — skip if an unacknowledged high-risk alert already exists
    existing = (
        db.query(models.Alert)
        .filter(
            models.Alert.wsa_id == wsa.id,
            models.Alert.alert_type == models.AlertType.risk_level_high,
            models.Alert.acknowledged_at.is_(None),
        )
        .first()
    )
    if existing:
        return

    alert = models.Alert(
        wsa_id=wsa.id,
        alert_type=models.AlertType.risk_level_high,
        message=f"{wsa.name} ({wsa.province}) has been classified as HIGH RISK. Immediate review recommended.",
    )
    db.add(alert)


def raise_report_volume_spike_alert(wsa: models.WSA, db: Session) -> None:
    # trigger when 5+ open reports for this WSA arrive within 24 hours
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_count = (
        db.query(models.CitizenReport)
        .filter(
            models.CitizenReport.wsa_id == wsa.id,
            models.CitizenReport.created_at >= cutoff,
        )
        .count()
    )
    if recent_count < 5:
        return

    existing = (
        db.query(models.Alert)
        .filter(
            models.Alert.wsa_id == wsa.id,
            models.Alert.alert_type == models.AlertType.report_volume_spike,
            models.Alert.acknowledged_at.is_(None),
        )
        .first()
    )
    if existing:
        return

    alert = models.Alert(
        wsa_id=wsa.id,
        alert_type=models.AlertType.report_volume_spike,
        message=(
            f"{wsa.name} has received {recent_count} citizen reports in the last 24 hours. "
            "A service delivery crisis may be developing."
        ),
    )
    db.add(alert)
