"""
Shared fixtures for all HydroSentinel tests.

Each test runs inside a transaction that rolls back after the test completes,
so the real database is never polluted.
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "postgresql://malo:Unlimitedphos%401@localhost:5433/hydrosentinel")
os.environ["TESTING"] = "1"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.com")
os.environ.setdefault("ADMIN_PASSWORD", "testpass1")
os.environ.setdefault("MODEL_PATH", "ai/model.pkl")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("PROJECT_NAME", "HydroSentinel Test")

from app.database import Base, get_db  # noqa: E402 — envs must be set first
from main import app  # noqa: E402

TEST_DB_URL = os.environ["DATABASE_URL"]
engine = create_engine(TEST_DB_URL)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def ensure_schema():
    """Run migrations and create all tables once per test session — no per-test deadlocks."""
    from main import apply_ai_schema_changes, create_database_extensions
    create_database_extensions()
    apply_ai_schema_changes()
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def db():
    """Database session wrapped in a transaction that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """FastAPI TestClient with DB dependency overridden to use the test session."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    """Create a real admin user in the test DB."""
    from app.auth import get_password_hash
    from app import models

    user = models.User(
        email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=get_password_hash("adminpass1"),
        role=models.UserRole.admin,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def admin_token(client, admin_user):
    """JWT access token for the test admin user."""
    resp = client.post("/auth/login", json={"email": admin_user.email, "password": "adminpass1"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def sample_wsa(db):
    """A WSA row for use in tests."""
    from app import models

    wsa = models.WSA(
        name=f"Test WSA {uuid.uuid4().hex[:6]}",
        province="Gauteng",
        blue_drop_score=45.0,
        risk_level=models.RiskLevel.low,
    )
    db.add(wsa)
    db.flush()
    return wsa
