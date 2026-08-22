import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.audit_helpers import write_audit
from app.database import get_db

router = APIRouter(prefix="/wsa", tags=["wsa"])

_EXPORT_COLUMNS = [
    "name", "province", "blue_drop_score", "green_drop_score", "nrw_percent",
    "maint_pct", "cap_status", "cap_due_date", "risk_level", "dws_cap_status",
    "bd_certification", "nd_performance",
]


@router.get("", response_model=list[schemas.WSARead])
def list_wsas(db: Session = Depends(get_db)) -> list[models.WSA]:
    return db.query(models.WSA).order_by(models.WSA.name.asc()).all()


@router.get("/export.csv")
def export_wsas_csv(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> StreamingResponse:
    wsas = db.query(models.WSA).order_by(models.WSA.name.asc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_EXPORT_COLUMNS)
    for wsa in wsas:
        writer.writerow([getattr(wsa, col) for col in _EXPORT_COLUMNS])

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=wsa_export.csv"},
    )


@router.get("/{wsa_id}", response_model=schemas.WSARead)
def get_wsa(wsa_id: UUID, db: Session = Depends(get_db)) -> models.WSA:
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")
    return wsa


@router.patch("/{wsa_id}", response_model=schemas.WSARead)
def update_wsa_cap_status(
    wsa_id: UUID,
    payload: schemas.WSAUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> models.WSA:
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")

    old_status = wsa.cap_status
    wsa.cap_status = payload.cap_status
    wsa.cap_due_date = payload.cap_due_date

    write_audit(
        db=db,
        user_id=current_user.id,
        action=models.AuditAction.cap_status_updated,
        table_name="wsa",
        record_id=wsa.id,
        old_value={"cap_status": old_status.value},
        new_value={"cap_status": payload.cap_status.value},
        ip_address=request.client.host if request.client else None,
    )

    db.add(wsa)
    db.commit()
    db.refresh(wsa)
    return wsa
