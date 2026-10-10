"""Public registration API.

POST /api/registrations — receives the landing-page interest form.
"""

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Header, HTTPException, Request

from .. import config, models
from ..schemas import RegistrationCreate

router = APIRouter(prefix="/api", tags=["registrations"])

_submission_times: dict[str, deque] = defaultdict(lambda: deque(maxlen=60))


def _check_registration_rate(ip: str) -> None:
    window = 60.0
    now = time.time()
    stamps = _submission_times[ip]
    while stamps and now - stamps[0] > window:
        stamps.popleft()
    if len(stamps) >= config.REGISTRATION_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Too many submissions from this connection. Please wait a minute and try again.",
        )
    stamps.append(now)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/sessions")
def list_public_sessions() -> dict:
    """Published, upcoming walk sessions only. Reveals visitor-facing
    fields; nothing internal (no created/updated timestamps, no drafts,
    no cancelled or past sessions)."""
    try:
        sessions = models.public_sessions()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Upcoming walks could not be loaded. Please refresh to retry.",
        )
    return {"items": sessions}


@router.post("/registrations", status_code=201)
def create_registration(
    payload: RegistrationCreate,
    request: Request,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> dict:
    if not payload.consent:
        # Belts-and-braces: the schema also rejects missing consent.
        raise HTTPException(status_code=422, detail="Consent is required to register interest.")

    # Honeypot: real visitors never fill the hidden "website" field.
    if payload.website:
        raise HTTPException(
            status_code=400,
            detail="Registration could not be accepted. Please try again without automated tooling.",
        )

    key: str | None = None
    if x_idempotency_key:
        key = x_idempotency_key.strip()
        if not (8 <= len(key) <= 64):
            raise HTTPException(status_code=400, detail="Invalid idempotency key length.")

    # Optional session association: must exist, be PUBLISHED and upcoming.
    session = None
    if payload.session_id is not None:
        try:
            session = models.get_session(payload.session_id)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="We could not save your registration just now. Please try again in a moment.",
            )
        if session is None or not models.session_eligible_for_interest(session):
            raise HTTPException(
                status_code=422,
                detail=[{
                    "field": "session_id",
                    "message": "This walk session is not open for interest. Please choose another session or register general interest.",
                }],
            )

    _check_registration_rate(_client_ip(request))

    try:
        result = models.create_registration(
            full_name=payload.full_name,
            email=payload.email,
            preferred_date=payload.preferred_date,
            guest_count=payload.guest_count,
            experience_type=payload.experience_type,
            notes=payload.notes,
            idempotency_key=key,
            session_id=payload.session_id,
        )
    except Exception:
        # Honest failure — never pretend the registration was saved.
        raise HTTPException(
            status_code=500,
            detail="We could not save your registration just now. Please try again in a moment.",
        )

    record = result["record"]
    return {
        "ok": True,
        "reference": record["public_reference"],
        "status": record["status"],
        "idempotent": result["idempotent"],
        "email_notifications": "not_configured",
        "session": (
            {
                "id": session["id"],
                "title": session["title"],
                "walk_date": session["walk_date"],
                "start_time": session["start_time"],
                "meeting_point": session["meeting_point"],
            }
            if session
            else None
        ),
        "message": "Interest received — this is an expression of interest, not a confirmed booking.",
    }