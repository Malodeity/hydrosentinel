"""FR-10: authorities are re-scored automatically when their latest score is older than the interval."""
from datetime import datetime, timedelta, timezone

from app import models
from app.scheduler import rescore_due


def _wsa(db, name):
    wsa = models.WSA(name=name, province="Gauteng", blue_drop_score=45.0, risk_level=models.RiskLevel.low)
    db.add(wsa)
    db.flush()
    return wsa


def _history(db, wsa, age_hours, scored_by=None):
    db.add(models.RiskScoreHistory(
        wsa_id=wsa.id, risk_level=models.RiskLevel.low, probability=0.9, model_source=models.ModelSource.heuristic,
        scored_by=scored_by, scored_at=datetime.now(timezone.utc) - timedelta(hours=age_hours),
    ))
    db.flush()


def _count(db, wsa):
    return db.query(models.RiskScoreHistory).filter(models.RiskScoreHistory.wsa_id == wsa.id).count()


def test_an_authority_that_was_never_scored_is_scored_and_marked_automatic(db):
    wsa = _wsa(db, "Sched Never")
    rescore_due(None, 24, db)
    row = db.query(models.RiskScoreHistory).filter(models.RiskScoreHistory.wsa_id == wsa.id).one()
    assert row.scored_by is None  # empty marks an automatic run


def test_a_stale_score_is_refreshed_but_a_recent_one_is_left_alone(db):
    # the point of the schedule: scores never go stale, but a restart or a second server must not re-score what is already fresh
    stale, fresh = _wsa(db, "Sched Stale"), _wsa(db, "Sched Fresh")
    _history(db, stale, age_hours=30)
    _history(db, fresh, age_hours=2)
    rescore_due(None, 24, db)
    assert _count(db, stale) == 2
    assert _count(db, fresh) == 1


def test_running_it_twice_in_a_row_does_not_score_twice(db):
    wsa = _wsa(db, "Sched Twice")
    rescore_due(None, 24, db)
    rescore_due(None, 24, db)
    assert _count(db, wsa) == 1


def test_a_worse_score_raises_the_same_alert_as_the_button(db):
    wsa = _wsa(db, "Sched Alert")
    wsa.blue_drop_score, wsa.nrw_percent, wsa.maint_pct = 5.0, 60.0, 0.0  # the fallback rule rates this combination as high risk
    db.flush()
    rescore_due(None, 24, db)
    db.refresh(wsa)
    assert wsa.risk_level == models.RiskLevel.high
    assert db.query(models.Alert).filter(models.Alert.wsa_id == wsa.id).count() >= 1


def test_the_schedule_endpoint_reports_interval_and_last_automatic_run(client, auth_headers, db):
    wsa = _wsa(db, "Sched Endpoint")
    _history(db, wsa, age_hours=1)  # automatic (scored_by empty)
    body = client.get("/risk/schedule", headers=auth_headers).json()
    assert body["interval_hours"] == 24
    assert body["last_automatic_run"] is not None


def test_the_schedule_endpoint_needs_an_admin(client):
    assert client.get("/risk/schedule").status_code == 401


def test_only_one_server_scores_at_a_time(db):
    # two servers share one database: while another connection holds the scheduler lock, this run must do nothing instead of scoring twice
    from tests.conftest import engine
    from app.scheduler import _LOCK_KEY

    wsa = _wsa(db, "Sched Locked")
    other_server = engine.connect()
    try:
        other_server.exec_driver_sql(f"SELECT pg_advisory_lock({_LOCK_KEY})")
        assert rescore_due(None, 24, db) == 0
        assert _count(db, wsa) == 0
    finally:
        other_server.exec_driver_sql(f"SELECT pg_advisory_unlock({_LOCK_KEY})")
        other_server.close()
    assert rescore_due(None, 24, db) >= 1
    assert _count(db, wsa) == 1
