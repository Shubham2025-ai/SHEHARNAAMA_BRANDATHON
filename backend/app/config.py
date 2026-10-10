"""Central configuration.

All secrets and deployment-specific values come from environment variables
(loaded from a local `.env` file when present).  Nothing sensitive is
hardcoded or shipped in client code.

Security policy for admin credentials:
- ADMIN_USERNAME and ADMIN_PASSWORD (or ADMIN_PASSWORD_HASH) must be set,
  otherwise admin endpoints return a clear 503 "setup required" error
  instead of silently allowing public access.
- Well-known default/weak passwords are rejected as insecure.
"""

import hashlib
import hmac
import os

from dotenv import load_dotenv

load_dotenv()


def _clean(name: str) -> str:
    return (os.getenv(name) or "").strip()


ENVIRONMENT: str = _clean("ENVIRONMENT") or "development"
DB_PATH: str = _clean("SHEHARNAAMA_DB_PATH") or os.path.join("data", "sheharnaama.sqlite3")

ADMIN_USERNAME: str = _clean("ADMIN_USERNAME")
ADMIN_PASSWORD: str = _clean("ADMIN_PASSWORD")
ADMIN_PASSWORD_HASH: str = _clean("ADMIN_PASSWORD_HASH").lower()

SESSION_SECRET: str = _clean("SESSION_SECRET")  # optional; ephemeral fallback if unset
SESSION_TTL_MINUTES: int = int(_clean("SESSION_TTL_MINUTES") or "120")
SECURE_COOKIES: bool = (
    _clean("SECURE_COOKIES") or ("true" if ENVIRONMENT == "production" else "false")
).lower() == "true"

REGISTRATION_RATE_LIMIT_PER_MINUTE: int = int(_clean("REGISTRATION_RATE_LIMIT") or "10")
LOGIN_MAX_FAILURES: int = 5
LOGIN_LOCKOUT_MINUTES: int = 10

MAX_BODY_BYTES: int = 32_000

SETUP_REQUIRED_MESSAGE = (
    "Admin access is not configured on this server. "
    "Set ADMIN_USERNAME and ADMIN_PASSWORD (or ADMIN_PASSWORD_HASH) in your "
    ".env file and restart the server. See .env.example."
)

_INSECURE_PASSWORDS = {
    "admin",
    "password",
    "admin123",
    "12345678",
    "change-me-strong-password",
    "sheharnaama",
}


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def admin_credentials_configured() -> bool:
    """True only when a usable, non-default credential pair is configured."""
    if not ADMIN_USERNAME or len(ADMIN_USERNAME) < 3:
        return False
    if ADMIN_PASSWORD_HASH:
        return len(ADMIN_PASSWORD_HASH) == 64
    if not ADMIN_PASSWORD:
        return False
    if len(ADMIN_PASSWORD) < 8 or ADMIN_PASSWORD.lower() in _INSECURE_PASSWORDS:
        return False
    return True


def admin_username_matches(provided: str) -> bool:
    if not admin_credentials_configured():
        return False
    return hmac.compare_digest(provided.encode("utf-8"), ADMIN_USERNAME.encode("utf-8"))


def admin_password_matches(provided: str) -> bool:
    if not admin_credentials_configured():
        return False
    if ADMIN_PASSWORD_HASH:
        expected = ADMIN_PASSWORD_HASH
    else:
        expected = _sha256_hex(ADMIN_PASSWORD)
    return hmac.compare_digest(_sha256_hex(provided), expected)