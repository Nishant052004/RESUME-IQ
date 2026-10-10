"""Shared pytest fixtures. The test DB env var must be set before `app` imports."""
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/resumeiq_test_{os.getpid()}.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth(client):
    """Register a recruiter and return an Authorization header."""
    response = client.post(
        "/api/auth/register",
        json={"email": "recruiter@test.com", "password": "secret123", "full_name": "Test Recruiter"},
    )
    if response.status_code == 409:  # rerun against a warm DB
        response = client.post("/api/auth/login", json={"email": "recruiter@test.com", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
