import time

from fastapi import Depends, HTTPException, status

from app import auth, models

# per-user sliding window — plain in-memory dict, fine for a single-process
# deployment. The AI endpoints (query agent, RAG, CAP draft) each cost a
# real OpenAI call, the query agent up to 5 in a row, so this must reject
# before the call is made, not after.
_WINDOW_SECONDS = 3600
_MAX_CALLS = 20

_call_log: dict[str, list[float]] = {}


def enforce_ai_rate_limit(current_user: models.User = Depends(auth.get_current_admin_user)) -> models.User:
    now = time.time()
    key = str(current_user.id)
    recent = [t for t in _call_log.get(key, []) if now - t <= _WINDOW_SECONDS]

    if len(recent) >= _MAX_CALLS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"AI request limit reached ({_MAX_CALLS} per hour). Try again later.",
        )

    recent.append(now)
    _call_log[key] = recent
    return current_user
