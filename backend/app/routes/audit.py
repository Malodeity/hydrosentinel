from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("", response_model=list[schemas.AuditLogRead])
def list_audit_log(
    limit: int = 200,
    record_id: UUID | None = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> list[models.AuditLog]:
    query = db.query(models.AuditLog)
    if record_id:
        query = query.filter(models.AuditLog.record_id == record_id)
    return query.order_by(models.AuditLog.created_at.desc()).limit(limit).all()
