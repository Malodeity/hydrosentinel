from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _build_alert_read(alert: models.Alert) -> schemas.AlertRead:
    return schemas.AlertRead(
        id=alert.id,
        wsa_id=alert.wsa_id,
        wsa_name=alert.wsa.name if alert.wsa else "",
        alert_type=alert.alert_type,
        message=alert.message,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        created_at=alert.created_at,
    )


@router.get("", response_model=list[schemas.AlertRead])
def list_alerts(
    unacknowledged_only: bool = False,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.AlertRead]:
    query = db.query(models.Alert).join(models.WSA)
    if unacknowledged_only:
        query = query.filter(models.Alert.acknowledged_at.is_(None))
    alerts = query.order_by(models.Alert.created_at.desc()).all()
    return [_build_alert_read(a) for a in alerts]


@router.patch("/{alert_id}/acknowledge", response_model=schemas.AlertRead)
def acknowledge_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AlertRead:
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.acknowledged_at:
        return _build_alert_read(alert)

    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _build_alert_read(alert)
