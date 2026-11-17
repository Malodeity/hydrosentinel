# User management API (admin only). Used by the Users tab (frontend pages/AdminPage.tsx, api/users.ts).

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.audit_helpers import write_audit
from app.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


# POST /users (admin): creates another admin, viewer or contractor account (an admin can be tied to one authority; a contractor belongs to one company). the password is stored as a bcrypt hash, never in clear.
@router.post("", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_national_admin),
) -> models.User:
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists")

    if payload.wsa_id and not db.query(models.WSA).filter(models.WSA.id == payload.wsa_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")
    if payload.contractor_id and not db.query(models.Contractor).filter(models.Contractor.id == payload.contractor_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contractor not found")

    user = models.User(
        email=payload.email,
        hashed_password=auth.get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
        wsa_id=payload.wsa_id,
        contractor_id=payload.contractor_id,
    )
    db.add(user)
    db.flush()

    write_audit(
        db=db,
        user_id=current_user.id,
        action=models.AuditAction.user_created,
        table_name="users",
        record_id=user.id,
        old_value=None,
        new_value={"email": user.email, "role": user.role.value, "wsa_id": str(user.wsa_id) if user.wsa_id else None,
                   "contractor_id": str(user.contractor_id) if user.contractor_id else None},
        ip_address=request.client.host if request.client else None,
    )

    db.commit()
    db.refresh(user)
    return user


# GET /users (admin): all accounts, for the Users tab.
@router.get("", response_model=list[schemas.UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_national_admin),
) -> list[models.User]:
    return db.query(models.User).order_by(models.User.created_at.asc()).all()


# PATCH /users/{id} (admin): activates or deactivates an account. an admin cannot deactivate their own account, so the system is never left with no way in.
@router.patch("/{user_id}", response_model=schemas.UserRead)
def update_user_status(
    user_id: UUID,
    payload: schemas.UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_national_admin),
) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id and not payload.is_active:
        # an admin who deactivates their own account locks themselves out of the admin page
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")

    user.is_active = payload.is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# PATCH /users/{id}/password (national admin): sets a new password for someone who forgot theirs. revokes their sessions and is written to the audit log (the password itself is never logged)
@router.patch("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: UUID,
    payload: schemas.PasswordReset,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_national_admin),
) -> None:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.hashed_password = auth.get_password_hash(payload.new_password)
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user.id, models.RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": datetime.now(timezone.utc)})
    write_audit(db, current_user.id, models.AuditAction.password_changed, "users", user.id,
                None, {"by": "admin", "email": user.email}, request.client.host if request.client else None)
    db.commit()
