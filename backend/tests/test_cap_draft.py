"""
CAP drafting asks the model to return structured JSON, which it will
occasionally get wrong (malformed JSON, wrong shape, garbage enum values,
missing fields). parse_cap_draft_json is the boundary that must degrade
safely instead of crashing the endpoint or handing the admin a broken item.
"""
import json
from unittest.mock import patch

from app.routes.ai import parse_cap_draft_json


def test_parses_well_formed_json():
    content = json.dumps({"items": [
        {"action": "Repair leak at Main St", "priority": "high", "suggested_due_in_days": 14, "justification": "3 open leak reports"},
    ]})
    items = parse_cap_draft_json(content)
    assert len(items) == 1
    assert items[0]["action"] == "Repair leak at Main St"
    assert items[0]["priority"] == "high"
    assert items[0]["suggested_due_in_days"] == 14


def test_accepts_bare_json_array_without_items_wrapper():
    content = json.dumps([{"action": "Fix pump", "priority": "medium", "justification": "x"}])
    items = parse_cap_draft_json(content)
    assert len(items) == 1
    assert items[0]["action"] == "Fix pump"


def test_invalid_json_returns_empty_list():
    assert parse_cap_draft_json("not json at all { broken") == []


def test_garbage_priority_falls_back_to_medium():
    content = json.dumps({"items": [{"action": "Do something", "priority": "URGENT!!", "justification": "x"}]})
    items = parse_cap_draft_json(content)
    assert items[0]["priority"] == "medium"


def test_missing_action_drops_the_item():
    content = json.dumps({"items": [{"priority": "high", "justification": "x"}, {"action": "Valid one", "priority": "low", "justification": "y"}]})
    items = parse_cap_draft_json(content)
    assert len(items) == 1
    assert items[0]["action"] == "Valid one"


def test_non_integer_due_days_becomes_none():
    content = json.dumps({"items": [{"action": "x", "priority": "low", "suggested_due_in_days": "soon", "justification": "y"}]})
    items = parse_cap_draft_json(content)
    assert items[0]["suggested_due_in_days"] is None


def test_caps_at_six_items():
    content = json.dumps({"items": [{"action": f"Item {i}", "priority": "low", "justification": "y"} for i in range(10)]})
    items = parse_cap_draft_json(content)
    assert len(items) == 6


def test_cap_draft_endpoint_requires_admin(client, sample_wsa):
    resp = client.get(f"/ai/wsa/{sample_wsa.id}/cap-draft")
    assert resp.status_code == 401


def test_cap_draft_endpoint_404_on_unknown_wsa(client, auth_headers):
    import uuid
    resp = client.get(f"/ai/wsa/{uuid.uuid4()}/cap-draft", headers=auth_headers)
    assert resp.status_code == 404


def test_cap_draft_endpoint_returns_parsed_items(client, auth_headers, sample_wsa):
    fake_response = json.dumps({"items": [
        {"action": "Investigate leak reports", "priority": "high", "suggested_due_in_days": 7, "justification": "based on open reports"},
    ]})
    with patch("app.routes.ai.call_openai_json", return_value=fake_response):
        resp = client.get(f"/ai/wsa/{sample_wsa.id}/cap-draft", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["action"] == "Investigate leak reports"


def test_cap_draft_endpoint_502_when_model_returns_unusable_output(client, auth_headers, sample_wsa):
    with patch("app.routes.ai.call_openai_json", return_value="garbage not json"):
        resp = client.get(f"/ai/wsa/{sample_wsa.id}/cap-draft", headers=auth_headers)
    assert resp.status_code == 502
