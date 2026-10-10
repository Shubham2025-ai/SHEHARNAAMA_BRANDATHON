# SHEHARNAAMA — Demo & Deployment Guide

Practical instructions for running, publishing and verifying the Sheharnaama
landing page for a live Brandathon Round 3 demonstration.

The website is a **pure static site**: one `index.html`, plus `assets/` for
CSS, JavaScript and images. There is **no backend, no build step and no
database**, so it can be hosted free on any static host and also runs
directly from a local folder.

---

## 1. Run the website locally

The landing page + registration API + admin console run together via the
full-stack server (recommended for demos — the form saves to SQLite and the
admin console works):

```powershell
cd D:\SHEHARNAAMA_BRANDATHON
venv\Scripts\pip install -r requirements.txt     # first time only
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
```
Then open: `http://127.0.0.1:8080` and admin at `/admin`.
See `README_FULLSTACK.md` for `.env` setup and the complete walkthrough.

### Option A — Python static server (frontend-only fallback)
```powershell
cd D:\SHEHARNAAMA_BRANDATHON
python -m http.server 8080
```
Then open: `http://localhost:8080`

Stop the server with `Ctrl + C`.

### Option B — Node
```powershell
npx serve .
```
Then open the printed local URL.

### Option C — VS Code Live Server extension
Right-click `index.html` → **Open with Live Server**.

### Option D — No internet at all (offline demo)
Double-click `index.html` — it opens via the `file://` protocol.
Everything works offline because:
- all images, CSS and JS are local files loaded with relative paths;
- the fonts (Playfair Display / Montserrat) fall back to system fonts
  (Georgia / Segoe UI) when Google Fonts is unreachable.

The interest form needs the full-stack server (§ above) to record
registrations; opened statically it honestly reports the service is
unreachable — the rest of the site works fully offline.

---

## 2. Publish the static website (free)

The site's root is `index.html` and every asset uses a relative path
(`assets/...`), so it can be uploaded as-is. Two reliable free options:

### Option A — GitHub Pages (recommended; free, permanent URL)

1. Create a free account at <https://github.com> (if you don't have one).
2. Create a new **public** repository, e.g. `sheharnaama`.
3. Upload the project files:
   - On the repo page click **Add file → Upload files**.
   - Drag in `index.html`, the `assets/` folder (and nothing else is
     required — `tools/` and `presentation-backup/` are optional).
   - Keep the folder structure exactly as-is: `index.html` must sit at the
     repository root, with `assets/` beside it.
   - Commit with **Commit changes**.
4. Enable Pages:
   - **Settings → Pages** (left sidebar).
   - Under **Build and deployment → Source**, choose **Deploy from a branch**.
   - Branch: `main`, folder: `/ (root)`. Click **Save**.
5. Wait 1–3 minutes. The site goes live at:
   `https://<your-username>.github.io/sheharnaama/`
6. Open that URL and confirm the page renders (fonts load, logo appears).

> Note: `og:image` in `index.html` uses a relative path. Social preview
> cards work best with an absolute URL — once you know the final URL,
> change the `<meta property="og:image" ...>` line to
> `https://<your-username>.github.io/sheharnaama/assets/img/og-image.png`.

### Option B — Netlify Drop (fastest, no Git needed)

1. Go to <https://app.netlify.com/drop>.
2. Sign in with a free account (or create one).
3. Drag the **project folder** (the folder containing `index.html` and
   `assets/`) onto the drop zone.
4. Netlify publishes instantly and shows a URL like
   `https://random-name.netlify.app`. Rename it under
   **Site configuration → Change site name** (e.g. `sheharnaama.netlify.app`).
5. Open the URL to confirm it works.

### What NOT to change while publishing
- Do **not** rename `index.html` or move it out of the root.
- Do **not** restructure `assets/` — every path in the code is relative
  (`assets/css/...`, `assets/img/...`, `assets/js/...`).
- No server configuration, environment variables or database are needed.
- Do not add paid services — nothing on this page requires a backend.

### If a genuine booking/contact integration is added later
All integration points live in one file: `assets/js/site.config.js`
(`contactEmail`, `whatsappNumber`, `bookingEndpoint`, `instagramUrl`).
The footer contact area, campaign social button and real form submission
activate automatically once real values are configured. Until then the site
correctly shows unconfigured placeholders and the honest demo form.

---

## 3. Verify the published website

Run through this checklist in a **private/incognito browser window**
(so no cached files or stored demo data from your machine interfere):

Desktop:
- [ ] Page loads with the arch logo and headline; no missing images.
- [ ] Header links scroll to: The Experience, Our Story, Story Passport, FAQ.
- [ ] "Join the First Walk" and hero CTAs scroll to the correct sections.
- [ ] Story Passport "Look inside" flips to the open spread and back.
- [ ] FAQ items expand and collapse.
- [ ] Gallery images enlarge in a lightbox and close again.
- [ ] Footer links all scroll; no dead links.

Mobile (or browser dev-tools at 360–390 px width):
- [ ] Hamburger opens the menu; choosing a link closes it.
- [ ] The menu's "Join the First Walk" button is visible.
- [ ] No horizontal scrolling anywhere on the page.
- [ ] Form fields fit the screen and the keyboard doesn't break layout.

Registration form (server-backed check):
- [ ] Submitting empty shows inline errors for name, email, guests,
      experience and consent.
- [ ] A fake email like `test@x` is rejected with a format message.
- [ ] A valid fictional submission returns a **server-generated reference**
      (e.g. `SH-2026-4C9A1B`) with wording that states it is an
      **expression of interest, not a confirmed tour booking** — never a
      "booking confirmed" claim.
- [ ] If the backend is not running, the form says the registration service
      is unreachable and nothing was saved — no fake success.

---

## 4. Keep an offline backup

Before travelling to the venue:

1. Copy the entire project folder to a USB stick **and** to a second device.
2. In the browser, after a demo submission, clear
   `localStorage` (F12 → Application → Local Storage) if you want a clean
   slate for the judges' run-through.
3. `presentation-backup/` contains full-page screenshots of desktop and
   mobile plus a printed copy of the demo script — usable if the laptop
   or projector fails entirely.
4. Host the published public URL as a last-resort fallback if the demo
   laptop dies.

---

## 5. What was verified before writing this guide

Re-ran on the current workspace (all passing):
- HTML well-formedness, anchor targets, aria targets, CSS/JS syntax checks.
- All 30 pages/assets served with HTTP 200 from the local server.
- 20-point automated interaction test (menu, passport flip, lightbox, form
  validation paths, honest demo message, localStorage demo record, FAQ,
  anchors) — 20/20 PASS.
- Horizontal-overflow scan at 360 / 390 / 768 / 1024 / 1280 / 1920 px — OK.

No public URL has been published from this workspace yet — follow §2 above;
once live, add the confirmed URL here: `_____________________`.