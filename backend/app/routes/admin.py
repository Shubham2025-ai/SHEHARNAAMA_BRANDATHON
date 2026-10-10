"""Admin authentication and registration-management endpoints.

Every data endpoint depends on auth.require_admin, so protection happens on
the server. If credentials are not configured, endpoints return 503 with a
clear setup message rather than open access.
"""

import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from .. import auth, config, models
from ..schemas import (
    LoginRequest,
    SessionCreate,
    SessionStatusUpdate,
    SessionUpdate,
    StatusUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

_CSV_COLUMNS = [
    ("public_reference", "Reference"),
    ("full_name", "Name"),
    ("email", "Email"),
    ("experience_type", "Experience"),
    ("session_title", "Session"),
    ("preferred_date", "Preferred date"),
    ("guest_count", "Guests"),
    ("status", "Status"),
    ("created_at", "Submitted (UTC)"),
    ("updated_at", "Updated (UTC)"),
    ("notes", "Notes"),
]


def _csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection (=, +, -, @ prefixes)."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@"):
        text = "'" + text
    return text


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    if not config.admin_credentials_configured():
        raise HTTPException(status_code=503, detail=config.SETUP_REQUIRED_MESSAGE)

    ip = request.client.host if request.client else "unknown"
    auth.check_login_allowed(ip)

    username_ok = config.admin_username_matches(payload.username.strip())
    password_ok = config.admin_password_matches(payload.password)
    if not (username_ok and password_ok):
        auth.record_login_failure(ip)
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    auth.clear_login_failures(ip)
    auth.create_session(response)
    return {"ok": True, "username": config.ADMIN_USERNAME}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    auth.destroy_session(request)
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(admin: str = Depends(auth.require_admin)) -> dict:
    return {
        "username": admin,
        "email_notifications": "not_configured",
    }


@router.get("/stats")
def stats(admin: str = Depends(auth.require_admin)) -> dict:
    return models.registration_counts()


@router.get("/registrations")
def list_registrations(
    admin: str = Depends(auth.require_admin),
    q: Optional[str] = Query(default=None, max_length=120),
    status: Optional[str] = Query(default=None),
    session_id: Optional[int] = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1, le=10_000),
    per_page: int = Query(default=25, ge=1, le=100),
) -> dict:
    if status is not None and status not in models.STATUS_VALUES:
        raise HTTPException(status_code=422, detail="Unknown registration status filter.")
    return models.list_registrations(
        query=q, status=status, session_id=session_id, page=page, per_page=per_page
    )


@router.get("/registrations/export.csv")
def export_csv(
    admin: str = Depends(auth.require_admin),
    q: Optional[str] = Query(default=None, max_length=120),
    status: Optional[str] = Query(default=None),
) -> StreamingResponse:
    if status is not None and status not in models.STATUS_VALUES:
        raise HTTPException(status_code=422, detail="Unknown registration status filter.")
    rows = models.export_rows(query=q, status=status)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow([label for _, label in _CSV_COLUMNS])
    for row in rows:
        writer.writerow([_csv_safe(row.get(key)) for key, _ in _CSV_COLUMNS])
    buffer.seek(0)

    filename = datetime.now(timezone.utc).strftime("sheharnaama-registrations-%Y%m%d.csv")
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/registrations/{registration_id}")
def registration_detail(
    registration_id: int, admin: str = Depends(auth.require_admin)
) -> dict:
    record = models.get_registration(registration_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Registration not found.")
    return record


@router.patch("/registrations/{registration_id}/status")
def update_status(
    registration_id: int,
    payload: StatusUpdate,
    admin: str = Depends(auth.require_admin),
) -> dict:
    if payload.status not in models.STATUS_VALUES:
        raise HTTPException(status_code=422, detail="Unknown registration status.")
    record = models.update_status(registration_id, payload.status)
    if record is None:
        raise HTTPException(status_code=404, detail="Registration not found.")
    return record


# --------------------------------------------------------------------------
# Walk sessions (all endpoints require admin authentication)
# --------------------------------------------------------------------------


@router.post("/sessions", status_code=201)
def create_session(payload: SessionCreate, admin: str = Depends(auth.require_admin)) -> dict:
    try:
        return models.create_session(
            title=payload.title,
            description=payload.description,
            walk_date=payload.walk_date,
            start_time=payload.start_time,
            duration_minutes=payload.duration_minutes,
            meeting_point=payload.meeting_point,
            capacity=payload.capacity,
            inclusions=payload.inclusions,
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The session could not be saved. Please try again in a moment.",
        )


@router.get("/sessions/stats")
def session_stats(admin: str = Depends(auth.require_admin)) -> dict:
    return models.session_counts()


@router.get("/sessions")
def list_sessions(
    admin: str = Depends(auth.require_admin),
    q: Optional[str] = Query(default=None, max_length=120),
    status: Optional[str] = Query(default=None),
) -> dict:
    if status is not None and status not in models.SESSION_STATUS_VALUES:
        raise HTTPException(status_code=422, detail="Unknown session status filter.")
    return {"items": models.list_sessions(query=q, status=status)}


@router.get("/sessions/{session_id}")
def session_detail(session_id: int, admin: str = Depends(auth.require_admin)) -> dict:
    session = models.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Walk session not found.")
    enquiries = models.list_registrations(
        session_id=session_id, page=1, per_page=100
    )
    return {"session": session, "enquiries": enquiries}


@router.patch("/sessions/{session_id}")
def update_session(
    session_id: int,
    payload: SessionUpdate,
    admin: str = Depends(auth.require_admin),
) -> dict:
    try:
        record = models.update_session(
            session_id,
            title=payload.title,
            description=payload.description,
            walk_date=payload.walk_date,
            start_time=payload.start_time,
            duration_minutes=payload.duration_minutes,
            meeting_point=payload.meeting_point,
            capacity=payload.capacity,
            inclusions=payload.inclusions,
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The session could not be updated. Please try again in a moment.",
        )
    if record is None:
        raise HTTPException(status_code=404, detail="Walk session not found.")
    return record


@router.patch("/sessions/{session_id}/status")
def update_session_status(
    session_id: int,
    payload: SessionStatusUpdate,
    admin: str = Depends(auth.require_admin),
) -> dict:
    record = models.set_session_status(session_id, payload.status)
    if record is None:
        raise HTTPException(status_code=404, detail="Walk session not found.")
    return record