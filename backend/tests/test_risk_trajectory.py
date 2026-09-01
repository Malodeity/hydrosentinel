"""Tests for the risk trajectory endpoints: GET /risk/trajectory/{id}, GET /risk/trending."""
from datetime import datetime, timedelta, timezone

from app import models


def _add_history(db, wsa, probability: float, days_ago: int):
    db.add(models.RiskScoreHistory(
        wsa_id=wsa.id,
        risk_level=models.RiskLevel.medium,
        probability=probability,
        model_source=models.ModelSource.heuristic,
        model_version="test",
        scored_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    ))
    db.flush()


def test_trajectory_with_no_history_is_insufficient_data(client, auth_headers, sample_wsa):
    resp = client.get(f"/risk/trajectory/{sample_wsa.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["trend"] == "insufficient_data"
    assert resp.json()["sample_size"] == 0


def test_trajectory_detects_worsening_trend(client, auth_headers, sample_wsa, db):
    _add_history(db, sample_wsa, 0.20, days_ago=3)
    _add_history(db, sample_wsa, 0.40, days_ago=2)
    _add_history(db, sample_wsa, 0.55, days_ago=1)

    resp = client.get(f"/risk/trajectory/{sample_wsa.id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["trend"] == "worsening"
    assert body["sample_size"] == 3


def test_trajectory_requires_auth(client, sample_wsa):
    resp = client.get(f"/risk/trajectory/{sample_wsa.id}")
    assert resp.status_code == 401


def test_trajectory_404_on_unknown_wsa(client, auth_headers):
    import uuid
    resp = client.get(f"/risk/trajectory/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


def test_trending_list_includes_wsa_crossing_tier(client, auth_headers, sample_wsa, db):
    # currently medium, rising fast enough to project into high
    _add_history(db, sample_wsa, 0.30, days_ago=2)
    _add_history(db, sample_wsa, 0.42, days_ago=1)
    _add_history(db, sample_wsa, 0.55, days_ago=0)

    resp = client.get("/risk/trending", headers=auth_headers)
    assert resp.status_code == 200
    ids = [item["wsa_id"] for item in resp.json()]
    assert str(sample_wsa.id) in ids


def test_trending_list_excludes_stable_wsa(client, auth_headers, sample_wsa, db):
    _add_history(db, sample_wsa, 0.55, days_ago=2)
    _add_history(db, sample_wsa, 0.54, days_ago=1)
    _add_history(db, sample_wsa, 0.55, days_ago=0)

    resp = client.get("/risk/trending", headers=auth_headers)
    assert resp.status_code == 200
    ids = [item["wsa_id"] for item in resp.json()]
    assert str(sample_wsa.id) not in ids
