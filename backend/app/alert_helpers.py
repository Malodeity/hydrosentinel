import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models

_EARTH_RADIUS_KM = 6371.0
_CLUSTER_RADIUS_KM = 2.0
_CLUSTER_WINDOW_HOURS = 6
_CLUSTER_MIN_REPORTS = 3


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    # great-circle distance between two lat/lng points, in kilometers
    lat1_r, lng1_r, lat2_r, lng2_r = map(math.radians, (lat1, lng1, lat2, lng2))
    d_lat = lat2_r - lat1_r
    d_lng = lng2_r - lng1_r
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(d_lng / 2) ** 2
    return _EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


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


def raise_geo_cluster_alert(wsa: models.WSA, new_report: models.CitizenReport, db: Session) -> None:
    # catches a localized incident (e.g. a burst main) fast: 3+ same-issue-type
    # reports within 2km of each other within 6h -- well below the
    # report_volume_spike threshold of 5 reports anywhere in the WSA within 24h
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_CLUSTER_WINDOW_HOURS)
    recent_same_type = (
        db.query(models.CitizenReport)
        .filter(
            models.CitizenReport.wsa_id == wsa.id,
            models.CitizenReport.issue_type == new_report.issue_type,
            models.CitizenReport.created_at >= cutoff,
        )
        .all()
    )

    nearby = [
        r for r in recent_same_type
        if haversine_km(new_report.lat, new_report.lng, r.lat, r.lng) <= _CLUSTER_RADIUS_KM
    ]
    if len(nearby) < _CLUSTER_MIN_REPORTS:
        return

    existing = (
        db.query(models.Alert)
        .filter(
            models.Alert.wsa_id == wsa.id,
            models.Alert.alert_type == models.AlertType.geo_cluster_incident,
            models.Alert.acknowledged_at.is_(None),
        )
        .first()
    )
    if existing:
        return

    alert = models.Alert(
        wsa_id=wsa.id,
        alert_type=models.AlertType.geo_cluster_incident,
        message=(
            f"{len(nearby)} {new_report.issue_type.value} reports within {_CLUSTER_RADIUS_KM}km of each other "
            f"in {wsa.name} in the last {_CLUSTER_WINDOW_HOURS} hours — a localized incident may be developing."
        ),
    )
    db.add(alert)


def raise_cap_overdue_alerts(db: Session) -> None:
    # checked lazily on read (no scheduler in this app) — ponytail: scan is
    # O(active WSAs), fine at this table size; move to a cron job if that changes
    today = date.today()
    overdue_wsas = (
        db.query(models.WSA)
        .filter(
            models.WSA.cap_due_date.isnot(None),
            models.WSA.cap_due_date < today,
            models.WSA.cap_status != models.CAPStatus.completed,
        )
        .all()
    )
    for wsa in overdue_wsas:
        existing = (
            db.query(models.Alert)
            .filter(
                models.Alert.wsa_id == wsa.id,
                models.Alert.alert_type == models.AlertType.cap_overdue,
                models.Alert.acknowledged_at.is_(None),
            )
            .first()
        )
        if existing:
            continue

        alert = models.Alert(
            wsa_id=wsa.id,
            alert_type=models.AlertType.cap_overdue,
            message=f"{wsa.name} ({wsa.province}) has a CAP due date of {wsa.cap_due_date.isoformat()} that has passed without completion.",
        )
        db.add(alert)
