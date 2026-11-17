"""
The map's "Summarise this view" feature asks GPT-4o to describe only the
authorities inside the visible map bounds. What matters:

- the numbers come from the database for exactly that view, never from the
  model, so an authority outside the view can't leak into the summary
- the model is only given real facts to describe (names, counts, scores)
- the map keeps working when OpenAI is down: counts still come back
- bad bounds or an empty view must not cost an OpenAI call
- repeating the same view must not cost a second OpenAI call
"""
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app import models
from app.routes import ai as ai_routes

# open Atlantic: no real authority sits here, so the test controls the whole view
VIEW = {"south": 9.0, "north": 11.0, "west": -31.0, "east": -29.0}


@pytest.fixture(autouse=True)
def _clear_cache():
    ai_routes._map_summary_cache.clear()
    yield
    ai_routes._map_summary_cache.clear()


def _wsa(db, name, lat, lng, risk, blue_drop=50.0):
    wsa = models.WSA(
        name=name, province="Test Province", lat=lat, lng=lng, risk_level=risk,
        blue_drop_score=blue_drop, cap_status=models.CAPStatus.none,
    )
    db.add(wsa)
    db.flush()
    return wsa


def _report(db, wsa, lat, lng, status, code):
    db.add(models.CitizenReport(
        wsa_id=wsa.id, issue_type=models.IssueType.leak, description="test",
        reference_code=code, case_status=status, lat=lat, lng=lng,
    ))
    db.flush()


def test_counts_only_authorities_inside_the_view(client, db):
    _wsa(db, "Inside High", 10.0, -30.0, models.RiskLevel.high)
    _wsa(db, "Inside Low", 10.5, -30.5, models.RiskLevel.low)
    _wsa(db, "Outside High", 40.0, -30.0, models.RiskLevel.high)

    with patch.object(ai_routes, "call_openai", return_value="A short summary."):
        body = client.get("/ai/map-view-summary", params=VIEW).json()

    assert body["stats"] == {"total": 2, "high": 1, "medium": 0, "low": 1, "open_reports": 0}
    assert body["content"] == "A short summary."


def test_open_reports_counts_only_unresolved_reports_in_view(client, db):
    wsa = _wsa(db, "Inside", 10.0, -30.0, models.RiskLevel.medium)
    _report(db, wsa, 10.1, -30.1, "open", "HS-MV0001")
    _report(db, wsa, 10.2, -30.2, "in_review", "HS-MV0002")
    _report(db, wsa, 10.3, -30.3, "resolved", "HS-MV0003")
    _report(db, wsa, 40.0, -30.0, "open", "HS-MV0004")  # outside the view

    with patch.object(ai_routes, "call_openai", return_value="ok"):
        body = client.get("/ai/map-view-summary", params=VIEW).json()

    assert body["stats"]["open_reports"] == 2


def test_the_model_is_given_the_highest_risk_authority_by_name(client, db):
    _wsa(db, "Calm Municipality", 10.0, -30.0, models.RiskLevel.low, blue_drop=95.0)
    _wsa(db, "Struggling Municipality", 10.4, -30.4, models.RiskLevel.high, blue_drop=12.0)

    with patch.object(ai_routes, "call_openai", return_value="ok") as mocked:
        client.get("/ai/map-view-summary", params=VIEW)

    user_prompt = mocked.call_args.args[1]
    assert "Struggling Municipality" in user_prompt
    assert user_prompt.index("Struggling Municipality") < user_prompt.index("Calm Municipality")


def test_openai_failure_still_returns_the_counts(client, db):
    _wsa(db, "Inside High", 10.0, -30.0, models.RiskLevel.high)

    with patch.object(ai_routes, "call_openai", side_effect=HTTPException(status_code=502, detail="OpenAI request failed")):
        response = client.get("/ai/map-view-summary", params=VIEW)

    assert response.status_code == 200
    assert response.json()["content"] is None
    assert response.json()["stats"]["total"] == 1


def test_empty_view_is_404_and_costs_no_openai_call(client):
    with patch.object(ai_routes, "call_openai") as mocked:
        response = client.get("/ai/map-view-summary", params=VIEW)

    assert response.status_code == 404
    mocked.assert_not_called()


@pytest.mark.parametrize("bounds", [
    {"south": 11.0, "north": 9.0, "west": -31.0, "east": -29.0},   # south above north
    {"south": 9.0, "north": 11.0, "west": -29.0, "east": -31.0},   # west east of east
    {"south": -95.0, "north": 11.0, "west": -31.0, "east": -29.0},  # latitude out of range
])
def test_invalid_bounds_are_422_and_cost_no_openai_call(client, bounds):
    with patch.object(ai_routes, "call_openai") as mocked:
        response = client.get("/ai/map-view-summary", params=bounds)

    assert response.status_code == 422
    mocked.assert_not_called()


def test_same_view_twice_costs_one_openai_call(client, db):
    _wsa(db, "Inside", 10.0, -30.0, models.RiskLevel.medium)

    with patch.object(ai_routes, "call_openai", return_value="cached text") as mocked:
        first = client.get("/ai/map-view-summary", params=VIEW).json()
        second = client.get("/ai/map-view-summary", params=VIEW).json()

    assert first["content"] == second["content"] == "cached text"
    assert mocked.call_count == 1
