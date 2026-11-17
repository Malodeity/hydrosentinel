import time

from fastapi import Depends, HTTPException, Request, status

from app import auth, models

# per-user sliding window — plain in-memory dict, fine for a single-process
# deployment. The AI endpoints (query agent, RAG, CAP draft) each cost a
# real OpenAI call, the query agent up to 5 in a row, so this must reject
# before the call is made, not after.
_WINDOW_SECONDS = 3600
_MAX_CALLS = 20

_call_log: dict[str, list[float]] = {}


# fastapi dependency: add it to any route that costs an openai call. it counts this admin's calls in the last hour,
# returns 429 once they pass the limit, and otherwise records the call and lets the request through
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


# how much of this admin's hourly AI allowance is used, so the screen can show it instead of surprising them with a 429.
# reading it does not count as a call
def ai_usage(current_user: models.User) -> dict:
    now = time.time()
    recent = sorted(t for t in _call_log.get(str(current_user.id), []) if now - t <= _WINDOW_SECONDS)
    # the allowance frees up one call when the oldest call in the window ages out
    resets_in = int((recent[0] + _WINDOW_SECONDS - now) // 60) + 1 if recent else 0
    return {"used": len(recent), "limit": _MAX_CALLS, "resets_in_minutes": resets_in}


# the public dashboard calls GPT-4o too (digests, "explain this rating", map summary) and has no login, so it is limited per visitor address
# instead of per admin. generous enough for normal browsing, tight enough that a script cannot run up the OpenAI bill
_PUBLIC_MAX_CALLS = 40


def enforce_public_ai_limit(request: Request) -> None:
    now = time.time()
    key = f"ip:{request.client.host if request.client else 'unknown'}"
    recent = [t for t in _call_log.get(key, []) if now - t <= _WINDOW_SECONDS]
    if len(recent) >= _PUBLIC_MAX_CALLS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many AI requests from this address. Try again in an hour.",
        )
    recent.append(now)
    _call_log[key] = recent
