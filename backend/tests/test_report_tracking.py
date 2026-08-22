"""
Citizens submitting a report have no account and no way to check its status
later. Each report gets a short reference_code at creation, and a public
(no-auth) endpoint looks up status by that code — without leaking the
report's location, WSA, or description to whoever holds the code.
"""
import io

from app import models


def _submit_report(client, sample_wsa):
    resp = client.post(
        "/reports",
        data={"wsa_id": str(sample_wsa.id), "issue_type": "leak", "description": "Pipe burst", "lat": "-26.2", "lng": "28.1"},
    )
    assert resp.status_code == 201
    return resp.json()


def test_submitted_report_gets_a_reference_code(client, sample_wsa):
    report = _submit_report(client, sample_wsa)
    assert report["reference_code"]
    assert len(report["reference_code"]) <= 12


def test_reference_codes_are_unique_across_reports(client, sample_wsa):
    codes = {_submit_report(client, sample_wsa)["reference_code"] for _ in range(5)}
    assert len(codes) == 5


def test_track_by_reference_code_returns_status_no_auth(client, sample_wsa):
    report = _submit_report(client, sample_wsa)

    resp = client.get(f"/reports/track/{report['reference_code']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["reference_code"] == report["reference_code"]
    assert body["case_status"] == "open"
    assert body["issue_type"] == "leak"


def test_track_response_excludes_pii(client, sample_wsa):
    report = _submit_report(client, sample_wsa)

    resp = client.get(f"/reports/track/{report['reference_code']}")
    body = resp.json()
    assert "wsa_id" not in body
    assert "lat" not in body
    assert "lng" not in body
    assert "description" not in body


def test_track_unknown_code_returns_404(client):
    resp = client.get("/reports/track/HS-NOTREAL")
    assert resp.status_code == 404


def test_track_reflects_status_update(client, sample_wsa, auth_headers, db):
    report = _submit_report(client, sample_wsa)

    resp = client.patch(
        f"/reports/{report['id']}",
        json={"case_status": "in_review", "admin_comment": "Looking into it"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    track_resp = client.get(f"/reports/track/{report['reference_code']}")
    assert track_resp.json()["case_status"] == "in_review"
    assert track_resp.json()["admin_comment"] == "Looking into it"
