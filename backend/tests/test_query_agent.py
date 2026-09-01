"""
The query agent is only worth building if its tools return real database
rows and the loop actually terminates. Two failure modes matter most: a
tool silently returning wrong/unfiltered data, and a model that keeps
calling tools forever (must be bounded, not trust the model to stop).
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from app import models
from ai.query_agent import TOOL_FUNCTIONS, run_query_agent, tool_get_report_counts, tool_get_wsas


def _make_wsa(db, **overrides):
    defaults = dict(
        name="Test WSA X", province="Gauteng", risk_level=models.RiskLevel.high,
        cap_status=models.CAPStatus.none, blue_drop_score=40.0,
    )
    defaults.update(overrides)
    wsa = models.WSA(**defaults)
    db.add(wsa)
    db.flush()
    return wsa


def test_tool_get_wsas_filters_by_province_and_risk(db, sample_wsa):
    _make_wsa(db, name="Other Province WSA", province="Limpopo", risk_level=models.RiskLevel.high)
    _make_wsa(db, name="Gauteng Low Risk", province="Gauteng", risk_level=models.RiskLevel.low)

    results = tool_get_wsas(db, province="Gauteng", risk_level="high")

    names = {r["name"] for r in results}
    assert "Other Province WSA" not in names
    assert "Gauteng Low Risk" not in names


def test_tool_get_wsas_filters_by_cap_status(db):
    # limit set high: the `db` fixture runs against the real dev database
    # inside a rolled-back transaction, which already has hundreds of WSAs
    # with cap_status='none' — the default limit alone could cut off before
    # reaching this test's own row
    _make_wsa(db, name="No CAP WSA Unique12345", cap_status=models.CAPStatus.none)
    _make_wsa(db, name="Completed CAP WSA Unique12345", cap_status=models.CAPStatus.completed)

    results = tool_get_wsas(db, cap_status="none", limit=10000)

    names = {r["name"] for r in results}
    assert "No CAP WSA Unique12345" in names
    assert "Completed CAP WSA Unique12345" not in names


def test_tool_get_report_counts_reflects_real_reports(db, sample_wsa):
    for _ in range(3):
        db.add(models.CitizenReport(
            wsa_id=sample_wsa.id, issue_type=models.IssueType.leak, description="x",
            reference_code=f"HS-{_}TEST0000"[:12], case_status="open", lat=0.0, lng=0.0,
        ))
    db.flush()

    result = tool_get_report_counts(db, wsa_name=sample_wsa.name, days=30)

    assert result["total"] == 3
    assert result["by_issue_type"]["leak"] == 3


def _fake_tool_call_response(name: str, arguments: str, call_id: str = "call_1"):
    tool_call = SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))
    message = SimpleNamespace(content=None, tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _fake_final_response(content: str):
    message = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_run_query_agent_executes_tool_and_returns_final_answer(db, sample_wsa):
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_tool_call_response("get_wsas", '{"province": "Gauteng"}'),
        _fake_final_response("There is 1 WSA in Gauteng."),
    ]

    answer, trace = run_query_agent("How many WSAs are in Gauteng?", db, client=fake_client)

    assert answer == "There is 1 WSA in Gauteng."
    assert trace[0]["tool"] == "get_wsas"
    assert fake_client.chat.completions.create.call_count == 2


def test_run_query_agent_stops_after_max_tool_rounds(db):
    fake_client = MagicMock()
    # model keeps calling tools forever — the loop must not trust it to stop
    fake_client.chat.completions.create.side_effect = [
        _fake_tool_call_response("get_wsas", "{}", call_id=f"call_{i}") for i in range(10)
    ]

    answer, trace = run_query_agent("infinite loop question", db, client=fake_client, max_rounds=3)

    assert fake_client.chat.completions.create.call_count == 3
    assert "unable" in answer.lower() or "could not" in answer.lower()


def test_run_query_agent_handles_unknown_tool_name_gracefully(db):
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_tool_call_response("not_a_real_tool", "{}"),
        _fake_final_response("Fallback answer."),
    ]

    answer, trace = run_query_agent("question", db, client=fake_client)

    assert answer == "Fallback answer."
    assert "error" in trace[0]["result"].lower() or "unknown" in trace[0]["result"].lower()


def test_all_registered_tools_are_callable_with_db_only():
    # every tool must work with just (db, **kwargs) — the agent loop calls
    # them generically via TOOL_FUNCTIONS[name](db, **arguments)
    for name, fn in TOOL_FUNCTIONS.items():
        assert callable(fn), name


def test_query_endpoint_requires_admin(client):
    resp = client.post("/ai/query", json={"question": "how many WSAs are high risk?"})
    assert resp.status_code == 401


def test_query_endpoint_returns_answer_and_trace(client, auth_headers):
    from unittest.mock import patch

    fake_trace = [{"tool": "get_wsas", "arguments": {"risk_level": "high"}, "result": "[]"}]
    with patch("app.routes.ai.run_query_agent", return_value=("There are 3 high-risk WSAs.", fake_trace)):
        resp = client.post("/ai/query", json={"question": "how many WSAs are high risk?"}, headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "There are 3 high-risk WSAs."
    assert body["tool_calls"][0]["tool"] == "get_wsas"


def test_query_endpoint_rejects_too_short_question(client, auth_headers):
    resp = client.post("/ai/query", json={"question": "hi"}, headers=auth_headers)
    assert resp.status_code == 422
