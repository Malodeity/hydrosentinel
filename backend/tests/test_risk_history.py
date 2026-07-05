"""Tests for risk scoring: history persistence, model_source flag, GET /risk/history."""
from app import models


def test_risk_score_saves_to_history(client, auth_headers, sample_wsa, db):
    resp = client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)
    assert resp.status_code == 200

    history = db.query(models.RiskScoreHistory).filter(
        models.RiskScoreHistory.wsa_id == sample_wsa.id
    ).all()
    assert len(history) == 1
    assert history[0].probability >= 0
    assert history[0].model_source in (models.ModelSource.xgboost, models.ModelSource.heuristic)


def test_risk_score_records_heuristic_source_when_no_model(client, auth_headers, sample_wsa, db):
    # model.pkl never exists in the test environment — fallback is always heuristic
    resp = client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["model_source"] == "heuristic"

    entry = db.query(models.RiskScoreHistory).filter(
        models.RiskScoreHistory.wsa_id == sample_wsa.id
    ).first()
    assert entry.model_source == models.ModelSource.heuristic
    assert entry.model_version == "heuristic_v1"


def test_risk_score_records_scored_by(client, auth_headers, admin_user, sample_wsa, db):
    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)
    entry = db.query(models.RiskScoreHistory).filter(
        models.RiskScoreHistory.wsa_id == sample_wsa.id
    ).first()
    assert entry.scored_by == admin_user.id


def test_multiple_scores_accumulate_in_history(client, auth_headers, sample_wsa, db):
    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)
    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)
    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)

    count = db.query(models.RiskScoreHistory).filter(
        models.RiskScoreHistory.wsa_id == sample_wsa.id
    ).count()
    assert count == 3


def test_get_risk_history_returns_entries(client, auth_headers, sample_wsa):
    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)
    client.post(f"/risk/score/{sample_wsa.id}", headers=auth_headers)

    resp = client.get(f"/risk/history/{sample_wsa.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["model_source"] in ("xgboost", "heuristic")


def test_get_risk_history_requires_auth(client, sample_wsa):
    resp = client.get(f"/risk/history/{sample_wsa.id}")
    assert resp.status_code == 401


def test_get_risk_history_404_on_unknown_wsa(client, auth_headers):
    import uuid
    resp = client.get(f"/risk/history/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
