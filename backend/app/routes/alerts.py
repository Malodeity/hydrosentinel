# Alerts API (admin only). Alerts are created by app/alert_helpers.py; this file lists them and lets an admin acknowledge them.
# Used by: the "System alerts" card on the Overview tab (frontend pages/AdminPage.tsx, api/alerts.ts).

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.alert_helpers import raise_assignment_overdue_alerts, raise_cap_overdue_alerts, resolve_stale_alerts
from app.database import get_db

router = APIRouter(prefix="/alerts", tags=["alerts"])


# turns an Alert row into the API shape (adds the authority's name, which the screen shows)
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


# GET /alerts (admin): lists alerts, newest first. before listing it (1) raises any new 'CAP overdue' alerts and (2) closes alerts whose cause has gone away.
# Both checks (and the contractor 'ticket overdue' check) run here, on read, because the app has no scheduler.
@router.get("", response_model=list[schemas.AlertRead])
def list_alerts(
    unacknowledged_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.AlertRead]:
    raise_cap_overdue_alerts(db)
    raise_assignment_overdue_alerts(db)
    resolve_stale_alerts(db)
    db.commit()

    query = db.query(models.Alert).join(models.WSA)
    if current_user.wsa_id is not None:
        # an admin tied to one authority only sees that authority's alerts
        query = query.filter(models.Alert.wsa_id == current_user.wsa_id)
    if unacknowledged_only:
        query = query.filter(models.Alert.acknowledged_at.is_(None))
    alerts = query.order_by(models.Alert.created_at.desc()).all()
    return [_build_alert_read(a) for a in alerts]


# PATCH /alerts/{id}/acknowledge (admin): marks an alert handled and records who did it. asking twice is harmless.
@router.patch("/{alert_id}/acknowledge", response_model=schemas.AlertRead)
def acknowledge_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AlertRead:
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    auth.require_wsa_access(current_user, alert.wsa_id)
    if alert.acknowledged_at:
        return _build_alert_read(alert)

    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _build_alert_read(alert)
