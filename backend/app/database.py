"""SQLite persistence layer.

- One connection per request (safe, simple, no shared mutable state).
- Parameterised statements everywhere.
- The database file lives in `data/` by default, which is NOT publicly
  served and is listed in .gitignore.
- Schema is versioned; `init_db` is idempotent and never deletes rows, so
  registrations survive application restarts.
"""

import os
import sqlite3
import threading
from contextlib import contextmanager

from . import config

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS walk_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    description      TEXT NOT NULL,
    walk_date        TEXT NOT NULL,
    start_time       TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes BETWEEN 15 AND 480),
    meeting_point    TEXT NOT NULL,
    capacity         INTEGER CHECK (capacity IS NULL OR (capacity BETWEEN 1 AND 60)),
    inclusions       TEXT,
    status           TEXT NOT NULL DEFAULT 'DRAFT'
                     CHECK (status IN ('DRAFT', 'PUBLISHED', 'CANCELLED', 'COMPLETED')),
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_walk_sessions_status ON walk_sessions (status);
CREATE INDEX IF NOT EXISTS idx_walk_sessions_date   ON walk_sessions (walk_date);

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS registrations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    public_reference TEXT NOT NULL UNIQUE,
    full_name        TEXT NOT NULL,
    email            TEXT NOT NULL,
    preferred_date   TEXT,
    guest_count      INTEGER NOT NULL CHECK (guest_count BETWEEN 1 AND 12),
    experience_type  TEXT NOT NULL CHECK (experience_type IN ('peth-stories-walk', 'private-group')),
    notes            TEXT,
    consent          INTEGER NOT NULL CHECK (consent = 1),
    status           TEXT NOT NULL DEFAULT 'INTEREST_RECEIVED'
                     CHECK (status IN ('INTEREST_RECEIVED', 'CONTACTED', 'WAITLISTED', 'CLOSED')),
    idempotency_key  TEXT UNIQUE,
    session_id       INTEGER REFERENCES walk_sessions (id),
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_registrations_email   ON registrations (email);
CREATE INDEX IF NOT EXISTS idx_registrations_status  ON registrations (status);
CREATE INDEX IF NOT EXISTS idx_registrations_created ON registrations (created_at DESC);
"""

_init_lock = threading.Lock()
_initialised = False


def _migrate(conn: sqlite3.Connection) -> None:
    """Incremental migrations for databases created before schema v2.

    v1 -> v2: registrations.session_id column (existing rows are preserved).
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(registrations)")}
    if columns and "session_id" not in columns:
        conn.execute(
            "ALTER TABLE registrations ADD COLUMN session_id INTEGER REFERENCES walk_sessions (id)"
        )
    # Safe in both orders: the column exists after a fresh install or the
    # migration above, so the index can always be created here.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_registrations_session ON registrations (session_id)"
    )


def init_db(db_path: str | None = None) -> None:
    """Create the database file and schema if needed. Idempotent.

    Existing registrations are never deleted; older databases are migrated
    in place to the current schema version.
    """
    global _initialised
    path = db_path or config.DB_PATH
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with _init_lock:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(_SCHEMA)
            _migrate(conn)
            conn.execute(
                "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(SCHEMA_VERSION),),
            )
            conn.commit()
        finally:
            conn.close()
        _initialised = True


def _ensure_initialised() -> None:
    if not _initialised:
        init_db()


@contextmanager
def get_connection():
    """Yield a short-lived SQLite connection with commit/rollback handling."""
    _ensure_initialised()
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()