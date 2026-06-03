from datetime import datetime, timedelta, timezone
from uuid import UUID

from openai import OpenAI
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/ai", tags=["ai"])

MODEL_NAME = "gpt-4o"


def get_openai_client() -> OpenAI:
    # this creates the openai client only when the api key exists in the environment
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured",
        )
    return OpenAI(api_key=settings.openai_api_key)


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


def get_wsa_or_404(db: Session, wsa_id: UUID) -> models.WSA:
    # this loads one wsa row and returns a 404 error when the uuid does not exist
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")
    return wsa


def build_wsa_prompt(wsa: models.WSA) -> str:
    # this builds the shared real-data prompt block used for summary and recommendation generation
    maint_gap = round(wsa.maint_pct - 8.0, 2) if wsa.maint_pct is not None else None
    return "\n".join(
        [
            f"WSA name: {wsa.name}",
            f"Province: {wsa.province}",
            f"Blue Drop score: {wsa.blue_drop_score if wsa.blue_drop_score is not None else 'unknown'}",
            f"Blue Drop certification: {wsa.bd_certification.value}",
            f"Green Drop score: {wsa.green_drop_score if wsa.green_drop_score is not None else 'unknown'}",
            f"NRW percent: {wsa.nrw_percent if wsa.nrw_percent is not None else 'unknown'}",
            f"No Drop performance: {wsa.nd_performance.value}",
            f"Maintenance percent of asset value: {wsa.maint_pct if wsa.maint_pct is not None else 'unknown'}",
            f"Maintenance gap vs 8% benchmark: {maint_gap if maint_gap is not None else 'unknown'}",
            f"Asset value (ZAR): {wsa.asset_value if wsa.asset_value is not None else 'unknown'}",
            f"Actual maintenance expenditure (ZAR): {wsa.maint_expenditure if wsa.maint_expenditure is not None else 'unknown'}",
            f"Number of water supply systems: {wsa.num_water_supply_systems if wsa.num_water_supply_systems is not None else 'unknown'}",
            f"Internal CAP status: {wsa.cap_status.value}",
            f"DWS-reported CAP status: {wsa.dws_cap_status.value}",
            f"Risk level: {wsa.risk_level.value}",
        ]
    )


def get_report_or_404(db: Session, report_id: UUID) -> models.CitizenReport:
    # this loads one citizen report row and returns a 404 error when the uuid does not exist
    report = db.query(models.CitizenReport).filter(models.CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


def build_report_prompt(report: models.CitizenReport, wsa: models.WSA) -> str:
    # this builds the real-data prompt block used when an admin wants help drafting a case comment
    return "\n".join(
        [
            f"Report id: {report.id}",
            f"Case status: {report.case_status}",
            f"Issue type: {report.issue_type.value}",
            f"Citizen description: {report.description or 'none provided'}",
            f"Report latitude: {report.lat}",
            f"Report longitude: {report.lng}",
            f"WSA name: {wsa.name}",
            f"WSA province: {wsa.province}",
            f"WSA risk level: {wsa.risk_level.value}",
            f"WSA Blue Drop score: {wsa.blue_drop_score if wsa.blue_drop_score is not None else 'unknown'}",
            f"WSA NRW percent: {wsa.nrw_percent if wsa.nrw_percent is not None else 'unknown'}",
            f"WSA maintenance percent: {wsa.maint_pct if wsa.maint_pct is not None else 'unknown'}",
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


@router.get("/wsa/{wsa_id}/summary", response_model=schemas.AITextResponse)
def get_wsa_summary(wsa_id: UUID, db: Session = Depends(get_db)) -> schemas.AITextResponse:
    # this generates a plain-english summary from the real wsa fields and saves it to wsa.summary
    wsa = get_wsa_or_404(db, wsa_id)
    system_prompt = (
        "You explain municipal water service data to South African citizens in plain English. "
        "Keep the response to one short paragraph, stay factual, and do not invent missing data."
    )
    user_prompt = (
        "Write a plain-English risk summary for this Water Services Authority using only the supplied data.\n\n"
        f"{build_wsa_prompt(wsa)}"
    )
    content = call_openai(system_prompt, user_prompt, max_tokens=220)
    wsa.summary = content
    db.add(wsa)
    db.commit()
    db.refresh(wsa)
    return schemas.AITextResponse(content=content)


@router.get("/wsa/{wsa_id}/recommendations", response_model=schemas.AIRecommendationsResponse)
def get_wsa_recommendations(
    wsa_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AIRecommendationsResponse:
    # this generates a short prioritised action list for admins using the real wsa values
    wsa = get_wsa_or_404(db, wsa_id)
    system_prompt = (
        "You advise South African municipal water administrators. "
        "Return a concise prioritised action list with exactly 3 numbered items and no extra heading."
    )
    user_prompt = (
        "Using the real WSA data below, write a prioritised action list for the municipal admin.\n\n"
        f"{build_wsa_prompt(wsa)}"
    )
    content = call_openai(system_prompt, user_prompt, max_tokens=260)
    return schemas.AIRecommendationsResponse(content=content, items=parse_numbered_items(content))


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
    avg_blue_drop = round(
        sum(item.blue_drop_score for item in wsas if item.blue_drop_score is not None)
        / max(1, sum(1 for item in wsas if item.blue_drop_score is not None)),
        2,
    )
    avg_nrw = round(
        sum(item.nrw_percent for item in wsas if item.nrw_percent is not None)
        / max(1, sum(1 for item in wsas if item.nrw_percent is not None)),
        2,
    )
    completed_cap = sum(1 for item in wsas if item.cap_status == models.CAPStatus.completed)

    system_prompt = (
        "You write short national water monitoring digests for a public South African dashboard. "
        "Write one plain-English paragraph, stay factual, and do not invent data."
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
    content = call_openai(system_prompt, user_prompt, max_tokens=220)
    digest = models.Summary(content=content)
    db.add(digest)
    db.commit()
    return schemas.AITextResponse(content=content)


@router.get("/wsa/{wsa_id}/risk-explanation", response_model=schemas.AITextResponse)
def get_risk_explanation(wsa_id: UUID, db: Session = Depends(get_db)) -> schemas.AITextResponse:
    # this explains in plain English why the wsa carries its current risk level
    wsa = get_wsa_or_404(db, wsa_id)
    system_prompt = (
        "You explain South African municipal water risk to non-technical citizens and officials. "
        "Write one short paragraph that explains the key reasons behind this WSA's risk level. "
        "Be specific, factual, and do not invent data."
    )
    user_prompt = (
        "Explain why this WSA has its current risk level based only on the data below.\n\n"
        f"{build_wsa_prompt(wsa)}"
    )
    return schemas.AITextResponse(content=call_openai(system_prompt, user_prompt, max_tokens=200))


@router.get("/wsa/{wsa_id}/comparison", response_model=schemas.AITextResponse)
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
        "Write one short plain-English paragraph. Be specific and factual."
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


@router.get("/province/{province}/digest", response_model=schemas.AITextResponse)
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
        "Write one plain-English paragraph, stay factual, do not invent data."
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


@router.get("/wsa/{wsa_id}/reports-summary", response_model=schemas.AITextResponse)
def get_reports_summary(
    wsa_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AITextResponse:
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
        "Write one short paragraph grouping the reports by type and flagging any patterns or hotspots. "
        "Be practical and concise."
    )
    user_prompt = "\n".join([
        f"Summarise these {len(reports)} open citizen reports for {wsa.name} ({wsa.province}).",
        f"Issue breakdown: {dict(type_counts)}",
        "Report descriptions:",
        descriptions,
    ])
    return schemas.AITextResponse(content=call_openai(system_prompt, user_prompt, max_tokens=220))


@router.get("/wsa/{wsa_id}/report-context", response_model=schemas.AITextResponse)
def get_report_context(
    wsa_id: UUID,
    issue_type: str = "general",
    db: Session = Depends(get_db),
) -> schemas.AITextResponse:
    # this gives a citizen targeted context about their wsa after submitting a report
    wsa = get_wsa_or_404(db, wsa_id)
    system_prompt = (
        "You give South African citizens brief, helpful context about their water service after they submit a report. "
        "Keep it to 2 sentences. Acknowledge their specific issue type, mention one relevant fact about the WSA, "
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


@router.get("/reports/{report_id}/comment", response_model=schemas.AITextResponse)
def generate_report_comment(
    report_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AITextResponse:
    # this drafts a short admin case comment from the real report and wsa fields so the admin can save or edit it
    report = get_report_or_404(db, report_id)
    wsa = get_wsa_or_404(db, report.wsa_id)
    system_prompt = (
        "You help South African municipal admins write short case updates for citizen water service reports. "
        "Write one practical paragraph in plain English, mention what the team will review or do next, and do not invent completed actions."
    )
    user_prompt = (
        "Draft an admin case comment for this citizen report using only the supplied report and WSA data.\n\n"
        f"{build_report_prompt(report, wsa)}"
    )
    content = call_openai(system_prompt, user_prompt, max_tokens=220)
    return schemas.AITextResponse(content=content)
