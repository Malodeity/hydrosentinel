"""
The query agent is only worth building if its tools return real database
rows and the loop actually terminates. Two failure modes matter most: a
tool silently returning wrong/unfiltered data, and a model that keeps
calling tools forever (must be bounded, not trust the model to stop).
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from app import models
from ai.query_agent import (
    TOOL_FUNCTIONS,
    run_query_agent,
    tool_compare_provinces,
    tool_count_wsas,
    tool_get_open_reports,
    tool_get_overdue_caps,
    tool_get_wsa_detail,
    tool_get_alerts,
    tool_get_audit_summary,
    tool_get_report_counts,
    tool_get_wsas,
)


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

    results = tool_get_wsas(db, cap_status="none", name_contains="Unique12345")

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


def test_tool_get_alerts_filters_by_wsa_name(db, sample_wsa):
    other_wsa = _make_wsa(db, name="Other Alert WSA")
    db.add(models.Alert(wsa_id=sample_wsa.id, alert_type=models.AlertType.risk_level_high, message="high risk here"))
    db.add(models.Alert(wsa_id=other_wsa.id, alert_type=models.AlertType.cap_overdue, message="cap overdue there"))
    db.flush()

    results = tool_get_alerts(db, wsa_name=sample_wsa.name)

    assert len(results) == 1
    assert results[0]["message"] == "high risk here"


def test_tool_get_alerts_filters_unacknowledged_only(db, sample_wsa):
    from datetime import datetime, timezone
    db.add(models.Alert(wsa_id=sample_wsa.id, alert_type=models.AlertType.risk_level_high, message="open one"))
    db.add(models.Alert(
        wsa_id=sample_wsa.id, alert_type=models.AlertType.cap_overdue, message="closed one",
        acknowledged_at=datetime.now(timezone.utc),
    ))
    db.flush()

    results = tool_get_alerts(db, wsa_name=sample_wsa.name, unacknowledged_only=True)

    assert len(results) == 1
    assert results[0]["message"] == "open one"


def test_tool_get_audit_summary_counts_by_action(db, admin_user):
    from app import models as m
    # the dev database may already hold real audit rows, so measure the change, not the total
    before = tool_get_audit_summary(db, days=30)["by_action"]
    db.add(m.AuditLog(user_id=admin_user.id, action=m.AuditAction.cap_status_updated, table_name="wsa", record_id=admin_user.id))
    db.add(m.AuditLog(user_id=admin_user.id, action=m.AuditAction.cap_status_updated, table_name="wsa", record_id=admin_user.id))
    db.add(m.AuditLog(user_id=admin_user.id, action=m.AuditAction.risk_score_run, table_name="wsa", record_id=admin_user.id))
    db.flush()

    after = tool_get_audit_summary(db, days=30)["by_action"]

    assert after["cap_status_updated"] - before.get("cap_status_updated", 0) == 2
    assert after["risk_score_run"] - before.get("risk_score_run", 0) == 1


def test_tool_compare_provinces_computes_real_averages(db):
    _make_wsa(db, name="CP WSA 1", province="Compare Province", blue_drop_score=80.0, risk_level=models.RiskLevel.low)
    _make_wsa(db, name="CP WSA 2", province="Compare Province", blue_drop_score=60.0, risk_level=models.RiskLevel.high)

    results = tool_compare_provinces(db)
    entry = next(r for r in results if r["province"] == "Compare Province")

    assert entry["wsa_count"] == 2
    assert entry["avg_blue_drop_score"] == 70.0
    assert entry["high_risk_count"] == 1


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


# ---- tools added for the AI assistant tab -------------------------------------------------------------------------------

def test_count_wsas_is_exact_and_not_cut_off_like_the_list_tool(db):
    # the list tool stops at 50 rows, so a "how many" question must use the count, which has no such limit
    before = tool_count_wsas(db, province="Countland")["count"]
    for i in range(55):
        _make_wsa(db, name=f"Countland WSA {i}", province="Countland")
    assert tool_count_wsas(db, province="Countland")["count"] == before + 55
    assert len(tool_get_wsas(db, province="Countland", limit=1000)) == 50  # the list is capped, the count is not


def test_overdue_caps_uses_the_one_rule_no_plan_and_completed_plans_are_never_overdue(db):
    from datetime import date, timedelta

    past = date.today() - timedelta(days=9)
    _make_wsa(db, name="Overdue Plan Unique77", cap_status=models.CAPStatus.in_progress, cap_due_date=past)
    _make_wsa(db, name="Done Plan Unique77", cap_status=models.CAPStatus.completed, cap_due_date=past)
    _make_wsa(db, name="No Plan Unique77", cap_status=models.CAPStatus.none, cap_due_date=past)
    names = {r["name"]: r for r in tool_get_overdue_caps(db)}
    assert names["Overdue Plan Unique77"]["days_overdue"] == 9
    assert "Done Plan Unique77" not in names and "No Plan Unique77" not in names


def test_open_reports_returns_the_true_total_and_excludes_resolved(db, sample_wsa):
    for i, status in enumerate(["open", "in_review", "resolved"]):
        db.add(models.CitizenReport(wsa_id=sample_wsa.id, issue_type=models.IssueType.leak, description="d", reference_code=f"HS-AGT0000{i}", case_status=status, lat=0, lng=0))
    db.flush()
    result = tool_get_open_reports(db, wsa_name=sample_wsa.name, limit=1)
    assert result["total_matching"] == 2  # the resolved one is not counted
    assert len(result["reports"]) == 1  # but only `limit` rows are shown, and the total says so


def test_wsa_detail_returns_candidates_instead_of_guessing_when_a_name_is_ambiguous(db):
    _make_wsa(db, name="Ambiguous Alpha Unique88")
    _make_wsa(db, name="Ambiguous Beta Unique88")
    result = tool_get_wsa_detail(db, "Unique88")
    assert "candidates" in result and len(result["candidates"]) == 2
    assert "error" in tool_get_wsa_detail(db, "Zzz No Such Place")
    assert tool_get_wsa_detail(db, "Ambiguous Alpha Unique88")["name"] == "Ambiguous Alpha Unique88"


def test_every_tool_in_the_schema_has_a_function_and_vice_versa():
    from ai.query_agent import TOOLS_SCHEMA

    assert {t["function"]["name"] for t in TOOLS_SCHEMA} == set(TOOL_FUNCTIONS)
