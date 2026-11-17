"""The public, aggregate-only report statistics shown on the dashboard."""
from datetime import datetime, timedelta, timezone

from app import models


def _report(db, wsa, code, status="open", age_days=1, resolved_after_days=None):
    created = datetime.now(timezone.utc) - timedelta(days=age_days)
    db.add(models.CitizenReport(
        wsa_id=wsa.id, issue_type=models.IssueType.leak, description="private text", reference_code=code, case_status=status,
        lat=-26.0, lng=28.0, created_at=created,
        resolved_at=created + timedelta(days=resolved_after_days) if resolved_after_days is not None else None,
    ))
    db.flush()


def test_needs_no_login_and_counts_open_resolved_and_the_past_week(client, db, sample_wsa):
    before = client.get("/reports/public-stats").json()
    _report(db, sample_wsa, "HS-PUB00001", "open", age_days=2)
    _report(db, sample_wsa, "HS-PUB00002", "resolved", age_days=20, resolved_after_days=4)
    after = client.get("/reports/public-stats").json()
    assert after["total"] == before["total"] + 2
    assert after["received_7d"] == before["received_7d"] + 1  # only the 2-day-old one
    assert after["open"] == before["open"] + 1 and after["resolved"] == before["resolved"] + 1
    assert after["by_wsa"][str(sample_wsa.id)] == {"open": 1, "resolved": 1}


def test_never_exposes_report_content(client, db, sample_wsa):
    # the dashboard is public: the response must hold counts only, so it must not contain text, codes or locations
    _report(db, sample_wsa, "HS-PRIVATE1")
    raw = client.get("/reports/public-stats").text
    assert "private text" not in raw and "HS-PRIVATE1" not in raw and "lat" not in raw


def test_resolution_days_skips_resolved_reports_with_no_recorded_time():
    from types import SimpleNamespace
    from app.routes.reports import resolution_days

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    make = lambda status, after: SimpleNamespace(case_status=status, created_at=start, resolved_at=start + timedelta(days=after) if after is not None else None)
    days = resolution_days([make("resolved", 2), make("resolved", 4), make("resolved", None), make("open", 9)])
    assert days == [2.0, 4.0]  # the untimed resolved report and the open one are both excluded
