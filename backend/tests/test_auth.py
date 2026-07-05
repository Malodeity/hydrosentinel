"""Tests for auth endpoints: login, refresh token, logout, is_active, last_login_at."""
import uuid
from datetime import datetime, timezone


def test_login_returns_access_and_refresh_tokens(client, admin_user):
    resp = client.post("/auth/login", json={"email": admin_user.email, "password": "adminpass1"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_sets_last_login_at(client, admin_user, db):
    assert admin_user.last_login_at is None
    client.post("/auth/login", json={"email": admin_user.email, "password": "adminpass1"})
    db.refresh(admin_user)
    assert admin_user.last_login_at is not None


def test_login_wrong_password_returns_401(client, admin_user):
    resp = client.post("/auth/login", json={"email": admin_user.email, "password": "wrongpass1"})
    assert resp.status_code == 401


def test_login_inactive_user_returns_403(client, admin_user, db):
    admin_user.is_active = False
    db.flush()
    resp = client.post("/auth/login", json={"email": admin_user.email, "password": "adminpass1"})
    assert resp.status_code == 403


def test_refresh_token_issues_new_access_token(client, admin_user):
    login = client.post("/auth/login", json={"email": admin_user.email, "password": "adminpass1"})
    raw_refresh = login.json()["refresh_token"]

    resp = client.post("/auth/refresh", json={"refresh_token": raw_refresh})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # new refresh token must differ from the old one
    assert data["refresh_token"] != raw_refresh


def test_refresh_token_can_only_be_used_once(client, admin_user):
    login = client.post("/auth/login", json={"email": admin_user.email, "password": "adminpass1"})
    raw_refresh = login.json()["refresh_token"]

    client.post("/auth/refresh", json={"refresh_token": raw_refresh})
    # second use of the same token must fail
    resp = client.post("/auth/refresh", json={"refresh_token": raw_refresh})
    assert resp.status_code == 401


def test_logout_revokes_refresh_token(client, admin_user):
    login = client.post("/auth/login", json={"email": admin_user.email, "password": "adminpass1"})
    raw_refresh = login.json()["refresh_token"]

    logout = client.post("/auth/logout", json={"refresh_token": raw_refresh})
    assert logout.status_code == 204

    resp = client.post("/auth/refresh", json={"refresh_token": raw_refresh})
    assert resp.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert "email" in resp.json()
