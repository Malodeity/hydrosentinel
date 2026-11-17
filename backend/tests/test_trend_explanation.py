"""The AI explanation behind a "trending toward higher risk" row."""
import uuid
from unittest.mock import patch

from app import models
from app.routes import ai as ai_routes


def _score(db, wsa, level, probability, source=models.ModelSource.heuristic):
    db.add(models.RiskScoreHistory(wsa_id=wsa.id, risk_level=level, probability=probability, model_source=source))
    db.flush()


def test_prompt_carries_the_score_history_and_its_sources(client, auth_headers, db, sample_wsa):
    # the model can only be honest about mixed xgboost/heuristic scores if it is told which is which
    _score(db, sample_wsa, models.RiskLevel.medium, 0.5, models.ModelSource.heuristic)
    _score(db, sample_wsa, models.RiskLevel.high, 0.8, models.ModelSource.xgboost)
    with patch.object(ai_routes, "call_openai", return_value="Explained.") as mocked:
        res = client.get(f"/ai/wsa/{sample_wsa.id}/trend-explanation", headers=auth_headers)
    assert res.status_code == 200 and res.json()["content"] == "Explained."
    system_prompt, user_prompt = mocked.call_args.args[0], mocked.call_args.args[1]
    assert "scored by heuristic" in user_prompt and "scored by xgboost" in user_prompt
    assert "not directly comparable" in system_prompt
    assert "Never invent" in system_prompt


def test_needs_at_least_two_scores_and_spends_no_ai_call_without_them(client, auth_headers, db, sample_wsa):
    _score(db, sample_wsa, models.RiskLevel.medium, 0.5)
    with patch.object(ai_routes, "call_openai") as mocked:
        res = client.get(f"/ai/wsa/{sample_wsa.id}/trend-explanation", headers=auth_headers)
    assert res.status_code == 404
    mocked.assert_not_called()


def test_unknown_authority_is_404_and_login_is_required(client, auth_headers, sample_wsa):
    assert client.get(f"/ai/wsa/{uuid.uuid4()}/trend-explanation", headers=auth_headers).status_code == 404
    assert client.get(f"/ai/wsa/{sample_wsa.id}/trend-explanation").status_code == 401
