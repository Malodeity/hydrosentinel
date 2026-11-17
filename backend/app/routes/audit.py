# Audit log API (admin only): read-only view of who changed what. Used by the Audit log tab (frontend pages/AdminPage.tsx, api/audit.ts).

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db

router = APIRouter(prefix="/audit-log", tags=["audit"])


# GET /audit-log (admin): the history of admin changes, newest first. rows are written by app/audit_helpers.py and are never edited.
@router.get("", response_model=list[schemas.AuditLogRead])
def list_audit_log(
    limit: int = 200,
    record_id: UUID | None = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_national_admin),
) -> list[models.AuditLog]:
    query = db.query(models.AuditLog)
    if record_id:
        query = query.filter(models.AuditLog.record_id == record_id)
    return query.order_by(models.AuditLog.created_at.desc()).limit(limit).all()
