from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.audit_helpers import write_audit
from app.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> models.User:
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists")

    user = models.User(
        email=payload.email,
        hashed_password=auth.get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
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
        new_value={"email": user.email, "role": user.role.value},
        ip_address=request.client.host if request.client else None,
    )

    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[schemas.UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> list[models.User]:
    return db.query(models.User).order_by(models.User.created_at.asc()).all()


@router.patch("/{user_id}", response_model=schemas.UserRead)
def update_user_status(
    user_id: UUID,
    payload: schemas.UserStatusUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = payload.is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
