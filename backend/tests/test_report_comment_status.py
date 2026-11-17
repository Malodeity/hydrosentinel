"""
"Generate AI comment" writes the note an admin saves WITH the status change.
If the admin picks "in review" in the dropdown but has not saved yet, the note
must describe moving the case to in review, not the saved "open" status.
"""
from unittest.mock import patch

import pytest

from app import models
from app.routes import ai as ai_routes


@pytest.fixture
def open_report(db, sample_wsa):
    report = models.CitizenReport(
        wsa_id=sample_wsa.id, issue_type=models.IssueType.leak, description="Burst pipe on Main Road",
        reference_code="HS-CMT0001", case_status="open", lat=-26.2, lng=28.0,
    )
    db.add(report)
    db.flush()
    return report


def _comment(client, auth_headers, report, **params):
    with patch.object(ai_routes, "call_openai", return_value="A short note.") as mocked:
        response = client.get(f"/ai/reports/{report.id}/comment", params=params, headers=auth_headers)
    return response, mocked


def test_comment_follows_the_status_the_admin_selected(client, auth_headers, open_report):
    response, mocked = _comment(client, auth_headers, open_report, case_status="in_review")

    assert response.status_code == 200
    system_prompt, user_prompt = mocked.call_args.args[0], mocked.call_args.args[1]
    assert "Status the admin is setting now: in_review" in user_prompt
    assert "Current case status: open" in user_prompt
    assert "review" in system_prompt.lower()


def test_resolved_note_is_told_not_to_invent_repair_work(client, auth_headers, open_report):
    _, mocked = _comment(client, auth_headers, open_report, case_status="resolved")

    system_prompt = mocked.call_args.args[0]
    assert "closing the case" in system_prompt
    assert "Do not describe repair work" in system_prompt


def test_without_a_status_it_uses_the_saved_one(client, auth_headers, open_report):
    _, mocked = _comment(client, auth_headers, open_report)

    user_prompt = mocked.call_args.args[1]
    assert "Case status: open" in user_prompt
    assert "Status the admin is setting now" not in user_prompt


def test_unknown_status_is_rejected_before_any_openai_call(client, auth_headers, open_report):
    response, mocked = _comment(client, auth_headers, open_report, case_status="deleted")

    assert response.status_code == 422
    mocked.assert_not_called()


def test_the_note_is_kept_short(client, auth_headers, open_report):
    _, mocked = _comment(client, auth_headers, open_report, case_status="in_review")

    assert "two sentences" in mocked.call_args.args[0]
    assert mocked.call_args.kwargs["max_tokens"] <= 100
