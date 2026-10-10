"""Backend tests for the Sheharnaama full-stack prototype.

Runs against a temporary per-test SQLite database — never the real one.
"""

import re

import pytest

from backend.app import config, models
from backend.app.routes import registrations


VALID = {
    "full_name": "Demo Visitor",
    "email": "demo-visitor@example.com",
    "preferred_date": "2026-11-15",
    "guest_count": 3,
    "experience_type": "peth-stories-walk",
    "notes": "One member uses a walking cane.",
    "consent": True,
    "website": "",
}


def register(client, payload=None, headers=None):
    return client.post(
        "/api/registrations",
        json=payload if payload is not None else dict(VALID),
        headers=headers or {},
    )


# 1. Health endpoint
def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# 2. Landing page delivery
def test_landing_page_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Sheharnaama" in response.text
    assert 'id="interest-form"' in response.text


# 3. Required-field validation
@pytest.mark.parametrize("missing", ["full_name", "email", "guest_count", "experience_type", "consent"])
def test_required_fields_enforced(client, missing):
    payload = dict(VALID)
    payload.pop(missing)
    response = register(client, payload)
    assert response.status_code == 422


# 4. Invalid email rejection
@pytest.mark.parametrize("bad", ["not-an-email", "a@b", "two@@ats.com", "user@ domain.com"])
def test_invalid_email_rejected(client, bad):
    payload = dict(VALID)
    payload["email"] = bad
    response = register(client, payload)
    assert response.status_code == 422


# 5. Invalid guest counts rejected (outside 1-12)
@pytest.mark.parametrize("guests", [0, -2, 13, 99])
def test_invalid_guest_count_rejected(client, guests):
    payload = dict(VALID)
    payload["guest_count"] = guests
    response = register(client, payload)
    assert response.status_code == 422


# 6. Consent enforcement
def test_consent_required(client):
    payload = dict(VALID)
    payload["consent"] = False
    response = register(client, payload)
    assert response.status_code == 422


# Honeypot rejection
def test_honeypot_rejects_bots(client):
    payload = dict(VALID)
    payload["website"] = "http://spam.example"
    response = register(client, payload)
    assert response.status_code == 400


# 7. Successful registration persists
def test_successful_registration_persists(admin_client):
    response = register(admin_client)
    assert response.status_code == 201
    data = response.json()
    assert data["ok"] is True
    reference = data["reference"]

    listed = admin_client.get("/api/admin/registrations")
    assert listed.status_code == 200
    refs = [item["public_reference"] for item in listed.json()["items"]]
    assert reference in refs


# 8. Registration reference generation
def test_reference_format_and_uniqueness(client):
    first = register(client).json()["reference"]
    second = register(
        client,
        {**VALID, "email": "second-visitor@example.com"},
    ).json()["reference"]
    assert re.fullmatch(r"SH-\d{4}-[0-9A-F]{6}", first)
    assert first != second


# 9. Registration survives application/database reconnection
def test_registration_survives_reconnection(admin_client):
    reference = register(admin_client).json()["reference"]
    record = models.get_registration_by_reference(reference)
    assert record is not None

    # Simulate a fresh application instance connecting to the same database.
    from fastapi.testclient import TestClient
    from backend.app.main import app as fresh_app

    with TestClient(fresh_app) as fresh_client:
        fresh_client.post(
            "/api/admin/login",
            json={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD},
        )
        listed = fresh_client.get("/api/admin/registrations")
        refs = [item["public_reference"] for item in listed.json()["items"]]
        assert reference in refs


# 10. No success response if the database operation fails
def test_database_failure_returns_error_not_success(client, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("simulated disk failure")

    monkeypatch.setattr(models, "create_registration", boom)
    response = register(client)
    assert response.status_code == 500
    body = response.json()
    assert "reference" not in body
    assert "could not save" in body["detail"].lower()


# 11. Unauthorized admin requests rejected
def test_admin_endpoints_require_auth(client):
    assert client.get("/api/admin/registrations").status_code == 401
    assert client.get("/api/admin/stats").status_code == 401
    assert client.get("/api/admin/registrations/1").status_code == 401
    assert client.get("/api/admin/registrations/export.csv").status_code == 401
    assert client.patch(
        "/api/admin/registrations/1/status", json={"status": "CONTACTED"}
    ).status_code == 401


# 12. Successful admin login
def test_admin_login_success(client):
    response = client.post(
        "/api/admin/login",
        json={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    assert "sheharnaama_admin" in response.cookies
    me = client.get("/api/admin/me")
    assert me.status_code == 200
    assert me.json()["username"] == config.ADMIN_USERNAME


# 13. Invalid admin login
def test_admin_login_invalid(client):
    response = client.post(
        "/api/admin/login",
        json={"username": config.ADMIN_USERNAME, "password": "wrong-password!"},
    )
    assert response.status_code == 401
    response = client.post(
        "/api/admin/login",
        json={"username": "nobody-else", "password": config.ADMIN_PASSWORD},
    )
    assert response.status_code == 401


# Login throttling protects against repeated attempts
def test_admin_login_throttling(client):
    for _ in range(config.LOGIN_MAX_FAILURES):
        client.post(
            "/api/admin/login",
            json={"username": config.ADMIN_USERNAME, "password": "wrong-password!"},
        )
    response = client.post(
        "/api/admin/login",
        json={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD},
    )
    assert response.status_code == 429


# 14. Protected registration listing (with auth + filters)
def test_admin_listing_search_and_filter(admin_client):
    register(admin_client, {**VALID, "full_name": "Asha Kulkarni", "email": "asha@example.com"})
    register(
        admin_client,
        {**VALID, "full_name": "Rohan Verma", "email": "rohan@example.com",
         "experience_type": "private-group"},
    )

    listed = admin_client.get("/api/admin/registrations")
    assert listed.json()["total"] == 2

    searched = admin_client.get("/api/admin/registrations", params={"q": "asha"})
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["full_name"] == "Asha Kulkarni"

    filtered = admin_client.get(
        "/api/admin/registrations", params={"status": "INTEREST_RECEIVED"}
    )
    assert filtered.json()["total"] == 2

    bad_status = admin_client.get("/api/admin/registrations", params={"status": "NOPE"})
    assert bad_status.status_code == 422

    listed_page = admin_client.get(
        "/api/admin/registrations", params={"per_page": 1, "page": 2}
    )
    assert len(listed_page.json()["items"]) == 1
    assert listed_page.json()["pages"] == 2


# 15. Registration status update persists
def test_status_update(admin_client):
    reference = register(admin_client).json()["reference"]
    detail = admin_client.get(
        "/api/admin/registrations", params={"q": reference}
    ).json()["items"][0]

    updated = admin_client.patch(
        f"/api/admin/registrations/{detail['id']}/status",
        json={"status": "CONTACTED"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "CONTACTED"

    reloaded = admin_client.get(f"/api/admin/registrations/{detail['id']}")
    assert reloaded.json()["status"] == "CONTACTED"


# 16. Invalid status update rejected
def test_invalid_status_rejected(admin_client):
    reference = register(admin_client).json()["reference"]
    detail = admin_client.get(
        "/api/admin/registrations", params={"q": reference}
    ).json()["items"][0]

    for bad in ["CONFIRMED", "PAID", ""]:
        response = admin_client.patch(
            f"/api/admin/registrations/{detail['id']}/status",
            json={"status": bad},
        )
        assert response.status_code == 422, bad

    missing = admin_client.patch("/api/admin/registrations/999999/status", json={"status": "CONTACTED"})
    assert missing.status_code == 404


# 17. Logout invalidates the session server-side
def test_logout_invalidates_session(admin_client):
    assert admin_client.get("/api/admin/me").status_code == 200
    response = admin_client.post("/api/admin/logout")
    assert response.status_code == 200
    assert admin_client.get("/api/admin/me").status_code == 401
    assert admin_client.get("/api/admin/registrations").status_code == 401


# 18. CSV export with formula-injection safety
def test_csv_export_and_safe_encoding(admin_client):
    register(
        admin_client,
        {**VALID, "full_name": "=HYPERLINK(\"http://evil.example\",\"click\")"},
    )
    response = admin_client.get("/api/admin/registrations/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "Reference,Name,Email" in body
    assert re.search(r"'\"?=HYPERLINK", body) or "'=HYPERLINK" in body
    assert "\r\n" in body  # spreadsheet-friendly line endings


# 19. Idempotency — duplicate submissions do not create duplicate records
def test_idempotent_duplicate_requests(client, admin_client):
    headers = {"X-Idempotency-Key": "test-key-12345678"}
    first = register(client, headers=headers)
    assert first.status_code == 201
    assert first.json()["idempotent"] is False

    duplicate = register(client, headers=headers)
    assert duplicate.status_code == 201
    assert duplicate.json()["idempotent"] is True
    assert duplicate.json()["reference"] == first.json()["reference"]

    listed = admin_client.get("/api/admin/registrations")
    assert listed.json()["total"] == 1

    bad_key = register(client, headers={"X-Idempotency-Key": "short"})
    assert bad_key.status_code == 400


# Registration throttling
def test_registration_throttling(client, monkeypatch):
    monkeypatch.setattr(config, "REGISTRATION_RATE_LIMIT_PER_MINUTE", 2)
    registrations._submission_times.clear()
    for i in range(2):
        response = register(
            client, {**VALID, "email": f"visitor-{i}@example.com"}
        )
        assert response.status_code == 201
    throttled = register(client, {**VALID, "email": "visitor-extra@example.com"})
    assert throttled.status_code == 429
    registrations._submission_times.clear()


# 20. Admin page + static assets served on same origin
def test_admin_page_and_assets_served(client):
    page = client.get("/admin")
    assert page.status_code == 200
    assert "Admin" in page.text

    asset = client.get("/assets/img/logo_icon.svg")
    assert asset.status_code == 200
    css = client.get("/assets/css/admin.css")
    assert css.status_code == 200

    # The database file must NOT be publicly reachable.
    leaked = client.get("/data/sheharnaama.sqlite3")
    assert leaked.status_code in (404, 405)