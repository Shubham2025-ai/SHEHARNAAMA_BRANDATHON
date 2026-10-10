"""Admin session management.

- Signed-in state is a random session id stored in an HttpOnly, SameSite=Lax
  cookie; the server keeps an in-memory session table with expiry.
- Credentials come from environment variables and are compared in constant
  time. No visitor accounts exist, so no visitor passwords are stored.
- Logout deletes the session id, invalidating the cookie server-side.
"""

import secrets
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import HTTPException, Request, Response

from . import config

SESSION_COOKIE = "sheharnaama_admin"
SESSION_TTL_SECONDS = config.SESSION_TTL_MINUTES * 60

_sessions: dict[str, float] = {}
_login_failures: dict[str, deque] = defaultdict(lambda: deque(maxlen=config.LOGIN_MAX_FAILURES))


def _prune_sessions() -> None:
    now = time.time()
    for sid in [s for s, exp in _sessions.items() if exp <= now]:
        _sessions.pop(sid, None)


def check_login_allowed(ip: str) -> None:
    """Reject IPs with too many recent failed logins."""
    window = config.LOGIN_LOCKOUT_MINUTES * 60
    now = time.time()
    attempts = _login_failures[ip]
    while attempts and now - attempts[0] > window:
        attempts.popleft()
    if len(attempts) >= config.LOGIN_MAX_FAILURES:
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Please wait a few minutes and try again.",
        )


def record_login_failure(ip: str) -> None:
    _login_failures[ip].append(time.time())


def clear_login_failures(ip: str) -> None:
    _login_failures.pop(ip, None)


def create_session(response: Response) -> None:
    _prune_sessions()
    sid = secrets.token_urlsafe(32)
    _sessions[sid] = time.time() + SESSION_TTL_SECONDS
    response.set_cookie(
        key=SESSION_COOKIE,
        value=sid,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=config.SECURE_COOKIES,
        path="/",
    )


def destroy_session(request: Request) -> None:
    sid: Optional[str] = request.cookies.get(SESSION_COOKIE)
    if sid:
        _sessions.pop(sid, None)


def require_admin(request: Request) -> str:
    """FastAPI dependency protecting every admin data endpoint."""
    if not config.admin_credentials_configured():
        raise HTTPException(status_code=503, detail=config.SETUP_REQUIRED_MESSAGE)
    _prune_sessions()
    sid: Optional[str] = request.cookies.get(SESSION_COOKIE)
    if not sid or sid not in _sessions:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return config.ADMIN_USERNAME


def reset_all_sessions() -> None:
    """Test helper — clears in-memory state between tests."""
    _sessions.clear()
    _login_failures.clear()