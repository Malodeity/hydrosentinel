# Citizen reports API. POST /reports (public) saves a report and its photos and may raise alerts; GET /reports/track/{code} (public) shows only the status;
# GET /reports/public-stats (public) gives totals only; the list, CSV export and PATCH (status + comment) are admin only.
# Photos are saved as files under data/uploads/{report_id}/, not in the database.

import csv
import io
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from statistics import median
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import assignment_helpers, auth, models, schemas
from app.alert_helpers import raise_geo_cluster_alert, raise_report_volume_spike_alert
from app.audit_helpers import write_audit
from app.database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])
# citizen photos are saved here, one folder per report, and served back under /uploads. the database stores no photo data
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "data" / "uploads"


def _generate_reference_code() -> str:
    # 4 random hex bytes = 8 hex chars, ~4 billion combinations — no collision
    # handling needed at this table's scale
    return f"HS-{secrets.token_hex(4).upper()}"


# the database has no photo column: this lists the files in the report's folder and returns their urls with the report fields
def photo_urls_for(report: models.CitizenReport) -> list[str]:
    report_directory = UPLOAD_ROOT / str(report.id)
    if not report_directory.exists():
        return []
    return [f"/uploads/{report.id}/{path.name}" for path in sorted(report_directory.iterdir()) if path.is_file()]


def build_report_response(report: models.CitizenReport, db: Session | None = None) -> schemas.CitizenReportRead:
    photo_urls = photo_urls_for(report)
    # the newest ticket on the report (active or finished), so the admin table can show who has it and what happened
    latest = assignment_helpers.latest_assignment(db, report.id) if db is not None else None

    return schemas.CitizenReportRead(
        id=report.id,
        wsa_id=report.wsa_id,
        issue_type=report.issue_type,
        description=report.description,
        reference_code=report.reference_code,
        case_status=report.case_status,
        admin_comment=report.admin_comment,
        reviewed_by=report.reviewed_by,
        resolved_by=report.resolved_by,
        reviewed_at=report.reviewed_at,
        resolved_at=report.resolved_at,
        lat=report.lat,
        lng=report.lng,
        created_at=report.created_at,
        photo_urls=photo_urls,
        photo_analysis=report.photo_analysis,
        assignment=assignment_helpers.summarize(latest) if latest else None,
    )


# public endpoint (no login): a resident submits a report. steps: check the authority exists (404), save the report with a new reference code,
# run the two alert checks (report volume spike and geographic cluster), then store only image files and ignore anything else
@router.post("", response_model=schemas.CitizenReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    wsa_id: uuid.UUID = Form(...),
    issue_type: models.IssueType = Form(...),
    description: str | None = Form(default=None),
    lat: float = Form(...),
    lng: float = Form(...),
    photos: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
) -> models.CitizenReport:
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")

    report = models.CitizenReport(
        wsa_id=wsa_id,
        issue_type=issue_type,
        description=description,
        reference_code=_generate_reference_code(),
        case_status="open",
        lat=lat,
        lng=lng,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    raise_report_volume_spike_alert(wsa, db)
    raise_geo_cluster_alert(wsa, report, db)
    db.commit()

    if photos:
        report_directory = UPLOAD_ROOT / str(report.id)
        report_directory.mkdir(parents=True, exist_ok=True)
        for photo in photos:
            suffix = Path(photo.filename or "").suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                continue
            target_path = report_directory / f"{uuid.uuid4()}{suffix}"
            with target_path.open("wb") as target_file:
                target_file.write(await photo.read())

    return build_report_response(report)


# public lookup by reference code. the response model leaves out the location and description, so a code alone never reveals more than the status
@router.get("/track/{reference_code}", response_model=schemas.CitizenReportTrackRead)
def track_report(reference_code: str, db: Session = Depends(get_db)) -> schemas.CitizenReportTrackRead:
    report = db.query(models.CitizenReport).filter(models.CitizenReport.reference_code == reference_code).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    # repair progress only while the report is still open: once it is resolved the status already says everything
    ticket = assignment_helpers.active_assignment(db, report.id) if report.case_status != "resolved" else None
    return schemas.CitizenReportTrackRead(
        reference_code=report.reference_code,
        issue_type=report.issue_type,
        case_status=report.case_status,
        admin_comment=report.admin_comment,
        created_at=report.created_at,
        repair_status=assignment_helpers.public_repair_status(ticket),
        repair_due_at=ticket.due_at if ticket else None,
    )


def resolution_days(reports) -> list[float]:
    # days from filing to resolution, only for reports that are resolved AND have a recorded time: a resolved report with no
    # timestamp must be left out, not counted as 0 days, or it would drag the median down
    return [
        (r.resolved_at - r.created_at).total_seconds() / 86400
        for r in reports
        if r.case_status == "resolved" and r.resolved_at is not None and r.resolved_at >= r.created_at
    ]


# public: how much residents are reporting and how fast reports get resolved. totals only, so it is safe to show on the open dashboard
@router.get("/public-stats", response_model=schemas.PublicReportStats)
def public_report_stats(db: Session = Depends(get_db)) -> schemas.PublicReportStats:
    reports = db.query(models.CitizenReport).all()
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    by_wsa: dict[str, schemas.WsaReportCounts] = {}
    for report in reports:
        counts = by_wsa.setdefault(str(report.wsa_id), schemas.WsaReportCounts(open=0, resolved=0))
        if report.case_status == "resolved":
            counts.resolved += 1
        else:
            counts.open += 1
    days = resolution_days(reports)
    return schemas.PublicReportStats(
        received_7d=sum(1 for r in reports if r.created_at >= week_ago),
        total=len(reports),
        open=sum(c.open for c in by_wsa.values()),
        resolved=sum(c.resolved for c in by_wsa.values()),
        median_days_to_resolve=round(median(days), 1) if days else None,
        resolved_sample=len(days),
        by_wsa=by_wsa,
    )


# an admin tied to one authority sees only that authority's reports; a national admin sees all
def _scoped_reports(db: Session, user: models.User):
    query = db.query(models.CitizenReport)
    if user.wsa_id is not None:
        query = query.filter(models.CitizenReport.wsa_id == user.wsa_id)
    return query


# admin only: every report, newest first
@router.get("", response_model=list[schemas.CitizenReportRead])
def list_reports(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.CitizenReportRead]:
    reports = _scoped_reports(db, current_user).order_by(models.CitizenReport.created_at.desc()).all()
    return [build_report_response(report, db) for report in reports]


_EXPORT_COLUMNS = ["reference_code", "issue_type", "case_status", "description", "created_at", "reviewed_at", "resolved_at"]
_ASSIGNMENT_COLUMNS = ["assigned_contractor", "ticket_status", "ticket_due_at"]


# ADMIN   GET /reports/export.csv: every report as a spreadsheet file (the Export CSV button on the Citizen reports tab).
@router.get("/export.csv")
def export_reports_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> StreamingResponse:
    reports = _scoped_reports(db, current_user).order_by(models.CitizenReport.created_at.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_EXPORT_COLUMNS + _ASSIGNMENT_COLUMNS)
    for report in reports:
        ticket = assignment_helpers.latest_assignment(db, report.id)
        ticket_cells = [ticket.contractor.name, ticket.status, ticket.due_at] if ticket else ["", "", ""]
        writer.writerow([getattr(report, col) for col in _EXPORT_COLUMNS] + ticket_cells)

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reports_export.csv"},
    )


# admin only: change a report's status and note. the first move to in_review records who reviewed it and when, the first move to resolved
# records who resolved it, and every change writes an audit row (a status change, or just a changed note)
@router.patch("/{report_id}", response_model=schemas.CitizenReportRead)
def update_report(
    report_id: uuid.UUID,
    payload: schemas.CitizenReportAdminUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.CitizenReportRead:
    report = db.query(models.CitizenReport).filter(models.CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    auth.require_wsa_access(current_user, report.wsa_id)

    old_status = report.case_status
    old_comment = report.admin_comment
    now = datetime.now(timezone.utc)

    report.case_status = payload.case_status
    report.admin_comment = payload.admin_comment.strip() if payload.admin_comment else None

    if payload.case_status == "in_review" and old_status != "in_review":
        report.reviewed_by = current_user.id
        report.reviewed_at = now

    if payload.case_status == "resolved" and old_status != "resolved":
        report.resolved_by = current_user.id
        report.resolved_at = now
        # resolving by hand ends any open repair ticket, so no contractor keeps working a closed report
        assignment_helpers.close_active_for_report(db, report, "Report resolved by the authority")

    action = (
        models.AuditAction.report_comment_updated
        if payload.case_status == old_status
        else models.AuditAction.report_status_updated
    )
    write_audit(
        db=db,
        user_id=current_user.id,
        action=action,
        table_name="citizen_reports",
        record_id=report.id,
        old_value={"case_status": old_status, "admin_comment": old_comment},
        new_value={"case_status": payload.case_status, "admin_comment": report.admin_comment},
        ip_address=request.client.host if request.client else None,
    )

    db.add(report)
    db.commit()
    db.refresh(report)
    return build_report_response(report, db)
