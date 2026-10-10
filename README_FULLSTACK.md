# SHEHARNAAMA — Full-Stack Setup & Operations Guide (Windows PowerShell)

The Sheharnaama landing page now runs as a full-stack prototype:
the existing static frontend, served by a **FastAPI** backend with a
**SQLite** database and a server-authenticated **admin console**.

An interest-form submission is an **expression of interest** — never a
confirmed tour booking, and no payment is involved.

---

## Architecture

```
index.html                 existing landing page (unchanged design)
admin.html                 admin console (served at /admin)
assets/                    existing CSS/JS/images (form JS now calls the API)
backend/app/
  main.py                  FastAPI app: serves frontend + API, same origin
  config.py                environment configuration & credential policy
  database.py              SQLite connection management, schema, migrations
  models.py                parameterised data access
  schemas.py               Pydantic validation
  auth.py                  sessions, cookies, login throttling
  routes/registrations.py  POST /api/registrations
  routes/admin.py          login/logout/me/stats/list/detail/status/CSV
data/                      SQLite database (NOT publicly served, git-ignored)
tests/                     automated tests (temporary DB only)
tools/                     frontend QA harnesses (dev only)
```

API surface:

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET  | `/api/health` | — | health check |
| POST | `/api/registrations` | — | interest registration (rate-limited, honeypot, idempotency-key aware, optional `session_id`) |
| GET  | `/api/sessions` | — | public upcoming schedule: published, future sessions only |
| POST | `/api/admin/login` | — | admin login (server-side session) |
| POST | `/api/admin/logout` | — | logout, invalidates session |
| GET  | `/api/admin/me` | ✓ | current session info |
| GET  | `/api/admin/stats` | ✓ | real enquiry counts by status |
| GET  | `/api/admin/registrations` | ✓ | searchable/filterable/paginated list (`session_id` filter supported) |
| GET  | `/api/admin/registrations/{id}` | ✓ | full detail incl. notes |
| PATCH | `/api/admin/registrations/{id}/status` | ✓ | enquiry status update (validated) |
| GET  | `/api/admin/registrations/export.csv` | ✓ | CSV export (formula-injection safe, includes session column) |
| POST | `/api/admin/sessions` | ✓ | create walk session (starts as DRAFT) |
| GET  | `/api/admin/sessions/stats` | ✓ | session counts by status |
| GET  | `/api/admin/sessions` | ✓ | list sessions with enquiry counts (`q`, `status` filters) |
| GET  | `/api/admin/sessions/{id}` | ✓ | session detail + linked enquiries |
| PATCH | `/api/admin/sessions/{id}` | ✓ | edit session details |
| PATCH | `/api/admin/sessions/{id}/status` | ✓ | publish / unpublish / cancel / complete |

Registration statuses: `INTEREST_RECEIVED` (initial), `CONTACTED`,
`WAITLISTED`, `CLOSED`.
Session statuses: `DRAFT` (initial), `PUBLISHED`, `CANCELLED`, `COMPLETED`.
Only **published, future-dated** sessions appear publicly; registering
interest against a session is an enquiry, never a reserved seat.

---

## 1. Create a virtual environment

```powershell
cd D:\SHEHARNAAMA_BRANDATHON
python -m venv venv
```

## 2. Install dependencies

```powershell
venv\Scripts\pip install -r requirements.txt
```

## 3. Create a secure local `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

Set at minimum:

```
ADMIN_USERNAME=demo-admin
ADMIN_PASSWORD=<a strong password, 8+ characters>
SESSION_SECRET=<any long random string>
```

Rules enforced by the server:
- Missing/weak credentials (e.g. `admin`, `password`, values shorter than 8
  characters) → admin endpoints return a clear **503 setup error**; admin is
  never left publicly accessible.
- Prefer `ADMIN_PASSWORD_HASH` (sha256 hex of the password) if you prefer
  not to store the plain password locally:
  ```powershell
  # PowerShell: print the hash of your password
  -join ([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes("YOUR-PASSWORD")) | ForEach-Object ToString "x2")
  ```

`.env` is git-ignored; only `.env.example` (placeholders) is tracked.

## 4. Start the server

Run from the project root:

```powershell
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
```

## 5. Open the landing page

<http://127.0.0.1:8080/>

## 6. Open the admin console

<http://127.0.0.1:8080/admin> — sign in with the credentials from `.env`.

## 7. Submit a test registration

Use the landing-page form, or from PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8080/api/registrations" `
  -ContentType "application/json" `
  -Body (@{ full_name="Demo Visitor"; email="demo@example.com"; `
            guest_count=2; experience_type="peth-stories-walk"; `
            consent=$true; website="" } | ConvertTo-Json)
```

The response contains a server-generated reference such as `SH-2026-4C9A1B`.

## 8. View it in the admin dashboard

Open `/admin` → the record appears in the table (counts update from the
database; zeros are shown when empty).

## 9. Update the registration status

Click the row → choose a status (Contacted / Waitlisted / Closed) →
**Save status**. Changes are validated server-side and persisted.

### Walk Sessions tab

Switch to **Walk Sessions** in the dashboard to manage the public schedule:

- **New walk session** → fill title, description, date, start time (24h),
  duration (15–480 min), meeting point, optional capacity (1–60) and
  inclusions. Sessions start as **DRAFT** (invisible to visitors).
- **Publish** to make a session appear on the public schedule; **Unpublish**
  returns it to draft; **Cancel** / **Complete** remove it from the public
  view while keeping the history visible in the console.
- Each row shows the live **enquiry count**; open a session to see the
  enquiries linked to it.

Publishing is an administrative act — publish only after the route, date and
meeting point are verified.

## 10. Export the CSV

Use **Export CSV** in the dashboard toolbar (respects search/status
filters), or:

```powershell
curl.exe -s -c cookies.txt -X POST -H "Content-Type: application/json" `
  -d '{\"username\":\"demo-admin\",\"password\":\"YOUR-PASSWORD\"}' `
  http://127.0.0.1:8080/api/admin/login
curl.exe -s -b cookies.txt -o registrations.csv `
  http://127.0.0.1:8080/api/admin/registrations/export.csv
```

## 11. Run the automated tests

```powershell
venv\Scripts\python -m pytest tests -v
```

Tests always run against a temporary per-test SQLite file — the real
`data/sheharnaama.sqlite3` is never touched by tests.

## 12. Back up / restore the database

```powershell
# Backup (while the server is stopped is safest)
Copy-Item data\sheharnaama.sqlite3 D:\backups\sheharnaama-$(Get-Date -Format yyyyMMdd).sqlite3

# Restore
Copy-Item D:\backups\sheharnaama-20261010.sqlite3 data\sheharnaama.sqlite3 -Force
```

The database survives application restarts; nothing is auto-deleted.
To remove a single test record, use the admin console (status CLOSED) or
delete the SQLite file to start empty.

---

## Email policy

Automated emails are **not configured** — no email is sent by this system.
The API response and the admin dashboard both say so explicitly; enquiries
are stored and followed up manually. When a provider is chosen, wire it
into `backend/app/routes/registrations.py` (one call site) and flip
`email_notifications` accordingly.

## Data & demo policy

- The real database (`data/sheharnaama.sqlite3`) starts **empty**.
  No fabricated customers are ever seeded. To delete test submissions:
  delete the file (with the server stopped) or remove rows manually.
- `tests/` uses only temporary per-test databases.
- Do not log or share visitor notes; they are stored solely to help plan a
  comfortable experience.

## Security summary

- Admin auth is server-side: HttpOnly + SameSite=Lax session cookie,
  constant-time credential comparison, login throttling (5 failures →
  10-minute lockout), configurable TTL, Secure cookies in production.
- All admin data endpoints are protected on the server, not by UI hiding.
- Parameterised SQL only; request-size limit; generic error messages
  without stack traces; honeypot + registration throttling.
- Visitor-supplied content is escaped in the admin UI (textContent-only
  rendering) and the CSV export neutralises `=+-@` formula prefixes.
- No payments, no visitor accounts, no real emails unless a provider is
  configured.