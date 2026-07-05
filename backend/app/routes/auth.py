import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_TOKEN_TTL_DAYS = 7


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _issue_tokens(user: models.User, db: Session) -> tuple[str, str]:
    access_token = auth.create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    raw_refresh = secrets.token_urlsafe(64)
    db.add(models.RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=_REFRESH_TOKEN_TTL_DAYS),
    ))
    return access_token, raw_refresh


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)) -> schemas.TokenResponse:
    user = auth.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    access_token, raw_refresh = _issue_tokens(user, db)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return schemas.TokenResponse(access_token=access_token, refresh_token=raw_refresh, user=user)


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)) -> schemas.TokenResponse:
    token_hash = _hash_token(payload.refresh_token)
    stored = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()

    if not stored or stored.revoked_at or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user = db.query(models.User).filter(models.User.id == stored.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")

    # revoke old token, issue fresh pair
    stored.revoked_at = datetime.now(timezone.utc)
    access_token, raw_refresh = _issue_tokens(user, db)
    db.commit()

    return schemas.TokenResponse(access_token=access_token, refresh_token=raw_refresh, user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: schemas.RefreshRequest, db: Session = Depends(get_db)) -> None:
    token_hash = _hash_token(payload.refresh_token)
    stored = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()
    if stored and not stored.revoked_at:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


@router.get("/me", response_model=schemas.UserRead)
def me(current_user: models.User = Depends(auth.get_current_user)) -> models.User:
    return current_user
