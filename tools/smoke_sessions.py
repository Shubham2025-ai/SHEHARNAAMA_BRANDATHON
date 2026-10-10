import os

os.environ["SHEHARNAAMA_DB_PATH"] = "data/smoke.sqlite3"
os.environ["ADMIN_USERNAME"] = "smoke-admin"
os.environ["ADMIN_PASSWORD"] = "Smoke-Test-Pass-9"

from fastapi.testclient import TestClient
from backend.app.main import app

with TestClient(app) as c:
    print("empty public sessions:", c.get("/api/sessions").json())
    c.post("/api/admin/login", json={"username": "smoke-admin", "password": "Smoke-Test-Pass-9"})
    created = c.post(
        "/api/admin/sessions",
        json={
            "title": "Peth Stories Walk - Demo",
            "description": "A demonstration session for smoke testing the schedule.",
            "walk_date": "2099-05-10",
            "start_time": "09:30",
            "duration_minutes": 120,
            "meeting_point": "Shaniwar Wada gate, Pune",
            "capacity": 12,
            "inclusions": "Story Passport included",
        },
    )
    print("created:", created.status_code, created.json()["status"])
    pub = c.get("/api/sessions").json()["items"]
    print("hidden while draft:", len(pub) == 0)
    sid = created.json()["id"]
    c.patch(f"/api/admin/sessions/{sid}/status", json={"status": "PUBLISHED"})
    pub = c.get("/api/sessions").json()["items"]
    print("visible after publish:", len(pub) == 1, "|", pub[0]["title"])
    reg = c.post(
        "/api/registrations",
        json={
            "full_name": "Smoke Visitor",
            "email": "smoke@example.com",
            "guest_count": 2,
            "experience_type": "peth-stories-walk",
            "consent": True,
            "session_id": sid,
        },
    )
    body = reg.json()
    print("registration w/ session:", reg.status_code, "| session echoed:", body.get("session", {}).get("title"))
    detail = c.get(f"/api/admin/sessions/{sid}").json()
    print("enquiry count on session:", len(detail["enquiries"]))
    general = c.post(
        "/api/registrations",
        json={
            "full_name": "General Visitor",
            "email": "general@example.com",
            "guest_count": 1,
            "experience_type": "private-group",
            "consent": True,
        },
    )
    print("general registration:", general.status_code)
    c.patch(f"/api/admin/sessions/{sid}/status", json={"status": "CANCELLED"})
    print("cancelled hidden from public:", len(c.get("/api/sessions").json()["items"]) == 0)