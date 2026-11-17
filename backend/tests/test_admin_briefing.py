"""The AI assistant tab's briefing and usage meter."""
from unittest.mock import patch

from app import models
from app.rate_limit import _MAX_CALLS
from app.routes import ai as ai_routes


def test_briefing_sends_database_facts_to_the_model_and_returns_them_beside_the_text(client, auth_headers, db, sample_wsa):
    db.add(models.CitizenReport(wsa_id=sample_wsa.id, issue_type=models.IssueType.leak, description="d", reference_code="HS-BRIEF001", case_status="open", lat=0, lng=0))
    db.flush()
    with patch.object(ai_routes, "call_openai", return_value="Status. 1. Act.") as mocked:
        res = client.get("/ai/admin-briefing", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["content"] == "Status. 1. Act."
    assert body["facts"]["unresolved_reports"] >= 1
    user_prompt = mocked.call_args.args[1]
    assert "unresolved reports" in user_prompt  # the facts reach the model
    assert "never invent" in mocked.call_args.args[0]


def test_briefing_needs_an_admin_and_counts_against_the_hourly_allowance(client, auth_headers):
    assert client.get("/ai/admin-briefing").status_code == 401
    with patch.object(ai_routes, "call_openai", return_value="x"):
        client.get("/ai/admin-briefing", headers=auth_headers)
    assert client.get("/ai/usage", headers=auth_headers).json()["used"] == 1


def test_usage_meter_reports_used_limit_and_reset_time_without_using_a_call(client, auth_headers):
    first = client.get("/ai/usage", headers=auth_headers).json()
    assert first == {"used": 0, "limit": _MAX_CALLS, "resets_in_minutes": 0}
    assert client.get("/ai/usage", headers=auth_headers).json()["used"] == 0  # reading it is free
    assert client.get("/ai/usage").status_code == 401
