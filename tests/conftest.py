"""Shared test fixtures.

Every test runs against its own temporary SQLite database (never the real
demo database), with in-memory session/rate-limit state cleared.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Configure environment BEFORE importing the application modules.
os.environ["SHEHARNAAMA_DB_PATH"] = "data/test-unused.sqlite3"
os.environ["ADMIN_USERNAME"] = "demo-admin"
os.environ["ADMIN_PASSWORD"] = "Round-3-Demo-Pass!"
os.environ["REGISTRATION_RATE_LIMIT"] = "1000"
os.environ["ENVIRONMENT"] = "development"
os.environ["SECURE_COOKIES"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app import auth, config, database  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.routes import registrations  # noqa: E402

VALID_PAYLOAD = {
    "full_name": "Demo Visitor",
    "email": "demo-visitor@example.com",
    "preferred_date": "2026-11-15",
    "guest_count": 3,
    "experience_type": "peth-stories-walk",
    "notes": "One member uses a walking cane.",
    "consent": True,
    "website": "",
}


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Fresh temporary database + clean in-memory state for every test."""
    db_file = tmp_path / "test-sheharnaama.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", str(db_file))
    database.init_db()
    auth.reset_all_sessions()
    registrations._submission_times.clear()
    yield
    auth.reset_all_sessions()
    registrations._submission_times.clear()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_client(client):
    """A client with an authenticated admin session cookie."""
    response = client.post(
        "/api/admin/login",
        json={"username": "demo-admin", "password": "Round-3-Demo-Pass!"},
    )
    assert response.status_code == 200, response.text
    return client