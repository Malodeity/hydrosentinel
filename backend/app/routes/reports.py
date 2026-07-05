import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.alert_helpers import raise_report_volume_spike_alert
from app.audit_helpers import write_audit
from app.database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "data" / "uploads"


def build_report_response(report: models.CitizenReport) -> schemas.CitizenReportRead:
    report_directory = UPLOAD_ROOT / str(report.id)
    photo_urls: list[str] = []
    if report_directory.exists():
        photo_urls = [f"/uploads/{report.id}/{path.name}" for path in sorted(report_directory.iterdir()) if path.is_file()]

    return schemas.CitizenReportRead(
        id=report.id,
        wsa_id=report.wsa_id,
        issue_type=report.issue_type,
        description=report.description,
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
    )


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
        case_status="open",
        lat=lat,
        lng=lng,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    raise_report_volume_spike_alert(wsa, db)
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


@router.get("", response_model=list[schemas.CitizenReportRead])
def list_reports(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.CitizenReportRead]:
    reports = db.query(models.CitizenReport).order_by(models.CitizenReport.created_at.desc()).all()
    return [build_report_response(report) for report in reports]


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
    return build_report_response(report)
