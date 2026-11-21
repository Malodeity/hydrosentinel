from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app import auth, models
from app.database import get_db

# per-user sliding window kept in the database (table ai_calls), so a restart does not clear it and several servers share one count.
# The AI endpoints (query agent, RAG, CAP draft) each cost a real OpenAI call, the query agent up to 5 in a row, so this must reject
# before the call is made, not after.
_WINDOW_SECONDS = 3600
_MAX_CALLS = 20
# the public dashboard calls GPT-4o too (digests, "explain this rating", map summary) and has no login, so it is limited per visitor address
# instead of per admin. generous enough for normal browsing, tight enough that a script cannot run up the OpenAI bill
_PUBLIC_MAX_CALLS = 40


def _window_start() -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=_WINDOW_SECONDS)


# counts this key's calls in the last hour and records a new one, or raises 429 when the limit is reached.
# the advisory lock makes check-then-record exact even when two servers handle the same user at the same moment (it is released at commit)
def _take(db: Session, key: str, limit: int, message: str) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})
    start = _window_start()
    db.execute(delete(models.AiCall).where(models.AiCall.key == key, models.AiCall.created_at < start))  # keeps the table small
    used = db.scalar(select(func.count()).select_from(models.AiCall).where(models.AiCall.key == key, models.AiCall.created_at >= start))
    if used >= limit:
        db.commit()  # release the lock; the old rows deleted above stay deleted
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)
    db.add(models.AiCall(key=key))
    db.commit()


# fastapi dependency: add it to any route that costs an openai call. it counts this admin's calls in the last hour,
# returns 429 once they pass the limit, and otherwise records the call and lets the request through
def enforce_ai_rate_limit(
    current_user: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(get_db),
) -> models.User:
    _take(db, f"user:{current_user.id}", _MAX_CALLS, f"AI request limit reached ({_MAX_CALLS} per hour). Try again later.")
    return current_user


# how much of this admin's hourly AI allowance is used, so the screen can show it instead of surprising them with a 429.
# reading it does not count as a call
def ai_usage(current_user: models.User, db: Session) -> dict:
    calls = list(
        db.scalars(
            select(models.AiCall.created_at)
            .where(models.AiCall.key == f"user:{current_user.id}", models.AiCall.created_at >= _window_start())
            .order_by(models.AiCall.created_at)
        )
    )
    # the allowance frees up one call when the oldest call in the window ages out
    resets_in = int((calls[0] + timedelta(seconds=_WINDOW_SECONDS) - datetime.now(timezone.utc)).total_seconds() // 60) + 1 if calls else 0
    return {"used": len(calls), "limit": _MAX_CALLS, "resets_in_minutes": resets_in}


def enforce_public_ai_limit(request: Request, db: Session = Depends(get_db)) -> None:
    _take(db, f"ip:{request.client.host if request.client else 'unknown'}", _PUBLIC_MAX_CALLS, "Too many AI requests from this address. Try again in an hour.")
