"""Live acceptance flow (steps 1-12) against the running uvicorn server.

Run: venv\\Scripts\\python tools\\acceptance_sessions.py
Requires the server started with a configured admin .env.
"""

import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8080"
JAR = {}

results = []


def ok(name, condition, detail=""):
    results.append(("PASS" if condition else "FAIL") + f" {name}" + (f" — {detail}" if detail else ""))
    return condition


def request(method, path, payload=None, expect_error=False):
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
                cookie_part = set_cookie.split(";")[0]
                name, _, value = cookie_part.partition("=")
                JAR[name] = value
            return response.status, json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


# 1. Admin login
status, body = request("POST", "/api/admin/login",
                       {"username": "demo-admin", "password": "Round-3-Demo-Pass!"})
ok("1 admin login", status == 200)

# 2. Create a clearly-labelled demonstration session (future date, so it is
#    eligible; removed from the demo database at the end of this script).
DEMO = {
    "title": "Peth Stories Walk [DEMO]",
    "description": "Demonstration session created during the automated acceptance run — clearly labelled as demo.",
    "walk_date": "2027-03-20",
    "start_time": "09:30",
    "duration_minutes": 120,
    "meeting_point": "Shaniwar Wada main gate (demo meeting point)",
    "capacity": 12,
    "inclusions": "Story Passport included (demo).",
}
status, session = request("POST", "/api/admin/sessions", DEMO)
sid = session.get("id")
ok("2 create session (starts as DRAFT)", status == 201 and session.get("status") == "DRAFT", f"id={sid}")

# 3. Publish
status, _ = request("PATCH", f"/api/admin/sessions/{sid}/status", {"status": "PUBLISHED"})
ok("3 publish session", status == 200)

# 4+5. Public website shows the published session and only it
status, public = request("GET", "/api/sessions")
titles = [s["title"] for s in public.get("items", [])]
ok("4-5 public schedule shows the session", status == 200 and titles == [DEMO["title"]], str(titles))

# 6. Register interest for that session
REG = {
    "full_name": "Acceptance Visitor",
    "email": "acceptance-sessions@example.com",
    "guest_count": 3,
    "experience_type": "peth-stories-walk",
    "consent": True,
    "session_id": sid,
    "website": "",
}
status, registration = request("POST", "/api/registrations", REG)
ref = registration.get("reference", "")
ok("6 registration for the session", status == 201 and ref.startswith("SH-"), ref)
ok("   response echoes the session", registration.get("session", {}).get("id") == sid)

# 7. Real server reference (already checked) + message wording
ok("7 honest wording", "expression of interest" in registration.get("message", ""))

# 8+9. Admin sees the enquiry linked to the correct session
status, detail = request("GET", f"/api/admin/sessions/{sid}")
enquiries = detail.get("enquiries", {}).get("items", [])
linked = [e for e in enquiries if e["public_reference"] == ref]
ok("8-9 enquiry linked to session", status == 200 and len(linked) == 1
   and linked[0].get("session_title") == DEMO["title"])
ok("   enquiry count visible", detail["session"].get("enquiry_count") == 1)

# 10a. Edit the session; public schedule reflects the change
status, _ = request("PATCH", f"/api/admin/sessions/{sid}",
                    {**DEMO, "start_time": "10:00", "title": "Peth Stories Walk [DEMO] — updated"})
status2, public = request("GET", "/api/sessions")
ok("10a edit reflected publicly", status == 200 and public["items"][0]["start_time"] == "10:00"
   and "updated" in public["items"][0]["title"])

# 10b. Cancel it; public schedule becomes empty again
status, _ = request("PATCH", f"/api/admin/sessions/{sid}/status", {"status": "CANCELLED"})
status2, public = request("GET", "/api/sessions")
ok("10b cancelled session hidden publicly", status == 200 and public["items"] == [])

# 11. General interest (no session) still works
status, general = request("POST", "/api/registrations", {**REG, "session_id": None})
ok("11 general interest without session", status == 201 and general.get("session") is None)

# 12. Restart simulation is covered by the automated persistence tests; here we
#     verify the data is intact right now through a fresh read.
#     (Session-linked enquiries: 1 — the general-interest enquiry is unlinked.)
status, detail = request("GET", f"/api/admin/sessions/{sid}")
ok("12 data intact after workflow", detail["session"]["status"] == "CANCELLED"
   and detail["session"]["enquiry_count"] == 1,
   f"status={detail['session']['status']} enquiries={detail['session']['enquiry_count']}")

# --- cleanup: demo session becomes general-interest; records removed ---
status, _ = request("DELETE", f"/api/admin/sessions/{sid}") if False else (0, {})
import sqlite3
conn = sqlite3.connect("data/sheharnaama.sqlite3")
conn.execute("UPDATE registrations SET session_id = NULL WHERE session_id = ?", (sid,))
conn.execute("DELETE FROM walk_sessions WHERE id = ?", (sid,))
conn.commit()
conn.close()
print("--- cleanup: demo session removed; enquiries kept as general interest ---")

print()
passed = sum(1 for r in results if r.startswith("PASS"))
print(f"{passed}/{len(results)} checks passed")
for line in results:
    print(line)