import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models


def tool_get_wsas(
    db: Session,
    province: str | None = None,
    risk_level: str | None = None,
    cap_status: str | None = None,
    limit: int = 20,
) -> list[dict]:
    query = db.query(models.WSA)
    if province:
        query = query.filter(models.WSA.province == province)
    if risk_level:
        query = query.filter(models.WSA.risk_level == risk_level)
    if cap_status:
        query = query.filter(models.WSA.cap_status == cap_status)
    results = query.limit(limit).all()
    return [
        {
            "name": w.name,
            "province": w.province,
            "risk_level": w.risk_level.value,
            "cap_status": w.cap_status.value,
            "blue_drop_score": w.blue_drop_score,
        }
        for w in results
    ]


def tool_get_trending_wsas(db: Session) -> list[dict]:
    # reuses the same trend math behind GET /risk/trending — the agent can
    # answer "who's getting worse" without a human clicking through the UI
    from ai.trajectory import compute_trajectory

    results = []
    for wsa in db.query(models.WSA).all():
        history = (
            db.query(models.RiskScoreHistory)
            .filter(models.RiskScoreHistory.wsa_id == wsa.id)
            .order_by(models.RiskScoreHistory.scored_at.asc())
            .all()
        )
        trajectory = compute_trajectory([float(h.probability) for h in history])
        if trajectory["crosses_tier"]:
            results.append({"name": wsa.name, "province": wsa.province, **trajectory})
    return results


def tool_get_report_counts(
    db: Session,
    province: str | None = None,
    wsa_name: str | None = None,
    days: int = 30,
) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = (
        db.query(models.CitizenReport)
        .join(models.WSA)
        .filter(models.CitizenReport.created_at >= cutoff)
    )
    if province:
        query = query.filter(models.WSA.province == province)
    if wsa_name:
        query = query.filter(models.WSA.name == wsa_name)
    reports = query.all()
    return {
        "total": len(reports),
        "by_issue_type": dict(Counter(r.issue_type.value for r in reports)),
    }


def tool_get_alerts(
    db: Session,
    wsa_name: str | None = None,
    unacknowledged_only: bool = False,
) -> list[dict]:
    query = db.query(models.Alert).join(models.WSA)
    if wsa_name:
        query = query.filter(models.WSA.name == wsa_name)
    if unacknowledged_only:
        query = query.filter(models.Alert.acknowledged_at.is_(None))
    alerts = query.order_by(models.Alert.created_at.desc()).limit(50).all()
    return [
        {
            "wsa_name": a.wsa.name,
            "alert_type": a.alert_type.value,
            "message": a.message,
            "acknowledged": a.acknowledged_at is not None,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


def tool_get_audit_summary(db: Session, days: int = 30) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = db.query(models.AuditLog).filter(models.AuditLog.created_at >= cutoff).all()
    return {
        "total": len(entries),
        "by_action": dict(Counter(e.action.value for e in entries)),
    }


def tool_compare_provinces(db: Session) -> list[dict]:
    wsas = db.query(models.WSA).all()
    by_province: dict[str, list[models.WSA]] = {}
    for wsa in wsas:
        by_province.setdefault(wsa.province, []).append(wsa)

    results = []
    for province, group in by_province.items():
        scores = [w.blue_drop_score for w in group if w.blue_drop_score is not None]
        results.append({
            "province": province,
            "wsa_count": len(group),
            "avg_blue_drop_score": round(sum(scores) / len(scores), 2) if scores else None,
            "high_risk_count": sum(1 for w in group if w.risk_level == models.RiskLevel.high),
        })
    return sorted(results, key=lambda r: r["province"])


TOOL_FUNCTIONS = {
    "get_wsas": tool_get_wsas,
    "get_trending_wsas": tool_get_trending_wsas,
    "get_report_counts": tool_get_report_counts,
    "get_alerts": tool_get_alerts,
    "get_audit_summary": tool_get_audit_summary,
    "compare_provinces": tool_compare_provinces,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_wsas",
            "description": "List Water Services Authorities, optionally filtered by province, risk level, or CAP status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "province": {"type": "string"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    "cap_status": {"type": "string", "enum": ["none", "submitted", "in_progress", "completed"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trending_wsas",
            "description": "List WSAs whose risk score trend is projected to cross into a worse risk tier soon, based on their scoring history.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_report_counts",
            "description": "Count citizen reports, optionally filtered by province or WSA name, over a number of days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "province": {"type": "string"},
                    "wsa_name": {"type": "string"},
                    "days": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts",
            "description": "List system alerts, optionally filtered by WSA name or unacknowledged-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wsa_name": {"type": "string"},
                    "unacknowledged_only": {"type": "boolean"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_audit_summary",
            "description": "Count admin actions (CAP updates, report triage, risk scoring) from the audit log over a number of days, grouped by action type.",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_provinces",
            "description": "Compare all provinces: WSA count, average Blue Drop score, and high-risk WSA count per province.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

_SYSTEM_PROMPT = (
    "You are a data analyst assistant for HydroSentinel, a South African municipal water monitoring platform. "
    "Answer the admin's question using ONLY the tools provided — never invent a number or a WSA name. "
    "Call a tool whenever you need real data. When you have enough information, give a concise, "
    "factual final answer citing the specific numbers you found."
)


def run_query_agent(question: str, db: Session, client=None, max_rounds: int = 5) -> tuple[str, list[dict]]:
    """
    Bounded tool-calling loop: the model can call get_wsas/get_trending_wsas/
    get_report_counts against the real database up to max_rounds times before
    this gives up and returns a fallback message — never trusts the model to
    stop calling tools on its own.
    """
    if client is None:
        from app.routes.ai import get_openai_client
        client = get_openai_client()

    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    trace: list[dict] = []

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS_SCHEMA,
            temperature=0.2,
            max_tokens=500,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content or "", trace

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        })

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}

            fn = TOOL_FUNCTIONS.get(name)
            if fn is None:
                result_text = f"Error: unknown tool '{name}'"
            else:
                try:
                    result = fn(db, **arguments)
                    result_text = json.dumps(result, default=str)
                except Exception as exc:  # noqa: BLE001 — a bad tool call shouldn't crash the whole agent loop
                    result_text = f"Error executing {name}: {exc}"

            trace.append({"tool": name, "arguments": arguments, "result": result_text})
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result_text})

    return "I was unable to fully answer that within the available tool calls. Try a more specific question.", trace
