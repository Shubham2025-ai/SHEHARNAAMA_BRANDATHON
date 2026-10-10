# Running the Site Offline (venue / no-internet fallback)

The website is fully self-contained: every image, stylesheet and script is a
local file loaded with relative paths, and fonts fall back to system fonts.
No internet connection is required at any point.

## Option 1 — Just open the file (simplest)
1. Open the project folder on the demo laptop.
2. Double-click **`index.html`**.
3. It opens in the default browser via `file://` — everything works:
   navigation, passport flip, gallery lightbox, FAQ, the demo form.

## Option 2 — Local server (nicer URLs, identical behaviour)
If Python is installed:
```powershell
cd <project folder>
python -m http.server 8080
```
Then open `http://localhost:8080`.

If Node is installed:
```powershell
npx serve .
```

## Demo-day checklist (offline)
- [ ] Project folder copied to the demo laptop **and** a USB stick.
- [ ] `index.html` opens and the logo appears (logo file:
      `assets/img/logo_icon.svg`).
- [ ] Fresh private window opened (so old localStorage demo submissions
      don't appear; clear via F12 → Application → Local Storage if needed).
- [ ] Screenshots in `presentation-backup/screenshots/` reviewed once —
      they are the projector-failure fallback.
- [ ] Printed copy of `DEMO_SCRIPT_COPY.md` in hand.

## What degrades gracefully without internet
- Google Fonts → system fallbacks (Georgia / Segoe UI). Layout intact.
- The interest form needs the full-stack backend
  (`venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080` —
  still fully offline-capable: the database and admin console are local).
  If only the static file is opened, the form honestly reports that the
  registration service is unreachable — everything else works.
- No data leaves the machine. Registrations are stored in the local
  SQLite file as expressions of interest only.