"""Sheharnaama — FastAPI application entrypoint.

Serves the existing static frontend and the JSON API on the same origin:
  GET  /                     → index.html (landing page)
  GET  /admin                → admin.html (protected admin UI)
  *    /assets/*             → static assets
  POST /api/registrations    → public interest registration
  /api/admin/*               → server-authenticated admin API
  GET  /api/health           → health check

Run from the project root:
  python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
"""

from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # reads a local .env at the project root when present

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, database
from .routes import admin as admin_routes
from .routes import registrations as registrations_routes

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.init_db()
    yield


app = FastAPI(
    title="Sheharnaama API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,  # keep the public surface minimal for a demo
    lifespan=lifespan,
)


# ---------- API routes ----------

app.include_router(registrations_routes.router)
app.include_router(admin_routes.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ---------- Validation error shaping ----------

@app.exception_handler(RequestValidationError)
def shape_validation_errors(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = []
    for error in exc.errors():
        loc = [part for part in error.get("loc", []) if isinstance(part, str)]
        fields.append(
            {
                "field": loc[-1] if loc else "form",
                "message": error.get("msg", "Invalid value."),
            }
        )
    return JSONResponse(status_code=422, content={"detail": fields})


# ---------- Request hygiene ----------

@app.middleware("http")
async def hygiene_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > config.MAX_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request too large."})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


# ---------- Existing static frontend (same origin) ----------

@app.get("/", include_in_schema=False)
def landing() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "index.html", media_type="text/html")


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "admin.html", media_type="text/html")


@app.get("/sample-story", include_in_schema=False)
@app.get("/sample-story.html", include_in_schema=False)
def sample_story_page() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "sample-story.html", media_type="text/html")


app.mount(
    "/assets",
    StaticFiles(directory=str(PROJECT_ROOT / "assets")),
    name="assets",
)


@app.exception_handler(404)
def not_found(request: Request, exc) -> JSONResponse:
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found."})
    return FileResponse(PROJECT_ROOT / "index.html", status_code=404, media_type="text/html")