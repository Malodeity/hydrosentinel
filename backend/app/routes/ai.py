# All the AI endpoints (OpenAI calls). Map of this file, top to bottom:
#   helpers          call_openai / call_openai_json / call_openai_vision, build_wsa_prompt (the data block every prompt shares)
#   public (no login, limited per visitor address): summaries, digests, risk explanation, comparison, map-view summary, report context
#   admin (login):   recommendations, reports summary, comment drafting
#   admin + hourly allowance (20/hour): CAP draft, regulations, question box, photo analysis, briefing, trend explanation
# Every prompt tells the model to use ONLY the supplied data; the numbers come from the database, the model only writes the wording.

import base64
import json
import time
from typing import Literal
from datetime import datetime, timedelta, timezone
from uuid import UUID

from openai import OpenAI
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ai.query_agent import run_query_agent, tool_count_wsas, tool_get_open_reports, tool_get_overdue_caps, tool_get_trending_wsas
from ai.trajectory import compute_trajectory
from ai.rag import retrieve
from app import auth, models, schemas
from app.config import settings
from app.database import get_db
from app.rate_limit import ai_usage, enforce_ai_rate_limit, enforce_public_ai_limit
from app.routes.reports import UPLOAD_ROOT

router = APIRouter(prefix="/ai", tags=["ai"])

MODEL_NAME = "gpt-4o"


def get_openai_client() -> OpenAI:
    # this creates the openai client only when the api key exists in the environment
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured",
        )
    # the library default read timeout is 600s with 2 retries, far too long for a live admin request
    return OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=1)


def call_openai(system_prompt: str, user_prompt: str, max_tokens: int = 400) -> str:
    # this sends one prompt to openai and returns the response text
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenAI request failed") from exc

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenAI returned an empty response")
    return content


def call_openai_json(system_prompt: str, user_prompt: str, max_tokens: int = 600) -> str:
    # same as call_openai but requests strict JSON output for structured features (e.g. CAP drafting)
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenAI request failed") from exc

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenAI returned an empty response")
    return content


def get_wsa_or_404(db: Session, wsa_id: UUID) -> models.WSA:
    # this loads one wsa row and returns a 404 error when the uuid does not exist
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")
    return wsa


def _average_or_unavailable(values: list[float]) -> float | str:
    # an average over no data must read as "no data", not as 0.0 (which a model reads as a real result)
    if not values:
        return "not available (no data)"
    return round(sum(values) / len(values), 2)


def build_wsa_prompt(wsa: models.WSA) -> str:
    # this builds the shared real-data prompt block used for summary and recommendation generation
    return "\n".join(
        [
            f"WSA name: {wsa.name}",
            f"Province: {wsa.province}",
            f"Blue Drop score: {wsa.blue_drop_score if wsa.blue_drop_score is not None else 'unknown'}",
            f"Blue Drop certification: {wsa.bd_certification.value}",
            # the model must quote DWS's real bands, not recall a threshold from memory (it once said 75)
            "Blue Drop bands: certified 95 and above, non-certified 50 to 94, poor 31 to 49, critical below 31",
            f"Green Drop score: {wsa.green_drop_score if wsa.green_drop_score is not None else 'unknown'}",
            f"NRW percent: {wsa.nrw_percent if wsa.nrw_percent is not None else 'unknown'}",
            f"No Drop performance: {wsa.nd_performance.value}",
            # Treasury's 8% norm is measured against asset value, which the data does not carry, so no benchmark is quoted
            f"Maintenance spending as percent of total operating expenditure: {wsa.maint_pct if wsa.maint_pct is not None else 'unknown'}",
            f"Actual maintenance expenditure (ZAR): {wsa.maint_expenditure if wsa.maint_expenditure is not None else 'unknown'}",
            f"Number of water supply systems: {wsa.num_water_supply_systems if wsa.num_water_supply_systems is not None else 'unknown'}",
            f"Internal CAP status: {wsa.cap_status.value}",
            f"DWS-reported CAP status: {wsa.dws_cap_status.value}",
            f"Risk level: {wsa.risk_level.value}",
        ]
    )


def _national_only(user: models.User) -> None:
    # tools that read across every authority are not offered to an admin tied to one authority
    if user.wsa_id is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="National admin access required")


def get_report_or_404(db: Session, report_id: UUID) -> models.CitizenReport:
    # this loads one citizen report row and returns a 404 error when the uuid does not exist
    report = db.query(models.CitizenReport).filter(models.CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


def build_report_prompt(report: models.CitizenReport, wsa: models.WSA, target_status: str | None = None) -> str:
    # this builds the real-data prompt block used when an admin wants help drafting a case comment
    return "\n".join(
        [
            f"Report id: {report.id}",
            *(
                [f"Current case status: {report.case_status}", f"Status the admin is setting now: {target_status}"]
                if target_status and target_status != report.case_status
                else [f"Case status: {report.case_status}"]
            ),
            f"Issue type: {report.issue_type.value}",
            f"Citizen description: {report.description or 'none provided'}",
            f"Report latitude: {report.lat}",
            f"Report longitude: {report.lng}",
            f"WSA name: {wsa.name}",
            f"WSA province: {wsa.province}",
            f"WSA risk level: {wsa.risk_level.value}",
            f"WSA Blue Drop score: {wsa.blue_drop_score if wsa.blue_drop_score is not None else 'unknown'}",
            f"WSA NRW percent: {wsa.nrw_percent if wsa.nrw_percent is not None else 'unknown'}",
            f"WSA maintenance percent of operating expenditure: {wsa.maint_pct if wsa.maint_pct is not None else 'unknown'}",
            f"WSA CAP status: {wsa.cap_status.value}",
        ]
    )


def parse_numbered_items(content: str) -> list[str]:
    # this turns a numbered or line-based model response into a clean list for the admin page
    items: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cleaned = line
        if len(line) > 2 and line[0].isdigit() and line[1] in {".", ")"}:
            cleaned = line[2:].strip()
        elif line.startswith("- "):
            cleaned = line[2:].strip()
        if cleaned:
            items.append(cleaned)
    return (items or [content.strip()])[:3]


# PUBLIC  GET /ai/wsa/{id}/summary: short AI summary of one authority. Shown as 'AI risk summary' on the CAP tab.
@router.get("/wsa/{wsa_id}/summary", response_model=schemas.AITextResponse, dependencies=[Depends(enforce_public_ai_limit)])
def get_wsa_summary(wsa_id: UUID, db: Session = Depends(get_db)) -> schemas.AITextResponse:
    # this generates a plain-english summary from the real wsa fields and saves it to wsa.summary
    wsa = get_wsa_or_404(db, wsa_id)
    system_prompt = (
        "You explain municipal water service data to South African citizens in plain English. "
        "Write at most two sentences, under 45 words: the risk level and the one or two figures that explain it. "
        "No introduction, stay factual, and do not invent missing data."
    )
    user_prompt = (
        "Write a plain-English risk summary for this Water Services Authority using only the supplied data.\n\n"
        f"{build_wsa_prompt(wsa)}"
    )
    content = call_openai(system_prompt, user_prompt, max_tokens=110)
    wsa.summary = content
    db.add(wsa)
    db.commit()
    db.refresh(wsa)
    return schemas.AITextResponse(content=content)


# ADMIN   GET /ai/wsa/{id}/recommendations: three prioritised actions for one authority. AI assistant tab > 'Focus on one authority'.
@router.get("/wsa/{wsa_id}/recommendations", response_model=schemas.AIRecommendationsResponse)
def get_wsa_recommendations(
    wsa_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AIRecommendationsResponse:
    auth.require_wsa_access(current_user, wsa_id)
    # this generates a short prioritised action list for admins using the real wsa values
    wsa = get_wsa_or_404(db, wsa_id)
    system_prompt = (
        "You advise South African municipal water administrators. "
        "Return exactly 3 numbered items, most important first. Each item is one short imperative sentence under 14 words. "
        "No heading, no explanation."
    )
    user_prompt = (
        "Using the real WSA data below, write a prioritised action list for the municipal admin.\n\n"
        f"{build_wsa_prompt(wsa)}"
    )
    content = call_openai(system_prompt, user_prompt, max_tokens=130)
    return schemas.AIRecommendationsResponse(content=content, items=parse_numbered_items(content))


# ADMIN + allowance  GET /ai/wsa/{id}/trend-explanation: why an authority is on the 'trending toward higher risk' list. Overview 'Why?' link.
@router.get("/wsa/{wsa_id}/trend-explanation", response_model=schemas.AITextResponse)
def get_trend_explanation(
    wsa_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(enforce_ai_rate_limit),
) -> schemas.AITextResponse:
    # explains, from the authority's own scoring history, why it appears on the "trending toward higher risk" list
    wsa = get_wsa_or_404(db, wsa_id)
    history = (
        db.query(models.RiskScoreHistory)
        .filter(models.RiskScoreHistory.wsa_id == wsa_id)
        .order_by(models.RiskScoreHistory.scored_at.asc())
        .all()
    )
    if len(history) < 2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not enough scoring history to explain a trend")
    trajectory = compute_trajectory([float(h.probability) for h in history])
    scores = "\n".join(
        f"- {h.scored_at.date().isoformat()}: {h.risk_level.value} risk, probability {float(h.probability):.2f}, scored by {h.model_source.value}"
        for h in history[-6:]
    )
    system_prompt = (
        "You explain an early-warning risk trend to a South African municipal water administrator. "
        "Write at most 3 short sentences (under 70 words in total): what the recent scores show, why it matters using one number "
        "from the data, and the first thing to check. Never invent causes or data. "
        "If the scores come from different sources (xgboost and heuristic), say they are not directly comparable."
    )
    user_prompt = "\n".join([
        build_wsa_prompt(wsa),
        f"Projected next level: {trajectory['projected_risk_level']} (probability {trajectory['projected_probability']})",
        "Recent risk scores, oldest first:",
        scores,
    ])
    return schemas.AITextResponse(content=call_openai(system_prompt, user_prompt, max_tokens=140))


# ADMIN   GET /ai/usage: how many of the 20 hourly AI calls are used. Does not use a call itself. Shown as the meter on the AI assistant tab.
@router.get("/usage", response_model=schemas.AIUsage)
def get_ai_usage(current_user: models.User = Depends(auth.get_current_admin_user)) -> dict:
    # how many of this admin's 20 hourly AI calls are used. does not itself use a call
    return ai_usage(current_user)


# ADMIN + allowance  GET /ai/admin-briefing: the start-of-day note on the AI assistant tab.
@router.get("/admin-briefing", response_model=schemas.AdminBriefing)
def get_admin_briefing(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(enforce_ai_rate_limit),
) -> schemas.AdminBriefing:
    _national_only(current_user)
    # a short "start here" note for the admin. the numbers come from the database (the same tools the question box uses, so they cannot
    # disagree with it); the model only decides the wording and the order of priorities
    waiting = tool_get_open_reports(db, min_age_days=14, limit=3)
    all_open = tool_get_open_reports(db, limit=1)
    overdue = tool_get_overdue_caps(db)
    trending = tool_get_trending_wsas(db)
    unacknowledged = db.query(models.Alert).filter(models.Alert.acknowledged_at.is_(None)).count()
    facts = {
        "unresolved_reports": all_open["total_matching"],
        "reports_waiting_14_days": waiting["total_matching"],
        "overdue_plans": len(overdue),
        "high_risk_without_plan": tool_count_wsas(db, risk_level="high", cap_status="none")["count"],
        "unacknowledged_alerts": unacknowledged,
        "authorities_trending_worse": len(trending),
    }
    lines = [f"- {key.replace('_', ' ')}: {value}" for key, value in facts.items()]
    if overdue:
        lines.append("Longest overdue plans: " + "; ".join(f"{o['name']} ({o['days_overdue']} days)" for o in overdue[:3]))
    if waiting["reports"]:
        lines.append("Oldest waiting reports: " + "; ".join(f"{r['wsa_name']} {r['issue_type']} ({r['age_days']} days)" for r in waiting["reports"]))
    if trending:
        lines.append("Trending worse: " + "; ".join(t["name"] for t in trending[:3]))
    system_prompt = (
        "You write a short start-of-day briefing for a South African municipal water administrator. "
        "First line: one sentence on the overall situation. Then at most 3 numbered priorities, most urgent first, each one short sentence "
        "naming a number or authority from the data. Use only the facts given; never invent a number, name or cause. "
        "If everything is zero, say nothing is urgent."
    )
    content = call_openai(system_prompt, "Today's facts:\n" + "\n".join(lines), max_tokens=220)
    return schemas.AdminBriefing(content=content, facts=facts)


# PUBLIC  GET /ai/digest: national summary on the dashboard. Saved for 24 hours so most visits cost nothing.
@router.get("/digest", response_model=schemas.AITextResponse)
def get_ai_digest(db: Session = Depends(get_db)) -> schemas.AITextResponse:
    # this returns the last digest when it is fresh and otherwise generates and stores a new one
    latest_digest = db.query(models.Summary).order_by(models.Summary.generated_at.desc()).first()
    now = datetime.now(timezone.utc)
    if latest_digest and latest_digest.generated_at >= now - timedelta(hours=24):
        return schemas.AITextResponse(content=latest_digest.content)

    wsas = db.query(models.WSA).all()
    if not wsas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No WSA records available")

    high_count = sum(1 for item in wsas if item.risk_level == models.RiskLevel.high)
    medium_count = sum(1 for item in wsas if item.risk_level == models.RiskLevel.medium)
    low_count = sum(1 for item in wsas if item.risk_level == models.RiskLevel.low)
    avg_blue_drop = _average_or_unavailable([w.blue_drop_score for w in wsas if w.blue_drop_score is not None])
    avg_nrw = _average_or_unavailable([w.nrw_percent for w in wsas if w.nrw_percent is not None])
    completed_cap = sum(1 for item in wsas if item.cap_status == models.CAPStatus.completed)

    system_prompt = (
        "You write short national water monitoring digests for a public South African dashboard. "
        "Write at most two plain-English sentences, under 50 words. Stay factual and do not invent data."
    )
    user_prompt = "\n".join(
        [
            "Write a national HydroSentinel dashboard digest using these real aggregate values.",
            f"Total WSAs: {len(wsas)}",
            f"High risk WSAs: {high_count}",
            f"Medium risk WSAs: {medium_count}",
            f"Low risk WSAs: {low_count}",
            f"Average Blue Drop score: {avg_blue_drop}",
            f"Average NRW percent: {avg_nrw}",
            f"CAP completed count: {completed_cap}",
        ]
    )
    content = call_openai(system_prompt, user_prompt, max_tokens=110)
    digest = models.Summary(content=content)
    db.add(digest)
    db.commit()
    return schemas.AITextResponse(content=content)


# ponytail: in-memory per-process cache, 10 minute TTL. A shared store if the API ever runs on several servers.
_MAP_SUMMARY_TTL_SECONDS = 600
_map_summary_cache: dict[int, tuple[float, str]] = {}
_RISK_ORDER = {models.RiskLevel.high: 0, models.RiskLevel.medium: 1, models.RiskLevel.low: 2}


# PUBLIC  GET /ai/map-view-summary: summarises the authorities inside the map area on screen ('Summarise this view' button).
@router.get("/map-view-summary", response_model=schemas.MapViewSummaryResponse, dependencies=[Depends(enforce_public_ai_limit)])
def get_map_view_summary(
    south: float = Query(ge=-90, le=90),
    north: float = Query(ge=-90, le=90),
    west: float = Query(ge=-180, le=180),
    east: float = Query(ge=-180, le=180),
    db: Session = Depends(get_db),
) -> schemas.MapViewSummaryResponse:
    # this describes the authorities inside the visible map bounds; the counts come from the database
    # and only real facts reach the model, so the summary cannot mention an authority outside the view
    if south >= north or west >= east:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid map bounds")

    wsas = (
        db.query(models.WSA)
        .filter(models.WSA.lat.between(south, north), models.WSA.lng.between(west, east))
        .all()
    )
    if not wsas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No authorities in this view")

    open_reports = (
        db.query(models.CitizenReport)
        .filter(
            models.CitizenReport.lat.between(south, north),
            models.CitizenReport.lng.between(west, east),
            models.CitizenReport.case_status.in_(["open", "in_review"]),
        )
        .count()
    )
    stats = schemas.MapViewStats(
        total=len(wsas),
        high=sum(1 for w in wsas if w.risk_level == models.RiskLevel.high),
        medium=sum(1 for w in wsas if w.risk_level == models.RiskLevel.medium),
        low=sum(1 for w in wsas if w.risk_level == models.RiskLevel.low),
        open_reports=open_reports,
    )

    # panning a little keeps the same authorities in view, so key the cache on who is visible
    cache_key = hash((tuple(sorted(str(w.id) for w in wsas)), open_reports))
    cached = _map_summary_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _MAP_SUMMARY_TTL_SECONDS:
        return schemas.MapViewSummaryResponse(stats=stats, content=cached[1])

    scores = [w.blue_drop_score for w in wsas if w.blue_drop_score is not None]
    most_at_risk = sorted(
        wsas,
        key=lambda w: (_RISK_ORDER[w.risk_level], w.blue_drop_score if w.blue_drop_score is not None else 101.0),
    )[:5]
    system_prompt = (
        "You describe what is visible on a South African water risk map for a public dashboard. "
        "Write at most two plain-English sentences, under 45 words in total. Use only the numbers and names provided. "
        "Do not invent data and do not give advice."
    )
    user_prompt = "\n".join(
        [
            "Describe the authorities currently in view on the map.",
            f"Water service authorities in view: {stats.total}",
            f"High risk: {stats.high}, medium risk: {stats.medium}, low risk: {stats.low}",
            f"Average Blue Drop score in view: {_average_or_unavailable(scores)}",
            f"Provinces in view: {', '.join(sorted({w.province for w in wsas}))}",
            f"Open or in-review citizen reports in view: {stats.open_reports}",
            "Authorities at highest risk in view (highest risk first):",
            *[
                f"- {w.name}: {w.risk_level.value} risk, Blue Drop score "
                f"{w.blue_drop_score if w.blue_drop_score is not None else 'unknown'}, CAP status {w.cap_status.value}"
                for w in most_at_risk
            ],
        ]
    )
    try:
        content = call_openai(system_prompt, user_prompt, max_tokens=110)
    except HTTPException:
        # the map still works without the model: return the counts and let the page say the summary is unavailable
        return schemas.MapViewSummaryResponse(stats=stats, content=None)

    _map_summary_cache[cache_key] = (time.monotonic(), content)
    return schemas.MapViewSummaryResponse(stats=stats, content=content)


# PUBLIC  GET /ai/wsa/{id}/risk-explanation: 'Explain this rating with AI' on the dashboard authority card.
@router.get("/wsa/{wsa_id}/risk-explanation", response_model=schemas.AITextResponse, dependencies=[Depends(enforce_public_ai_limit)])
def get_risk_explanation(wsa_id: UUID, db: Session = Depends(get_db)) -> schemas.AITextResponse:
    # this explains in plain English why the wsa carries its current risk level
    wsa = get_wsa_or_404(db, wsa_id)
    system_prompt = (
        "You explain South African municipal water risk to non-technical citizens and officials. "
        "Write at most two sentences, under 40 words, giving the key reasons for this WSA's risk level. "
        "Be specific, factual, and do not invent data."
    )
    user_prompt = (
        "Explain why this WSA has its current risk level based only on the data below.\n\n"
        f"{build_wsa_prompt(wsa)}"
    )
    return schemas.AITextResponse(content=call_openai(system_prompt, user_prompt, max_tokens=200))


# PUBLIC  GET /ai/wsa/{id}/comparison: compares one authority with others in its province (dashboard 'Provincial comparison' tab).
@router.get("/wsa/{wsa_id}/comparison", response_model=schemas.AITextResponse, dependencies=[Depends(enforce_public_ai_limit)])
def get_wsa_comparison(wsa_id: UUID, db: Session = Depends(get_db)) -> schemas.AITextResponse:
    # this compares the wsa against others in the same province so users have relative context
    wsa = get_wsa_or_404(db, wsa_id)
    peers = db.query(models.WSA).filter(
        models.WSA.province == wsa.province,
        models.WSA.id != wsa.id,
        models.WSA.blue_drop_score.isnot(None),
    ).all()

    if not peers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not enough WSAs in province to compare")

    bd_scores = [p.blue_drop_score for p in peers if p.blue_drop_score is not None]
    avg_bd = round(sum(bd_scores) / len(bd_scores), 1) if bd_scores else None
    rank = sum(1 for s in bd_scores if s > (wsa.blue_drop_score or 0)) + 1

    system_prompt = (
        "You compare South African water service authorities for a public dashboard. "
        "Write at most two plain-English sentences, under 40 words. Be specific and factual."
    )
    user_prompt = "\n".join([
        f"Compare {wsa.name} against the other {len(peers)} WSAs in {wsa.province}.",
        f"{wsa.name} Blue Drop score: {wsa.blue_drop_score}%",
        f"Province average Blue Drop score: {avg_bd}%",
        f"Rank in province by Blue Drop score: {rank} of {len(peers) + 1}",
        f"{wsa.name} NRW percent: {wsa.nrw_percent}",
        f"{wsa.name} risk level: {wsa.risk_level.value}",
        f"{wsa.name} CAP status: {wsa.cap_status.value}",
    ])
    return schemas.AITextResponse(content=call_openai(system_prompt, user_prompt, max_tokens=200))


# PUBLIC  GET /ai/province/{name}/digest: summary of one province (dashboard 'Province digest' tab).
@router.get("/province/{province}/digest", response_model=schemas.AITextResponse, dependencies=[Depends(enforce_public_ai_limit)])
def get_province_digest(province: str, db: Session = Depends(get_db)) -> schemas.AITextResponse:
    # this generates a province-level summary from all wsas in that province
    wsas = db.query(models.WSA).filter(models.WSA.province == province).all()
    if not wsas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No WSAs found for this province")

    bd_scores = [w.blue_drop_score for w in wsas if w.blue_drop_score is not None]
    avg_bd = round(sum(bd_scores) / len(bd_scores), 1) if bd_scores else None
    high_risk = sum(1 for w in wsas if w.risk_level == models.RiskLevel.high)
    critical = sum(1 for w in wsas if w.bd_certification == models.BDCertification.critical)

    system_prompt = (
        "You write concise provincial water service summaries for a public South African dashboard. "
        "Write at most two plain-English sentences, under 50 words. Stay factual and do not invent data."
    )
    user_prompt = "\n".join([
        f"Write a water service summary for {province} province.",
        f"Total WSAs: {len(wsas)}",
        f"Average Blue Drop score: {avg_bd}%",
        f"High risk WSAs: {high_risk}",
        f"WSAs with critical Blue Drop certification: {critical}",
        f"WSAs with completed CAP: {sum(1 for w in wsas if w.cap_status == models.CAPStatus.completed)}",
    ])
    return schemas.AITextResponse(content=call_openai(system_prompt, user_prompt, max_tokens=200))


# ADMIN   GET /ai/wsa/{id}/reports-summary: what the open citizen reports for an authority add up to (CAP tab, and AI assistant tab).
@router.get("/wsa/{wsa_id}/reports-summary", response_model=schemas.AITextResponse)
def get_reports_summary(
    wsa_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AITextResponse:
    auth.require_wsa_access(current_user, wsa_id)
    # this summarises all open and in-review citizen reports for a wsa to help admins triage quickly
    wsa = get_wsa_or_404(db, wsa_id)
    reports = (
        db.query(models.CitizenReport)
        .filter(
            models.CitizenReport.wsa_id == wsa_id,
            models.CitizenReport.case_status.in_(["open", "in_review"]),
        )
        .all()
    )
    if not reports:
        return schemas.AITextResponse(content="No open or in-review reports for this WSA.")

    from collections import Counter
    type_counts = Counter(r.issue_type.value for r in reports)
    descriptions = "\n".join(
        f"- [{r.issue_type.value}] {r.description or 'no description'}"
        for r in reports[:20]
    )

    system_prompt = (
        "You help South African municipal admins triage citizen water service reports. "
        "Write at most two sentences, under 40 words, grouping the reports by type and naming any pattern or hotspot. "
        "Be practical. No introduction."
    )
    user_prompt = "\n".join([
        f"Summarise these {len(reports)} open citizen reports for {wsa.name} ({wsa.province}).",
        f"Issue breakdown: {dict(type_counts)}",
        "Report descriptions:",
        descriptions,
    ])
    return schemas.AITextResponse(content=call_openai(system_prompt, user_prompt, max_tokens=220))


# PUBLIC  GET /ai/wsa/{id}/report-context: the short reply a resident sees right after submitting a report.
@router.get("/wsa/{wsa_id}/report-context", response_model=schemas.AITextResponse, dependencies=[Depends(enforce_public_ai_limit)])
def get_report_context(
    wsa_id: UUID,
    issue_type: str = "general",
    db: Session = Depends(get_db),
) -> schemas.AITextResponse:
    # this gives a citizen targeted context about their wsa after submitting a report
    wsa = get_wsa_or_404(db, wsa_id)
    system_prompt = (
        "You give South African citizens brief, helpful context about their water service after they submit a report. "
        "Keep it to 2 sentences, under 35 words. Acknowledge their specific issue type, mention one relevant fact about the WSA, "
        "and end with reassurance that the report has been logged. Do not invent data."
    )
    user_prompt = "\n".join([
        f"A citizen just submitted a '{issue_type}' report for {wsa.name} in {wsa.province}.",
        f"WSA Blue Drop score: {wsa.blue_drop_score if wsa.blue_drop_score is not None else 'unknown'}",
        f"WSA NRW percent: {wsa.nrw_percent if wsa.nrw_percent is not None else 'unknown'}",
        f"WSA risk level: {wsa.risk_level.value}",
        f"WSA CAP status: {wsa.cap_status.value}",
        "Write a short, reassuring, factual message for the citizen.",
    ])
    return schemas.AITextResponse(content=call_openai(system_prompt, user_prompt, max_tokens=120))


# what the note should say for each status the admin can choose, so it matches the change they are about to save
_COMMENT_GUIDE = {
    "open": "The case stays open. Say it has been logged and is waiting for review.",
    "in_review": "The admin is moving the case to in review. Say the team has started reviewing it and what will be checked next.",
    "resolved": (
        "The admin is closing the case as resolved. Say the team is closing the case and the resident can submit a new report "
        "if the problem continues. Do not describe repair work unless the data states it."
    ),
}


# ADMIN   GET /ai/reports/{id}/comment: drafts the admin note for a report; it follows the status the admin has selected ('AI comment' button).
@router.get("/reports/{report_id}/comment", response_model=schemas.AITextResponse)
def generate_report_comment(
    report_id: UUID,
    case_status: Literal["open", "in_review", "resolved"] | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AITextResponse:
    # this drafts the case note for the status the admin has selected (saved or not) so the note matches the change
    report = get_report_or_404(db, report_id)
    auth.require_wsa_access(current_user, report.wsa_id)
    wsa = get_wsa_or_404(db, report.wsa_id)
    target = case_status or report.case_status
    system_prompt = (
        "You help South African municipal admins write the short note saved with a citizen report's status change. "
        "Write at most two sentences, under 40 words, in plain English, with no greeting or sign-off. "
        "Do not invent completed actions. " + _COMMENT_GUIDE.get(target, _COMMENT_GUIDE["open"])
    )
    user_prompt = (
        "Draft the admin's case note for this citizen report using only the supplied report and WSA data.\n\n"
        f"{build_report_prompt(report, wsa, target)}"
    )
    content = call_openai(system_prompt, user_prompt, max_tokens=90)
    return schemas.AITextResponse(content=content)


# ---------------------------------------------------------------------------------------------------------------------
# photo analysis: an admin asks GPT-4o (vision) what a resident's photo shows. it is on demand, admin only and rate limited
# because every call costs money and sends the photo to OpenAI, so it never runs automatically on a public upload
# ---------------------------------------------------------------------------------------------------------------------
_IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
_MAX_ANALYSIS_BYTES = 4 * 1024 * 1024
_PHOTO_ISSUES = {"leak", "quality", "outage", "not_water_related", "unclear"}
_LEVELS = {"low", "medium", "high"}

_PHOTO_SYSTEM_PROMPT = (
    "You help South African municipal water officials check a photo that a resident sent with a water service report. "
    "Say only what is visibly shown, and never guess beyond it. "
    'Return ONLY a JSON object: {"issue_type": "leak"|"quality"|"outage"|"not_water_related"|"unclear", '
    '"severity": "low"|"medium"|"high", "confidence": "low"|"medium"|"high", "summary": string}. '
    "leak = water escaping from a pipe, hydrant or meter, or flooding. quality = discoloured, dirty or contaminated-looking water. "
    "outage = a dry tap or empty water infrastructure. not_water_related = no water service problem is visible. "
    "unclear = you cannot tell. The summary is one sentence of at most 25 words about the water issue only. "
    "Do not identify or describe people, faces, vehicle number plates or street addresses."
)


def call_openai_vision(system_prompt: str, user_text: str, image_bytes: bytes, mime: str) -> str:
    # like call_openai_json but sends one image too; detail=low keeps the cost and the wait small
    client = get_openai_client()
    data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=160,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
                ]},
            ],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenAI request failed") from exc

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenAI returned an empty response")
    return content


def _photo_verdict(suggested: str, reported: str) -> str:
    # a photo can only prove or disprove what a photo can show: an unclear photo or a billing report is inconclusive
    if suggested == "unclear" or reported == "billing":
        return "inconclusive"
    return "matches" if suggested == reported else "mismatch"


def parse_photo_analysis(content: str, reported_issue: str) -> dict | None:
    # the model's reply is only trusted after it is checked: any value outside the allowed lists becomes the safe default,
    # and the verdict is worked out here from the model's issue_type and what the resident reported, never taken from the model
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    issue = data.get("issue_type") if data.get("issue_type") in _PHOTO_ISSUES else "unclear"
    return {
        "issue_type": issue,
        "severity": data.get("severity") if data.get("severity") in _LEVELS else "low",
        "confidence": data.get("confidence") if data.get("confidence") in _LEVELS else "low",
        "summary": str(data.get("summary") or "").strip()[:200],
        "verdict": _photo_verdict(issue, reported_issue),
    }


# ADMIN + allowance  POST /ai/reports/{id}/analyze-photo: GPT-4o looks at one photo and the SERVER decides if it matches the reported issue.
@router.post("/reports/{report_id}/analyze-photo", response_model=schemas.PhotoAnalysis)
def analyze_report_photo(
    report_id: UUID,
    photo_index: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(enforce_ai_rate_limit),
) -> schemas.PhotoAnalysis:
    # admin only. checks everything that can be checked BEFORE spending an openai call (a photo exists, it is an image, it is not huge).
    # the model is deliberately not told what the resident reported, so it cannot simply agree; we compare afterwards
    report = get_report_or_404(db, report_id)
    auth.require_wsa_access(current_user, report.wsa_id)
    folder = UPLOAD_ROOT / str(report.id)
    photos = sorted(path for path in folder.iterdir() if path.is_file()) if folder.exists() else []
    if not photos or photo_index >= len(photos):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This report has no such photo")

    photo = photos[photo_index]
    mime = _IMAGE_TYPES.get(photo.suffix.lower())
    if mime is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="That file is not a supported image")
    if photo.stat().st_size > _MAX_ANALYSIS_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="That photo is too large to analyse")

    content = call_openai_vision(
        _PHOTO_SYSTEM_PROMPT,
        "Look at this photo from a resident's water service report and answer in the JSON format.",
        photo.read_bytes(),
        mime,
    )
    analysis = parse_photo_analysis(content, report.issue_type.value)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not read the photo analysis")

    analysis["photo"] = photo.name
    analysis["analysed_at"] = datetime.now(timezone.utc).isoformat()
    report.photo_analysis = analysis
    db.add(report)
    db.commit()
    return schemas.PhotoAnalysis(**analysis)


_VALID_PRIORITIES = {"high", "medium", "low"}


def parse_cap_draft_json(content: str) -> list[dict]:
    # the model occasionally returns malformed JSON, the wrong shape, or a
    # garbage priority value -- this is the boundary that must degrade to an
    # empty/partial list instead of ever crashing the endpoint
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        return []
    if not isinstance(items, list):
        return []

    valid: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        action = item.get("action")
        if not action or not isinstance(action, str):
            continue

        priority = item.get("priority")
        priority = priority if priority in _VALID_PRIORITIES else "medium"

        due_days = item.get("suggested_due_in_days")
        due_days = due_days if isinstance(due_days, int) and not isinstance(due_days, bool) else None

        valid.append({
            "action": action,
            "priority": priority,
            "suggested_due_in_days": due_days,
            "justification": str(item.get("justification") or ""),
        })

    return valid[:6]


# ADMIN + allowance  GET /ai/wsa/{id}/cap-draft: 3-5 suggested corrective actions with priority and deadline ('Draft CAP', CAP tab).
@router.get("/wsa/{wsa_id}/cap-draft", response_model=schemas.CapDraftResponse)
def get_cap_draft(
    wsa_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(enforce_ai_rate_limit),
) -> schemas.CapDraftResponse:
    auth.require_wsa_access(current_user, wsa_id)
    # drafts a structured, evidence-linked corrective action plan an admin
    # can review and edit, instead of a single paragraph of prose
    wsa = get_wsa_or_404(db, wsa_id)

    from collections import Counter
    open_reports = (
        db.query(models.CitizenReport)
        .filter(
            models.CitizenReport.wsa_id == wsa_id,
            models.CitizenReport.case_status.in_(["open", "in_review"]),
        )
        .all()
    )
    issue_counts = dict(Counter(r.issue_type.value for r in open_reports))

    system_prompt = (
        "You are drafting a Corrective Action Plan (CAP) for a South African municipal water administrator. "
        "Return ONLY a JSON object of the exact shape "
        '{"items": [{"action": string, "priority": "high"|"medium"|"low", '
        '"suggested_due_in_days": integer, "justification": string}]}. '
        "Produce 3 to 5 items. Each action is a short imperative under 12 words. Each justification is one sentence under 20 words "
        "that cites a specific number from the supplied data (a score, a percentage, or a report count) -- never invent data, thresholds or a completed action."
    )
    user_prompt = "\n".join([
        "Draft a corrective action plan using only the real data below.",
        build_wsa_prompt(wsa),
        f"Open citizen reports by issue type: {issue_counts or 'none'}",
    ])

    content = call_openai_json(system_prompt, user_prompt)
    items = parse_cap_draft_json(content)
    if not items:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not generate a structured CAP draft")

    return schemas.CapDraftResponse(items=items)


# ADMIN + allowance  GET /ai/regulatory-context: answers from the DWS PDFs with page citations ('Ask the regulations').
@router.get("/regulatory-context", response_model=schemas.RegulatoryContextResponse)
def get_regulatory_context(
    query: str,
    _: models.User = Depends(enforce_ai_rate_limit),
) -> schemas.RegulatoryContextResponse:
    # answers a question using only excerpts actually retrieved from the DWS
    # regulatory PDFs already in data/raw/, with a source+page citation per
    # excerpt -- every claim in the answer can be traced back to a real page
    excerpts = retrieve(query, top_k=5)
    if not excerpts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No relevant excerpts found in the indexed regulatory documents")

    context_block = "\n\n".join(f"[{e['source']} p.{e['page']}]\n{e['text'][:1000]}" for e in excerpts)
    system_prompt = (
        "You answer questions about South African water regulation using ONLY the supplied excerpts. "
        "Answer in at most three sentences, with no introduction. "
        "Cite the source file and page for every claim, like (source.pdf, p.12). "
        "If the excerpts do not answer the question, say so plainly instead of guessing."
    )
    user_prompt = f"Question: {query}\n\nExcerpts:\n{context_block}"
    answer = call_openai(system_prompt, user_prompt, max_tokens=220)

    return schemas.RegulatoryContextResponse(
        answer=answer,
        sources=[schemas.RegulatorySource(source=e["source"], page=e["page"], score=round(e["score"], 3)) for e in excerpts],
    )


# ADMIN + allowance  POST /ai/query: the question box over live data (see ai/query_agent.py).
@router.post("/query", response_model=schemas.AIQueryResponse)
def post_ai_query(
    payload: schemas.AIQueryRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(enforce_ai_rate_limit),
) -> schemas.AIQueryResponse:
    # the question box reads every authority's data, so it is for national admins only
    _national_only(current_user)
    # a natural-language front end over the platform's own data: the model
    # calls real read-only queries (ai/query_agent.py) instead of reciting a
    # canned digest — "which Eastern Cape WSAs got worse and still have no
    # CAP" gets answered with actual rows, not a paragraph.
    # run_query_agent() creates its own OpenAI client via get_openai_client()
    # when none is injected, which already raises 503 if the key is missing —
    # same pattern as every other endpoint in this file.
    answer, trace = run_query_agent(payload.question, db)
    return schemas.AIQueryResponse(
        answer=answer,
        tool_calls=[schemas.AIQueryToolCall(**t) for t in trace],
    )


# ADMIN + allowance  GET /ai/reports/{id}/work-order: a draft ticket for a report. the contractor suggestion is plain rules (covers this authority and
# issue type, fewest open tickets, fewest rejections); GPT-4o only writes the instructions. nothing is saved: the admin edits and clicks Assign.
@router.get("/reports/{report_id}/work-order", response_model=schemas.WorkOrderDraft)
def draft_work_order(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(enforce_ai_rate_limit),
) -> schemas.WorkOrderDraft:
    from app import assignment_helpers as helpers

    report = get_report_or_404(db, report_id)
    auth.require_wsa_access(current_user, report.wsa_id)
    wsa = get_wsa_or_404(db, report.wsa_id)

    def load(contractor: models.Contractor) -> tuple[int, int]:
        tickets = db.query(models.ReportAssignment).filter(models.ReportAssignment.contractor_id == contractor.id).all()
        return (sum(1 for t in tickets if t.status in helpers.ACTIVE), sum(1 for t in tickets if t.status == "rejected"))

    fits = [
        c for c in db.query(models.Contractor).filter(models.Contractor.is_active.is_(True)).all()
        if helpers.can_serve(db, c.id, report.wsa_id, report.issue_type.value)
    ]
    best = min(fits, key=lambda c: (*load(c), c.name)) if fits else None
    if best:
        open_count, rejected = load(best)
        reason = f"Works on {report.issue_type.value} reports for {wsa.name}; {open_count} open ticket(s), {rejected} rejected so far."
    else:
        reason = f"No active contractor is set up for {report.issue_type.value} reports in {wsa.name}. Add one under Contractors."

    analysis = report.photo_analysis or {}
    photo_line = f"AI photo check: {analysis.get('summary')}" if analysis else "No photo analysis."
    system_prompt = (
        "You write work instructions for a water repair contractor in South Africa. Write at most 3 short sentences, plain English, "
        "no greeting. Say what was reported, where (use the coordinates), and what to check or do first. Use ONLY the supplied facts and do not invent details."
    )
    user_prompt = (
        f"Issue type: {report.issue_type.value}\nCitizen description: {report.description or 'none provided'}\n"
        f"Location: {report.lat}, {report.lng} in {wsa.name} ({wsa.province})\n{photo_line}"
    )
    try:
        instructions = call_openai(system_prompt, user_prompt, max_tokens=120)
    except HTTPException:
        # no key or OpenAI down: a plain template is still a usable draft
        instructions = (
            f"Attend to the reported {report.issue_type.value} at {report.lat}, {report.lng} ({wsa.name}). "
            f"Resident says: {report.description or 'no description given'}. Confirm the fault on site and report what you find."
        )
    return schemas.WorkOrderDraft(
        instructions=instructions,
        suggested_contractor_id=best.id if best else None,
        suggested_contractor_name=best.name if best else None,
        reason=reason,
        due_at=helpers.default_due(report.issue_type.value),
    )
