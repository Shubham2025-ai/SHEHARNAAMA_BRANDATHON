"""Restart-persistence check: creates demo data, restarts the real uvicorn
server process, and verifies both the session and the registration survive.

Run: venv\\Scripts\\python tools\\restart_persistence_check.py
"""

import json
import os
import subprocess
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8080"
JAR = {}
results = []


def ok(name, condition, detail=""):
    results.append(("PASS" if condition else "FAIL") + f" {name}" + (f" — {detail}" if detail else ""))


def request(method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    for key, value in JAR.items():
        req.add_header("Cookie", f"{key}={value}")
    try:
        with urllib.request.urlopen(req) as response:
            set_cookie = response.headers.get("Set-Cookie")
            if set_cookie:
                name, _, value = set_cookie.split(";")[0].partition("=")
                JAR[name] = value
            return response.status, json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def stop_server():
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Where-Object { $_.CommandLine -match 'uvicorn' } | "
         "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
        capture_output=True,
    )
    time.sleep(1.5)


def start_server():
    subprocess.Popen(
        ["venv\\Scripts\\python.exe", "-m", "uvicorn", "backend.app.main:app",
         "--host", "127.0.0.1", "--port", "8080"],
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=".",
    )
    for _ in range(30):
        time.sleep(1)
        try:
            request("GET", "/api/health")
            return True
        except Exception:
            continue
    return False


# --- phase 1: with the server running, create demo session + registration ---
status, _ = request("POST", "/api/admin/login",
                    {"username": "demo-admin", "password": "Round-3-Demo-Pass!"})
ok("login before restart", status == 200)

SESSION = {
    "title": "Persistence Check [DEMO]",
    "description": "Demo session created to verify restart persistence, labelled clearly as demo.",
    "walk_date": "2027-06-15",
    "start_time": "08:00",
    "duration_minutes": 90,
    "meeting_point": "Persistence checkpoint (demo)",
    "capacity": 10,
    "inclusions": None,
}
status, session = request("POST", "/api/admin/sessions", SESSION)
sid = session.get("id")
ok("demo session created", status == 201, f"id={sid}")
request("PATCH", f"/api/admin/sessions/{sid}/status", {"status": "PUBLISHED"})

status, reg = request("POST", "/api/registrations", {
    "full_name": "Persistence Visitor",
    "email": "persist-check@example.com",
    "guest_count": 2,
    "experience_type": "peth-stories-walk",
    "consent": True,
    "session_id": sid,
})
reference = reg.get("reference")
ok("demo registration created", status == 201, reference or "")

# --- phase 2: restart the real application process ---
stop_server()
ok("server restarted", start_server())

# --- phase 3: fresh login, verify both records survived ---
status, _ = request("POST", "/api/admin/login",
                    {"username": "demo-admin", "password": "Round-3-Demo-Pass!"})
ok("login after restart", status == 200)

status, detail = request("GET", f"/api/admin/sessions/{sid}")
ok("session persisted (with enquiry link)", status == 200
   and detail["session"]["title"] == SESSION["title"]
   and detail["session"]["status"] == "PUBLISHED"
   and detail["session"]["enquiry_count"] == 1)

status, found = request("GET", f"/api/admin/registrations?q={reference}")
ok("registration persisted", status == 200
   and found["items"][0]["public_reference"] == reference
   and found["items"][0]["session_id"] == sid)

# --- cleanup: remove the demo session; keep nothing fabricated in the demo DB ---
import sqlite3
conn = sqlite3.connect("data/sheharnaama.sqlite3")
conn.execute("UPDATE registrations SET session_id = NULL WHERE session_id = ?", (sid,))
conn.execute("DELETE FROM walk_sessions WHERE id = ?", (sid,))
conn.execute("DELETE FROM registrations WHERE email = 'persist-check@example.com'")
conn.commit()
conn.close()
print("--- cleanup: demo records removed; demo database is empty again ---")

print()
passed = sum(1 for r in results if r.startswith("PASS"))
print(f"{passed}/{len(results)} checks passed")
for line in results:
    print(line)