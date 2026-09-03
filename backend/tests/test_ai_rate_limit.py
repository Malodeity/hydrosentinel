"""
The AI endpoints (query agent, RAG, CAP draft) each cost real OpenAI calls --
the query agent alone can burn up to 5 round-trips per question. Nothing
stopped an admin account (or a bug in a client) from hammering these and
running up real spend. enforce_ai_rate_limit is a per-user sliding window
that must reject the call BEFORE it reaches OpenAI, not after.
"""
import time

import pytest
from fastapi import HTTPException

from app.rate_limit import _call_log, enforce_ai_rate_limit


@pytest.fixture(autouse=True)
def _clear_call_log():
    _call_log.clear()
    yield
    _call_log.clear()


def test_allows_calls_under_the_limit(admin_user):
    for _ in range(5):
        enforce_ai_rate_limit(admin_user)  # should not raise


def test_blocks_calls_over_the_limit(admin_user):
    for _ in range(20):
        enforce_ai_rate_limit(admin_user)

    with pytest.raises(HTTPException) as exc_info:
        enforce_ai_rate_limit(admin_user)
    assert exc_info.value.status_code == 429


def test_limit_is_per_user_not_global(admin_user, db):
    from app.auth import get_password_hash
    from app import models

    other_admin = models.User(email="other-admin@test.com", hashed_password=get_password_hash("x"), role=models.UserRole.admin, is_active=True)
    db.add(other_admin)
    db.flush()

    for _ in range(20):
        enforce_ai_rate_limit(admin_user)

    # a different user should not be blocked by the first user's usage
    enforce_ai_rate_limit(other_admin)


def test_old_calls_fall_out_of_the_window(admin_user):
    from app import rate_limit

    now = time.time()
    # simulate 20 calls that happened over an hour ago
    _call_log[str(admin_user.id)] = [now - rate_limit._WINDOW_SECONDS - 10] * 20

    enforce_ai_rate_limit(admin_user)  # should not raise — those calls have expired


def test_endpoint_returns_429_when_rate_limited(client, auth_headers, admin_user):
    from app.rate_limit import _call_log

    _call_log[str(admin_user.id)] = [time.time()] * 20
    resp = client.post("/ai/query", json={"question": "how many WSAs are high risk?"}, headers=auth_headers)
    assert resp.status_code == 429
    _call_log.clear()
