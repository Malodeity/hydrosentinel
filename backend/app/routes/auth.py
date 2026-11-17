# Sign-in API: login, token refresh, logout. The frontend side is api/client.ts (stores the tokens and retries a request once after a 401).

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import settings
from app.audit_helpers import write_audit
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# two tokens: the access token (a short-lived jwt) proves who you are on each request; the refresh token lasts 7 days and lets the
# browser get a new access token without asking for the password again
_REFRESH_TOKEN_TTL_DAYS = 7


# refresh tokens are stored only as a sha-256 hash, so a copy of the database cannot be used to sign in
def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# makes a short-lived access token (JWT) plus a long-lived refresh token, and saves the refresh token's hash
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


# checks the email and password, refuses disabled accounts, and returns an access token plus a refresh token
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


# swaps a valid refresh token for a new pair. each refresh token works once: the old one is revoked, so a stolen copy
# stops working as soon as the real user refreshes
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


# POST /auth/logout: revokes the refresh token on the server, so signing out really ends the session.
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: schemas.RefreshRequest, db: Session = Depends(get_db)) -> None:
    token_hash = _hash_token(payload.refresh_token)
    stored = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()
    if stored and not stored.revoked_at:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


# GET /auth/me: who am I? used by the frontend to check the saved login is still valid.
@router.get("/me", response_model=schemas.UserRead)
def me(current_user: models.User = Depends(auth.get_current_user)) -> models.User:
    return current_user


# POST /auth/change-password: the signed-in user sets a new password. needs the current one; every refresh token is revoked so other devices must sign in again
@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: schemas.PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> None:
    if not auth.verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is wrong")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a different password")
    current_user.hashed_password = auth.get_password_hash(payload.new_password)
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == current_user.id, models.RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": datetime.now(timezone.utc)})
    write_audit(db, current_user.id, models.AuditAction.password_changed, "users", current_user.id,
                None, {"by": "self"}, request.client.host if request.client else None)
    db.commit()
