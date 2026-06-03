from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db

router = APIRouter(prefix="/wsa", tags=["wsa"])


@router.get("", response_model=list[schemas.WSARead])
def list_wsas(db: Session = Depends(get_db)) -> list[models.WSA]:
    # this returns all wsas for the dashboard map and admin screens
    return db.query(models.WSA).order_by(models.WSA.name.asc()).all()


@router.get("/{wsa_id}", response_model=schemas.WSARead)
def get_wsa(wsa_id: UUID, db: Session = Depends(get_db)) -> models.WSA:
    # this loads one wsa by uuid when the frontend needs a single record
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")
    return wsa


@router.patch("/{wsa_id}", response_model=schemas.WSARead)
def update_wsa_cap_status(
    wsa_id: UUID,
    payload: schemas.WSAUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> models.WSA:
    # this updates only the cap status so the admin page has one small safe edit action
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")

    wsa.cap_status = payload.cap_status
    db.add(wsa)
    db.commit()
    db.refresh(wsa)
    return wsa
