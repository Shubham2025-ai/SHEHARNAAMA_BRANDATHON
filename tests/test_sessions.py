"""Walk-schedule & session-management tests (temporary databases only)."""

import sqlite3
from datetime import date, timedelta

import pytest

from backend.app import config, database, models

FUTURE_DATE = (date.today() + timedelta(days=14)).isoformat()
PAST_DATE = (date.today() - timedelta(days=7)).isoformat()

VALID_SESSION = {
    "title": "Peth Stories Walk - Old Pune",
    "description": "A story-led morning through the lanes of the old city.",
    "walk_date": FUTURE_DATE,
    "start_time": "09:30",
    "duration_minutes": 120,
    "meeting_point": "Shaniwar Wada main gate, Pune",
    "capacity": 12,
    "inclusions": "Story Passport included.",
}

VALID_REGISTRATION = {
    "full_name": "Session Tester",
    "email": "session-tester@example.com",
    "guest_count": 2,
    "experience_type": "peth-stories-walk",
    "consent": True,
    "website": "",
}


@pytest.fixture()
def admin_session(admin_client):
    return admin_client


def create_session(client, **overrides):
    payload = {**VALID_SESSION, **overrides}
    return client.post("/api/admin/sessions", json=payload)


# 1. Creating a session with valid input
def test_create_session_valid(admin_session):
    response = create_session(admin_session)
    assert response.status_code == 201
    session = response.json()
    assert session["status"] == "DRAFT"          # never published by accident
    assert session["title"] == VALID_SESSION["title"]


# 2. Rejecting invalid session data
def test_create_session_invalid_data(admin_session):
    # Full payloads posted directly (so a "missing field" case stays missing).
    cases = [
        {**VALID_SESSION, "title": "x"},                          # too short
        {**VALID_SESSION, "description": "short"},                # <10 chars
        {**VALID_SESSION, "walk_date": "15/12/2026"},             # not ISO
        {**VALID_SESSION, "walk_date": "2099-02-30"},             # impossible date
        {**VALID_SESSION, "start_time": "9:30"},                  # missing zero
        {**VALID_SESSION, "start_time": "25:00"},                 # out of range
        {**VALID_SESSION, "duration_minutes": 5},                 # below 15
        {**VALID_SESSION, "capacity": 0},                         # invalid capacity
        {**VALID_SESSION, "capacity": 61},                        # above 60
        {k: v for k, v in VALID_SESSION.items() if k != "meeting_point"},  # missing field
    ]
    for payload in cases:
        response = admin_session.post("/api/admin/sessions", json=payload)
        assert response.status_code == 422, payload


# 3. Public visibility of published sessions
def test_public_visibility_of_published_sessions(admin_session, client):
    created = create_session(admin_session).json()
    assert client.get("/api/sessions").json()["items"] == []   # draft hidden

    admin_session.patch(f"/api/admin/sessions/{created['id']}/status", json={"status": "PUBLISHED"})
    items = client.get("/api/sessions").json()["items"]
    assert len(items) == 1
    public = items[0]
    assert public["title"] == VALID_SESSION["title"]
    # Only visitor-relevant fields are exposed
    assert "created_at" not in public and "updated_at" not in public


# 4. Hiding draft, cancelled, completed and past sessions
def test_non_eligible_sessions_hidden(admin_session, client):
    draft = create_session(admin_session).json()

    published = create_session(admin_session, title="Published upcoming").json()
    admin_session.patch(f"/api/admin/sessions/{published['id']}/status", json={"status": "PUBLISHED"})

    cancelled = create_session(admin_session, title="Cancelled one").json()
    admin_session.patch(f"/api/admin/sessions/{cancelled['id']}/status", json={"status": "PUBLISHED"})
    admin_session.patch(f"/api/admin/sessions/{cancelled['id']}/status", json={"status": "CANCELLED"})

    completed = create_session(admin_session, title="Completed one").json()
    admin_session.patch(f"/api/admin/sessions/{completed['id']}/status", json={"status": "PUBLISHED"})
    admin_session.patch(f"/api/admin/sessions/{completed['id']}/status", json={"status": "COMPLETED"})

    past = create_session(admin_session, title="Past one", walk_date=PAST_DATE).json()
    admin_session.patch(f"/api/admin/sessions/{past['id']}/status", json={"status": "PUBLISHED"})

    items = client.get("/api/sessions").json()["items"]
    titles = [s["title"] for s in items]
    assert titles == ["Published upcoming"]  # draft/cancelled/completed/past all hidden


# 5. Unauthenticated administrative session actions rejected
def test_session_admin_requires_auth(client):
    assert client.get("/api/admin/sessions").status_code == 401
    assert client.get("/api/admin/sessions/1").status_code == 401
    assert client.post("/api/admin/sessions", json=VALID_SESSION).status_code == 401
    assert client.patch("/api/admin/sessions/1", json=VALID_SESSION).status_code == 401
    assert client.patch(
        "/api/admin/sessions/1/status", json={"status": "PUBLISHED"}
    ).status_code == 401


# 6. Editing sessions
def test_edit_session(admin_session):
    created = create_session(admin_session).json()
    edited = admin_session.patch(
        f"/api/admin/sessions/{created['id']}",
        json={**VALID_SESSION, "title": "Edited title", "start_time": "17:45", "capacity": None},
    )
    assert edited.status_code == 200
    body = edited.json()
    assert body["title"] == "Edited title"
    assert body["start_time"] == "17:45"
    assert body["capacity"] is None

    invalid_edit = admin_session.patch(
        f"/api/admin/sessions/{created['id']}",
        json={**VALID_SESSION, "walk_date": "not-a-date"},
    )
    assert invalid_edit.status_code == 422

    missing = admin_session.patch("/api/admin/sessions/999999", json=VALID_SESSION)
    assert missing.status_code == 404


# 7. Cancelling sessions hides them and keeps records auditable
def test_cancel_session(admin_session, client):
    created = create_session(admin_session).json()
    admin_session.patch(f"/api/admin/sessions/{created['id']}/status", json={"status": "PUBLISHED"})
    response = admin_session.patch(
        f"/api/admin/sessions/{created['id']}/status", json={"status": "CANCELLED"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert client.get("/api/sessions").json()["items"] == []
    # Admin can still see the session history
    listed = admin_session.get("/api/admin/sessions").json()["items"]
    assert listed[0]["status"] == "CANCELLED"


# Invalid status values rejected
def test_invalid_session_status_rejected(admin_session):
    created = create_session(admin_session).json()
    response = admin_session.patch(
        f"/api/admin/sessions/{created['id']}/status", json={"status": "CONFIRMED"}
    )
    assert response.status_code == 422
    unknown = admin_session.patch("/api/admin/sessions/999999/status", json={"status": "PUBLISHED"})
    assert unknown.status_code == 404


# 8. Associating an interest registration with a published session
def test_registration_with_session(admin_session, client):
    created = create_session(admin_session).json()
    admin_session.patch(f"/api/admin/sessions/{created['id']}/status", json={"status": "PUBLISHED"})

    response = client.post(
        "/api/registrations",
        json={**VALID_REGISTRATION, "session_id": created["id"]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["reference"].startswith("SH-")
    assert body["session"]["id"] == created["id"]
    assert body["session"]["meeting_point"] == VALID_SESSION["meeting_point"]

    # The enquiry is counted and listed against the session
    detail = admin_session.get(f"/api/admin/sessions/{created['id']}").json()
    assert detail["session"]["enquiry_count"] == 1
    refs = [e["public_reference"] for e in detail["enquiries"]["items"]]
    assert body["reference"] in refs


# 9. General interest registrations without a session keep working
def test_general_registration_without_session(client, admin_client):
    response = client.post("/api/registrations", json=VALID_REGISTRATION)
    assert response.status_code == 201
    assert response.json().get("session") is None

    listed = admin_client.get("/api/admin/registrations").json()
    assert listed["total"] == 1
    assert listed["items"][0]["session_id"] is None
    assert listed["items"][0]["session_title"] is None


# 10. Invalid session references rejected
def test_invalid_session_reference_rejected(client, admin_client):
    # Non-existent id
    response = client.post("/api/registrations", json={**VALID_REGISTRATION, "session_id": 999999})
    assert response.status_code == 422
    # Draft session
    draft = create_session(admin_client).json()
    response = client.post("/api/registrations", json={**VALID_REGISTRATION, "session_id": draft["id"]})
    assert response.status_code == 422
    # Cancelled session
    cancelled = create_session(admin_client, title="Cancelled run").json()
    admin_client.patch(f"/api/admin/sessions/{cancelled['id']}/status", json={"status": "CANCELLED"})
    response = client.post("/api/registrations", json={**VALID_REGISTRATION, "session_id": cancelled["id"]})
    assert response.status_code == 422
    # Past-dated published session
    past = create_session(admin_client, title="Past run", walk_date=PAST_DATE).json()
    admin_client.patch(f"/api/admin/sessions/{past['id']}/status", json={"status": "PUBLISHED"})
    response = client.post("/api/registrations", json={**VALID_REGISTRATION, "session_id": past["id"]})
    assert response.status_code == 422


# 11. Existing registrations preserved through schema migration v1 -> v2
def test_migration_preserves_existing_registrations(tmp_path):
    old_db = tmp_path / "migrated.sqlite3"
    conn = sqlite3.connect(old_db)
    conn.executescript(
        """
        CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_reference TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL, email TEXT NOT NULL, preferred_date TEXT,
            guest_count INTEGER NOT NULL, experience_type TEXT NOT NULL,
            notes TEXT, consent INTEGER NOT NULL, status TEXT NOT NULL,
            idempotency_key TEXT UNIQUE, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        INSERT INTO registrations (public_reference, full_name, email, guest_count,
            experience_type, consent, status, created_at, updated_at)
        VALUES ('SH-2026-LEGACY1', 'Existing Visitor', 'existing@example.com', 2,
            'peth-stories-walk', 1, 'CONTACTED', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00');
        INSERT INTO schema_meta VALUES ('schema_version', '1');
        """
    )
    conn.commit()
    conn.close()

    # Run the app's migration against this legacy database.
    database.init_db(str(old_db))
    migrated = sqlite3.connect(old_db)
    columns = {row[1] for row in migrated.execute("PRAGMA table_info(registrations)")}
    rows = list(migrated.execute("SELECT public_reference, full_name FROM registrations"))
    migrated.close()

    assert "session_id" in columns
    assert rows == [("SH-2026-LEGACY1", "Existing Visitor")]


# 12. Session + registration data persist after a restart
def test_session_data_persists_after_restart(admin_session, client):
    created = create_session(admin_session).json()
    admin_session.patch(f"/api/admin/sessions/{created['id']}/status", json={"status": "PUBLISHED"})
    client.post("/api/registrations", json={**VALID_REGISTRATION, "session_id": created["id"]})

    from fastapi.testclient import TestClient
    from backend.app.main import app as fresh_app

    with TestClient(fresh_app) as fresh_client:
        fresh_client.post(
            "/api/admin/login",
            json={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD},
        )
        sessions = fresh_client.get("/api/admin/sessions").json()["items"]
        assert [s["title"] for s in sessions] == [VALID_SESSION["title"]]
        assert sessions[0]["enquiry_count"] == 1
        detail = fresh_client.get(f"/api/admin/sessions/{created['id']}").json()
        assert detail["session"]["status"] == "PUBLISHED"


# 13. Admin session stats and filters
def test_admin_session_list_filters_and_counts(admin_session):
    s1 = create_session(admin_session, title="Alpha walk").json()
    create_session(admin_session, title="Beta walk", walk_date=PAST_DATE).json()
    admin_session.patch(f"/api/admin/sessions/{s1['id']}/status", json={"status": "PUBLISHED"})

    published = admin_session.get("/api/admin/sessions", params={"status": "PUBLISHED"}).json()["items"]
    assert [s["title"] for s in published] == ["Alpha walk"]

    searched = admin_session.get("/api/admin/sessions", params={"q": "beta"}).json()["items"]
    assert [s["title"] for s in searched] == ["Beta walk"]

    bad = admin_session.get("/api/admin/sessions", params={"status": "NOPE"})
    assert bad.status_code == 422

    counts = admin_session.get("/api/admin/sessions/stats").json()
    assert counts["total"] == 2
    assert counts["DRAFT"] == 1 and counts["PUBLISHED"] == 1


# 14. Existing registration functionality unchanged (regression spot-check)
def test_existing_registration_flow_unaffected(client):
    response = client.post(
        "/api/registrations",
        json={
            "full_name": "Plain Visitor",
            "email": "plain@example.com",
            "preferred_date": "2026-12-20",
            "guest_count": 5,
            "experience_type": "peth-stories-walk",
            "consent": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["session"] is None
    assert body["message"].lower().startswith("interest received")