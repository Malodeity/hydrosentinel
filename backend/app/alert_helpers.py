# Everything that creates or closes alerts. Called from the routes that can cause one:
#   raise_high_risk_alert / raise_risk_increased_alert   <- routes/risk.py (after scoring)
#   raise_report_volume_spike_alert / raise_geo_cluster_alert <- routes/reports.py (after a new report)
#   raise_cap_overdue_alerts / raise_assignment_overdue_alerts / resolve_stale_alerts <- routes/alerts.py (on every read: the app has no scheduler)
# Every raise_* function first checks for an unacknowledged alert of the same type for that authority, so one problem never creates a pile of duplicates.

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


_RISK_RANK = {models.RiskLevel.low: 0, models.RiskLevel.medium: 1, models.RiskLevel.high: 2}


def raise_risk_increased_alert(wsa: models.WSA, old_level: models.RiskLevel, db: Session) -> None:
    # fires when a new score moves an authority to a worse tier (low -> medium, medium -> high, low -> high).
    # staying the same or improving raises nothing, and an unacknowledged alert of this type blocks a duplicate
    if _RISK_RANK[wsa.risk_level] <= _RISK_RANK[old_level]:
        return

    existing = (
        db.query(models.Alert)
        .filter(
            models.Alert.wsa_id == wsa.id,
            models.Alert.alert_type == models.AlertType.risk_level_increased,
            models.Alert.acknowledged_at.is_(None),
        )
        .first()
    )
    if existing:
        return

    db.add(models.Alert(
        wsa_id=wsa.id,
        alert_type=models.AlertType.risk_level_increased,
        message=f"{wsa.name} ({wsa.province}) moved from {old_level.value} to {wsa.risk_level.value} risk.",
    ))


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
            # "none" means there is no plan, so nothing can be overdue: the same rule the admin screens use
            models.WSA.cap_status.notin_([models.CAPStatus.completed, models.CAPStatus.none]),
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


def _overdue_tickets_by_wsa(db: Session) -> dict:
    # contractor tickets still with the contractor whose due time has passed, grouped by authority
    tickets = (
        db.query(models.ReportAssignment)
        .join(models.CitizenReport, models.CitizenReport.id == models.ReportAssignment.report_id)
        .filter(
            models.ReportAssignment.status.in_(("assigned", "accepted", "in_progress", "sent_back")),
            models.ReportAssignment.due_at.isnot(None),
            models.ReportAssignment.due_at < datetime.now(timezone.utc),
        )
        .all()
    )
    grouped: dict = {}
    for ticket in tickets:
        grouped.setdefault(ticket.report.wsa_id, []).append(ticket)
    return grouped


def raise_assignment_overdue_alerts(db: Session) -> None:
    # one alert per authority while any of its repair tickets is past due (read-time check, like the CAP one)
    for wsa_id, tickets in _overdue_tickets_by_wsa(db).items():
        existing = (
            db.query(models.Alert)
            .filter(
                models.Alert.wsa_id == wsa_id,
                models.Alert.alert_type == models.AlertType.assignment_overdue,
                models.Alert.acknowledged_at.is_(None),
            )
            .first()
        )
        if existing:
            continue
        wsa = tickets[0].report.wsa
        db.add(models.Alert(
            wsa_id=wsa_id,
            alert_type=models.AlertType.assignment_overdue,
            message=f"{len(tickets)} repair ticket(s) in {wsa.name} are past their due time and not yet fixed.",
        ))


def resolve_stale_alerts(db: Session) -> None:
    # closes alerts whose cause has gone away, so the list never says "CAP overdue" about a plan that is now complete
    # or "high risk" about an authority that is no longer high. closed alerts keep their history; acknowledged_by stays empty
    # because nobody clicked: the system closed them. checked lazily on read, like the overdue scan above
    today = date.today()
    open_alerts = (
        db.query(models.Alert)
        .filter(
            models.Alert.acknowledged_at.is_(None),
            models.Alert.alert_type.in_([models.AlertType.cap_overdue, models.AlertType.risk_level_high, models.AlertType.assignment_overdue]),
        )
        .all()
    )
    overdue_by_wsa = _overdue_tickets_by_wsa(db)
    for alert in open_alerts:
        wsa = alert.wsa
        if wsa is None:
            continue
        if alert.alert_type == models.AlertType.assignment_overdue:
            resolved = alert.wsa_id not in overdue_by_wsa
        elif alert.alert_type == models.AlertType.cap_overdue:
            still_overdue = (
                wsa.cap_due_date is not None
                and wsa.cap_due_date < today
                and wsa.cap_status not in (models.CAPStatus.completed, models.CAPStatus.none)
            )
            resolved = not still_overdue
        else:
            resolved = wsa.risk_level != models.RiskLevel.high
        if resolved:
            alert.acknowledged_at = datetime.now(timezone.utc)
            db.add(alert)
