"""
The AI endpoints (query agent, RAG, CAP draft) each cost real OpenAI calls --
the query agent alone can burn up to 5 round-trips per question. Nothing
stopped an admin account (or a bug in a client) from hammering these and
running up real spend. enforce_ai_rate_limit is a per-user sliding window
that must reject the call BEFORE it reaches OpenAI, not after.

The count lives in the ai_calls table (not in process memory), so a restart does not
reset it and several servers share one count.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app import models, rate_limit
from app.rate_limit import ai_usage, enforce_ai_rate_limit


def _record(db, user, count, age_seconds=0):
    when = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    for _ in range(count):
        db.add(models.AiCall(key=f"user:{user.id}", created_at=when))
    db.flush()


def test_allows_calls_under_the_limit(admin_user, db):
    for _ in range(5):
        enforce_ai_rate_limit(admin_user, db)  # should not raise


def test_blocks_calls_over_the_limit(admin_user, db):
    for _ in range(20):
        enforce_ai_rate_limit(admin_user, db)

    with pytest.raises(HTTPException) as exc_info:
        enforce_ai_rate_limit(admin_user, db)
    assert exc_info.value.status_code == 429


def test_limit_is_per_user_not_global(admin_user, db):
    from app.auth import get_password_hash

    other_admin = models.User(email="other-admin@test.com", hashed_password=get_password_hash("x"), role=models.UserRole.admin, is_active=True)
    db.add(other_admin)
    db.flush()

    for _ in range(20):
        enforce_ai_rate_limit(admin_user, db)

    # a different user should not be blocked by the first user's usage
    enforce_ai_rate_limit(other_admin, db)


def test_old_calls_fall_out_of_the_window(admin_user, db):
    _record(db, admin_user, 20, age_seconds=rate_limit._WINDOW_SECONDS + 10)  # 20 calls that happened over an hour ago
    enforce_ai_rate_limit(admin_user, db)  # should not raise: those calls have expired
    assert ai_usage(admin_user, db)["used"] == 1


def test_the_count_is_stored_in_the_database_so_another_server_or_a_restart_sees_it(admin_user, db):
    # the whole point of FR-09: the old in-memory dict was lost on restart and was per process. a fresh call must see calls already recorded
    _record(db, admin_user, 20)
    with pytest.raises(HTTPException) as exc_info:
        enforce_ai_rate_limit(admin_user, db)
    assert exc_info.value.status_code == 429


def test_usage_reports_used_and_reset_time_without_costing_a_call(admin_user, db):
    _record(db, admin_user, 3, age_seconds=600)
    usage = ai_usage(admin_user, db)
    assert usage["used"] == 3 and usage["limit"] == 20
    assert 49 <= usage["resets_in_minutes"] <= 51  # the oldest call is 10 minutes old
    assert ai_usage(admin_user, db)["used"] == 3  # reading does not add a call


def test_endpoint_returns_429_when_rate_limited(client, auth_headers, admin_user, db):
    _record(db, admin_user, 20)
    resp = client.post("/ai/query", json={"question": "how many WSAs are high risk?"}, headers=auth_headers)
    assert resp.status_code == 429


def test_openai_client_has_a_short_timeout_so_an_outage_fails_fast():
    # the library default read timeout is 600s; an OpenAI outage must not hold a request that long
    from unittest.mock import patch
    from app.routes import ai as ai_routes

    with patch.object(ai_routes.settings, "openai_api_key", "test-key"):
        client = ai_routes.get_openai_client()

    assert client.timeout == 30.0
    assert client.max_retries == 1
