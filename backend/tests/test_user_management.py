"""
Only one hardcoded admin exists today, seeded from env vars. Real teams need
more than one admin account and a way to deactivate someone who leaves —
without touching the database by hand.
"""
from app import models


def test_admin_can_create_new_admin_user(client, auth_headers):
    resp = client.post(
        "/users",
        json={"email": "new-admin@hydrosentinel.co.za", "password": "supersecret1", "role": "admin"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new-admin@hydrosentinel.co.za"
    assert body["role"] == "admin"
    assert body["is_active"] is True


def test_new_user_can_log_in_with_chosen_password(client, auth_headers):
    client.post(
        "/users",
        json={"email": "login-check@hydrosentinel.co.za", "password": "supersecret1", "role": "viewer"},
        headers=auth_headers,
    )
    resp = client.post("/auth/login", json={"email": "login-check@hydrosentinel.co.za", "password": "supersecret1"})
    assert resp.status_code == 200


def test_duplicate_email_returns_409(client, auth_headers, admin_user):
    resp = client.post(
        "/users",
        json={"email": admin_user.email, "password": "supersecret1", "role": "admin"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_non_admin_cannot_create_users(client, db):
    from app.auth import get_password_hash

    viewer = models.User(email="viewer@test.com", hashed_password=get_password_hash("viewerpass1"), role=models.UserRole.viewer, is_active=True)
    db.add(viewer)
    db.flush()
    login = client.post("/auth/login", json={"email": "viewer@test.com", "password": "viewerpass1"})
    token = login.json()["access_token"]

    resp = client.post(
        "/users",
        json={"email": "x@test.com", "password": "supersecret1", "role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_list_users_requires_admin(client):
    resp = client.get("/users")
    assert resp.status_code == 401


def test_list_users_returns_all(client, auth_headers, admin_user):
    resp = client.get("/users", headers=auth_headers)
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert admin_user.email in emails


def test_deactivate_user(client, auth_headers, db):
    from app.auth import get_password_hash

    target = models.User(email="deactivate-me@test.com", hashed_password=get_password_hash("targetpass1"), role=models.UserRole.viewer, is_active=True)
    db.add(target)
    db.flush()

    resp = client.patch(f"/users/{target.id}", json={"is_active": False}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_deactivated_user_cannot_log_in(client, auth_headers, db):
    from app.auth import get_password_hash

    target = models.User(email="locked-out@test.com", hashed_password=get_password_hash("targetpass1"), role=models.UserRole.viewer, is_active=True)
    db.add(target)
    db.flush()

    client.patch(f"/users/{target.id}", json={"is_active": False}, headers=auth_headers)

    resp = client.post("/auth/login", json={"email": "locked-out@test.com", "password": "targetpass1"})
    assert resp.status_code == 403


def test_deactivate_unknown_user_returns_404(client, auth_headers):
    resp = client.patch("/users/00000000-0000-0000-0000-000000000000", json={"is_active": False}, headers=auth_headers)
    assert resp.status_code == 404
