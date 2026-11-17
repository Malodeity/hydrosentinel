"""
Photo analysis lets an admin ask GPT-4o to look at a resident's photo and say what it shows.

What must hold:
- the model is NOT told what the resident reported, so it cannot just agree; the server compares afterwards
- the verdict is decided by the server from the model's answer, never taken from the model
- a photo can only prove or disprove what a photo can show: billing and unclear photos are "inconclusive"
- nothing about the analysis reaches the public tracking page
- it costs a real OpenAI call, so it is admin only and rate limited, and bad input never reaches OpenAI
"""
import json
from unittest.mock import patch

import pytest

from app import models
from app.rate_limit import _call_log
from app.routes import ai as ai_routes

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    _call_log.clear()
    monkeypatch.setattr(ai_routes, "UPLOAD_ROOT", tmp_path)
    yield
    _call_log.clear()


def _report(db, wsa, issue=models.IssueType.leak, code="HS-PH000001"):
    report = models.CitizenReport(
        wsa_id=wsa.id, issue_type=issue, description="Water running down the street", reference_code=code,
        case_status="open", lat=-26.2, lng=28.0,
    )
    db.add(report)
    db.flush()
    return report


def _photo(tmp_path, report, name="a.png", data=PNG):
    folder = tmp_path / str(report.id)
    folder.mkdir(exist_ok=True)
    (folder / name).write_bytes(data)


def _reply(issue="leak", severity="medium", confidence="high", summary="Water gushing from a broken pipe."):
    return json.dumps({"issue_type": issue, "severity": severity, "confidence": confidence, "summary": summary})


def _analyse(client, auth_headers, report, reply, **params):
    with patch.object(ai_routes, "call_openai_vision", return_value=reply) as mocked:
        response = client.post(f"/ai/reports/{report.id}/analyze-photo", params=params, headers=auth_headers)
    return response, mocked


def test_photo_that_matches_the_report(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa, models.IssueType.leak)
    _photo(tmp_path, report)

    response, mocked = _analyse(client, auth_headers, report, _reply("leak"))

    assert response.status_code == 200
    body = response.json()
    assert body["issue_type"] == "leak" and body["verdict"] == "matches"
    assert body["photo"] == "a.png" and body["severity"] == "medium"
    assert mocked.call_args.args[2] == PNG and mocked.call_args.args[3] == "image/png"


def test_photo_that_contradicts_the_report_is_a_mismatch(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa, models.IssueType.outage)
    _photo(tmp_path, report)

    response, _ = _analyse(client, auth_headers, report, _reply("leak"))

    assert response.json()["verdict"] == "mismatch"


def test_a_photo_showing_no_water_problem_contradicts_a_leak_report(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa, models.IssueType.leak)
    _photo(tmp_path, report)

    response, _ = _analyse(client, auth_headers, report, _reply("not_water_related"))

    assert response.json()["verdict"] == "mismatch"


def test_a_billing_report_cannot_be_checked_from_a_photo(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa, models.IssueType.billing)
    _photo(tmp_path, report)

    response, _ = _analyse(client, auth_headers, report, _reply("leak"))

    assert response.json()["verdict"] == "inconclusive"


def test_an_unclear_photo_proves_nothing(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa, models.IssueType.leak)
    _photo(tmp_path, report)

    response, _ = _analyse(client, auth_headers, report, _reply("unclear", confidence="low"))

    assert response.json()["verdict"] == "inconclusive"


def test_a_made_up_issue_value_from_the_model_becomes_unclear(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa)
    _photo(tmp_path, report)

    response, _ = _analyse(client, auth_headers, report, _reply("banana", severity="catastrophic", confidence="certain"))

    body = response.json()
    assert (body["issue_type"], body["severity"], body["confidence"], body["verdict"]) == ("unclear", "low", "low", "inconclusive")


def test_the_model_is_not_told_what_the_resident_reported_and_must_not_identify_people(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa, models.IssueType.outage, code="HS-SECRET01")
    _photo(tmp_path, report)

    _, mocked = _analyse(client, auth_headers, report, _reply("leak"))

    system_prompt, user_text = mocked.call_args.args[0], mocked.call_args.args[1]
    assert "Do not identify or describe people" in system_prompt
    assert "Water running down the street" not in user_text and "HS-SECRET01" not in user_text and "outage" not in user_text.lower()


def test_the_analysis_is_saved_for_admins_but_never_shown_on_the_public_tracking_page(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa, code="HS-TRACK001")
    _photo(tmp_path, report)
    _analyse(client, auth_headers, report, _reply("leak"))

    admin_view = next(item for item in client.get("/reports", headers=auth_headers).json() if item["id"] == str(report.id))
    public_view = client.get("/reports/track/HS-TRACK001").json()

    assert admin_view["photo_analysis"]["issue_type"] == "leak"
    assert "photo_analysis" not in public_view


def test_a_report_with_no_photo_is_404_and_costs_no_openai_call(client, auth_headers, db, sample_wsa):
    report = _report(db, sample_wsa)

    response, mocked = _analyse(client, auth_headers, report, _reply())

    assert response.status_code == 404
    mocked.assert_not_called()


def test_a_file_that_is_not_an_image_is_rejected_before_openai(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa)
    _photo(tmp_path, report, name="notes.txt", data=b"hello")

    response, mocked = _analyse(client, auth_headers, report, _reply())

    assert response.status_code == 422
    mocked.assert_not_called()


def test_a_huge_photo_is_rejected_before_openai(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa)
    _photo(tmp_path, report, data=b"0" * (5 * 1024 * 1024))

    response, mocked = _analyse(client, auth_headers, report, _reply())

    assert response.status_code == 413
    mocked.assert_not_called()


def test_a_photo_index_past_the_end_is_404(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa)
    _photo(tmp_path, report)

    response, mocked = _analyse(client, auth_headers, report, _reply(), photo_index=3)

    assert response.status_code == 404
    mocked.assert_not_called()


def test_an_unreadable_model_reply_is_502_and_nothing_is_saved(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa)
    _photo(tmp_path, report)

    response, _ = _analyse(client, auth_headers, report, "I think it is a leak, probably.")

    assert response.status_code == 502
    db.refresh(report)
    assert report.photo_analysis is None


def test_it_needs_an_admin_token(client, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa)
    _photo(tmp_path, report)

    with patch.object(ai_routes, "call_openai_vision") as mocked:
        response = client.post(f"/ai/reports/{report.id}/analyze-photo")

    assert response.status_code == 401
    mocked.assert_not_called()


def test_it_counts_towards_the_hourly_ai_limit(client, auth_headers, db, sample_wsa, tmp_path):
    report = _report(db, sample_wsa)
    _photo(tmp_path, report)

    with patch.object(ai_routes, "call_openai_vision", return_value=_reply()) as mocked:
        statuses = [client.post(f"/ai/reports/{report.id}/analyze-photo", headers=auth_headers).status_code for _ in range(21)]

    assert statuses[:20] == [200] * 20 and statuses[20] == 429
    assert mocked.call_count == 20
