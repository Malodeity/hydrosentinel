"""
The existing report_volume_spike alert only fires at 5+ reports anywhere in
a WSA within 24h -- too blunt to catch a localized incident (e.g. a burst
main) fast. A geo-cluster alert should fire on 3+ same-issue-type reports
within 2km of each other within 6h, even if the WSA's total report count
never gets near 5 -- catching a real localized event earlier.
"""
from datetime import datetime, timedelta, timezone

from app import models
from app.alert_helpers import haversine_km, raise_geo_cluster_alert


def test_haversine_zero_for_identical_points():
    assert haversine_km(-26.2041, 28.0473, -26.2041, 28.0473) == 0.0


def test_haversine_known_distance_johannesburg_to_pretoria():
    # Johannesburg to Pretoria is approximately 55km
    km = haversine_km(-26.2041, 28.0473, -25.7479, 28.2293)
    assert 50 < km < 60


def _make_report(db, wsa, lat, lng, issue_type, minutes_ago=0):
    report = models.CitizenReport(
        wsa_id=wsa.id,
        issue_type=issue_type,
        description="test",
        reference_code=f"HS-TEST{minutes_ago}{lat}"[:12],
        case_status="open",
        lat=lat,
        lng=lng,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    db.add(report)
    db.flush()
    return report


def test_geo_cluster_alert_fires_on_three_nearby_same_type_reports(db, sample_wsa):
    base_lat, base_lng = -26.2041, 28.0473
    _make_report(db, sample_wsa, base_lat, base_lng, models.IssueType.leak, minutes_ago=10)
    _make_report(db, sample_wsa, base_lat + 0.005, base_lng, models.IssueType.leak, minutes_ago=5)
    newest = _make_report(db, sample_wsa, base_lat - 0.005, base_lng, models.IssueType.leak, minutes_ago=0)

    raise_geo_cluster_alert(sample_wsa, newest, db)
    db.flush()

    alert = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.geo_cluster_incident)
        .first()
    )
    assert alert is not None
    assert "leak" in alert.message.lower()


def test_geo_cluster_alert_does_not_fire_on_two_reports(db, sample_wsa):
    base_lat, base_lng = -26.2041, 28.0473
    _make_report(db, sample_wsa, base_lat, base_lng, models.IssueType.leak, minutes_ago=5)
    newest = _make_report(db, sample_wsa, base_lat + 0.005, base_lng, models.IssueType.leak, minutes_ago=0)

    raise_geo_cluster_alert(sample_wsa, newest, db)
    db.flush()

    alert = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.geo_cluster_incident)
        .first()
    )
    assert alert is None


def test_geo_cluster_alert_ignores_reports_far_apart(db, sample_wsa):
    _make_report(db, sample_wsa, -26.2041, 28.0473, models.IssueType.leak, minutes_ago=10)
    _make_report(db, sample_wsa, -25.7479, 28.2293, models.IssueType.leak, minutes_ago=5)  # ~55km away
    newest = _make_report(db, sample_wsa, -26.2041, 28.0473, models.IssueType.leak, minutes_ago=0)

    raise_geo_cluster_alert(sample_wsa, newest, db)
    db.flush()

    alert = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.geo_cluster_incident)
        .first()
    )
    assert alert is None


def test_geo_cluster_alert_ignores_different_issue_types(db, sample_wsa):
    base_lat, base_lng = -26.2041, 28.0473
    _make_report(db, sample_wsa, base_lat, base_lng, models.IssueType.billing, minutes_ago=10)
    _make_report(db, sample_wsa, base_lat + 0.005, base_lng, models.IssueType.quality, minutes_ago=5)
    newest = _make_report(db, sample_wsa, base_lat - 0.005, base_lng, models.IssueType.leak, minutes_ago=0)

    raise_geo_cluster_alert(sample_wsa, newest, db)
    db.flush()

    alert = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.geo_cluster_incident)
        .first()
    )
    assert alert is None


def test_geo_cluster_alert_ignores_old_reports_outside_window(db, sample_wsa):
    base_lat, base_lng = -26.2041, 28.0473
    _make_report(db, sample_wsa, base_lat, base_lng, models.IssueType.leak, minutes_ago=500)  # >6h old
    _make_report(db, sample_wsa, base_lat + 0.005, base_lng, models.IssueType.leak, minutes_ago=400)
    newest = _make_report(db, sample_wsa, base_lat - 0.005, base_lng, models.IssueType.leak, minutes_ago=0)

    raise_geo_cluster_alert(sample_wsa, newest, db)
    db.flush()

    alert = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.geo_cluster_incident)
        .first()
    )
    assert alert is None


def test_geo_cluster_alert_not_duplicated(db, sample_wsa):
    base_lat, base_lng = -26.2041, 28.0473
    _make_report(db, sample_wsa, base_lat, base_lng, models.IssueType.leak, minutes_ago=10)
    _make_report(db, sample_wsa, base_lat + 0.005, base_lng, models.IssueType.leak, minutes_ago=5)
    newest = _make_report(db, sample_wsa, base_lat - 0.005, base_lng, models.IssueType.leak, minutes_ago=0)

    raise_geo_cluster_alert(sample_wsa, newest, db)
    raise_geo_cluster_alert(sample_wsa, newest, db)
    db.flush()

    count = (
        db.query(models.Alert)
        .filter(models.Alert.wsa_id == sample_wsa.id, models.Alert.alert_type == models.AlertType.geo_cluster_incident)
        .count()
    )
    assert count == 1
