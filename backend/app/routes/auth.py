from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)) -> schemas.TokenResponse:
    user = auth.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = auth.create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    return schemas.TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=schemas.UserRead)
def me(current_user: models.User = Depends(auth.get_current_user)) -> models.User:
    return current_user
