# The question box on the AI assistant tab. The model is given a menu of READ-ONLY database tools (the functions below, listed in TOOLS_SCHEMA)
# and may call them for up to 5 rounds; the answer is built from what they return. Nothing here writes to the database.
# To add a capability: write a tool_* function, add it to TOOL_FUNCTIONS and TOOLS_SCHEMA (a test checks the two lists match).

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models


def _overdue_filter():
    # the one definition of "CAP overdue" used everywhere: a deadline that has passed on a plan that exists and is not finished
    # (an authority with no plan has nothing to be late on). see also alert_helpers.raise_cap_overdue_alerts
    return (
        models.WSA.cap_due_date.isnot(None),
        models.WSA.cap_due_date < date.today(),
        models.WSA.cap_status.notin_([models.CAPStatus.completed, models.CAPStatus.none]),
    )


def tool_get_wsas(
    db: Session,
    province: str | None = None,
    risk_level: str | None = None,
    cap_status: str | None = None,
    name_contains: str | None = None,
    limit: int = 20,
) -> list[dict]:
    # lists authorities (at most `limit`, never more than 50); use count_wsas when the question is "how many"
    query = db.query(models.WSA)
    if province:
        query = query.filter(models.WSA.province == province)
    if risk_level:
        query = query.filter(models.WSA.risk_level == risk_level)
    if cap_status:
        query = query.filter(models.WSA.cap_status == cap_status)
    if name_contains:
        query = query.filter(models.WSA.name.ilike(f"%{name_contains}%"))
    results = query.order_by(models.WSA.name).limit(max(1, min(limit, 50))).all()
    return [
        {
            "name": w.name,
            "province": w.province,
            "risk_level": w.risk_level.value,
            "cap_status": w.cap_status.value,
            "cap_due_date": w.cap_due_date.isoformat() if w.cap_due_date else None,
            "blue_drop_score": w.blue_drop_score,
            "green_drop_score": w.green_drop_score,
            "nrw_percent": w.nrw_percent,
        }
        for w in results
    ]


def tool_count_wsas(
    db: Session,
    province: str | None = None,
    risk_level: str | None = None,
    cap_status: str | None = None,
    overdue_only: bool = False,
) -> dict:
    # an exact count, so the model never has to count rows from a truncated list (the list tool stops at 20 to 50 rows)
    query = db.query(models.WSA)
    if province:
        query = query.filter(models.WSA.province == province)
    if risk_level:
        query = query.filter(models.WSA.risk_level == risk_level)
    if cap_status:
        query = query.filter(models.WSA.cap_status == cap_status)
    if overdue_only:
        query = query.filter(*_overdue_filter())
    return {"count": query.count()}


def tool_get_overdue_caps(db: Session) -> list[dict]:
    # plans past their deadline, longest overdue first
    rows = db.query(models.WSA).filter(*_overdue_filter()).order_by(models.WSA.cap_due_date.asc()).limit(50).all()
    return [
        {
            "name": w.name,
            "province": w.province,
            "cap_status": w.cap_status.value,
            "cap_due_date": w.cap_due_date.isoformat(),
            "days_overdue": (date.today() - w.cap_due_date).days,
            "risk_level": w.risk_level.value,
        }
        for w in rows
    ]


def tool_get_open_reports(
    db: Session,
    province: str | None = None,
    wsa_name: str | None = None,
    issue_type: str | None = None,
    min_age_days: int = 0,
    limit: int = 10,
) -> dict:
    # unresolved citizen reports, oldest first. returns the true total as well as the rows, because only `limit` rows are shown
    query = (
        db.query(models.CitizenReport)
        .join(models.WSA)
        .filter(models.CitizenReport.case_status != "resolved")
    )
    if province:
        query = query.filter(models.WSA.province == province)
    if wsa_name:
        query = query.filter(models.WSA.name == wsa_name)
    if issue_type:
        query = query.filter(models.CitizenReport.issue_type == issue_type)
    if min_age_days > 0:
        query = query.filter(models.CitizenReport.created_at <= datetime.now(timezone.utc) - timedelta(days=min_age_days))
    total = query.count()
    rows = query.order_by(models.CitizenReport.created_at.asc()).limit(min(limit, 25)).all()
    now = datetime.now(timezone.utc)
    return {
        "total_matching": total,
        "reports": [
            {
                "reference_code": r.reference_code,
                "wsa_name": r.wsa.name,
                "issue_type": r.issue_type.value,
                "status": r.case_status,
                "age_days": (now - r.created_at).days,
                "description": (r.description or "")[:120],
            }
            for r in rows
        ],
    }


def tool_get_wsa_detail(db: Session, name: str) -> dict:
    # everything known about one authority: indicators, plan, recent risk scores, open reports and unhandled alerts.
    # a name that matches several authorities returns the candidates instead of guessing
    matches = db.query(models.WSA).filter(models.WSA.name.ilike(f"%{name}%")).order_by(models.WSA.name).limit(10).all()
    if not matches:
        return {"error": f"No authority matches '{name}'"}
    exact = [w for w in matches if w.name.lower() == name.lower()]
    if len(matches) > 1 and not exact:
        return {"error": "Several authorities match; ask again with one of these names", "candidates": [w.name for w in matches]}
    wsa = exact[0] if exact else matches[0]
    history = (
        db.query(models.RiskScoreHistory)
        .filter(models.RiskScoreHistory.wsa_id == wsa.id)
        .order_by(models.RiskScoreHistory.scored_at.desc())
        .limit(5)
        .all()
    )
    open_reports = (
        db.query(models.CitizenReport)
        .filter(models.CitizenReport.wsa_id == wsa.id, models.CitizenReport.case_status != "resolved")
        .count()
    )
    open_alerts = db.query(models.Alert).filter(models.Alert.wsa_id == wsa.id, models.Alert.acknowledged_at.is_(None)).count()
    return {
        "name": wsa.name,
        "province": wsa.province,
        "risk_level": wsa.risk_level.value,
        "blue_drop_score": wsa.blue_drop_score,
        "green_drop_score": wsa.green_drop_score,
        "nrw_percent": wsa.nrw_percent,
        "maintenance_percent_of_opex": wsa.maint_pct,
        "cap_status": wsa.cap_status.value,
        "cap_due_date": wsa.cap_due_date.isoformat() if wsa.cap_due_date else None,
        "unresolved_reports": open_reports,
        "unacknowledged_alerts": open_alerts,
        "recent_risk_scores_newest_first": [
            {"date": h.scored_at.date().isoformat(), "risk_level": h.risk_level.value, "probability": float(h.probability), "source": h.model_source.value}
            for h in history
        ],
    }


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
    "count_wsas": tool_count_wsas,
    "get_overdue_caps": tool_get_overdue_caps,
    "get_open_reports": tool_get_open_reports,
    "get_wsa_detail": tool_get_wsa_detail,
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
            "description": "List Water Services Authorities (at most `limit`, max 50), optionally filtered by province, risk level, CAP status or part of the name. Use count_wsas for 'how many'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "province": {"type": "string"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    "cap_status": {"type": "string", "enum": ["none", "submitted", "in_progress", "completed"]},
                    "name_contains": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_wsas",
            "description": "Exact number of authorities matching the filters. Always use this for 'how many' questions instead of counting a list. overdue_only counts plans past their deadline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "province": {"type": "string"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    "cap_status": {"type": "string", "enum": ["none", "submitted", "in_progress", "completed"]},
                    "overdue_only": {"type": "boolean"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_overdue_caps",
            "description": "Corrective action plans past their deadline, longest overdue first, with days overdue.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_open_reports",
            "description": "Unresolved citizen reports, oldest first, with the true total matching. Filter by province, authority name, issue type (leak, outage, quality, billing) or minimum age in days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "province": {"type": "string"},
                    "wsa_name": {"type": "string"},
                    "issue_type": {"type": "string", "enum": ["leak", "outage", "quality", "billing"]},
                    "min_age_days": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wsa_detail",
            "description": "Everything known about one authority by name: indicators, plan and deadline, recent risk scores, unresolved reports and unacknowledged alerts.",
            "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
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
    "Call a tool whenever you need real data. For any 'how many' question use count_wsas or the total a tool reports; never count rows yourself, because lists are cut off. "
    "If a tool returns an error or finds nothing, say so plainly instead of guessing. When you have enough information, give a short, "
    "factual final answer: at most three sentences, or a list of at most five short lines, citing the specific "
    "numbers you found. No introduction and no closing remarks."
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
