import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "data" / "uploads"


def build_report_response(report: models.CitizenReport) -> schemas.CitizenReportRead:
    # this reads any saved photo files for the report and returns them with the normal report fields
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
    # this creates one citizen report after checking that the chosen wsa exists
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
    # this returns all reports for admins so they can review submissions in one table
    reports = db.query(models.CitizenReport).order_by(models.CitizenReport.created_at.desc()).all()
    return [build_report_response(report) for report in reports]


@router.patch("/{report_id}", response_model=schemas.CitizenReportRead)
def update_report(
    report_id: uuid.UUID,
    payload: schemas.CitizenReportAdminUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> schemas.CitizenReportRead:
    # this lets an admin track the case stage and keep one saved response on the report
    report = db.query(models.CitizenReport).filter(models.CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    report.case_status = payload.case_status
    report.admin_comment = payload.admin_comment.strip() if payload.admin_comment else None
    db.add(report)
    db.commit()
    db.refresh(report)
    return build_report_response(report)
