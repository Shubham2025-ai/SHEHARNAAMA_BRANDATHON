import os

os.environ["SHEHARNAAMA_DB_PATH"] = "data/debug.sqlite3"
os.environ["ADMIN_USERNAME"] = "debug-admin"
os.environ["ADMIN_PASSWORD"] = "Debug-Test-Pass-1"

from fastapi.testclient import TestClient
from backend.app.main import app

with TestClient(app) as c:
    r = c.post("/api/admin/login", json={"username": "debug-admin", "password": "Debug-Test-Pass-1"})
    print("login:", r.status_code)
    r = c.get("/api/admin/sessions")
    print("admin sessions GET:", r.status_code, r.text[:200])
    r = c.post("/api/admin/sessions", json={
        "title": "Debug session", "description": "Debugging route registration.",
        "walk_date": "2099-01-01", "start_time": "09:00", "duration_minutes": 60,
        "meeting_point": "Somewhere", "capacity": 5, "inclusions": None})
    print("admin sessions POST:", r.status_code, r.text[:200])