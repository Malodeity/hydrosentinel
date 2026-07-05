import uuid
from typing import Any

from sqlalchemy.orm import Session

from app import models


def write_audit(
    db: Session,
    user_id: uuid.UUID,
    action: models.AuditAction,
    table_name: str,
    record_id: uuid.UUID,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    entry = models.AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
    )
    db.add(entry)
